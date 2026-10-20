from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .device import ReportedState


class EnergyImpactType(StrEnum):
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"


class EvidenceSource(StrEnum):
    WHOLE_HOME_METER = "WHOLE_HOME_METER"
    DEVICE_STATE_HISTORY = "DEVICE_STATE_HISTORY"
    DEVICE_ENERGY_METER = "DEVICE_ENERGY_METER"


class ContributorReason(StrEnum):
    RUNTIME_INCREASE = "RUNTIME_INCREASE"
    MEASURED_ENERGY_INCREASE = "MEASURED_ENERGY_INCREASE"


class AnalysisConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class ProjectionMethod(StrEnum):
    RUN_RATE = "RUN_RATE"


class EnergyScenario(StrEnum):
    NORMAL_CURRENT_CYCLE = "NORMAL_CURRENT_CYCLE"
    NEAR_THRESHOLD = "NEAR_THRESHOLD"


class DeviceCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    supports_control: bool = False
    supports_state_history: bool = False
    supports_runtime: bool = False
    supports_device_power: bool = False
    supports_device_energy: bool = False
    has_estimated_cycle_energy: bool = False


class HouseholdDevice(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    name: str
    device_type: str
    capabilities: DeviceCapabilities
    nominal_power_kw: float | None = Field(default=None, gt=0)
    estimated_cycle_kwh: float | None = Field(default=None, gt=0)


class WholeHomeReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    instantaneous_watts: float = Field(ge=0)
    cumulative_kwh: float = Field(ge=0)


class DeviceStateTransition(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    timestamp: datetime
    state: ReportedState


class DeviceEnergyReading(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    timestamp: datetime
    cumulative_kwh: float = Field(ge=0)


class BillingCycle(BaseModel):
    model_config = ConfigDict(frozen=True)

    cycle_start: datetime
    cycle_end: datetime
    previous_cycle_start: datetime
    previous_cycle_end: datetime
    current_simulated_at: datetime

    @model_validator(mode="after")
    def validate_boundaries(self):
        if not self.cycle_start < self.current_simulated_at <= self.cycle_end:
            raise ValueError("current simulated time must fall within the current cycle")
        if not self.previous_cycle_start < self.previous_cycle_end <= self.cycle_start:
            raise ValueError("previous cycle boundaries must precede current cycle")
        return self


class EnergyProjection(BaseModel):
    model_config = ConfigDict(frozen=True)

    projected_kwh: float = Field(ge=0)
    method: ProjectionMethod
    days_elapsed: float = Field(gt=0)
    cycle_days: float = Field(gt=0)


class PeriodComparisonResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_kwh: float = Field(ge=0)
    previous_equivalent_kwh: float = Field(ge=0)
    difference_kwh: float
    change_percent: float | None
    elapsed_days: float = Field(gt=0)
    projection: EnergyProjection
    evidence_source: EvidenceSource
    speakable_summary: str


class UsageContributor(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    device: str
    reason: ContributorReason
    current_runtime_hours: float = Field(ge=0)
    previous_runtime_hours: float = Field(ge=0)
    runtime_change_hours: float
    runtime_change_percent: float | None
    energy_impact_kwh: float = Field(gt=0)
    energy_impact_type: EnergyImpactType
    evidence_source: EvidenceSource
    confidence: AnalysisConfidence


class UsageChangeExplanation(BaseModel):
    model_config = ConfigDict(frozen=True)

    household_change_kwh: float
    household_change_percent: float | None
    contributors: tuple[UsageContributor, ...]
    known_contribution_kwh: float = Field(ge=0)
    unattributed_kwh: float = Field(ge=0)
    attribution_overage_kwh: float = Field(ge=0)
    limitations: tuple[str, ...]
    speakable_summary: str
    current_kwh: float = 0.0
    previous_equivalent_kwh: float = 0.0
