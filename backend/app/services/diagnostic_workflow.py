from app.connectors import DeviceConnector
from app.engines import DiagnosticEngine, SafetyEngine
from app.models import (
    AttemptResult,
    AuditEvent,
    AuditEventType,
    DiagnosticClassification,
    DiagnosticWorkflowResult,
    FinalStatus,
    SafetyAction,
    VerificationStatus,
)

from .verification import VerificationService


class DiagnosticWorkflowService:
    def __init__(
        self,
        connector: DeviceConnector,
        *,
        diagnostic_engine: DiagnosticEngine | None = None,
        safety_engine: SafetyEngine | None = None,
    ) -> None:
        self._connector = connector
        self._diagnostic = diagnostic_engine or DiagnosticEngine()
        self._safety = safety_engine or SafetyEngine()

    def run(self, device_id: str) -> DiagnosticWorkflowResult:
        profile = self._connector.get_profile(device_id)
        attempts: list[AttemptResult] = []
        audit: list[AuditEvent] = []
        retries_used = 0
        safety_action = SafetyAction.NONE

        while True:
            attempt_number = len(attempts) + 1
            baseline = self._connector.read_power(device_id, sample="baseline")
            self._connector.turn_on(device_id)
            self._record(
                audit,
                AuditEventType.COMMAND_SENT,
                attempt_number,
                "ON command sent to simulated connector.",
            )
            settled_reading = self._connector.read_power(
                device_id, sample="settled"
            )
            telemetry = self._connector.get_telemetry(device_id)
            verification = VerificationService.verify_telemetry(
                profile=profile, telemetry=telemetry
            )
            finding = self._diagnostic.classify(
                profile=profile,
                baseline_watts=baseline.watts,
                telemetry=telemetry,
                verification=verification,
            )
            # A settled reading can look normal after an unsafe peak. The peak
            # governs the workflow, so this attempt must fail closed and flow
            # through the existing high-draw power-cut policy.
            if finding.classification is DiagnosticClassification.ABNORMAL_HIGH_DRAW:
                verification = VerificationStatus.FAILED
            observed = (
                telemetry.power_samples_watts[-1]
                if telemetry.power_samples_watts
                else settled_reading.watts
            )
            attempt = AttemptResult(
                attempt=attempt_number,
                reported_state=telemetry.reported_state,
                available=telemetry.available,
                baseline_watts=baseline.watts,
                power_samples_watts=telemetry.power_samples_watts,
                observed_watts=observed,
                observed_power_delta_watts=round(observed - baseline.watts, 2),
                verification=verification,
                diagnostic_classification=finding.classification,
                confidence=finding.confidence,
                evidence=finding.evidence,
            )
            attempts.append(attempt)

            if verification is VerificationStatus.VERIFIED:
                if retries_used:
                    self._record(
                        audit,
                        AuditEventType.RETRY_SUCCEEDED,
                        attempt_number,
                        "Retry produced a verified electrical response.",
                    )
                self._record(
                    audit,
                    AuditEventType.WORKFLOW_COMPLETED,
                    attempt_number,
                    "Expected electrical response verified.",
                )
                status = FinalStatus.RECOVERED if retries_used else FinalStatus.VERIFIED
                return self._result(
                    device_id=device_id,
                    attempts=attempts,
                    audit=audit,
                    retries_used=retries_used,
                    final_status=status,
                    safety_action=SafetyAction.NONE,
                    resolved=True,
                    profile_name=profile.name,
                )

            self._record(
                audit,
                AuditEventType.VERIFICATION_FAILED,
                attempt_number,
                "Expected electrical response could not be verified.",
            )
            self._record(
                audit,
                AuditEventType.DIAGNOSTIC_CLASSIFIED,
                attempt_number,
                f"Observed evidence classified as {finding.classification.value}.",
            )
            decision = self._safety.decide(
                profile=profile,
                classification=finding.classification,
                retries_used=retries_used,
            )
            safety_action = decision.action

            if decision.cut_power:
                self._connector.turn_off(device_id)
                trigger_watts = max(telemetry.power_samples_watts)
                availability_context = (
                    " Telemetry was unavailable after the recorded observation."
                    if not telemetry.available
                    else ""
                )
                self._record(
                    audit,
                    AuditEventType.SAFETY_STOP,
                    attempt_number,
                    f"Abnormal high draw detected at {trigger_watts:.0f} W; "
                    "simulated device power was cut."
                    f"{availability_context}",
                )
                self._record(
                    audit,
                    AuditEventType.WORKFLOW_COMPLETED,
                    attempt_number,
                    "Workflow ended with a safety stop and no retry.",
                )
                return self._result(
                    device_id=device_id,
                    attempts=attempts,
                    audit=audit,
                    retries_used=retries_used,
                    final_status=FinalStatus.SAFETY_STOP,
                    safety_action=safety_action,
                    resolved=False,
                    profile_name=profile.name,
                )

            if decision.retry_allowed:
                retries_used += 1
                self._record(
                    audit,
                    AuditEventType.RETRY_STARTED,
                    attempt_number + 1,
                    f"Safe retry {retries_used} started.",
                )
                continue

            if retries_used:
                self._record(
                    audit,
                    AuditEventType.RETRY_FAILED,
                    attempt_number,
                    "Retry did not produce a verified electrical response.",
                )
            self._record(
                audit,
                AuditEventType.WORKFLOW_COMPLETED,
                attempt_number,
                "Retry policy exhausted; workflow remains unresolved.",
            )
            return self._result(
                device_id=device_id,
                attempts=attempts,
                audit=audit,
                retries_used=retries_used,
                final_status=FinalStatus.UNRESOLVED,
                safety_action=safety_action,
                resolved=False,
                profile_name=profile.name,
            )

    @staticmethod
    def _record(
        events: list[AuditEvent],
        event: AuditEventType,
        attempt: int | None,
        detail: str,
    ) -> None:
        events.append(
            AuditEvent(
                sequence=len(events) + 1,
                event=event,
                attempt=attempt,
                detail=detail,
            )
        )

    @staticmethod
    def _result(
        *,
        device_id: str,
        attempts: list[AttemptResult],
        audit: list[AuditEvent],
        retries_used: int,
        final_status: FinalStatus,
        safety_action: SafetyAction,
        resolved: bool,
        profile_name: str,
    ) -> DiagnosticWorkflowResult:
        final_attempt = attempts[-1]
        if final_status is FinalStatus.VERIFIED:
            summary = (
                f"{profile_name} reports on, and its expected electrical response "
                "was verified."
            )
        elif final_status is FinalStatus.RECOVERED:
            summary = (
                f"{profile_name} did not respond normally at first, but its expected "
                "electrical response was verified after one safe retry."
            )
        elif final_status is FinalStatus.SAFETY_STOP:
            summary = (
                f"{profile_name} showed abnormally high electrical draw, so I stopped "
                "it without retrying. It may require inspection."
            )
        else:
            classification = final_attempt.diagnostic_classification
            retry_text = (
                "after one safe retry" if retries_used == 1 else "without a safe retry"
            )
            if classification is DiagnosticClassification.CONNECTIVITY_FAILURE:
                summary = (
                    f"I couldn't reach {profile_name} {retry_text}, so I can't verify "
                    "its operation."
                )
            elif classification is DiagnosticClassification.START_THEN_STOP:
                summary = (
                    f"{profile_name}'s electrical behavior is consistent with starting "
                    f"and then stopping {retry_text}. It may require inspection."
                )
            elif classification is DiagnosticClassification.STANDBY_ONLY:
                summary = (
                    f"{profile_name} reports that it's on, but remained near standby "
                    f"power {retry_text}. It may require inspection."
                )
            elif classification is DiagnosticClassification.NOT_REACHING_EXPECTED_LOAD:
                summary = (
                    f"{profile_name} reports that it's on, but did not reach its "
                    f"configured running range {retry_text}. It may require inspection."
                )
            else:
                summary = (
                    f"{profile_name} reports that it's on, but I still can't verify "
                    f"normal electrical operation {retry_text}. It may require inspection."
                )

        evidence = tuple(
            dict.fromkeys(item for attempt in attempts for item in attempt.evidence)
        )
        return DiagnosticWorkflowResult(
            device=device_id,
            requested_action="ON",
            final_status=final_status,
            initial_verification=attempts[0].verification,
            diagnostic_classification=final_attempt.diagnostic_classification,
            confidence=final_attempt.confidence,
            attempts=tuple(attempts),
            retries_used=retries_used,
            safety_action=safety_action,
            resolved=resolved,
            evidence=evidence,
            audit_events=tuple(audit),
            speakable_summary=summary,
        )
