from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .device import ActualState, DeviceProfile, FaultMode, ReportedState
from .energy import DeviceCapabilities, EnergyScenario
from .tariff import ThresholdWarning


class DeviceView(BaseModel):
    model_config = ConfigDict(frozen=True)

    device_id: str
    name: str
    device_type: str
    reported_state: ReportedState | None
    physical_state: ActualState | None
    available: bool
    capabilities: DeviceCapabilities
    current_watts: float | None
    current_runtime_hours: float | None
    electrical_profile: DeviceProfile | None = None
    recent_evidence: tuple[str, ...] = ()
    simulation_only_fields: tuple[str, ...] = ()


class HouseholdOverview(BaseModel):
    model_config = ConfigDict(frozen=True)

    simulated_at: datetime
    energy_scenario: EnergyScenario
    current_cycle_kwh: float
    previous_equivalent_kwh: float
    change_percent: float | None
    projected_month_end_kwh: float
    tariff_warning: ThresholdWarning
    current_estimated_energy_charge: str
    projected_estimated_energy_charge: str
    devices: tuple[DeviceView, ...]


class DemoState(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: str
    energy_scenario: EnergyScenario
    heater_fault: FaultMode
    simulated_at: datetime
