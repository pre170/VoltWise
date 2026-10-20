from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ReportedState(StrEnum):
    OFF = "OFF"
    ON = "ON"


class ActualState(StrEnum):
    OFF = "OFF"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


class FaultMode(StrEnum):
    NONE = "NONE"
    OFFLINE = "OFFLINE"
    NO_DRAW = "NO_DRAW"
    NO_DRAW_THEN_RECOVER = "NO_DRAW_THEN_RECOVER"
    STANDBY_ONLY = "STANDBY_ONLY"
    START_THEN_STOP = "START_THEN_STOP"
    HIGH_DRAW = "HIGH_DRAW"
    UNDERPOWERED = "UNDERPOWERED"


class HighDrawBehavior(StrEnum):
    STOP_AND_CUT_POWER = "STOP_AND_CUT_POWER"


class SafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(ge=0)
    allow_retry: bool
    allow_power_cycle: bool
    cooldown_seconds: int = Field(ge=0)
    high_draw_behavior: HighDrawBehavior
    requires_confirmation_for_power_cycle: bool


class DeviceProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    name: str
    expected_running_watts: float = Field(gt=0)
    standby_watts: float = Field(ge=0)
    acceptable_running_min: float = Field(gt=0)
    acceptable_running_max: float = Field(gt=0)
    abnormal_high_draw_threshold: float = Field(gt=0)
    startup_min_watts: float = Field(gt=0)
    no_response_delta_watts: float = Field(ge=0)
    standby_tolerance_watts: float = Field(ge=0)
    safety_policy: SafetyPolicy
    supports_control: bool = True
    supports_state: bool = True
    supports_device_power: bool = True

    @property
    def expected_power_watts(self) -> float:
        """Compatibility name retained for the first vertical slice."""
        return self.expected_running_watts

    @property
    def minimum_running_power_watts(self) -> float:
        """Compatibility name retained for the first vertical slice."""
        return self.acceptable_running_min

    @property
    def standby_power_watts(self) -> float:
        """Compatibility name retained for the first vertical slice."""
        return self.standby_watts


class PowerReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    watts: float = Field(ge=0)
    sample: str


class DeviceTelemetry(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    reported_state: ReportedState
    power_samples_watts: tuple[float, ...]

