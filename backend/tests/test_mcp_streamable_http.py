import asyncio
from contextlib import asynccontextmanager
import socket

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
import pytest
import uvicorn

from app.config import Settings
from app.application import VoltWiseApplication
from app.connectors import SimulatedDeviceConnector
from app.mcp.http import create_mcp_http_app
from app.mcp.server import application
from app.models import FaultMode
from app.services import DiagnosticWorkflowService, VerificationService


EXPECTED_TOOLS = {
    "power_control_device",
    "power_turn_on_and_verify",
    "power_run_diagnostic",
    "power_compare_periods",
    "power_explain_usage_change",
    "power_get_tariff_status",
    "power_forecast_bill",
    "power_estimate_load_impact",
    "power_suggest_actions",
}


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@asynccontextmanager
async def running_mcp_server(
    *,
    token: str | None = None,
    max_request_body_size: int = 1_048_576,
    bound_application: VoltWiseApplication | None = None,
):
    port = available_port()
    settings = Settings(
        mcp_port=port,
        mcp_bearer_token=token,
        mcp_allowed_hosts=("127.0.0.1:*",),
        mcp_allowed_origins=("http://127.0.0.1:*",),
        mcp_max_request_body_size=max_request_body_size,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_mcp_http_app(settings, bound_application),
            host="127.0.0.1",
            port=port,
            log_level="error",
        )
    )
    task = asyncio.create_task(server.serve())
    try:
        for _ in range(200):
            if server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.01)
        else:
            raise RuntimeError("Timed out starting the Streamable HTTP test server")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=5)


@asynccontextmanager
async def official_session(url: str, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with httpx2.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(url, http_client=http_client) as streams:
            async with ClientSession(*streams) as session:
                initialized = await session.initialize()
                yield session, initialized


def test_real_streamable_http_client_lists_and_calls_tools() -> None:
    async def exercise() -> None:
        application.reset_demo()
        async with running_mcp_server() as url:
            async with official_session(url) as (session, initialized):
                assert initialized.protocol_version == "2025-11-25"
                listed = await session.list_tools()
                assert {tool.name for tool in listed.tools} == EXPECTED_TOOLS

                comparison = await session.call_tool("power_compare_periods", {})
                assert comparison.structured_content is not None
                assert comparison.structured_content["current_kwh"] == 142.0
                assert comparison.structured_content["previous_equivalent_kwh"] == 118.0
                assert comparison.structured_content["projection"]["method"] == "RUN_RATE"

                diagnostic = await session.call_tool(
                    "power_run_diagnostic", {"device": "heater"}
                )
                assert diagnostic.structured_content is not None
                assert diagnostic.structured_content["final_status"] == "VERIFIED"
                assert diagnostic.structured_content["diagnostic_classification"] == "OK"

    asyncio.run(exercise())


def test_real_streamable_http_returns_no_draw_failure() -> None:
    async def exercise() -> None:
        application.set_device_fault("heater", FaultMode.NO_DRAW)
        try:
            async with running_mcp_server() as url:
                async with official_session(url) as (session, _):
                    result = await session.call_tool(
                        "power_run_diagnostic", {"device": "heater"}
                    )
                    assert result.structured_content is not None
                    assert result.structured_content["final_status"] == "UNRESOLVED"
                    assert result.structured_content["diagnostic_classification"] == (
                        "NO_ELECTRICAL_RESPONSE"
                    )
                    assert result.structured_content["retries_used"] == 1
        finally:
            application.reset_demo()

    asyncio.run(exercise())


def test_real_streamable_http_direct_high_draw_cuts_power() -> None:
    async def exercise() -> None:
        application.set_device_fault("heater", FaultMode.HIGH_DRAW)
        try:
            async with running_mcp_server() as url:
                async with official_session(url) as (session, initialized):
                    result = await session.call_tool(
                        "power_turn_on_and_verify", {"device": "heater"}
                    )
                    assert initialized.protocol_version == "2025-11-25"
                    assert result.structured_content is not None
                    assert result.structured_content["verification"] == "FAILED"
                    assert result.structured_content["reported_state"] == "ON"
                    assert result.structured_content["observed_power_watts"] == 2200.0
                    assert "high draw" in result.structured_content["reason"].lower()
                    assert application.connector.get_reported_state("heater").value == "OFF"
                    assert application.connector.read_power(
                        "heater", sample="after_stop"
                    ).watts == 2.0
        finally:
            application.reset_demo()

    asyncio.run(exercise())


def test_real_streamable_http_diagnostic_scenario_matrix() -> None:
    async def exercise() -> None:
        scenarios = (
            (FaultMode.NONE, "VERIFIED", 0),
            (FaultMode.NO_DRAW, "UNRESOLVED", 1),
            (FaultMode.NO_DRAW_THEN_RECOVER, "RECOVERED", 1),
            (FaultMode.HIGH_DRAW, "SAFETY_STOP", 0),
        )
        try:
            async with running_mcp_server() as url:
                async with official_session(url) as (session, initialized):
                    assert initialized.protocol_version == "2025-11-25"
                    for fault, expected_status, expected_retries in scenarios:
                        application.set_device_fault("heater", fault)
                        result = await session.call_tool(
                            "power_run_diagnostic", {"device": "heater"}
                        )
                        assert result.structured_content is not None
                        assert result.structured_content["final_status"] == (
                            expected_status
                        )
                        assert result.structured_content["retries_used"] == (
                            expected_retries
                        )
                    assert application.connector.get_reported_state("heater").value == (
                        "OFF"
                    )
        finally:
            application.reset_demo()

    asyncio.run(exercise())


def test_real_streamable_http_high_peak_then_normal_still_stops(
    tmp_path,
) -> None:
    class HighPeakThenNormalConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace((2200.0, 1500.0))

    settings = Settings(database_path=tmp_path / "high-peak.db")
    bound = VoltWiseApplication(settings)
    connector = HighPeakThenNormalConnector(FaultMode.NONE)
    bound.connector = connector
    bound.verification_service = VerificationService(connector)
    bound.diagnostic_service = DiagnosticWorkflowService(connector)

    async def exercise() -> None:
        async with running_mcp_server(bound_application=bound) as url:
            async with official_session(url) as (session, initialized):
                direct = await session.call_tool(
                    "power_turn_on_and_verify", {"device": "heater"}
                )
                assert direct.structured_content is not None
                assert direct.structured_content["verification"] == "FAILED"
                assert direct.structured_content["observed_power_watts"] == 2200.0
                assert connector.get_reported_state("heater").value == "OFF"

                connector.reset()
                result = await session.call_tool(
                    "power_run_diagnostic", {"device": "heater"}
                )
                assert initialized.protocol_version == "2025-11-25"
                assert result.structured_content is not None
                assert result.structured_content["final_status"] == "SAFETY_STOP"
                assert result.structured_content["initial_verification"] == "FAILED"
                assert result.structured_content["safety_action"] == (
                    "POWER_CUT_HIGH_DRAW"
                )
                assert result.structured_content["retries_used"] == 0
                attempt = result.structured_content["attempts"][0]
                assert attempt["power_samples_watts"] == [2200.0, 1500.0]
                assert attempt["observed_watts"] == 1500.0
                assert attempt["verification"] == "FAILED"
                assert connector.get_reported_state("heater").value == "OFF"

    asyncio.run(exercise())


@pytest.mark.parametrize("samples", [(2200.0, 1500.0), (2200.0,)])
def test_real_streamable_http_combined_high_draw_and_unavailable_stops(
    tmp_path, samples: tuple[float, ...]
) -> None:
    class HighDrawThenUnavailableConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace(samples)
            self._state.available = False

    settings = Settings(database_path=tmp_path / "combined-high-draw.db")
    bound = VoltWiseApplication(settings)
    connector = HighDrawThenUnavailableConnector(FaultMode.NONE)
    bound.connector = connector
    bound.verification_service = VerificationService(connector)
    bound.diagnostic_service = DiagnosticWorkflowService(connector)

    async def exercise() -> None:
        async with running_mcp_server(bound_application=bound) as url:
            async with official_session(url) as (session, initialized):
                direct = await session.call_tool(
                    "power_turn_on_and_verify", {"device": "heater"}
                )
                assert direct.structured_content is not None
                assert direct.structured_content["verification"] == "FAILED"
                assert direct.structured_content["observed_power_watts"] == 2200.0
                assert "unavailable" in direct.structured_content["reason"].lower()
                assert connector.get_reported_state("heater").value == "OFF"

                connector.reset()
                result = await session.call_tool(
                    "power_run_diagnostic", {"device": "heater"}
                )
                assert initialized.protocol_version == "2025-11-25"
                assert result.structured_content is not None
                assert result.structured_content["final_status"] == "SAFETY_STOP"
                assert result.structured_content["diagnostic_classification"] == (
                    "ABNORMAL_HIGH_DRAW"
                )
                assert result.structured_content["safety_action"] == (
                    "POWER_CUT_HIGH_DRAW"
                )
                assert result.structured_content["retries_used"] == 0
                attempt = result.structured_content["attempts"][0]
                assert attempt["available"] is False
                assert attempt["power_samples_watts"] == list(samples)
                assert any(
                    "unavailable" in item.lower()
                    for item in result.structured_content["evidence"]
                )
                safety_event = next(
                    event
                    for event in result.structured_content["audit_events"]
                    if event["event"] == "SAFETY_STOP"
                )
                assert "2200 W" in safety_event["detail"]
                assert "unavailable" in safety_event["detail"].lower()
                assert connector.get_reported_state("heater").value == "OFF"

    asyncio.run(exercise())


def test_invalid_origin_is_rejected() -> None:
    async def exercise() -> None:
        async with running_mcp_server() as url:
            async with httpx2.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Origin": "https://untrusted.example"},
                    json={},
                )
            assert response.status_code == 403
            assert response.text == "Invalid Origin header"

    asyncio.run(exercise())


def test_configured_bearer_token_is_accepted_by_official_client() -> None:
    async def exercise() -> None:
        async with running_mcp_server(token="test-only-secret") as url:
            async with official_session(url, "test-only-secret") as (session, _):
                listed = await session.list_tools()
                assert {tool.name for tool in listed.tools} == EXPECTED_TOOLS

    asyncio.run(exercise())


def test_missing_bearer_token_is_rejected() -> None:
    async def exercise() -> None:
        async with running_mcp_server(token="test-only-secret") as url:
            async with httpx2.AsyncClient() as client:
                response = await client.post(url, json={})
            assert response.status_code == 401
            assert response.headers["www-authenticate"] == "Bearer"
            assert response.json() == {"error": "Unauthorized"}

    asyncio.run(exercise())


def test_incorrect_bearer_token_is_rejected() -> None:
    async def exercise() -> None:
        async with running_mcp_server(token="test-only-secret") as url:
            async with httpx2.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Authorization": "Bearer wrong-secret"},
                    json={},
                )
            assert response.status_code == 401
            assert response.json() == {"error": "Unauthorized"}

    asyncio.run(exercise())


def test_oversized_request_is_rejected_by_sdk_middleware() -> None:
    async def exercise() -> None:
        async with running_mcp_server(max_request_body_size=64) as url:
            async with httpx2.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=b"x" * 65,
                    headers={"Content-Type": "application/json"},
                )
            assert response.status_code == 413
            assert response.text == "Request body too large"

    asyncio.run(exercise())
