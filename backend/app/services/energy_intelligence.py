from app.engines import EnergyUsageEngine, UsageAnalysisEngine
from app.models import PeriodComparisonResult, UsageChangeExplanation
from app.repositories import EnergyRepository


class EnergyIntelligenceService:
    def __init__(self, repository: EnergyRepository) -> None:
        self._usage = EnergyUsageEngine(repository)
        self._analysis = UsageAnalysisEngine(repository)

    def compare_periods(self) -> PeriodComparisonResult:
        return self._usage.compare_equivalent_periods()

    def explain_usage_change(self) -> UsageChangeExplanation:
        return self._analysis.explain_change()
