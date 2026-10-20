from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


from .device import ReportedState


class SimulatorIntent(StrEnum):
    ENERGY_COMPARISON = "ENERGY_COMPARISON"
    USAGE_EXPLANATION = "USAGE_EXPLANATION"
    TARIFF_STATUS = "TARIFF_STATUS"
    BILL_FORECAST = "BILL_FORECAST"
    SUGGESTIONS = "SUGGESTIONS"
    TARGET_300 = "TARGET_300"
    VERIFY_HEATER = "VERIFY_HEATER"
    DIAGNOSE_HEATER = "DIAGNOSE_HEATER"
    CONTROL_DEVICE = "CONTROL_DEVICE"


class DeviceControlResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    device: str
    name: str
    command: str
    reported_state: ReportedState
    success: bool = True
    speakable_summary: str


class MCPTraceTransport(StrEnum):
    STREAMABLE_HTTP = "STREAMABLE_HTTP"


class MCPTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    trace_id: str
    timestamp: datetime
    transport: MCPTraceTransport = MCPTraceTransport.STREAMABLE_HTTP
    protocol_version: str | None = None
    intent: SimulatorIntent
    tool_name: str
    tool_arguments: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )
    result_summary: str
    duration_ms: float = Field(ge=0)
    success: bool
    error: str | None = None


class MCPToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    arguments: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )


class SimulatorChatResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    intent: SimulatorIntent
    tool_call: MCPToolCall
    result: dict[str, object]
    trace_id: str
