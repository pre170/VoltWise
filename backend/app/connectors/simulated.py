from dataclasses import dataclass

from app.models import (
    ActualState,
    DeviceProfile,
    DeviceTelemetry,
    FaultMode,
    HighDrawBehavior,
    PowerReading,
    ReportedState,
    SafetyPolicy,
)


@dataclass
class _SimulatedDeviceState:
    available: bool
    reported_state: ReportedState
    actual_state: ActualState
    watts: float
    power_samples_watts: tuple[float, ...]


class SimulatedDeviceConnector:
    """Deterministic Level C heater simulation; no random values or real waits."""

    HEATER = DeviceProfile(
        device_id="heater",
        name="Living Room Heater",
        expected_running_watts=1500.0,
        standby_watts=2.0,
        acceptable_running_min=1200.0,
        acceptable_running_max=1700.0,
        abnormal_high_draw_threshold=1900.0,
        startup_min_watts=1200.0,
        no_response_delta_watts=10.0,
        standby_tolerance_watts=3.0,
        safety_policy=SafetyPolicy(
            max_retries=1,
            allow_retry=True,
            allow_power_cycle=False,
            cooldown_seconds=0,
            high_draw_behavior=HighDrawBehavior.STOP_AND_CUT_POWER,
            requires_confirmation_for_power_cycle=True,
        ),
    )

    def __init__(self, heater_fault: FaultMode = FaultMode.NONE) -> None:
        self._heater_fault = heater_fault
        self._ordinary_states: dict[str, ReportedState] = {
            "light": ReportedState.OFF,
            "fan": ReportedState.OFF,
            "tv": ReportedState.OFF,
            "ac": ReportedState.OFF,
            "dishwasher": ReportedState.OFF,
        }
        self.reset()

    def reset(self) -> None:
        self._command_count = 0
        self._state = _SimulatedDeviceState(
            available=True,
            reported_state=ReportedState.OFF,
            actual_state=ActualState.OFF,
            watts=self.HEATER.standby_power_watts,
            power_samples_watts=(self.HEATER.standby_watts,),
        )
        self._ordinary_states = {
            "light": ReportedState.OFF,
            "fan": ReportedState.OFF,
            "tv": ReportedState.OFF,
            "ac": ReportedState.OFF,
            "dishwasher": ReportedState.OFF,
        }

    def control_ordinary_device(self, device_id: str, command: str) -> ReportedState:
        normalized_id = device_id.lower().strip()
        if normalized_id not in self._ordinary_states:
            raise ValueError(f"Unknown ordinary device: {device_id!r}")
        normalized_cmd = command.upper().strip()
        state = ReportedState.ON if normalized_cmd in ("TURN_ON", "ON") else ReportedState.OFF
        self._ordinary_states[normalized_id] = state
        return state

    def get_ordinary_state(self, device_id: str) -> ReportedState | None:
        return self._ordinary_states.get(device_id.lower().strip())

    def set_fault(self, fault: FaultMode) -> None:
        self._heater_fault = fault
        self.reset()

    def get_profile(self, device_id: str) -> DeviceProfile:
        self._require_heater(device_id)
        return self.HEATER

    def read_power(self, device_id: str, *, sample: str) -> PowerReading:
        self._require_heater(device_id)
        return PowerReading(device_id=device_id, watts=self._state.watts, sample=sample)

    def turn_on(self, device_id: str) -> None:
        self._require_heater(device_id)
        self._command_count += 1
        fault = self._heater_fault
        if fault is FaultMode.NO_DRAW_THEN_RECOVER and self._command_count > 1:
            fault = FaultMode.NONE

        if fault is FaultMode.OFFLINE:
            self._state.available = False
            self._state.reported_state = ReportedState.OFF
            self._state.actual_state = ActualState.OFF
            self._set_power_trace((self.HEATER.standby_watts,))
            return

        self._state.available = True
        self._state.reported_state = ReportedState.ON
        if fault in (FaultMode.NO_DRAW, FaultMode.NO_DRAW_THEN_RECOVER):
            self._state.actual_state = ActualState.FAILED
            self._set_power_trace((7.0,))
        elif fault is FaultMode.STANDBY_ONLY:
            self._state.actual_state = ActualState.FAILED
            self._set_power_trace((5.0,))
        elif fault is FaultMode.START_THEN_STOP:
            self._state.actual_state = ActualState.FAILED
            self._set_power_trace((1500.0, 5.0))
        elif fault is FaultMode.HIGH_DRAW:
            self._state.actual_state = ActualState.RUNNING
            self._set_power_trace((2200.0,))
        elif fault is FaultMode.UNDERPOWERED:
            self._state.actual_state = ActualState.RUNNING
            self._set_power_trace((650.0,))
        else:
            self._state.actual_state = ActualState.RUNNING
            self._set_power_trace((self.HEATER.expected_running_watts,))

    def turn_off(self, device_id: str) -> None:
        self._require_heater(device_id)
        self._state.reported_state = ReportedState.OFF
        self._state.actual_state = ActualState.OFF
        self._set_power_trace((self.HEATER.standby_watts,))

    def get_reported_state(self, device_id: str) -> ReportedState:
        self._require_heater(device_id)
        return self._state.reported_state

    def get_actual_state(self, device_id: str) -> ActualState:
        self._require_heater(device_id)
        return self._state.actual_state

    @property
    def heater_fault(self) -> FaultMode:
        return self._heater_fault

    def get_telemetry(self, device_id: str) -> DeviceTelemetry:
        self._require_heater(device_id)
        return DeviceTelemetry(
            available=self._state.available,
            reported_state=self._state.reported_state,
            power_samples_watts=self._state.power_samples_watts,
        )

    def _set_power_trace(self, samples: tuple[float, ...]) -> None:
        self._state.power_samples_watts = samples
        self._state.watts = samples[-1]

    @staticmethod
    def _require_heater(device_id: str) -> None:
        if device_id != "heater":
            raise ValueError(f"Unknown device: {device_id!r}. Available device: 'heater'.")

