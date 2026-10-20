from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol

from app.models import (
    BillingCycle,
    DeviceCapabilities,
    DeviceEnergyReading,
    EnergyScenario,
    DeviceStateTransition,
    HouseholdDevice,
    ReportedState,
    WholeHomeReading,
)
from app.simulation import SimulationClock


class EnergyRepository(Protocol):
    def get_billing_cycle(self) -> BillingCycle: ...

    def get_devices(self) -> Sequence[HouseholdDevice]: ...

    def get_household_readings(
        self, start: datetime, end: datetime
    ) -> Sequence[WholeHomeReading]: ...

    def get_device_state_history(
        self, device_id: str, start: datetime, end: datetime
    ) -> Sequence[DeviceStateTransition]: ...

    def get_device_energy_readings(
        self, device_id: str, start: datetime, end: datetime
    ) -> Sequence[DeviceEnergyReading]: ...


class FixtureEnergyRepository:
    """Deterministic household history for the canonical VoltWise demo."""

    CURRENT_START = datetime(2026, 9, 1)
    CURRENT_END = datetime(2026, 10, 1)
    PREVIOUS_START = datetime(2026, 8, 2)
    PREVIOUS_END = CURRENT_START
    DEMO_NOW = datetime(2026, 9, 15)
    NEAR_THRESHOLD_NOW = datetime(2026, 9, 28)

    PREVIOUS_DAILY_KWH = (9.0,) * 6 + (8.0,) * 8 + (8.0,) * 10 + (7.0,) * 6
    CURRENT_DAILY_KWH = (11.0,) * 2 + (10.0,) * 12 + (10.5,) * 16
    NEAR_THRESHOLD_DAILY_KWH = (
        (11.0,) * 2 + (10.0,) * 12 + (12.0,) * 12 + (10.0,) + (10.0,) * 3
    )

    DEVICES = (
        HouseholdDevice(
            device_id="ac",
            name="Air Conditioner",
            device_type="AIR_CONDITIONER",
            capabilities=DeviceCapabilities(
                supports_control=True,
                supports_state_history=True,
                supports_runtime=True,
            ),
            nominal_power_kw=0.75,
        ),
        HouseholdDevice(
            device_id="heater",
            name="Living Room Heater",
            device_type="HEATER",
            capabilities=DeviceCapabilities(
                supports_control=True,
                supports_state_history=True,
                supports_runtime=True,
                supports_device_power=True,
                supports_device_energy=True,
            ),
            nominal_power_kw=1.5,
        ),
        HouseholdDevice(
            device_id="refrigerator",
            name="Refrigerator",
            device_type="REFRIGERATOR",
            capabilities=DeviceCapabilities(
                supports_state_history=True,
                supports_runtime=True,
                supports_device_power=True,
                supports_device_energy=True,
            ),
            nominal_power_kw=0.15,
        ),
        HouseholdDevice(
            device_id="tv",
            name="TV",
            device_type="TELEVISION",
            capabilities=DeviceCapabilities(
                supports_state_history=True,
                supports_runtime=True,
            ),
            nominal_power_kw=0.1,
        ),
        HouseholdDevice(
            device_id="dishwasher",
            name="Dishwasher",
            device_type="DISHWASHER",
            capabilities=DeviceCapabilities(
                supports_control=True,
                supports_state_history=True,
                supports_runtime=True,
                has_estimated_cycle_energy=True,
            ),
            nominal_power_kw=1.2,
            estimated_cycle_kwh=5.0,
        ),
    )

    def __init__(
        self, scenario: EnergyScenario = EnergyScenario.NORMAL_CURRENT_CYCLE
    ) -> None:
        self.scenario = scenario
        self.clock = SimulationClock(self._scenario_time(scenario))
        self._seed()

    def reset(self) -> None:
        self.clock.reset()
        self._seed()

    def set_scenario(self, scenario: EnergyScenario) -> None:
        self.scenario = scenario
        self.clock = SimulationClock(self._scenario_time(scenario))
        self._seed()

    def get_billing_cycle(self) -> BillingCycle:
        return BillingCycle(
            cycle_start=self.CURRENT_START,
            cycle_end=self.CURRENT_END,
            previous_cycle_start=self.PREVIOUS_START,
            previous_cycle_end=self.PREVIOUS_END,
            current_simulated_at=self.clock.now,
        )

    def get_devices(self) -> Sequence[HouseholdDevice]:
        return self.DEVICES

    def get_household_readings(
        self, start: datetime, end: datetime
    ) -> Sequence[WholeHomeReading]:
        return tuple(reading for reading in self._household if start <= reading.timestamp <= end)

    def get_device_state_history(
        self, device_id: str, start: datetime, end: datetime
    ) -> Sequence[DeviceStateTransition]:
        self._require_device(device_id)
        history = self._state_history.get(device_id, ())
        prior = [item for item in history if item.timestamp <= start]
        within = [item for item in history if start < item.timestamp < end]
        return tuple(prior[-1:] + within)

    def get_device_energy_readings(
        self, device_id: str, start: datetime, end: datetime
    ) -> Sequence[DeviceEnergyReading]:
        self._require_device(device_id)
        readings = self._device_energy.get(device_id, ())
        return tuple(item for item in readings if start <= item.timestamp <= end)

    def _seed(self) -> None:
        self._household = self._make_household_readings()
        self._state_history = self._make_state_history()
        self._device_energy = self._make_device_energy()

    def _make_household_readings(self) -> tuple[WholeHomeReading, ...]:
        readings: list[WholeHomeReading] = []
        cumulative = 1000.0
        current_days = (
            self.NEAR_THRESHOLD_DAILY_KWH
            if self.scenario is EnergyScenario.NEAR_THRESHOLD
            else self.CURRENT_DAILY_KWH
        )
        all_days = self.PREVIOUS_DAILY_KWH + current_days
        for index in range(len(all_days) + 1):
            timestamp = self.PREVIOUS_START + timedelta(days=index)
            readings.append(
                WholeHomeReading(
                    timestamp=timestamp,
                    instantaneous_watts=600.0 + (index % 4) * 25.0,
                    cumulative_kwh=round(cumulative, 3),
                )
            )
            if index < len(all_days):
                cumulative += all_days[index]
        return tuple(readings)

    def _make_state_history(self) -> dict[str, tuple[DeviceStateTransition, ...]]:
        histories: dict[str, list[DeviceStateTransition]] = {
            device.device_id: [] for device in self.DEVICES
        }

        self._add_daily_runtime(histories["ac"], "ac", self.PREVIOUS_START, (4.0,) * 10 + (3.0,) * 4)
        self._add_daily_runtime(histories["ac"], "ac", self.CURRENT_START, (5.0,) * 13 + (8.0,))
        self._add_daily_runtime(histories["heater"], "heater", self.PREVIOUS_START, (1.0,) * 4)
        self._add_daily_runtime(histories["heater"], "heater", self.CURRENT_START, (1.0,) * 5)
        self._add_daily_runtime(histories["refrigerator"], "refrigerator", self.PREVIOUS_START, (8.0,) * 14, start_hour=1)
        self._add_daily_runtime(histories["refrigerator"], "refrigerator", self.CURRENT_START, (8.0,) * 14, start_hour=1)
        self._add_daily_runtime(histories["tv"], "tv", self.PREVIOUS_START, (3.0,) * 14, start_hour=18)
        self._add_daily_runtime(histories["tv"], "tv", self.CURRENT_START, (4.0,) * 2 + (3.0,) * 12, start_hour=18)
        self._add_daily_runtime(histories["dishwasher"], "dishwasher", self.PREVIOUS_START, (1.0,) * 8, start_hour=20)
        self._add_daily_runtime(histories["dishwasher"], "dishwasher", self.CURRENT_START, (1.0,) * 9, start_hour=20)
        return {key: tuple(sorted(value, key=lambda item: item.timestamp)) for key, value in histories.items()}

    @staticmethod
    def _add_daily_runtime(
        history: list[DeviceStateTransition],
        device_id: str,
        start: datetime,
        durations: tuple[float, ...],
        *,
        start_hour: int = 12,
    ) -> None:
        history.append(DeviceStateTransition(device_id=device_id, timestamp=start, state=ReportedState.OFF))
        for day, duration in enumerate(durations):
            on_at = start + timedelta(days=day, hours=start_hour)
            history.extend(
                (
                    DeviceStateTransition(device_id=device_id, timestamp=on_at, state=ReportedState.ON),
                    DeviceStateTransition(device_id=device_id, timestamp=on_at + timedelta(hours=duration), state=ReportedState.OFF),
                )
            )

    def _make_device_energy(self) -> dict[str, tuple[DeviceEnergyReading, ...]]:
        return {
            "heater": self._cumulative_device_readings(
                "heater",
                (1.5,) * 4 + (0.0,) * 26,
                (1.5,) * 5 + (0.0,) * 25,
            ),
            "refrigerator": self._cumulative_device_readings(
                "refrigerator", (1.0,) * 30, (1.05,) * 30
            ),
        }

    def _cumulative_device_readings(
        self,
        device_id: str,
        previous_daily: tuple[float, ...],
        current_daily: tuple[float, ...],
    ) -> tuple[DeviceEnergyReading, ...]:
        readings: list[DeviceEnergyReading] = []
        cumulative = 100.0
        starts = (self.PREVIOUS_START, self.CURRENT_START)
        for index, (start, daily) in enumerate(
            zip(starts, (previous_daily, current_daily), strict=True)
        ):
            if index == 1:
                cumulative = 100.0 + sum(previous_daily)
            for index in range(len(daily) + 1):
                readings.append(
                    DeviceEnergyReading(
                        device_id=device_id,
                        timestamp=start + timedelta(days=index),
                        cumulative_kwh=round(cumulative, 3),
                    )
                )
                if index < len(daily):
                    cumulative += daily[index]
        return tuple(readings)

    def _require_device(self, device_id: str) -> None:
        if device_id not in {device.device_id for device in self.DEVICES}:
            raise ValueError(f"Unknown device: {device_id!r}")

    @classmethod
    def _scenario_time(cls, scenario: EnergyScenario) -> datetime:
        if scenario is EnergyScenario.NEAR_THRESHOLD:
            return cls.NEAR_THRESHOLD_NOW
        return cls.DEMO_NOW
