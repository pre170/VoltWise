from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApplicationEventType(StrEnum):
    DEVICE_COMMAND = "DEVICE_COMMAND"
    VERIFICATION = "VERIFICATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    RETRY = "RETRY"
    SAFETY_STOP = "SAFETY_STOP"
    ENERGY_QUERY = "ENERGY_QUERY"
    TARIFF_QUERY = "TARIFF_QUERY"
    SCENARIO_CHANGED = "SCENARIO_CHANGED"
    FAULT_CHANGED = "FAULT_CHANGED"
    DEMO_RESET = "DEMO_RESET"


class ApplicationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: int | None = Field(default=None, ge=1)
    timestamp: datetime
    event_type: ApplicationEventType
    device_id: str | None = None
    action: str
    outcome: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
