import pytest

from app.connectors import SimulatedDeviceConnector
from app.models import (
    DiagnosticClassification,
    FaultMode,
    ReportedState,
    VerificationStatus,
)
from app.services import VerificationService


def test_heater_success_has_expected_electrical_response() -> None:
    service = VerificationService(SimulatedDeviceConnector(FaultMode.NONE))

    result = service.turn_on_and_verify("heater")

    assert result.verification is VerificationStatus.VERIFIED
    assert result.reported_state is ReportedState.ON
    assert result.expected_power_watts == 1500.0
    assert result.observed_power_delta_watts == 1498.0
    assert result.observed_power_watts == 1500.0
    assert result.confidence == pytest.approx(0.98)
    assert result.evidence_source == "DEVICE_LEVEL_POWER"
    assert result.telemetry_available is True
    assert result.diagnostic_classification == DiagnosticClassification.OK.value


def test_heater_reports_on_but_no_draw_fails_verification() -> None:
    service = VerificationService(SimulatedDeviceConnector(FaultMode.NO_DRAW))

    result = service.turn_on_and_verify("heater")

    assert result.verification is VerificationStatus.FAILED
    assert result.reported_state is ReportedState.ON
    assert result.observed_power_delta_watts == 5.0
    assert result.confidence == pytest.approx(0.92)
    assert result.reason == "No expected electrical response detected."
    assert "cannot verify" in result.speakable_summary
    assert result.telemetry_available is True
    assert result.diagnostic_classification == (
        DiagnosticClassification.NO_ELECTRICAL_RESPONSE.value
    )


def test_high_draw_verification_preserves_trigger_and_cuts_power() -> None:
    connector = SimulatedDeviceConnector(FaultMode.HIGH_DRAW)
    service = VerificationService(connector)

    result = service.turn_on_and_verify("heater")

    assert result.verification is VerificationStatus.FAILED
    assert result.reported_state is ReportedState.ON
    assert result.observed_power_watts == 2200.0
    assert result.observed_power_delta_watts == 2198.0
    assert "high draw" in result.reason.lower()
    assert result.telemetry_available is True
    assert result.diagnostic_classification == (
        DiagnosticClassification.ABNORMAL_HIGH_DRAW.value
    )
    assert "power was cut" in result.speakable_summary.lower()
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


def test_direct_verification_stops_on_high_peak_before_normal_settled_draw() -> None:
    class HighPeakThenNormalConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace((2200.0, 1500.0))

    connector = HighPeakThenNormalConnector(FaultMode.NONE)

    result = VerificationService(connector).turn_on_and_verify("heater")

    assert result.verification is VerificationStatus.FAILED
    assert result.reported_state is ReportedState.ON
    assert result.observed_power_watts == 2200.0
    assert result.observed_power_delta_watts == 2198.0
    assert "high draw" in result.reason.lower()
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


@pytest.mark.parametrize("samples", [(2200.0, 1500.0), (2200.0,)])
def test_direct_verification_prioritizes_recorded_high_draw_when_unavailable(
    samples: tuple[float, ...],
) -> None:
    class HighDrawThenUnavailableConnector(SimulatedDeviceConnector):
        def turn_on(self, device_id: str) -> None:
            super().turn_on(device_id)
            self._set_power_trace(samples)
            self._state.available = False

    connector = HighDrawThenUnavailableConnector(FaultMode.NONE)

    result = VerificationService(connector).turn_on_and_verify("heater")

    assert result.verification is VerificationStatus.FAILED
    assert result.observed_power_watts == 2200.0
    assert "high draw" in result.reason.lower()
    assert "unavailable" in result.reason.lower()
    assert result.telemetry_available is False
    assert result.diagnostic_classification == (
        DiagnosticClassification.ABNORMAL_HIGH_DRAW.value
    )
    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="after_stop").watts == 2.0


def test_reset_restores_identical_baseline() -> None:
    connector = SimulatedDeviceConnector(FaultMode.NONE)
    connector.turn_on("heater")

    connector.reset()

    assert connector.get_reported_state("heater") is ReportedState.OFF
    assert connector.read_power("heater", sample="baseline").watts == 2.0


def test_unknown_device_is_rejected() -> None:
    service = VerificationService(SimulatedDeviceConnector())

    with pytest.raises(ValueError, match="Unknown device"):
        service.turn_on_and_verify("oven")

