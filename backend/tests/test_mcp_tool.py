import asyncio

from app.mcp.server import (
    connector,
    power_compare_periods,
    power_estimate_load_impact,
    power_explain_usage_change,
    power_forecast_bill,
    power_get_tariff_status,
    power_run_diagnostic,
    power_suggest_actions,
    power_turn_on_and_verify,
)
from app.models import FaultMode


def test_mcp_tool_returns_typed_structured_result() -> None:
    connector.set_fault(FaultMode.NO_DRAW)

    result = power_turn_on_and_verify("heater")
    payload = result.model_dump(mode="json")

    assert payload["device"] == "heater"
    assert payload["command"] == "ON"
    assert payload["reported_state"] == "ON"
    assert payload["verification"] == "FAILED"
    assert payload["expected_power_watts"] == 1500.0
    assert payload["observed_power_delta_watts"] == 5.0
    assert payload["confidence"] == 0.92
    assert payload["reason"] == "No expected electrical response detected."
    assert payload["telemetry_available"] is True
    assert payload["diagnostic_classification"] == "NO_ELECTRICAL_RESPONSE"


def test_tool_is_registered_with_mcp_and_has_structured_output_schema() -> None:
    tools = asyncio.run(mcp_tools())

    tool = next(item for item in tools if item.name == "power_turn_on_and_verify")
    assert tool.input_schema["required"] == ["device"]
    assert "verification" in tool.output_schema["properties"]
    assert "telemetry_available" in tool.output_schema["properties"]
    assert "diagnostic_classification" in tool.output_schema["properties"]


def test_mcp_dispatch_returns_structured_content() -> None:
    connector.set_fault(FaultMode.NO_DRAW)

    result = asyncio.run(mcp_call("power_turn_on_and_verify", {"device": "heater"}))

    assert result.structured_content is not None
    assert result.structured_content["verification"] == "FAILED"
    assert result.structured_content["observed_power_delta_watts"] == 5.0


def test_mcp_direct_verification_cuts_high_draw_and_preserves_observation() -> None:
    connector.set_fault(FaultMode.HIGH_DRAW)

    result = asyncio.run(mcp_call("power_turn_on_and_verify", {"device": "heater"}))

    assert result.structured_content is not None
    assert result.structured_content["verification"] == "FAILED"
    assert result.structured_content["reported_state"] == "ON"
    assert result.structured_content["observed_power_watts"] == 2200.0
    assert "high draw" in result.structured_content["reason"].lower()
    assert connector.get_reported_state("heater").value == "OFF"


def test_diagnostic_tool_returns_typed_workflow_result() -> None:
    connector.set_fault(FaultMode.NO_DRAW_THEN_RECOVER)

    payload = power_run_diagnostic("heater").model_dump(mode="json")

    assert payload["final_status"] == "RECOVERED"
    assert payload["retries_used"] == 1
    assert len(payload["attempts"]) == 2
    assert payload["attempts"][0]["diagnostic_classification"] == (
        "NO_ELECTRICAL_RESPONSE"
    )


def test_diagnostic_tool_is_registered_with_valid_schemas() -> None:
    tools = asyncio.run(mcp_tools())

    tool = next(item for item in tools if item.name == "power_run_diagnostic")
    assert tool.input_schema["required"] == ["device"]
    assert "final_status" in tool.output_schema["properties"]
    assert "attempts" in tool.output_schema["properties"]
    assert "audit_events" in tool.output_schema["properties"]


def test_mcp_dispatch_returns_structured_diagnostic_result() -> None:
    connector.set_fault(FaultMode.HIGH_DRAW)

    result = asyncio.run(mcp_call("power_run_diagnostic", {"device": "heater"}))

    assert result.structured_content is not None
    assert result.structured_content["final_status"] == "SAFETY_STOP"
    assert result.structured_content["retries_used"] == 0
    assert result.structured_content["safety_action"] == "POWER_CUT_HIGH_DRAW"


def test_energy_tools_are_registered_with_output_schemas() -> None:
    tools = {item.name: item for item in asyncio.run(mcp_tools())}

    comparison = tools["power_compare_periods"]
    explanation = tools["power_explain_usage_change"]
    assert comparison.input_schema["properties"] == {}
    assert "current_kwh" in comparison.output_schema["properties"]
    assert explanation.input_schema["properties"] == {}
    assert "contributors" in explanation.output_schema["properties"]
    assert "unattributed_kwh" in explanation.output_schema["properties"]


def test_comparison_tool_and_mcp_dispatch_return_structured_result() -> None:
    direct = power_compare_periods()
    dispatched = asyncio.run(mcp_call("power_compare_periods", {}))

    assert direct.current_kwh == 142.0
    assert direct.previous_equivalent_kwh == 118.0
    assert dispatched.structured_content is not None
    assert dispatched.structured_content["projection"]["method"] == "RUN_RATE"


def test_explanation_tool_and_mcp_dispatch_return_structured_result() -> None:
    direct = power_explain_usage_change()
    dispatched = asyncio.run(mcp_call("power_explain_usage_change", {}))

    assert direct.contributors[0].device_id == "ac"
    assert direct.unattributed_kwh > 0
    assert dispatched.structured_content is not None
    assert dispatched.structured_content["contributors"][0]["energy_impact_type"] == (
        "ESTIMATED"
    )


def test_tariff_tools_register_with_structured_schemas() -> None:
    tools = {item.name: item for item in asyncio.run(mcp_tools())}

    assert "current_usage_kwh" in tools["power_get_tariff_status"].output_schema["properties"]
    assert "projected" in tools["power_forecast_bill"].output_schema["properties"]
    assert tools["power_estimate_load_impact"].input_schema["required"] == ["device"]
    assert "threshold_crossed" in tools["power_estimate_load_impact"].output_schema["properties"]
    assert "target_kwh" in tools["power_suggest_actions"].input_schema["properties"]
    assert "recommendations" in tools["power_suggest_actions"].output_schema["properties"]


def test_tariff_status_and_bill_tools_dispatch() -> None:
    status = asyncio.run(mcp_call("power_get_tariff_status", {}))
    bill = asyncio.run(mcp_call("power_forecast_bill", {}))

    assert status.structured_content["tariff_id"] == "ILLUSTRATIVE_DEMO_TARIFF"
    assert status.structured_content["is_demo"] is True
    assert bill.structured_content["projected"]["energy_charge"] == "1384.32"


def test_load_impact_and_action_tools_dispatch() -> None:
    impact = asyncio.run(
        mcp_call("power_estimate_load_impact", {"device": "dishwasher"})
    )
    actions = asyncio.run(mcp_call("power_suggest_actions", {"target_kwh": 300}))

    assert impact.structured_content["energy_impact_type"] == "ESTIMATED"
    assert impact.structured_content["informative_only"] is True
    assert actions.structured_content["target_status"] == "ACHIEVABLE_WITH_REDUCTION"
    assert actions.structured_content["recommendations"][0]["impact_type"] == "ESTIMATED"


def test_direct_tariff_tool_functions() -> None:
    assert power_get_tariff_status().current_usage_kwh == 142
    assert power_forecast_bill().is_demo is True
    assert power_estimate_load_impact("dishwasher").threshold_crossed is False
    assert power_suggest_actions(300).target_kwh == 300


async def mcp_tools():
    from app.mcp.server import mcp

    return await mcp.list_tools()


async def mcp_call(name: str, arguments: dict[str, str]):
    from app.mcp.server import mcp

    return await mcp.call_tool(name, arguments)

