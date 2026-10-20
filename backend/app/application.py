from datetime import UTC, datetime
import os

from app.config import ApplicationMode, Settings
from app.connectors import SimulatedDeviceConnector
from app.engines import RuntimeEngine
from app.errors import DeviceNotFoundError, VoltWiseError
from app.models import (
    ApplicationEvent,
    ApplicationEventType,
    AuditEventType,
    BillForecast,
    DemoState,
    DeviceControlResult,
    DeviceView,
    DiagnosticWorkflowResult,
    EnergyScenario,
    FaultMode,
    HouseholdOverview,
    LoadImpactResult,
    PeriodComparisonResult,
    ReportedState,
    TariffStatus,
    UsageChangeExplanation,
    VerificationResult,
    ActionSuggestions,
)
from app.repositories import EventRepository, FixtureEnergyRepository, SQLiteEventRepository
from app.services import (
    DiagnosticWorkflowService,
    EnergyIntelligenceService,
    TariffIntelligenceService,
    VerificationService,
)
from app.tariffs import illustrative_demo_tariff


class VoltWiseApplication:
    SCENARIO_STATE_KEY = "energy_scenario"
    FAULT_STATE_KEY = "heater_fault"
    RESET_GENERATION_STATE_KEY = "demo_reset_generation"

    def __init__(
        self,
        settings: Settings,
        *,
        event_repository: EventRepository | None = None,
        initial_scenario: EnergyScenario = EnergyScenario.NORMAL_CURRENT_CYCLE,
        initial_fault: FaultMode = FaultMode.NONE,
    ) -> None:
        if settings.mode is not ApplicationMode.SIMULATION:
            raise NotImplementedError("Only SIMULATION mode is currently supported")
        self.settings = settings
        self.event_repository = event_repository or SQLiteEventRepository(
            settings.database_path
        )
        self._reset_generation = self.event_repository.get_state(
            self.RESET_GENERATION_STATE_KEY
        )
        scenario = EnergyScenario(
            self.event_repository.get_state(self.SCENARIO_STATE_KEY)
            or initial_scenario.value
        )
        fault = FaultMode(
            self.event_repository.get_state(self.FAULT_STATE_KEY) or initial_fault.value
        )
        self.connector = SimulatedDeviceConnector(fault)
        self.energy_repository = FixtureEnergyRepository(scenario)
        self.verification_service = VerificationService(self.connector)
        self.diagnostic_service = DiagnosticWorkflowService(self.connector)
        self.energy_service = EnergyIntelligenceService(self.energy_repository)
        self.tariff_service = TariffIntelligenceService(
            self.energy_repository, illustrative_demo_tariff()
        )

    def turn_on_and_verify(self, device_id: str) -> VerificationResult:
        device_id = device_id.lower().strip()
        self._require_controllable_device(device_id)
        self._event(
            ApplicationEventType.DEVICE_COMMAND,
            device_id,
            "TURN_ON",
            "SENT",
        )
        result = self.verification_service.turn_on_and_verify(device_id)
        self._event(
            ApplicationEventType.VERIFICATION,
            device_id,
            "TURN_ON_AND_VERIFY",
            result.verification.value,
            {"confidence": result.confidence},
        )
        profile = self.connector.get_profile(device_id)
        if result.observed_power_watts >= profile.abnormal_high_draw_threshold:
            self._event(
                ApplicationEventType.SAFETY_STOP,
                device_id,
                "POWER_CUT_HIGH_DRAW",
                "SAFETY_STOP",
                {
                    "trigger_watts": result.observed_power_watts,
                    "final_reported_state": self.connector.get_reported_state(
                        device_id
                    ).value,
                },
            )
        return result

    def control_device(self, device_id: str, command: str = "TURN_ON") -> DeviceControlResult:
        device_id = device_id.lower().strip()
        cmd = command.upper().strip()
        names = {
            "light": "Living Room Light",
            "fan": "Ceiling Fan",
            "tv": "TV",
            "ac": "Air Conditioner",
            "dishwasher": "Dishwasher",
            "heater": "Living Room Heater",
        }
        if device_id not in names:
            raise VoltWiseError(
                "DEVICE_OPERATION_UNAVAILABLE",
                f"Ordinary control is not configured for device: {device_id}",
            )
        if device_id == "heater":
            if cmd in ("TURN_OFF", "OFF"):
                self.connector.turn_off("heater")
                self._event(
                    ApplicationEventType.DEVICE_COMMAND,
                    "heater",
                    "TURN_OFF",
                    "OFF",
                )
                return DeviceControlResult(
                    device="heater",
                    name="Living Room Heater",
                    command="TURN_OFF",
                    reported_state=ReportedState.OFF,
                    success=True,
                    speakable_summary="Turned off the living room heater.",
                )
            raise VoltWiseError(
                "DEVICE_OPERATION_UNAVAILABLE",
                "To turn on the heater, use physical verification.",
            )
        state = self.connector.control_ordinary_device(device_id, cmd)
        name = names[device_id]
        action_verb = "on" if state is ReportedState.ON else "off"
        summary = f"Turned {action_verb} the {name.lower()}."
        self._event(
            ApplicationEventType.DEVICE_COMMAND,
            device_id,
            cmd,
            state.value,
        )
        return DeviceControlResult(
            device=device_id,
            name=name,
            command=cmd,
            reported_state=state,
            success=True,
            speakable_summary=summary,
        )

    def run_diagnostic(self, device_id: str) -> DiagnosticWorkflowResult:
        device_id = device_id.lower().strip()
        self._require_controllable_device(device_id)
        result = self.diagnostic_service.run(device_id)
        for audit in result.audit_events:
            event_type = self._audit_event_type(audit.event)
            self._event(
                event_type,
                device_id,
                audit.event.value,
                result.final_status.value,
                {"attempt": audit.attempt, "sequence": audit.sequence},
            )
        return result

    def compare_periods(self) -> PeriodComparisonResult:
        result = self.energy_service.compare_periods()
        self._event(
            ApplicationEventType.ENERGY_QUERY,
            None,
            "COMPARE_PERIODS",
            "COMPLETED",
            {"current_kwh": result.current_kwh},
        )
        return result

    def explain_usage_change(self) -> UsageChangeExplanation:
        result = self.energy_service.explain_usage_change()
        self._event(
            ApplicationEventType.ENERGY_QUERY,
            None,
            "EXPLAIN_USAGE_CHANGE",
            "COMPLETED",
            {"unattributed_kwh": result.unattributed_kwh},
        )
        return result

    def get_tariff_status(self) -> TariffStatus:
        result = self.tariff_service.get_status()
        self._event(
            ApplicationEventType.TARIFF_QUERY,
            None,
            "GET_TARIFF_STATUS",
            result.threshold_warning.value,
        )
        return result

    def forecast_bill(self) -> BillForecast:
        result = self.tariff_service.forecast_bill()
        self._event(
            ApplicationEventType.TARIFF_QUERY,
            None,
            "FORECAST_BILL",
            "COMPLETED",
        )
        return result

    def estimate_load_impact(self, device_id: str) -> LoadImpactResult:
        device_id = device_id.lower().strip()
        self._require_device(device_id)
        try:
            result = self.tariff_service.estimate_load_impact(device_id)
        except ValueError as exc:
            raise VoltWiseError("LOAD_IMPACT_UNAVAILABLE", str(exc)) from exc
        self._event(
            ApplicationEventType.TARIFF_QUERY,
            device_id,
            "ESTIMATE_LOAD_IMPACT",
            "THRESHOLD_CROSSED" if result.threshold_crossed else "COMPLETED",
        )
        return result

    def suggest_actions(self, target_kwh: float | None = None) -> ActionSuggestions:
        if target_kwh is not None and target_kwh <= 0:
            raise VoltWiseError("INVALID_TARGET", "target_kwh must be greater than zero")
        result = self.tariff_service.suggest_actions(target_kwh)
        self._event(
            ApplicationEventType.TARIFF_QUERY,
            None,
            "SUGGEST_ACTIONS",
            result.target_status.value if result.target_status else "COMPLETED",
        )
        return result

    def household_overview(self) -> HouseholdOverview:
        comparison = self.energy_service.compare_periods()
        tariff = self.tariff_service.get_status()
        cycle = self.energy_repository.get_billing_cycle()
        return HouseholdOverview(
            simulated_at=cycle.current_simulated_at,
            energy_scenario=self.energy_repository.scenario,
            current_cycle_kwh=comparison.current_kwh,
            previous_equivalent_kwh=comparison.previous_equivalent_kwh,
            change_percent=comparison.change_percent,
            projected_month_end_kwh=comparison.projection.projected_kwh,
            tariff_warning=tariff.threshold_warning,
            current_estimated_energy_charge=str(
                tariff.current_estimated_energy_charge
            ),
            projected_estimated_energy_charge=str(
                tariff.projected_estimated_energy_charge
            ),
            devices=self.list_devices(),
        )

    def list_devices(self) -> tuple[DeviceView, ...]:
        return tuple(self.get_device(device.device_id) for device in self.energy_repository.get_devices())

    def get_device(self, device_id: str) -> DeviceView:
        device_id = device_id.lower().strip()
        device = self._require_device(device_id)
        cycle = self.energy_repository.get_billing_cycle()
        history = self.energy_repository.get_device_state_history(
            device_id, cycle.cycle_start, cycle.current_simulated_at
        )
        reported = history[-1].state if history else None
        runtime = (
            RuntimeEngine.calculate_hours(
                history, cycle.cycle_start, cycle.current_simulated_at
            )
            if device.capabilities.supports_runtime
            else None
        )
        physical = None
        available = True
        watts = None
        profile = None
        evidence = []
        simulation_fields: tuple[str, ...] = ()
        if device_id == "heater":
            telemetry = self.connector.get_telemetry("heater")
            reported = telemetry.reported_state
            physical = self.connector.get_actual_state("heater")
            available = telemetry.available
            watts = telemetry.power_samples_watts[-1]
            profile = self.connector.get_profile("heater")
            evidence.append(f"Latest simulated device power: {watts:.0f} W")
            simulation_fields = ("physical_state", "heater_fault")
        elif reported is not None:
            ordinary = self.connector.get_ordinary_state(device_id)
            if ordinary is not None:
                reported = ordinary
            evidence.append("Latest state is derived from simulated state history.")
        return DeviceView(
            device_id=device.device_id,
            name=device.name,
            device_type=device.device_type,
            reported_state=reported,
            physical_state=physical,
            available=available,
            capabilities=device.capabilities,
            current_watts=watts,
            current_runtime_hours=runtime,
            electrical_profile=profile,
            recent_evidence=tuple(evidence),
            simulation_only_fields=simulation_fields,
        )

    def demo_state(self) -> DemoState:
        return DemoState(
            mode=self.settings.mode.value,
            energy_scenario=self.energy_repository.scenario,
            heater_fault=self.connector.heater_fault,
            simulated_at=self.energy_repository.clock.now,
        )

    def set_energy_scenario(self, scenario: EnergyScenario) -> DemoState:
        self.energy_repository.set_scenario(scenario)
        self.event_repository.set_state(self.SCENARIO_STATE_KEY, scenario.value)
        self._event(
            ApplicationEventType.SCENARIO_CHANGED,
            None,
            "SET_ENERGY_SCENARIO",
            scenario.value,
        )
        return self.demo_state()

    def set_device_fault(self, device_id: str, fault: FaultMode) -> DemoState:
        device_id = device_id.lower().strip()
        self._require_controllable_device(device_id)
        self.connector.set_fault(fault)
        self.event_repository.set_state(self.FAULT_STATE_KEY, fault.value)
        self._event(
            ApplicationEventType.FAULT_CHANGED,
            device_id,
            "SET_DEVICE_FAULT",
            fault.value,
        )
        return self.demo_state()

    def reset_demo(self) -> DemoState:
        self.energy_repository.set_scenario(EnergyScenario.NORMAL_CURRENT_CYCLE)
        self.connector.set_fault(FaultMode.NONE)
        self.event_repository.set_state(
            self.SCENARIO_STATE_KEY, EnergyScenario.NORMAL_CURRENT_CYCLE.value
        )
        self.event_repository.set_state(self.FAULT_STATE_KEY, FaultMode.NONE.value)
        generation = str(
            int(
                self.event_repository.get_state(self.RESET_GENERATION_STATE_KEY)
                or "0"
            )
            + 1
        )
        self.event_repository.set_state(self.RESET_GENERATION_STATE_KEY, generation)
        self._reset_generation = generation
        self._event(
            ApplicationEventType.DEMO_RESET,
            None,
            "RESET_DEMO",
            "COMPLETED",
        )
        return self.demo_state()

    def recent_events(self, limit: int = 50):
        return self.event_repository.recent(limit)

    def refresh_persisted_demo_state(self) -> None:
        """Adopt demo controls changed by another local adapter process."""

        scenario_value = self.event_repository.get_state(self.SCENARIO_STATE_KEY)
        if scenario_value is not None:
            scenario = EnergyScenario(scenario_value)
            if self.energy_repository.scenario is not scenario:
                self.energy_repository.set_scenario(scenario)
        fault_value = self.event_repository.get_state(self.FAULT_STATE_KEY)
        if fault_value is not None:
            fault = FaultMode(fault_value)
            if self.connector.heater_fault is not fault:
                self.connector.set_fault(fault)
        reset_generation = self.event_repository.get_state(
            self.RESET_GENERATION_STATE_KEY
        )
        if (
            reset_generation is not None
            and reset_generation != self._reset_generation
        ):
            # REST and MCP run in separate processes. A generation change must
            # clear transient connector and clock state even when the selected
            # scenario and fault values themselves did not change.
            self.energy_repository.reset()
            self.connector.reset()
            self._reset_generation = reset_generation

    def _require_device(self, device_id: str):
        normalized = device_id.lower().strip()
        for device in self.energy_repository.get_devices():
            if device.device_id == normalized:
                return device
        raise DeviceNotFoundError(device_id)

    def _require_controllable_device(self, device_id: str) -> None:
        device = self._require_device(device_id)
        if device.device_id != "heater":
            raise VoltWiseError(
                "DEVICE_OPERATION_UNAVAILABLE",
                f"Verification is not configured for device: {device_id}",
            )

    def _event(
        self,
        event_type: ApplicationEventType,
        device_id: str | None,
        action: str,
        outcome: str,
        details: dict[str, str | int | float | bool | None] | None = None,
    ) -> ApplicationEvent:
        return self.event_repository.append(
            ApplicationEvent(
                timestamp=datetime.now(UTC),
                event_type=event_type,
                device_id=device_id,
                action=action,
                outcome=outcome,
                details=details or {},
            )
        )

    @staticmethod
    def _audit_event_type(event: AuditEventType) -> ApplicationEventType:
        if event in (AuditEventType.RETRY_STARTED, AuditEventType.RETRY_SUCCEEDED, AuditEventType.RETRY_FAILED):
            return ApplicationEventType.RETRY
        if event is AuditEventType.SAFETY_STOP:
            return ApplicationEventType.SAFETY_STOP
        if event is AuditEventType.COMMAND_SENT:
            return ApplicationEventType.DEVICE_COMMAND
        if event is AuditEventType.VERIFICATION_FAILED:
            return ApplicationEventType.VERIFICATION
        return ApplicationEventType.DIAGNOSTIC


_default_application: VoltWiseApplication | None = None


def get_application(settings: Settings | None = None) -> VoltWiseApplication:
    global _default_application
    if settings is not None:
        return VoltWiseApplication(settings)
    if _default_application is None:
        scenario = EnergyScenario(
            os.getenv(
                "VOLTWISE_ENERGY_SCENARIO",
                EnergyScenario.NORMAL_CURRENT_CYCLE.value,
            ).upper()
        )
        fault = FaultMode(
            os.getenv("VOLTWISE_HEATER_FAULT", FaultMode.NONE.value).upper()
        )
        _default_application = VoltWiseApplication(
            Settings.from_environment(),
            initial_scenario=scenario,
            initial_fault=fault,
        )
    return _default_application
