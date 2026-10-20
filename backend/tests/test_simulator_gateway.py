import asyncio
from contextlib import asynccontextmanager
import importlib
from pathlib import Path
import socket
import sqlite3

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from app.api.app import create_app
from app.application import VoltWiseApplication
from app.config import Settings
from app.mcp.http import create_mcp_http_app
from app.models import FaultMode
from app.services.simulator_gateway import route_simulator_message


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@asynccontextmanager
async def real_gateway_stack(tmp_path: Path):
    port = available_port()
    settings = Settings(
        database_path=tmp_path / "gateway.db",
        mcp_port=port,
        mcp_url=f"http://127.0.0.1:{port}/mcp",
        mcp_allowed_hosts=("127.0.0.1:*",),
    )
    application = VoltWiseApplication(settings)
    mcp_server_module = importlib.import_module("app.mcp.server")
    original_application = mcp_server_module.application
    mcp_server_module.application = application
    server = uvicorn.Server(
        uvicorn.Config(
            create_mcp_http_app(settings),
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
    )
    server_task = asyncio.create_task(server.serve())
    try:
        for _ in range(200):
            if server.started:
                break
            if server_task.done():
                await server_task
            await asyncio.sleep(0.01)
        else:
            raise RuntimeError("Timed out starting MCP server")
        api = create_app(application, settings=settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://api.test"
        ) as client:
            yield client, settings
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=5)
        mcp_server_module.application = original_application


async def negotiated_protocol(url: str) -> str:
    async with streamable_http_client(url) as streams:
        async with ClientSession(*streams) as session:
            return (await session.initialize()).protocol_version


def test_energy_chat_crosses_real_mcp_and_persists_trace(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with real_gateway_stack(tmp_path) as (client, settings):
            actual_protocol = await negotiated_protocol(settings.mcp_url)
            response = await client.post(
                "/api/sim/chat", json={"message": "How are we doing this month?"}
            )

            assert response.status_code == 200
            payload = response.json()
            assert payload["intent"] == "ENERGY_COMPARISON"
            assert payload["tool_call"] == {
                "name": "power_compare_periods",
                "arguments": {},
            }
            assert payload["result"]["current_kwh"] == 142.0
            assert payload["result"]["previous_equivalent_kwh"] == 118.0
            assert payload["result"]["change_percent"] == 20.34
            assert payload["result"]["projection"]["projected_kwh"] == 304.29

            traces = (await client.get("/api/sim/traces")).json()
            assert len(traces) == 1
            trace = traces[0]
            assert trace["trace_id"] == payload["trace_id"]
            assert trace["transport"] == "STREAMABLE_HTTP"
            assert trace["protocol_version"] == actual_protocol
            assert trace["tool_name"] == "power_compare_periods"
            assert trace["tool_arguments"] == {}
            assert trace["success"] is True
            assert trace["duration_ms"] >= 0
            assert "142 kilowatt-hours" in trace["result_summary"]

            with sqlite3.connect(settings.database_path) as connection:
                stored = connection.execute(
                    """
                    SELECT transport, tool_name, tool_arguments_json, success,
                           duration_ms, result_summary, protocol_version
                    FROM mcp_traces WHERE trace_id = ?
                    """,
                    (payload["trace_id"],),
                ).fetchone()
            assert stored is not None
            assert stored[0:4] == ("STREAMABLE_HTTP", "power_compare_periods", "{}", 1)
            assert stored[4] >= 0
            assert "142 kilowatt-hours" in stored[5]
            assert stored[6] == actual_protocol

    asyncio.run(exercise())


def test_device_control_crosses_real_mcp_and_persists_trace(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with real_gateway_stack(tmp_path) as (client, settings):
            response = await client.post(
                "/api/sim/chat", json={"message": "Turn on the living room light"}
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["intent"] == "CONTROL_DEVICE"
            assert payload["tool_call"] == {
                "name": "power_control_device",
                "arguments": {"device": "light", "command": "TURN_ON"},
            }
            assert payload["result"]["device"] == "light"
            assert payload["result"]["reported_state"] == "ON"
            assert payload["result"]["success"] is True

            traces = (await client.get("/api/sim/traces")).json()
            assert len(traces) == 1
            assert traces[0]["tool_name"] == "power_control_device"
            assert traces[0]["success"] is True

    asyncio.run(exercise())


def test_no_draw_diagnostic_crosses_gateway_and_real_mcp(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with real_gateway_stack(tmp_path) as (client, _):
            injected = await client.post(
                "/api/demo/device-fault",
                json={"device": "heater", "fault": "NO_DRAW"},
            )
            assert injected.json()["heater_fault"] == "NO_DRAW"
            try:
                response = await client.post(
                    "/api/sim/chat", json={"message": "Diagnose the heater"}
                )
                assert response.status_code == 200
                payload = response.json()
                assert payload["tool_call"]["name"] == "power_run_diagnostic"
                assert payload["tool_call"]["arguments"] == {"device": "heater"}
                assert payload["result"]["final_status"] == "UNRESOLVED"
                assert payload["result"]["diagnostic_classification"] == (
                    "NO_ELECTRICAL_RESPONSE"
                )
                assert payload["result"]["retries_used"] == 1
                trace = (await client.get("/api/sim/traces?limit=1")).json()[0]
                assert trace["tool_name"] == "power_run_diagnostic"
                assert trace["success"] is True
            finally:
                reset = await client.post("/api/demo/reset")
                assert reset.json()["heater_fault"] == "NONE"

    asyncio.run(exercise())


def test_mcp_unavailable_returns_controlled_error_without_fallback(tmp_path: Path) -> None:
    async def exercise() -> None:
        unavailable_port = available_port()
        settings = Settings(
            database_path=tmp_path / "unavailable.db",
            mcp_url=f"http://127.0.0.1:{unavailable_port}/mcp",
            mcp_client_timeout_seconds=0.5,
        )
        application = VoltWiseApplication(settings)
        api = create_app(application, settings=settings)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://api.test"
        ) as client:
            response = await client.post(
                "/api/sim/chat", json={"message": "How are we doing this month?"}
            )
            assert response.status_code == 503
            assert response.json() == {
                "error": {
                    "code": "MCP_SERVICE_UNAVAILABLE",
                    "message": "VoltWise's MCP service is temporarily unavailable. Check that the MCP server is running and try again.",
                }
            }
            traces = (await client.get("/api/sim/traces")).json()
            assert len(traces) == 1
            assert traces[0]["success"] is False
            assert traces[0]["result_summary"] == "MCP request failed."
            assert application.recent_events() == ()

    asyncio.run(exercise())


def test_mcp_process_adopts_demo_state_persisted_by_rest_process(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "shared-state.db")
    rest_application = VoltWiseApplication(settings)
    mcp_application = VoltWiseApplication(settings)

    rest_application.set_device_fault("heater", FaultMode.NO_DRAW)
    assert mcp_application.connector.heater_fault.value == "NONE"

    mcp_application.refresh_persisted_demo_state()

    assert mcp_application.connector.heater_fault.value == "NO_DRAW"


def test_mcp_process_adopts_reset_even_when_selections_are_unchanged(
    tmp_path: Path,
) -> None:
    settings = Settings(database_path=tmp_path / "shared-reset.db")
    rest_application = VoltWiseApplication(settings)
    mcp_application = VoltWiseApplication(settings)
    mcp_application.control_device("light", "TURN_ON")
    mcp_application.turn_on_and_verify("heater")

    rest_application.reset_demo()
    mcp_application.refresh_persisted_demo_state()

    assert mcp_application.connector.get_ordinary_state("light").value == "OFF"
    assert mcp_application.connector.get_reported_state("heater").value == "OFF"
    assert mcp_application.connector.get_actual_state("heater").value == "OFF"
    assert mcp_application.connector.read_power("heater", sample="reset").watts == 2.0
    assert mcp_application.demo_state().energy_scenario.value == "NORMAL_CURRENT_CYCLE"
    assert mcp_application.demo_state().heater_fault.value == "NONE"


@pytest.mark.parametrize(
    ("message", "intent", "tool", "arguments"),
    [
        ("Compare this cycle", "ENERGY_COMPARISON", "power_compare_periods", {}),
        ("What changed?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("Alexa, what's causing my electricity usage to increase?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("Why is my electricity bill going up?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("What's using more electricity?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("Why did my energy usage increase?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("Which appliance is contributing most to my energy increase?", "USAGE_EXPLANATION", "power_explain_usage_change", {}),
        ("Alexa, turn on the living room light", "CONTROL_DEVICE", "power_control_device", {"device": "light", "command": "TURN_ON"}),
        ("Where are we on the tariff?", "TARIFF_STATUS", "power_get_tariff_status", {}),
        ("Forecast my bill", "BILL_FORECAST", "power_forecast_bill", {}),
        ("What should we do?", "SUGGESTIONS", "power_suggest_actions", {}),
        ("Can we stay under 300 kWh?", "TARGET_300", "power_suggest_actions", {"target_kwh": 300.0}),
        ("Turn the heater on", "VERIFY_HEATER", "power_turn_on_and_verify", {"device": "heater"}),
        ("Check what's wrong with the heater", "DIAGNOSE_HEATER", "power_run_diagnostic", {"device": "heater"}),
        ("Turn on the living room light", "CONTROL_DEVICE", "power_control_device", {"device": "light", "command": "TURN_ON"}),
        ("Turn on the fan", "CONTROL_DEVICE", "power_control_device", {"device": "fan", "command": "TURN_ON"}),
        ("Turn on the TV", "CONTROL_DEVICE", "power_control_device", {"device": "tv", "command": "TURN_ON"}),
        ("Turn on the AC", "CONTROL_DEVICE", "power_control_device", {"device": "ac", "command": "TURN_ON"}),
        ("Turn off the light", "CONTROL_DEVICE", "power_control_device", {"device": "light", "command": "TURN_OFF"}),
    ],
)
def test_deterministic_router_only_selects_tools(
    message: str,
    intent: str,
    tool: str,
    arguments: dict[str, object],
) -> None:
    routed = route_simulator_message(message)
    assert routed.intent == intent
    assert routed.name == tool
    assert routed.arguments == arguments


def test_natural_language_energy_question_returns_honest_conversational_explanation(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        async with real_gateway_stack(tmp_path) as (client, settings):
            response = await client.post(
                "/api/sim/chat",
                json={"message": "Alexa, what's causing my electricity usage to increase?"},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["intent"] == "USAGE_EXPLANATION"
            assert payload["tool_call"] == {
                "name": "power_explain_usage_change",
                "arguments": {},
            }
            result = payload["result"]
            assert result["household_change_kwh"] == 24.0
            assert result["current_kwh"] == 142.0
            assert result["previous_equivalent_kwh"] == 118.0
            assert result["known_contribution_kwh"] == 19.35
            assert result["unattributed_kwh"] == 4.65

            ac = result["contributors"][0]
            assert ac["device_id"] == "ac"
            assert "Air Conditioner" in ac["device"]
            assert ac["energy_impact_kwh"] == 15.75
            assert ac["energy_impact_type"] == "ESTIMATED"

            msg = payload["message"]
            assert "24 kilowatt-hours" in msg
            assert "142 kWh vs 118 kWh" in msg
            assert "Longer AC runtime is one identified contributor" in msg
            assert "estimated 15.75 kilowatt-hours" in msg
            assert "Other monitored appliances account for 3.60 kilowatt-hours" in msg
            assert "4.65 kilowatt-hours remains unattributed" in msg
            assert "available data does not fully explain the increase" in msg
            assert "wouldn't attribute all of it to the AC" in msg

            traces = (await client.get("/api/sim/traces")).json()
            assert len(traces) == 1
            assert traces[0]["tool_name"] == "power_explain_usage_change"
            assert traces[0]["result_summary"] == msg

    asyncio.run(exercise())


def test_bill_question_distinguishes_energy_from_billing_cost(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with real_gateway_stack(tmp_path) as (client, _):
            response = await client.post(
                "/api/sim/chat",
                json={"message": "Why is my electricity bill going up?"},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["intent"] == "USAGE_EXPLANATION"
            msg = payload["message"]
            assert "energy consumption rather than a confirmed utility bill change" in msg
            assert "24 kilowatt-hours" in msg
            assert "estimated 15.75 kilowatt-hours" in msg

    asyncio.run(exercise())


def test_unsupported_intent_is_distinct_from_mcp_unavailable() -> None:
    with pytest.raises(Exception) as raised:
        route_simulator_message("Will it rain tomorrow?")
    assert getattr(raised.value, "code", None) == "UNSUPPORTED_SIMULATION_INTENT"
