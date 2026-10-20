from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.application import VoltWiseApplication
from app.config import Settings
from app.models import EnergyScenario, FaultMode
from app.connectors import SimulatedDeviceConnector
from app.services import DiagnosticWorkflowService, VerificationService


@pytest.fixture
def application(tmp_path: Path) -> VoltWiseApplication:
    return VoltWiseApplication(Settings(database_path=tmp_path / "voltwise.db"))


@pytest.fixture
def client(application: VoltWiseApplication):
    with TestClient(create_app(application)) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    assert client.get("/api/health").json() == {
        "status": "ok",
        "service": "voltwise",
        "mode": "simulation",
    }


def test_household_overview_composes_existing_services(client: TestClient) -> None:
    payload = client.get("/api/household/overview").json()

    assert payload["simulated_at"] == "2026-09-15T00:00:00"
    assert payload["energy_scenario"] == "NORMAL_CURRENT_CYCLE"
    assert payload["current_cycle_kwh"] == 142.0
    assert payload["previous_equivalent_kwh"] == 118.0
    assert payload["projected_month_end_kwh"] == 304.29
    assert payload["tariff_warning"] == "PROJECTED_TO_CROSS"
    assert payload["current_estimated_energy_charge"] == "489.00"
    assert len(payload["devices"]) == 5


def test_devices_list_has_distinct_capabilities_and_admin_markers(client: TestClient) -> None:
    payload = client.get("/api/devices").json()
    devices = {item["device_id"]: item for item in payload}

    assert set(devices) == {"ac", "heater", "refrigerator", "tv", "dishwasher"}
    assert devices["ac"]["capabilities"]["supports_device_energy"] is False
    assert devices["heater"]["current_watts"] == 2.0
    assert "physical_state" in devices["heater"]["simulation_only_fields"]


def test_known_device_detail(client: TestClient) -> None:
    payload = client.get("/api/devices/heater").json()

    assert payload["device_type"] == "HEATER"
    assert payload["reported_state"] == "OFF"
    assert payload["physical_state"] == "OFF"
    assert payload["electrical_profile"]["expected_running_watts"] == 1500.0


def test_unknown_device_returns_structured_404(client: TestClient) -> None:
    response = client.get("/api/devices/unknown")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "DEVICE_NOT_FOUND",
            "message": "Unknown device: unknown",
        }
    }


def test_verification_endpoint_matches_shared_service(
    client: TestClient, application: VoltWiseApplication
) -> None:
    expected = application.verification_service.turn_on_and_verify("heater")
    application.connector.reset()

    response = client.post("/api/devices/heater/turn-on-and-verify")

    assert response.status_code == 200
    assert response.json() == expected.model_dump(mode="json")


def test_direct_high_draw_verification_records_cutoff_audit(
    client: TestClient, application: VoltWiseApplication
) -> None:
    application.set_device_fault("heater", FaultMode.HIGH_DRAW)

    response = client.post("/api/devices/heater/turn-on-and-verify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"] == "FAILED"
    assert payload["reported_state"] == "ON"
    assert payload["observed_power_watts"] == 2200.0
    heater = client.get("/api/devices/heater").json()
    assert heater["reported_state"] == "OFF"
    assert heater["current_watts"] == 2.0
    safety = next(
        event
        for event in client.get("/api/events").json()
        if event["event_type"] == "SAFETY_STOP"
    )
    assert safety["action"] == "POWER_CUT_HIGH_DRAW"
    assert safety["details"] == {
        "trigger_watts": 2200.0,
        "final_reported_state": "OFF",
    }


@pytest.mark.parametrize("samples", [(2200.0, 1500.0), (2200.0,)])
def test_rest_combined_high_draw_and_unavailable_telemetry_stops_safely(
    client: TestClient,
    application: VoltWiseApplication,
    samples: tuple[float, ...],
) -> None:
    class HighDrawThenUnavailableConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace(samples)
            self._state.available = False

    connector = HighDrawThenUnavailableConnector(FaultMode.NONE)
    application.connector = connector
    application.verification_service = VerificationService(connector)
    application.diagnostic_service = DiagnosticWorkflowService(connector)

    direct = client.post("/api/devices/heater/turn-on-and-verify").json()

    assert direct["verification"] == "FAILED"
    assert direct["observed_power_watts"] == 2200.0
    assert "unavailable" in direct["reason"].lower()
    assert connector.get_reported_state("heater").value == "OFF"
    direct_safety = next(
        event
        for event in client.get("/api/events").json()
        if event["event_type"] == "SAFETY_STOP"
    )
    assert direct_safety["details"]["trigger_watts"] == 2200.0
    assert direct_safety["details"]["final_reported_state"] == "OFF"

    connector.reset()
    diagnostic = client.post("/api/devices/heater/diagnose").json()

    assert diagnostic["final_status"] == "SAFETY_STOP"
    assert diagnostic["diagnostic_classification"] == "ABNORMAL_HIGH_DRAW"
    assert diagnostic["retries_used"] == 0
    assert diagnostic["attempts"][0]["available"] is False
    assert diagnostic["attempts"][0]["power_samples_watts"] == list(samples)
    diagnostic_safety = next(
        event
        for event in diagnostic["audit_events"]
        if event["event"] == "SAFETY_STOP"
    )
    assert "2200 W" in diagnostic_safety["detail"]
    assert "unavailable" in diagnostic_safety["detail"].lower()
    assert connector.get_reported_state("heater").value == "OFF"


def test_diagnostic_endpoint_matches_shared_service(
    client: TestClient, application: VoltWiseApplication
) -> None:
    application.connector.set_fault(FaultMode.NO_DRAW)
    expected = application.diagnostic_service.run("heater")
    application.connector.set_fault(FaultMode.NO_DRAW)

    response = client.post("/api/devices/heater/diagnose")

    assert response.json() == expected.model_dump(mode="json")


def test_energy_endpoints(client: TestClient) -> None:
    comparison = client.get("/api/energy/comparison")
    explanation = client.get("/api/energy/explanation")

    assert comparison.json()["current_kwh"] == 142.0
    assert explanation.json()["contributors"][0]["device_id"] == "ac"
    assert explanation.json()["unattributed_kwh"] == 4.65


def test_tariff_endpoints(client: TestClient) -> None:
    status = client.get("/api/tariff/status").json()
    forecast = client.get("/api/tariff/forecast").json()
    impact = client.get("/api/tariff/load-impact/dishwasher").json()
    actions = client.post(
        "/api/tariff/recommendations", json={"target_kwh": 300}
    ).json()

    assert status["current_usage_kwh"] == "142.000"
    assert forecast["projected"]["energy_charge"] == "1384.32"
    assert impact["estimated_operation_kwh"] == "5.000"
    assert actions["target_status"] == "ACHIEVABLE_WITH_REDUCTION"


def test_scenario_switches_without_restart(client: TestClient) -> None:
    response = client.post(
        "/api/demo/energy-scenario", json={"scenario": "NEAR_THRESHOLD"}
    )

    assert response.status_code == 200
    assert response.json()["energy_scenario"] == "NEAR_THRESHOLD"
    assert client.get("/api/tariff/status").json()["current_usage_kwh"] == "296.000"


def test_invalid_scenario_uses_consistent_error(client: TestClient) -> None:
    response = client.post(
        "/api/demo/energy-scenario", json={"scenario": "NOT_REAL"}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    ("fault", "status", "retries"),
    [
        ("NO_DRAW", "UNRESOLVED", 1),
        ("NO_DRAW_THEN_RECOVER", "RECOVERED", 1),
        ("HIGH_DRAW", "SAFETY_STOP", 0),
    ],
)
def test_fault_injection_and_diagnostic_through_http(
    client: TestClient, fault: str, status: str, retries: int
) -> None:
    injected = client.post(
        "/api/demo/device-fault", json={"device": "heater", "fault": fault}
    )
    diagnostic = client.post("/api/devices/heater/diagnose")

    assert injected.json()["heater_fault"] == fault
    assert diagnostic.json()["final_status"] == status
    assert diagnostic.json()["retries_used"] == retries


def test_invalid_fault_and_invalid_target_are_structured(client: TestClient) -> None:
    bad_fault = client.post(
        "/api/demo/device-fault", json={"device": "heater", "fault": "BROKEN"}
    )
    bad_target = client.post(
        "/api/tariff/recommendations", json={"target_kwh": -1}
    )

    assert bad_fault.status_code == 422
    assert bad_fault.json()["error"]["code"] == "INVALID_REQUEST"
    assert bad_target.status_code == 422
    assert bad_target.json()["error"]["code"] == "INVALID_REQUEST"


def test_demo_reset_restores_canonical_state(client: TestClient) -> None:
    client.post(
        "/api/demo/energy-scenario", json={"scenario": "NEAR_THRESHOLD"}
    )
    client.post(
        "/api/demo/device-fault", json={"device": "heater", "fault": "NO_DRAW"}
    )
    client.post("/api/devices/heater/turn-on-and-verify")

    reset = client.post("/api/demo/reset").json()
    heater = client.get("/api/devices/heater").json()

    assert reset["energy_scenario"] == "NORMAL_CURRENT_CYCLE"
    assert reset["heater_fault"] == "NONE"
    assert reset["simulated_at"] == "2026-09-15T00:00:00"
    assert heater["reported_state"] == "OFF"
    assert heater["physical_state"] == "OFF"
    assert heater["current_watts"] == 2.0


def test_demo_reset_preserves_history_and_does_not_create_mcp_trace(
    client: TestClient, application: VoltWiseApplication
) -> None:
    client.get("/api/energy/comparison")
    event_count = len(application.recent_events())
    traces_before = client.get("/api/sim/traces").json()

    response = client.post("/api/demo/reset")

    assert response.status_code == 200
    assert len(application.recent_events()) == event_count + 1
    assert application.recent_events()[0].action == "RESET_DEMO"
    assert client.get("/api/sim/traces").json() == traces_before


def test_events_are_persisted_and_limit_is_honored(
    client: TestClient, application: VoltWiseApplication
) -> None:
    client.get("/api/energy/comparison")
    client.get("/api/tariff/status")
    client.post("/api/devices/heater/turn-on-and-verify")

    response = client.get("/api/events?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["event_id"] > response.json()[1]["event_id"]
    assert len(application.recent_events(50)) >= 4


def test_events_and_demo_state_survive_application_recreation(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "persistent.db")
    first = VoltWiseApplication(settings)
    first.set_energy_scenario(EnergyScenario.NEAR_THRESHOLD)
    first.set_device_fault("heater", FaultMode.NO_DRAW)
    first.run_diagnostic("heater")

    second = VoltWiseApplication(settings)

    assert second.demo_state().energy_scenario is EnergyScenario.NEAR_THRESHOLD
    assert second.demo_state().heater_fault is FaultMode.NO_DRAW
    assert len(second.recent_events()) == len(first.recent_events())


def test_test_databases_are_isolated(tmp_path: Path) -> None:
    first = VoltWiseApplication(Settings(database_path=tmp_path / "one.db"))
    second = VoltWiseApplication(Settings(database_path=tmp_path / "two.db"))
    first.compare_periods()

    assert len(first.recent_events()) == 1
    assert second.recent_events() == ()


def test_cors_allows_only_configured_development_origins(client: TestClient) -> None:
    allowed_responses = [
        client.options(
            "/api/health",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173")
    ]
    denied = client.options(
        "/api/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert [response.headers["access-control-allow-origin"] for response in allowed_responses] == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert "access-control-allow-origin" not in denied.headers


def test_openapi_contains_core_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    assert response.status_code == 200
    assert "/api/household/overview" in paths
    assert "/api/devices/{device_id}/diagnose" in paths
    assert "/api/energy/comparison" in paths
    assert "/api/tariff/status" in paths
    assert "/api/demo/device-fault" in paths
    assert "/api/events" in paths
    assert "/api/sim/chat" in paths
    assert "/api/sim/traces" in paths


def test_module_level_mcp_and_http_adapters_share_application_container() -> None:
    from app.api.app import app as http_app
    from app.mcp.server import application as mcp_application

    assert http_app.state.voltwise is mcp_application

