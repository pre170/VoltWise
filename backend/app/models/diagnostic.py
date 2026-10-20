from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .device import ReportedState
from .verification import VerificationStatus


class DiagnosticClassification(StrEnum):
    OK = "OK"
    CONNECTIVITY_FAILURE = "CONNECTIVITY_FAILURE"
    NO_ELECTRICAL_RESPONSE = "NO_ELECTRICAL_RESPONSE"
    STANDBY_ONLY = "STANDBY_ONLY"
    START_THEN_STOP = "START_THEN_STOP"
    ABNORMAL_HIGH_DRAW = "ABNORMAL_HIGH_DRAW"
    NOT_REACHING_EXPECTED_LOAD = "NOT_REACHING_EXPECTED_LOAD"
    UNKNOWN = "UNKNOWN"


class FinalStatus(StrEnum):
    VERIFIED = "VERIFIED"
    RECOVERED = "RECOVERED"
    UNRESOLVED = "UNRESOLVED"
    SAFETY_STOP = "SAFETY_STOP"


class SafetyAction(StrEnum):
    NONE = "NONE"
    STOP_RETRYING = "STOP_RETRYING"
    POWER_CUT_HIGH_DRAW = "POWER_CUT_HIGH_DRAW"


class AuditEventType(StrEnum):
    COMMAND_SENT = "COMMAND_SENT"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    DIAGNOSTIC_CLASSIFIED = "DIAGNOSTIC_CLASSIFIED"
    RETRY_STARTED = "RETRY_STARTED"
    RETRY_SUCCEEDED = "RETRY_SUCCEEDED"
    RETRY_FAILED = "RETRY_FAILED"
    SAFETY_STOP = "SAFETY_STOP"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"


class DiagnosticFinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    classification: DiagnosticClassification
    confidence: float = Field(ge=0, le=1)
    evidence: tuple[str, ...]


class AttemptResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt: int = Field(ge=1)
    reported_state: ReportedState
    available: bool
    baseline_watts: float
    power_samples_watts: tuple[float, ...]
    observed_watts: float
    observed_power_delta_watts: float
    verification: VerificationStatus
    diagnostic_classification: DiagnosticClassification
    confidence: float = Field(ge=0, le=1)
    evidence: tuple[str, ...]


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int = Field(ge=1)
    event: AuditEventType
    attempt: int | None = Field(default=None, ge=1)
    detail: str


class DiagnosticWorkflowResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    device: str
    requested_action: str
    final_status: FinalStatus
    initial_verification: VerificationStatus
    diagnostic_classification: DiagnosticClassification
    confidence: float = Field(ge=0, le=1)
    attempts: tuple[AttemptResult, ...]
    retries_used: int = Field(ge=0)
    safety_action: SafetyAction
    resolved: bool
    evidence: tuple[str, ...]
    audit_events: tuple[AuditEvent, ...]
    speakable_summary: str
