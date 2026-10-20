from collections.abc import Sequence
from datetime import datetime

from app.models import (
    EnergyProjection,
    EvidenceSource,
    PeriodComparisonResult,
    ProjectionMethod,
    WholeHomeReading,
)
from app.repositories import EnergyRepository


class EnergyUsageEngine:
    def __init__(self, repository: EnergyRepository) -> None:
        self._repository = repository

    def compare_equivalent_periods(self) -> PeriodComparisonResult:
        cycle = self._repository.get_billing_cycle()
        elapsed = cycle.current_simulated_at - cycle.cycle_start
        previous_end = cycle.previous_cycle_start + elapsed
        current_kwh = self.period_kwh(
            self._repository.get_household_readings(
                cycle.cycle_start, cycle.current_simulated_at
            ),
            cycle.cycle_start,
            cycle.current_simulated_at,
        )
        previous_kwh = self.period_kwh(
            self._repository.get_household_readings(
                cycle.previous_cycle_start, previous_end
            ),
            cycle.previous_cycle_start,
            previous_end,
        )
        difference = round(current_kwh - previous_kwh, 3)
        percent = self.percent_change(difference, previous_kwh)
        elapsed_days = elapsed.total_seconds() / 86400.0
        cycle_days = (cycle.cycle_end - cycle.cycle_start).total_seconds() / 86400.0
        projection = EnergyProjection(
            projected_kwh=round(current_kwh / elapsed_days * cycle_days, 2),
            method=ProjectionMethod.RUN_RATE,
            days_elapsed=elapsed_days,
            cycle_days=cycle_days,
        )
        if percent is None:
            comparison_text = "There is no previous usage baseline for a percentage comparison."
        else:
            comparison_text = f"That's about {abs(percent):.0f} percent {'higher' if percent >= 0 else 'lower'}."
        return PeriodComparisonResult(
            current_kwh=current_kwh,
            previous_equivalent_kwh=previous_kwh,
            difference_kwh=difference,
            change_percent=percent,
            elapsed_days=elapsed_days,
            projection=projection,
            evidence_source=EvidenceSource.WHOLE_HOME_METER,
            speakable_summary=(
                f"You've used about {current_kwh:.0f} kilowatt-hours in the first "
                f"{elapsed_days:.0f} days of this billing cycle, compared with "
                f"{previous_kwh:.0f} at the same point last cycle. {comparison_text}"
            ),
        )

    @staticmethod
    def period_kwh(
        readings: Sequence[WholeHomeReading], start: datetime, end: datetime
    ) -> float:
        if end <= start:
            raise ValueError("Energy period end must be after start")
        by_time = {reading.timestamp: reading for reading in readings}
        if start not in by_time or end not in by_time:
            raise ValueError("Exact cumulative readings are required at both period boundaries")
        delta = by_time[end].cumulative_kwh - by_time[start].cumulative_kwh
        if delta < 0:
            raise ValueError("Cumulative meter reading decreased within the period")
        return round(delta, 3)

    @staticmethod
    def percent_change(difference: float, previous: float) -> float | None:
        if previous == 0:
            return None
        return round(difference / previous * 100.0, 2)

