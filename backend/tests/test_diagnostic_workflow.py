import pytest

from app.connectors import SimulatedDeviceConnector
from app.models import (
    AuditEventType,
    DiagnosticClassification,
    DeviceTelemetry,
    FaultMode,
    FinalStatus,
    ReportedState,
    SafetyAction,
    VerificationStatus,
)
from app.engines import DiagnosticEngine
from app.services import DiagnosticWorkflowService


def run(fault: FaultMode):
    connector = SimulatedDeviceConnector(fault)
    return connector, DiagnosticWorkflowService(connector).run("heater")


def test_normal_heater_succeeds_without_retry() -> None:
    _, result = run(FaultMode.NONE)

    assert result.final_status is FinalStatus.VERIFIED
    assert result.diagnostic_classification is DiagnosticClassification.OK
    assert result.resolved is True
    assert result.retries_used == 0
    assert len(result.attempts) == 1


@pytest.mark.parametrize(
    ("fault", "classification"),
    [
        (FaultMode.OFFLINE, DiagnosticClassification.CONNECTIVITY_FAILURE),
        (FaultMode.NO_DRAW, DiagnosticClassification.NO_ELECTRICAL_RESPONSE),
        (FaultMode.STANDBY_ONLY, DiagnosticClassification.STANDBY_ONLY),
        (FaultMode.START_THEN_STOP, DiagnosticClassification.START_THEN_STOP),
        (FaultMode.HIGH_DRAW, DiagnosticClassification.ABNORMAL_HIGH_DRAW),
        (FaultMode.UNDERPOWERED, DiagnosticClassification.NOT_REACHING_EXPECTED_LOAD),
    ],
)
def test_fault_telemetry_is_classified(fault, classification) -> None:
    _, result = run(fault)

    assert result.diagnostic_classification is classification
    assert result.attempts[0].diagnostic_classification is classification


def test_start_then_stop_is_derived_from_power_trace() -> None:
    _, result = run(FaultMode.START_THEN_STOP)

    assert result.attempts[0].power_samples_watts == (1500.0, 5.0)
    assert result.attempts[0].observed_watts == 5.0
    assert result.attempts[0].verification is VerificationStatus.FAILED


def test_high_draw_never_retries_and_cuts_simulated_power() -> None:
    connector, result = run(FaultMode.HIGH_DRAW)

    assert result.final_status is FinalStatus.SAFETY_STOP
    assert result.safety_action is SafetyAction.POWER_CUT_HIGH_DRAW
    assert result.retries_used == 0
    assert len(result.attempts) == 1
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


def test_high_peak_then_normal_settled_draw_still_causes_safety_stop() -> None:
    class HighPeakThenNormalConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace((2200.0, 1500.0))

    connector = HighPeakThenNormalConnector(FaultMode.NONE)

    result = DiagnosticWorkflowService(connector).run("heater")

    assert result.final_status is FinalStatus.SAFETY_STOP
    assert result.initial_verification is VerificationStatus.FAILED
    assert result.diagnostic_classification is DiagnosticClassification.ABNORMAL_HIGH_DRAW
    assert result.safety_action is SafetyAction.POWER_CUT_HIGH_DRAW
    assert result.retries_used == 0
    assert len(result.attempts) == 1
    assert result.attempts[0].power_samples_watts == (2200.0, 1500.0)
    assert result.attempts[0].observed_watts == 1500.0
    assert result.attempts[0].verification is VerificationStatus.FAILED
    assert [event.event for event in result.audit_events] == [
        AuditEventType.COMMAND_SENT,
        AuditEventType.VERIFICATION_FAILED,
        AuditEventType.DIAGNOSTIC_CLASSIFIED,
        AuditEventType.SAFETY_STOP,
        AuditEventType.WORKFLOW_COMPLETED,
    ]
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


@pytest.mark.parametrize("samples", [(2200.0, 1500.0), (2200.0,)])
def test_recorded_high_draw_precedes_unavailable_telemetry_and_never_retries(
    samples: tuple[float, ...],
) -> None:
    class HighDrawThenUnavailableConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace(samples)
            self._state.available = False

    connector = HighDrawThenUnavailableConnector(FaultMode.NONE)

    result = DiagnosticWorkflowService(connector).run("heater")

    assert result.final_status is FinalStatus.SAFETY_STOP
    assert result.diagnostic_classification is DiagnosticClassification.ABNORMAL_HIGH_DRAW
    assert result.safety_action is SafetyAction.POWER_CUT_HIGH_DRAW
    assert result.retries_used == 0
    assert len(result.attempts) == 1
    assert result.attempts[0].available is False
    assert result.attempts[0].power_samples_watts == samples
    assert 2200.0 in result.attempts[0].power_samples_watts
    assert any("unavailable" in item.lower() for item in result.evidence)
    events = [event.event for event in result.audit_events]
    assert AuditEventType.SAFETY_STOP in events
    assert AuditEventType.RETRY_STARTED not in events
    safety_event = next(
        event
        for event in result.audit_events
        if event.event is AuditEventType.SAFETY_STOP
    )
    assert "2200 W" in safety_event.detail
    assert "unavailable" in safety_event.detail.lower()
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


@pytest.mark.parametrize("samples", [(1500.0,), ()])
def test_unavailable_without_unsafe_observation_remains_connectivity_failure(
    samples: tuple[float, ...],
) -> None:
    finding = DiagnosticEngine().classify(
        profile=SimulatedDeviceConnector.HEATER,
        baseline_watts=2.0,
        telemetry=DeviceTelemetry(
            available=False,
            reported_state=ReportedState.ON,
            power_samples_watts=samples,
        ),
        verification=VerificationStatus.FAILED,
    )

    assert finding.classification is DiagnosticClassification.CONNECTIVITY_FAILURE
    assert all("high draw" not in item.lower() for item in finding.evidence)


@pytest.mark.parametrize("samples", [(1500.0,), ()])
def test_unavailable_workflow_without_unsafe_observation_does_not_invent_high_draw(
    samples: tuple[float, ...],
) -> None:
    class UnavailableConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._state.available = False
            self._state.power_samples_watts = samples

    connector = UnavailableConnector(FaultMode.NONE)

    result = DiagnosticWorkflowService(connector).run("heater")

    assert result.final_status is FinalStatus.UNRESOLVED
    assert result.diagnostic_classification is DiagnosticClassification.CONNECTIVITY_FAILURE
    assert result.retries_used == 1
    assert result.safety_action is SafetyAction.STOP_RETRYING
    assert all(
        attempt.diagnostic_classification
        is DiagnosticClassification.CONNECTIVITY_FAILURE
        for attempt in result.attempts
    )
    assert AuditEventType.SAFETY_STOP not in {
        event.event for event in result.audit_events
    }
    assert connector.get_reported_state("heater") is ReportedState.ON


def test_persistent_failure_uses_exactly_policy_retry_limit() -> None:
    connector, result = run(FaultMode.NO_DRAW)

    assert result.final_status is FinalStatus.UNRESOLVED
    assert result.retries_used == connector.HEATER.safety_policy.max_retries == 1
    assert len(result.attempts) == 2
    assert [attempt.attempt for attempt in result.attempts] == [1, 2]
    assert all(
        attempt.verification is VerificationStatus.FAILED
        for attempt in result.attempts
    )
    assert result.safety_action is SafetyAction.STOP_RETRYING


def test_recoverable_failure_succeeds_after_one_retry() -> None:
    _, result = run(FaultMode.NO_DRAW_THEN_RECOVER)

    assert result.final_status is FinalStatus.RECOVERED
    assert result.resolved is True
    assert result.retries_used == 1
    assert [attempt.verification for attempt in result.attempts] == [
        VerificationStatus.FAILED,
        VerificationStatus.VERIFIED,
    ]
    assert [attempt.diagnostic_classification for attempt in result.attempts] == [
        DiagnosticClassification.NO_ELECTRICAL_RESPONSE,
        DiagnosticClassification.OK,
    ]


def test_evidence_is_derived_and_returned() -> None:
    _, result = run(FaultMode.UNDERPOWERED)

    assert result.evidence
    assert any("650 W" in item for item in result.evidence)
    assert "may require inspection" in result.speakable_summary


def test_persistent_failure_audit_events_are_in_logical_order() -> None:
    _, result = run(FaultMode.NO_DRAW)

    assert [event.event for event in result.audit_events] == [
        AuditEventType.COMMAND_SENT,
        AuditEventType.VERIFICATION_FAILED,
        AuditEventType.DIAGNOSTIC_CLASSIFIED,
        AuditEventType.RETRY_STARTED,
        AuditEventType.COMMAND_SENT,
        AuditEventType.VERIFICATION_FAILED,
        AuditEventType.DIAGNOSTIC_CLASSIFIED,
        AuditEventType.RETRY_FAILED,
        AuditEventType.WORKFLOW_COMPLETED,
    ]
    assert [event.sequence for event in result.audit_events] == list(
        range(1, len(result.audit_events) + 1)
    )


def test_high_draw_audit_records_safety_stop_without_retry_event() -> None:
    _, result = run(FaultMode.HIGH_DRAW)
    events = [event.event for event in result.audit_events]

    assert AuditEventType.SAFETY_STOP in events
    assert AuditEventType.RETRY_STARTED not in events
    assert events[-1] is AuditEventType.WORKFLOW_COMPLETED


def test_recoverable_audit_records_retry_success() -> None:
    _, result = run(FaultMode.NO_DRAW_THEN_RECOVER)
    events = [event.event for event in result.audit_events]

    assert AuditEventType.RETRY_STARTED in events
    assert AuditEventType.RETRY_SUCCEEDED in events
    assert events[-1] is AuditEventType.WORKFLOW_COMPLETED


def test_reset_replays_recoverable_fixture_deterministically() -> None:
    connector = SimulatedDeviceConnector(FaultMode.NO_DRAW_THEN_RECOVER)
    service = DiagnosticWorkflowService(connector)
    first = service.run("heater")

    connector.reset()
    second = service.run("heater")

    assert second == first

