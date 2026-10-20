from app.connectors import DeviceConnector
from app.engines import DiagnosticEngine, SafetyEngine
from app.models import (
    ConfidenceLevel,
    DeviceProfile,
    DeviceTelemetry,
    ReportedState,
    VerificationResult,
    VerificationStatus,
)


class VerificationService:
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

    def turn_on_and_verify(self, device_id: str) -> VerificationResult:
        profile = self._connector.get_profile(device_id)
        baseline = self._connector.read_power(device_id, sample="baseline")
        self._connector.turn_on(device_id)
        reported_state = self._connector.get_reported_state(device_id)
        observed = self._connector.read_power(device_id, sample="settled")
        telemetry = self._connector.get_telemetry(device_id)
        result_observed_watts = observed.watts
        status = self.verify_telemetry(profile=profile, telemetry=telemetry)
        finding = self._diagnostic.classify(
            profile=profile,
            baseline_watts=baseline.watts,
            telemetry=telemetry,
            verification=status,
        )
        safety = self._safety.decide(
            profile=profile,
            classification=finding.classification,
            retries_used=0,
        )
        if safety.cut_power:
            result_observed_watts = max(telemetry.power_samples_watts)
            self._connector.turn_off(device_id)
            status = VerificationStatus.FAILED
            confidence = finding.confidence
            reason = "Abnormal high draw detected; simulated power was cut."
            summary = (
                f"{profile.name} reported on and drew {result_observed_watts:.0f} watts, "
                "above its configured safety limit, so simulated power was cut "
                "without retrying."
            )
            if not telemetry.available:
                reason += " Telemetry was unavailable after the recorded observation."
                summary += " Telemetry was unavailable after that recorded observation."
        elif status is VerificationStatus.VERIFIED:
            confidence = 0.98
            reason = "Direct device-level power is within the expected running range."
            summary = (
                f"{profile.name} reports on, and its measured electrical response "
                "was verified."
            )
        else:
            status = VerificationStatus.FAILED
            confidence = 0.92
            reason = "No expected electrical response detected."
            summary = (
                f"{profile.name} reports on, but I cannot verify normal electrical "
                "operation based on the available device-level power reading."
            )

        return VerificationResult(
            device=device_id,
            command="ON",
            reported_state=reported_state,
            verification=status,
            expected_power_watts=profile.expected_power_watts,
            observed_power_delta_watts=round(
                result_observed_watts - baseline.watts, 2
            ),
            observed_power_watts=result_observed_watts,
            confidence=confidence,
            confidence_level=ConfidenceLevel.HIGH,
            evidence_source="DEVICE_LEVEL_POWER",
            telemetry_available=telemetry.available,
            diagnostic_classification=finding.classification.value,
            reason=reason,
            speakable_summary=summary,
        )

    @staticmethod
    def verify_telemetry(
        *, profile: DeviceProfile, telemetry: DeviceTelemetry
    ) -> VerificationStatus:
        if not telemetry.power_samples_watts:
            return VerificationStatus.FAILED
        settled_watts = telemetry.power_samples_watts[-1]
        if (
            telemetry.available
            and telemetry.reported_state is ReportedState.ON
            and profile.acceptable_running_min
            <= settled_watts
            <= profile.acceptable_running_max
        ):
            return VerificationStatus.VERIFIED
        return VerificationStatus.FAILED

