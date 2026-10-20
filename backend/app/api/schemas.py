from pydantic import BaseModel, ConfigDict, Field

from app.models import EnergyScenario, FaultMode


class HealthResponse(BaseModel):
    status: str
    service: str
    mode: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class TargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_kwh: float | None = Field(default=None, gt=0)


class EnergyScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: EnergyScenario


class DeviceFaultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device: str
    fault: FaultMode


class SimulatorChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500)
