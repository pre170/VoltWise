from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .device import ReportedState


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"


class VerificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    device: str
    command: str
    reported_state: ReportedState
    verification: VerificationStatus
    expected_power_watts: float
    observed_power_delta_watts: float
    observed_power_watts: float
    confidence: float = Field(ge=0, le=1)
    confidence_level: ConfidenceLevel
    evidence_source: str
    telemetry_available: bool
    diagnostic_classification: str
    reason: str
    speakable_summary: str

