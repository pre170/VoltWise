from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .energy import EnergyImpactType, ProjectionMethod


class TariffType(StrEnum):
    TELESCOPIC = "TELESCOPIC"
    NON_TELESCOPIC = "NON_TELESCOPIC"


class ThresholdWarning(StrEnum):
    NEAR_THRESHOLD = "NEAR_THRESHOLD"
    PROJECTED_TO_CROSS = "PROJECTED_TO_CROSS"
    THRESHOLD_ALREADY_CROSSED = "THRESHOLD_ALREADY_CROSSED"
    SAFE_MARGIN = "SAFE_MARGIN"


class TargetStatus(StrEnum):
    ON_TRACK = "ON_TRACK"
    ACHIEVABLE_WITH_REDUCTION = "ACHIEVABLE_WITH_REDUCTION"
    UNLIKELY_AT_CURRENT_RATE = "UNLIKELY_AT_CURRENT_RATE"
    TARGET_ALREADY_EXCEEDED = "TARGET_ALREADY_EXCEEDED"


class TariffSlab(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_kwh: Decimal = Field(ge=0)
    to_kwh: Decimal | None = Field(default=None, gt=0)
    rate_per_kwh: Decimal = Field(ge=0)


class TariffPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    tariff_id: str
    name: str
    tariff_type: TariffType
    currency: str
    slabs: tuple[TariffSlab, ...]
    fixed_charge: Decimal = Field(default=Decimal("0"), ge=0)
    taxes_or_adjustments: Decimal = Decimal("0")
    time_of_day_windows: tuple[str, ...] = ()
    source: str
    effective_from: date
    effective_to: date | None = None
    is_demo: bool

    @model_validator(mode="after")
    def validate_slabs(self):
        if not self.slabs or self.slabs[0].from_kwh != 0:
            raise ValueError("Tariff slabs must begin at 0 kWh")
        for index, slab in enumerate(self.slabs):
            if slab.to_kwh is not None and slab.to_kwh <= slab.from_kwh:
                raise ValueError("Tariff slab upper boundary must exceed lower boundary")
            if index < len(self.slabs) - 1:
                if slab.to_kwh != self.slabs[index + 1].from_kwh:
                    raise ValueError("Tariff slabs must be contiguous")
            elif slab.to_kwh is not None:
                raise ValueError("Final tariff slab must have no upper boundary")
        return self


class TariffAwarenessPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    near_threshold_kwh: Decimal = Field(default=Decimal("10"), gt=0)
    achievable_run_rate_ratio: Decimal = Field(default=Decimal("1.25"), ge=1)
    suggested_ac_reduction_hours: Decimal = Field(default=Decimal("2"), gt=0)


class SlabCharge(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_kwh: Decimal
    to_kwh: Decimal | None
    units_charged: Decimal
    rate_per_kwh: Decimal
    charge: Decimal


class TariffCalculation(BaseModel):
    model_config = ConfigDict(frozen=True)

    consumption_kwh: Decimal
    energy_charge: Decimal
    fixed_charge: Decimal
    taxes_or_adjustments: Decimal
    estimated_total: Decimal
    currency: str
    tariff_type: TariffType
    slab_breakdown: tuple[SlabCharge, ...]


class ThresholdCrossing(BaseModel):
    model_config = ConfigDict(frozen=True)

    threshold_kwh: Decimal
    estimated_at: datetime
    method: ProjectionMethod


class TariffStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    tariff_id: str
    tariff_name: str
    tariff_type: TariffType
    currency: str
    source: str
    is_demo: bool
    current_usage_kwh: Decimal
    current_slab: str
    current_estimated_energy_charge: Decimal
    next_threshold_kwh: Decimal | None
    units_until_next_threshold: Decimal | None
    current_marginal_rate: Decimal
    next_marginal_rate: Decimal | None
    projected_month_end_kwh: Decimal
    projected_slab: str
    projected_estimated_energy_charge: Decimal
    expected_threshold_crossings: tuple[ThresholdCrossing, ...]
    threshold_warning: ThresholdWarning
    speakable_summary: str


class BillForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    tariff_id: str
    is_demo: bool
    current: TariffCalculation
    projected: TariffCalculation
    projection_method: ProjectionMethod
    assumptions: tuple[str, ...]
    speakable_summary: str


class LoadImpactResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    device: str
    estimated_operation_kwh: Decimal
    energy_impact_type: EnergyImpactType
    before_usage_kwh: Decimal
    after_usage_kwh: Decimal
    before_slab: str
    after_slab: str
    before_energy_charge: Decimal
    after_energy_charge: Decimal
    estimated_incremental_energy_charge: Decimal
    threshold_crossed: bool
    crossed_thresholds_kwh: tuple[Decimal, ...]
    informative_only: bool
    speakable_summary: str


class ActionRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank: int = Field(ge=1)
    action: str
    reason: str
    evidence_source: str
    estimated_reduction_kwh: Decimal | None = Field(default=None, ge=0)
    impact_type: EnergyImpactType | None = None


class ActionSuggestions(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_kwh: Decimal | None
    target_status: TargetStatus | None
    current_usage_kwh: Decimal
    projected_usage_kwh: Decimal
    remaining_kwh_budget: Decimal | None
    remaining_days: Decimal
    required_average_daily_kwh: Decimal | None
    current_daily_run_rate_kwh: Decimal
    recommendations: tuple[ActionRecommendation, ...]
    speakable_summary: str
