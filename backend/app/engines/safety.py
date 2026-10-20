from dataclasses import dataclass

from app.models import DeviceProfile, DiagnosticClassification, SafetyAction


@dataclass(frozen=True)
class SafetyDecision:
    retry_allowed: bool
    action: SafetyAction
    cut_power: bool = False


class SafetyEngine:
    def decide(
        self,
        *,
        profile: DeviceProfile,
        classification: DiagnosticClassification,
        retries_used: int,
    ) -> SafetyDecision:
        if classification is DiagnosticClassification.ABNORMAL_HIGH_DRAW:
            return SafetyDecision(
                retry_allowed=False,
                action=SafetyAction.POWER_CUT_HIGH_DRAW,
                cut_power=True,
            )

        policy = profile.safety_policy
        allowed = policy.allow_retry and retries_used < policy.max_retries
        return SafetyDecision(
            retry_allowed=allowed,
            action=SafetyAction.NONE if allowed else SafetyAction.STOP_RETRYING,
        )
