import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import socket

import httpx2
import pytest
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import Settings
from app.deployment import create_deployment_app


REQUIRED_MCP_TOOLS = {
    "power_turn_on_and_verify",
    "power_run_diagnostic",
    "power_compare_periods",
    "power_explain_usage_change",
    "power_get_tariff_status",
    "power_forecast_bill",
    "power_estimate_load_impact",
    "power_suggest_actions",
}
EXPECTED_ADDITIONAL_MCP_TOOLS = {"power_control_device"}
PUBLIC_DEMO_CREDENTIALS = {
    "public_demo_enabled": True,
    "demo_basic_username": "judge",
    "demo_basic_password": "test-password",
    "mcp_bearer_token": "test-mcp-token",
}


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def static_fixture(root: Path) -> Path:
    static = root / "dist"
    (static / "assets").mkdir(parents=True, exist_ok=True)
    (static / "index.html").write_text(
        "<!doctype html><title>VoltWise deployment</title>", encoding="utf-8"
    )
    (static / "assets" / "probe.txt").write_text("static-ok", encoding="utf-8")
    return static


@asynccontextmanager
async def running_deployment(
    tmp_path: Path,
    *,
    mcp_url: str | None = None,
    settings_overrides: dict | None = None,
):
    port = available_port()
    values = dict(
        database_path=tmp_path / "deployment.db",
        mcp_url=mcp_url or f"http://127.0.0.1:{port}/mcp",
        mcp_allowed_hosts=("127.0.0.1:*",),
        mcp_allowed_origins=("http://127.0.0.1:*",),
    )
    values.update(settings_overrides or {})
    settings = Settings(**values)
    application = create_deployment_app(settings, static_fixture(tmp_path))
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="error")
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
            raise RuntimeError("Timed out starting deployment test server")
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=5)


def test_single_port_serves_spa_api_health_and_real_mcp(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with running_deployment(tmp_path) as url:
            async with httpx2.AsyncClient(base_url=url) as client:
                root = await client.get("/")
                spa_route = await client.get("/digital-home/demo")
                asset = await client.get("/assets/probe.txt")
                health = await client.get("/health")
                api_health = await client.get("/api/health")
                reset = await client.post("/api/demo/reset")
                chat = await client.post(
                    "/api/sim/chat",
                    json={"message": "How are we doing this month?"},
                )
                trace = (await client.get("/api/sim/traces?limit=1")).json()[0]

            assert root.status_code == 200
            assert "VoltWise deployment" in root.text
            assert spa_route.text == root.text
            assert asset.text == "static-ok"
            assert health.json() == {"status": "ok", "service": "voltwise"}
            assert api_health.status_code == 200
            assert reset.json()["heater_fault"] == "NONE"
            assert chat.status_code == 200
            assert chat.json()["intent"] == "ENERGY_COMPARISON"
            assert trace["transport"] == "STREAMABLE_HTTP"
            assert trace["protocol_version"] == "2025-11-25"
            assert trace["success"] is True

    asyncio.run(exercise())


def test_single_port_exposes_all_tools_to_official_mcp_client(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with running_deployment(tmp_path) as url:
            async with streamable_http_client(f"{url}/mcp") as streams:
                async with ClientSession(*streams) as session:
                    initialized = await session.initialize()
                    tools = {tool.name for tool in (await session.list_tools()).tools}

            assert initialized.protocol_version == "2025-11-25"
            assert REQUIRED_MCP_TOOLS <= tools
            assert tools - REQUIRED_MCP_TOOLS == EXPECTED_ADDITIONAL_MCP_TOOLS

    asyncio.run(exercise())


def test_sqlite_selection_and_audit_survive_combined_app_restart(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        async with running_deployment(tmp_path) as first_url:
            async with httpx2.AsyncClient(base_url=first_url) as client:
                await client.post(
                    "/api/demo/energy-scenario",
                    json={"scenario": "NEAR_THRESHOLD"},
                )
                await client.post(
                    "/api/demo/device-fault",
                    json={"device": "heater", "fault": "NO_DRAW"},
                )
                response = await client.post(
                    "/api/sim/chat",
                    json={"message": "Turn on the heater"},
                )
                assert response.status_code == 200

        async with running_deployment(tmp_path) as second_url:
            async with httpx2.AsyncClient(base_url=second_url) as client:
                state = (await client.get("/api/demo/state")).json()
                overview = (await client.get("/api/household/overview")).json()
                traces = (await client.get("/api/sim/traces")).json()
                events = (await client.get("/api/events")).json()

            heater = next(
                device for device in overview["devices"] if device["device_id"] == "heater"
            )
            assert state["energy_scenario"] == "NEAR_THRESHOLD"
            assert state["heater_fault"] == "NO_DRAW"
            assert heater["reported_state"] == "OFF"
            assert heater["current_watts"] == 2.0
            assert traces[0]["tool_name"] == "power_turn_on_and_verify"
            assert events

    asyncio.run(exercise())


def test_deployment_requires_built_frontend(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Frontend production build missing"):
        create_deployment_app(Settings(database_path=tmp_path / "db.sqlite"), tmp_path)


def test_combined_host_has_no_direct_fallback_when_mcp_target_is_unavailable(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        unavailable_url = f"http://127.0.0.1:{available_port()}/mcp"
        async with running_deployment(tmp_path, mcp_url=unavailable_url) as url:
            async with httpx2.AsyncClient(base_url=url) as client:
                response = await client.post(
                    "/api/sim/chat",
                    json={"message": "How are we doing this month?"},
                )
                trace = (await client.get("/api/sim/traces?limit=1")).json()[0]

            assert response.status_code == 503
            assert response.json()["error"]["code"] == "MCP_SERVICE_UNAVAILABLE"
            assert trace["success"] is False
            assert trace["result_summary"] == "MCP request failed."

    asyncio.run(exercise())


def test_public_demo_protects_ui_rest_history_and_admin_routes(tmp_path: Path) -> None:
    async def exercise() -> None:
        async with running_deployment(
            tmp_path, settings_overrides=PUBLIC_DEMO_CREDENTIALS
        ) as url:
            async with httpx2.AsyncClient(base_url=url) as client:
                for path in (
                    "/",
                    "/api/demo/state",
                    "/api/demo/reset",
                    "/api/events",
                    "/api/sim/traces",
                ):
                    response = (
                        await client.post(path)
                        if path.endswith("/reset")
                        else await client.get(path)
                    )
                    assert response.status_code == 401
                    assert response.json()["error"]["code"] == (
                        "AUTHENTICATION_REQUIRED"
                    )

                assert (await client.get("/health")).status_code == 200
                authenticated = httpx2.BasicAuth("judge", "test-password")
                assert (await client.get("/", auth=authenticated)).status_code == 200
                await client.post(
                    "/api/demo/device-fault",
                    auth=authenticated,
                    json={"device": "heater", "fault": "HIGH_DRAW"},
                )
                events_before = (
                    await client.get("/api/events", auth=authenticated)
                ).json()
                rejected_reset = await client.post("/api/demo/reset")
                state_after_rejection = (
                    await client.get("/api/demo/state", auth=authenticated)
                ).json()
                events_after = (
                    await client.get("/api/events", auth=authenticated)
                ).json()
                assert rejected_reset.status_code == 401
                assert state_after_rejection["heater_fault"] == "HIGH_DRAW"
                assert events_after == events_before
                assert (
                    await client.post("/api/demo/reset", auth=authenticated)
                ).status_code == 200
                assert (await client.get("/docs", auth=authenticated)).status_code == 404
                assert (
                    await client.get("/redoc", auth=authenticated)
                ).status_code == 404
                assert (
                    await client.get("/openapi.json", auth=authenticated)
                ).status_code == 404

    asyncio.run(exercise())


def test_public_demo_mcp_requires_bearer_but_internal_gateway_still_works(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        async with running_deployment(
            tmp_path, settings_overrides=PUBLIC_DEMO_CREDENTIALS
        ) as url:
            async with httpx2.AsyncClient(base_url=url) as client:
                missing = await client.post(f"{url}/mcp")
                basic_only = await client.post(
                    f"{url}/mcp", auth=httpx2.BasicAuth("judge", "test-password")
                )
                chat = await client.post(
                    "/api/sim/chat",
                    auth=httpx2.BasicAuth("judge", "test-password"),
                    json={"message": "How are we doing this month?"},
                )

            assert missing.status_code == 401
            assert basic_only.status_code == 401
            assert chat.status_code == 200
            assert chat.json()["tool_call"]["name"] == "power_compare_periods"

            headers = {"Authorization": "Bearer test-mcp-token"}
            async with httpx2.AsyncClient(headers=headers) as authorized_client:
                async with streamable_http_client(
                    f"{url}/mcp", http_client=authorized_client
                ) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        tools = {
                            tool.name for tool in (await session.list_tools()).tools
                        }
            assert REQUIRED_MCP_TOOLS <= tools
            assert tools - REQUIRED_MCP_TOOLS == EXPECTED_ADDITIONAL_MCP_TOOLS

    asyncio.run(exercise())


def test_public_demo_rest_body_and_rate_limits(tmp_path: Path) -> None:
    async def exercise() -> None:
        overrides = {
            **PUBLIC_DEMO_CREDENTIALS,
            "rest_max_request_body_size": 32,
            "rest_rate_limit_per_minute": 2,
            "rest_mutation_rate_limit_per_minute": 2,
        }
        async with running_deployment(
            tmp_path, settings_overrides=overrides
        ) as url:
            auth = httpx2.BasicAuth("judge", "test-password")
            async with httpx2.AsyncClient(base_url=url, auth=auth) as client:
                too_large = await client.post(
                    "/api/sim/chat", json={"message": "x" * 100}
                )
                first_read = await client.get("/api/demo/state")
                second_read = await client.get("/api/demo/state")
                limited_read = await client.get("/api/demo/state")
                first_mutation = await client.post("/api/demo/reset")
                limited_mutation = await client.post("/api/demo/reset")

            assert too_large.status_code == 413
            assert too_large.json()["error"]["code"] == "REQUEST_TOO_LARGE"
            assert first_read.status_code == second_read.status_code == 200
            assert limited_read.status_code == 429
            assert limited_read.headers["retry-after"] == "60"
            assert first_mutation.status_code == 200
            assert limited_mutation.status_code == 429

    asyncio.run(exercise())


def test_public_demo_rest_timeout_is_controlled(tmp_path: Path) -> None:
    async def exercise() -> None:
        overrides = {
            **PUBLIC_DEMO_CREDENTIALS,
            "rest_request_timeout_seconds": 0.000001,
        }
        async with running_deployment(
            tmp_path, settings_overrides=overrides
        ) as url:
            async with httpx2.AsyncClient(
                base_url=url, auth=httpx2.BasicAuth("judge", "test-password")
            ) as client:
                response = await client.get("/api/demo/state")

            assert response.status_code == 504
            assert response.json()["error"]["code"] == "REQUEST_TIMEOUT"

    asyncio.run(exercise())


def test_public_demo_rejects_chunked_body_over_limit(tmp_path: Path) -> None:
    async def chunks():
        yield b'{"message":"'
        yield b"x" * 100
        yield b'"}'

    async def exercise() -> None:
        overrides = {
            **PUBLIC_DEMO_CREDENTIALS,
            "rest_max_request_body_size": 32,
        }
        async with running_deployment(
            tmp_path, settings_overrides=overrides
        ) as url:
            async with httpx2.AsyncClient(
                base_url=url, auth=httpx2.BasicAuth("judge", "test-password")
            ) as client:
                response = await client.post(
                    "/api/sim/chat",
                    content=chunks(),
                    headers={"Content-Type": "application/json"},
                )

            assert response.status_code == 413
            assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"

    asyncio.run(exercise())


def test_public_demo_refuses_to_start_without_all_server_secrets() -> None:
    with pytest.raises(ValueError, match="Public demo mode requires"):
        Settings(public_demo_enabled=True)
