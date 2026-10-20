from app.models import (
    DeviceProfile,
    DeviceTelemetry,
    DiagnosticClassification,
    DiagnosticFinding,
    ReportedState,
    VerificationStatus,
)


class DiagnosticEngine:
    """Classifies observed evidence; it has no knowledge of simulator fault names."""

    def classify(
        self,
        *,
        profile: DeviceProfile,
        baseline_watts: float,
        telemetry: DeviceTelemetry,
        verification: VerificationStatus,
    ) -> DiagnosticFinding:
        samples = telemetry.power_samples_watts
        if samples and max(samples) >= profile.abnormal_high_draw_threshold:
            peak = max(samples)
            evidence = [
                f"Peak measured power was {peak:.0f} W.",
                f"The safety threshold is {profile.abnormal_high_draw_threshold:.0f} W.",
            ]
            if not telemetry.available:
                evidence.append(
                    "Telemetry was unavailable after the recorded power observation."
                )
            return self._finding(
                DiagnosticClassification.ABNORMAL_HIGH_DRAW,
                0.99,
                *evidence,
            )
        if not telemetry.available:
            evidence = ["Device was unavailable when the command was attempted."]
            if samples:
                evidence.append("No unsafe high-draw observation was recorded.")
            else:
                evidence.append("No valid power observations were available.")
            return self._finding(
                DiagnosticClassification.CONNECTIVITY_FAILURE,
                0.99,
                *evidence,
            )
        if not samples:
            return self._finding(
                DiagnosticClassification.UNKNOWN,
                0.5,
                "No valid power observations were available.",
            )

        settled = samples[-1]
        peak = max(samples)
        delta = settled - baseline_watts

        if verification is VerificationStatus.VERIFIED:
            return self._finding(
                DiagnosticClassification.OK,
                0.98,
                "Device remained reachable and reported ON.",
                "Measured power was within the configured running range.",
            )
        if peak >= profile.startup_min_watts and settled < profile.acceptable_running_min:
            return self._finding(
                DiagnosticClassification.START_THEN_STOP,
                0.96,
                f"Power briefly reached {peak:.0f} W.",
                f"Settled power then fell to {settled:.0f} W.",
            )
        if abs(settled - profile.standby_watts) <= profile.standby_tolerance_watts:
            return self._finding(
                DiagnosticClassification.STANDBY_ONLY,
                0.94,
                "Device remained reachable and reported ON.",
                f"Measured power remained near standby at {settled:.0f} W.",
            )
        if profile.no_response_delta_watts < settled < profile.acceptable_running_min:
            return self._finding(
                DiagnosticClassification.NOT_REACHING_EXPECTED_LOAD,
                0.91,
                f"Measured power reached {settled:.0f} W.",
                f"Configured running range begins at {profile.acceptable_running_min:.0f} W.",
            )
        if abs(delta) <= profile.no_response_delta_watts:
            return self._finding(
                DiagnosticClassification.NO_ELECTRICAL_RESPONSE,
                0.92,
                "Device remained reachable and reported ON.",
                "Expected running electrical response was not observed.",
            )
        if telemetry.reported_state is not ReportedState.ON:
            return self._finding(
                DiagnosticClassification.UNKNOWN,
                0.6,
                "The device did not report ON.",
                "Available electrical evidence was insufficient for a more specific classification.",
            )
        return self._finding(
            DiagnosticClassification.UNKNOWN,
            0.5,
            "Available telemetry did not match a configured diagnostic pattern.",
        )

    @staticmethod
    def _finding(
        classification: DiagnosticClassification,
        confidence: float,
        *evidence: str,
    ) -> DiagnosticFinding:
        return DiagnosticFinding(
            classification=classification,
            confidence=confidence,
            evidence=evidence,
        )
