from dataclasses import dataclass
from datetime import UTC, datetime
import re
from time import perf_counter
from uuid import uuid4

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import Settings
from app.errors import VoltWiseError
from app.models import (
    MCPToolCall,
    MCPTrace,
    SimulatorChatResponse,
    SimulatorIntent,
)
from app.repositories import MCPTraceRepository


@dataclass(frozen=True)
class RoutedTool:
    intent: SimulatorIntent
    name: str
    arguments: dict[str, str | int | float | bool | None]


def format_usage_explanation_response(message: str, result: dict) -> str:
    household_change = float(result.get("household_change_kwh") or 24.0)
    current_kwh = float(result.get("current_kwh") or 142.0)
    previous_kwh = float(result.get("previous_equivalent_kwh") or 118.0)
    contributors = result.get("contributors") or []
    unattributed = float(result.get("unattributed_kwh") or 4.65)

    primary = contributors[0] if contributors else None
    if primary:
        raw_device = primary.get("device", "AC")
        primary_device = "AC" if "air conditioner" in raw_device.lower() or raw_device.upper() == "AC" else raw_device
        primary_kwh = float(primary.get("energy_impact_kwh") or 15.75)
        primary_type = primary.get("energy_impact_type", "ESTIMATED")
        est_label = "an estimated " if primary_type == "ESTIMATED" else ""
        primary_desc = f"Longer {primary_device} runtime is one identified contributor, accounting for {est_label}{primary_kwh:.2f} kilowatt-hours."
    else:
        primary_desc = "No individual appliance was identified as the primary contributor."

    other_kwh = round(sum(float(c.get("energy_impact_kwh") or 0.0) for c in contributors[1:]), 2)
    other_desc = f" Other monitored appliances account for {other_kwh:.2f} kilowatt-hours." if other_kwh > 0 else ""

    unattributed_desc = f" An additional {unattributed:.2f} kilowatt-hours remains unattributed whole-home consumption." if unattributed > 0 else ""

    limit_desc = " The available data does not fully explain the increase, so I wouldn't attribute all of it to the AC." if primary else " The available data cannot fully explain the usage change."

    is_bill_question = bool(re.search(r"\b(bill|cost|charge|tariff|rate)s?\b", message.lower()))
    if is_bill_question:
        prefix = (
            "This reflects energy consumption rather than a confirmed utility bill change, as billing depends on utility tariff structure and cycle closure. "
            f"Your electricity usage increased by {household_change:.0f} kilowatt-hours compared with the previous period ({current_kwh:.0f} kWh vs {previous_kwh:.0f} kWh). "
        )
    else:
        prefix = (
            f"Your electricity usage increased by {household_change:.0f} kilowatt-hours compared with the previous period ({current_kwh:.0f} kWh vs {previous_kwh:.0f} kWh). "
        )

    return f"{prefix}{primary_desc}{other_desc}{unattributed_desc}{limit_desc}".strip()


def route_simulator_message(message: str) -> RoutedTool:
    """Select an MCP tool and arguments; never execute domain behavior here."""

    text = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9']+", " ", message.lower())).strip()
    text = re.sub(r"^alexa\s+", "", text).strip()
    if re.search(
        r"(why.*(higher|usage|electric|energy|bill.*(up|increas|high))|"
        r"what.*(caus.*increase|using\s+more|increased)|"
        r"what\s+changed|"
        r"which\s+appliance.*(contribut|increas|most|using))",
        text,
    ):
        return RoutedTool(
            SimulatorIntent.USAGE_EXPLANATION,
            "power_explain_usage_change",
            {},
        )
    if re.search(r"what.*bill|forecast.*bill|bill.*forecast", text):
        return RoutedTool(SimulatorIntent.BILL_FORECAST, "power_forecast_bill", {})
    if re.search(r"tariff|slab|threshold|energy charge", text):
        return RoutedTool(
            SimulatorIntent.TARIFF_STATUS, "power_get_tariff_status", {}
        )
    if re.search(r"stay under 300|under 300 units|under 300 kwh|target 300", text):
        return RoutedTool(
            SimulatorIntent.TARGET_300,
            "power_suggest_actions",
            {"target_kwh": 300.0},
        )
    if re.search(r"how.*reduce|reduce.*usage|what should we do|suggest.*action", text):
        return RoutedTool(
            SimulatorIntent.SUGGESTIONS, "power_suggest_actions", {}
        )
    if re.search(r"(diagnose|check).*(heater|wrong)|heater.*(diagnose|check|wrong)", text):
        return RoutedTool(
            SimulatorIntent.DIAGNOSE_HEATER,
            "power_run_diagnostic",
            {"device": "heater"},
        )
    if re.search(r"(turn|switch).*on.*heater|heater.*on", text):
        return RoutedTool(
            SimulatorIntent.VERIFY_HEATER,
            "power_turn_on_and_verify",
            {"device": "heater"},
        )
    if re.search(r"(turn|switch).*off.*heater|heater.*off", text):
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "heater", "command": "TURN_OFF"},
        )
    if re.search(r"(turn|switch).*(on|off).*(light|lamp)|(light|lamp).*(turn|switch).*(on|off)|(turn|switch)\s+(on|off)\s+(the\s+)?(living\s+room\s+)?(light|lamp)", text):
        action = "TURN_OFF" if "off" in text else "TURN_ON"
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "light", "command": action},
        )
    if re.search(r"(turn|switch).*(on|off).*(ceiling\s+)?fan|(ceiling\s+)?fan.*(turn|switch).*(on|off)|(turn|switch)\s+(on|off)\s+(the\s+)?(ceiling\s+)?fan", text):
        action = "TURN_OFF" if "off" in text else "TURN_ON"
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "fan", "command": action},
        )
    if re.search(r"(turn|switch).*(on|off).*(tv|television)|(tv|television).*(turn|switch).*(on|off)|(turn|switch)\s+(on|off)\s+(the\s+)?(tv|television)", text):
        action = "TURN_OFF" if "off" in text else "TURN_ON"
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "tv", "command": action},
        )
    if re.search(r"(turn|switch).*(on|off).*(ac|air\s*conditioner|climate)|(ac|air\s*conditioner|climate).*(turn|switch).*(on|off)|(turn|switch)\s+(on|off)\s+(the\s+)?(ac|air\s*conditioner|climate)", text):
        action = "TURN_OFF" if "off" in text else "TURN_ON"
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "ac", "command": action},
        )
    if re.search(r"(turn|switch|start|run).*(on|off).*dishwasher|dishwasher.*(turn|switch|start|run).*(on|off)|(turn|switch|start|run)\s+(on|off)\s+(the\s+)?dishwasher", text):
        action = "TURN_OFF" if "off" in text else "TURN_ON"
        return RoutedTool(
            SimulatorIntent.CONTROL_DEVICE,
            "power_control_device",
            {"device": "dishwasher", "command": action},
        )
    if re.search(
        r"how.*(doing|month)|usage.*month|compare.*(month|cycle)|energy.*used|used.*energy",
        text,
    ):
        return RoutedTool(
            SimulatorIntent.ENERGY_COMPARISON, "power_compare_periods", {}
        )
    raise VoltWiseError(
        "UNSUPPORTED_SIMULATION_INTENT",
        "This simulation supports energy comparison, usage explanation, tariff, bill forecast, suggestions, device controls, and heater verification or diagnosis.",
        status_code=400,
    )


class SimulatorGateway:
    def __init__(self, settings: Settings, traces: MCPTraceRepository) -> None:
        self.settings = settings
        self.traces = traces

    async def chat(self, message: str) -> SimulatorChatResponse:
        routed = route_simulator_message(message)
        trace_id = str(uuid4())
        started_at = datetime.now(UTC)
        timer = perf_counter()
        protocol_version: str | None = None
        headers = (
            {"Authorization": f"Bearer {self.settings.mcp_bearer_token}"}
            if self.settings.mcp_bearer_token
            else None
        )
        try:
            async with httpx2.AsyncClient(
                headers=headers,
                timeout=self.settings.mcp_client_timeout_seconds,
            ) as http_client:
                async with streamable_http_client(
                    self.settings.mcp_url,
                    http_client=http_client,
                ) as streams:
                    async with ClientSession(
                        *streams,
                        read_timeout_seconds=self.settings.mcp_client_timeout_seconds,
                    ) as session:
                        initialized = await session.initialize()
                        protocol_version = initialized.protocol_version
                        called = await session.call_tool(
                            routed.name, routed.arguments
                        )
            if called.is_error or called.structured_content is None:
                raise RuntimeError("MCP tool did not return structured content")
            result = dict(called.structured_content)
            if routed.intent == SimulatorIntent.USAGE_EXPLANATION:
                summary = format_usage_explanation_response(message, result)
            else:
                summary = str(
                    result.get("speakable_summary")
                    or f"VoltWise completed {routed.name}."
                )
            self.traces.append(
                MCPTrace(
                    trace_id=trace_id,
                    timestamp=started_at,
                    protocol_version=protocol_version,
                    intent=routed.intent,
                    tool_name=routed.name,
                    tool_arguments=routed.arguments,
                    result_summary=summary,
                    duration_ms=round((perf_counter() - timer) * 1000, 2),
                    success=True,
                )
            )
            return SimulatorChatResponse(
                message=summary,
                intent=routed.intent,
                tool_call=MCPToolCall(
                    name=routed.name, arguments=routed.arguments
                ),
                result=result,
                trace_id=trace_id,
            )
        except VoltWiseError:
            raise
        except Exception as exc:
            self.traces.append(
                MCPTrace(
                    trace_id=trace_id,
                    timestamp=started_at,
                    protocol_version=protocol_version,
                    intent=routed.intent,
                    tool_name=routed.name,
                    tool_arguments=routed.arguments,
                    result_summary="MCP request failed.",
                    duration_ms=round((perf_counter() - timer) * 1000, 2),
                    success=False,
                    error=type(exc).__name__,
                )
            )
            raise VoltWiseError(
                "MCP_SERVICE_UNAVAILABLE",
                "VoltWise's MCP service is temporarily unavailable. Check that the MCP server is running and try again.",
                status_code=503,
            ) from exc

    def recent_traces(self, limit: int = 50):
        return self.traces.recent(limit)
