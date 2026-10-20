from datetime import timedelta
from decimal import Decimal

from app.engines import TariffEngine
from app.models import (
    ActionRecommendation,
    ActionSuggestions,
    AnalysisConfidence,
    BillForecast,
    EnergyImpactType,
    LoadImpactResult,
    ProjectionMethod,
    TargetStatus,
    TariffAwarenessPolicy,
    TariffPlan,
    TariffStatus,
    ThresholdCrossing,
    ThresholdWarning,
)
from app.repositories import EnergyRepository

from .energy_intelligence import EnergyIntelligenceService


class TariffIntelligenceService:
    def __init__(
        self,
        repository: EnergyRepository,
        tariff: TariffPlan,
        *,
        policy: TariffAwarenessPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._tariff = tariff
        self._policy = policy or TariffAwarenessPolicy()
        self._engine = TariffEngine()
        self._energy = EnergyIntelligenceService(repository)

    def get_status(self) -> TariffStatus:
        comparison = self._energy.compare_periods()
        cycle = self._repository.get_billing_cycle()
        current = self._engine.energy(comparison.current_kwh)
        projected = self._engine.energy(comparison.projection.projected_kwh)
        current_charge = self._engine.calculate(self._tariff, current)
        projected_charge = self._engine.calculate(self._tariff, projected)
        threshold, remaining, next_rate = self._engine.next_threshold(
            self._tariff, current
        )
        crossings = self._crossing_forecasts(current, projected)
        warning = self._warning(current, projected, threshold, remaining)
        crossed_text = (
            " It is projected to cross the "
            + ", ".join(
                f"{self._format_kwh(item.threshold_kwh)} kilowatt-hour"
                for item in crossings
            )
            + (" thresholds." if len(crossings) > 1 else " threshold.")
            if crossings
            else ""
        )
        if threshold is not None and remaining is not None:
            position = (
                f"You are about {self._format_kwh(remaining)} kilowatt-hours from the "
                f"next {self._format_kwh(threshold)} kilowatt-hour threshold."
            )
        else:
            position = "You are already in the highest configured marginal slab."
        return TariffStatus(
            tariff_id=self._tariff.tariff_id,
            tariff_name=self._tariff.name,
            tariff_type=self._tariff.tariff_type,
            currency=self._tariff.currency,
            source=self._tariff.source,
            is_demo=self._tariff.is_demo,
            current_usage_kwh=current,
            current_slab=self._engine.slab_label(self._tariff, current),
            current_estimated_energy_charge=current_charge.energy_charge,
            next_threshold_kwh=threshold,
            units_until_next_threshold=remaining,
            current_marginal_rate=self._engine.slab_for(
                self._tariff, current
            ).rate_per_kwh,
            next_marginal_rate=next_rate,
            projected_month_end_kwh=projected,
            projected_slab=self._engine.slab_label(self._tariff, projected),
            projected_estimated_energy_charge=projected_charge.energy_charge,
            expected_threshold_crossings=crossings,
            threshold_warning=warning,
            speakable_summary=(
                f"Under the configured illustrative tariff, estimated energy usage is "
                f"{self._format_kwh(current)} kilowatt-hours. {position} Based on the "
                f"current run rate, usage is projected at about {self._format_kwh(projected)} "
                f"kilowatt-hours by cycle end.{crossed_text} Under this incremental tariff, "
                "only units within each slab receive that slab's rate."
            ),
        )

    def forecast_bill(self) -> BillForecast:
        comparison = self._energy.compare_periods()
        current = self._engine.calculate(self._tariff, comparison.current_kwh)
        projected = self._engine.calculate(
            self._tariff, comparison.projection.projected_kwh
        )
        return BillForecast(
            tariff_id=self._tariff.tariff_id,
            is_demo=self._tariff.is_demo,
            current=current,
            projected=projected,
            projection_method=ProjectionMethod.RUN_RATE,
            assumptions=(
                "Tariff values are illustrative demo values, not a real utility tariff.",
                "Projection uses the current average daily run rate.",
                "Amounts are estimated energy charges, not a complete utility bill.",
                "No time-of-day price windows are configured.",
            ),
            speakable_summary=(
                f"The current estimated energy charge is {self._tariff.currency} "
                f"{current.energy_charge}. Based on the current run rate, the projected "
                f"month-end energy charge is approximately {self._tariff.currency} "
                f"{projected.energy_charge}. This excludes unmodeled utility charges."
            ),
        )

    def estimate_load_impact(self, device_id: str) -> LoadImpactResult:
        device_id = device_id.lower().strip()
        devices = {device.device_id: device for device in self._repository.get_devices()}
        if device_id not in devices:
            raise ValueError(f"Unknown device: {device_id!r}")
        device = devices[device_id]
        if device.estimated_cycle_kwh is None:
            raise ValueError(f"No configured operation-energy estimate for {device.name}")
        comparison = self._energy.compare_periods()
        before = self._engine.energy(comparison.current_kwh)
        operation = self._engine.energy(device.estimated_cycle_kwh)
        after = before + operation
        before_charge = self._engine.calculate(self._tariff, before)
        after_charge = self._engine.calculate(self._tariff, after)
        crossed = self._engine.thresholds_crossed(self._tariff, before, after)
        if crossed:
            summary = (
                f"This {device.name} operation is estimated to use {self._format_kwh(operation)} "
                f"kilowatt-hours and take usage from {self._format_kwh(before)} to "
                f"{self._format_kwh(after)} kilowatt-hours, crossing the "
                f"{self._format_kwh(crossed[-1])} kilowatt-hour threshold. Under the "
                "configured incremental tariff, only units above that threshold move "
                "to the higher marginal rate."
            )
        else:
            summary = (
                f"This {device.name} operation is estimated to use {self._format_kwh(operation)} "
                f"kilowatt-hours and add approximately {self._tariff.currency} "
                f"{after_charge.energy_charge - before_charge.energy_charge} in energy "
                "charges. It does not cross the next tariff threshold."
            )
        return LoadImpactResult(
            device_id=device.device_id,
            device=device.name,
            estimated_operation_kwh=operation,
            energy_impact_type=EnergyImpactType.ESTIMATED,
            before_usage_kwh=before,
            after_usage_kwh=after,
            before_slab=self._engine.slab_label(self._tariff, before),
            after_slab=self._engine.slab_label(self._tariff, after),
            before_energy_charge=before_charge.energy_charge,
            after_energy_charge=after_charge.energy_charge,
            estimated_incremental_energy_charge=(
                after_charge.energy_charge - before_charge.energy_charge
            ),
            threshold_crossed=bool(crossed),
            crossed_thresholds_kwh=crossed,
            informative_only=True,
            speakable_summary=summary,
        )

    def suggest_actions(self, target_kwh: float | None = None) -> ActionSuggestions:
        comparison = self._energy.compare_periods()
        explanation = self._energy.explain_usage_change()
        cycle = self._repository.get_billing_cycle()
        current = self._engine.energy(comparison.current_kwh)
        projected = self._engine.energy(comparison.projection.projected_kwh)
        elapsed_days = Decimal(str(comparison.elapsed_days))
        remaining_days = Decimal(
            str((cycle.cycle_end - cycle.current_simulated_at).total_seconds() / 86400)
        ).quantize(Decimal("0.001"))
        run_rate = (current / elapsed_days).quantize(Decimal("0.01"))

        target = self._engine.energy(target_kwh) if target_kwh is not None else None
        target_status = None
        remaining_budget = None
        required_daily = None
        if target is not None:
            remaining_budget = max(Decimal("0"), target - current)
            required_daily = (
                (remaining_budget / remaining_days).quantize(Decimal("0.01"))
                if remaining_days > 0
                else Decimal("0")
            )
            if current >= target:
                target_status = TargetStatus.TARGET_ALREADY_EXCEEDED
            elif projected <= target:
                target_status = TargetStatus.ON_TRACK
            elif run_rate <= required_daily * self._policy.achievable_run_rate_ratio:
                target_status = TargetStatus.ACHIEVABLE_WITH_REDUCTION
            else:
                target_status = TargetStatus.UNLIKELY_AT_CURRENT_RATE

        recommendations: list[ActionRecommendation] = []
        ac = next(
            (item for item in explanation.contributors if item.device_id == "ac"), None
        )
        if ac is not None and ac.runtime_change_hours > 0:
            devices = {item.device_id: item for item in self._repository.get_devices()}
            reduction = (
                self._policy.suggested_ac_reduction_hours
                * Decimal(str(devices["ac"].nominal_power_kw))
            ).quantize(Decimal("0.001"))
            recommendations.append(
                ActionRecommendation(
                    rank=1,
                    action="Reduce unnecessary air-conditioner runtime where comfortable.",
                    reason=(
                        f"Observed AC runtime increased by {ac.runtime_change_hours:.0f} hours "
                        "versus the equivalent previous period."
                    ),
                    evidence_source="DEVICE_STATE_HISTORY",
                    estimated_reduction_kwh=reduction,
                    impact_type=EnergyImpactType.ESTIMATED,
                )
            )
        if explanation.unattributed_kwh > 0:
            recommendations.append(
                ActionRecommendation(
                    rank=len(recommendations) + 1,
                    action="Review persistent or unmonitored household loads.",
                    reason=(
                        f"Approximately {explanation.unattributed_kwh:.2f} kWh of the "
                        "increase remains unattributed."
                    ),
                    evidence_source="WHOLE_HOME_METER",
                )
            )

        if target is None:
            target_text = "No consumption target was supplied."
        elif target_status is TargetStatus.TARGET_ALREADY_EXCEEDED:
            target_text = f"The {self._format_kwh(target)} kilowatt-hour target has already been reached or exceeded."
        elif target_status is TargetStatus.ON_TRACK:
            target_text = f"Based on the current run rate, you are on track to stay within {self._format_kwh(target)} kilowatt-hours."
        else:
            target_text = (
                f"To stay within {self._format_kwh(target)} kilowatt-hours, average usage "
                f"would need to be about {required_daily} kilowatt-hours per remaining day, "
                f"compared with the current {run_rate} kilowatt-hour daily run rate."
            )
        return ActionSuggestions(
            target_kwh=target,
            target_status=target_status,
            current_usage_kwh=current,
            projected_usage_kwh=projected,
            remaining_kwh_budget=remaining_budget,
            remaining_days=remaining_days,
            required_average_daily_kwh=required_daily,
            current_daily_run_rate_kwh=run_rate,
            recommendations=tuple(recommendations),
            speakable_summary=(
                f"{target_text} The strongest evidence-based action is to reduce "
                "unnecessary AC runtime where comfortable; any reduction estimate is not guaranteed."
            ),
        )

    def _crossing_forecasts(
        self, current: Decimal, projected: Decimal
    ) -> tuple[ThresholdCrossing, ...]:
        cycle = self._repository.get_billing_cycle()
        elapsed_days = Decimal(
            str((cycle.current_simulated_at - cycle.cycle_start).total_seconds() / 86400)
        )
        daily_rate = current / elapsed_days
        forecasts = []
        for threshold in self._engine.thresholds_crossed(
            self._tariff, current, projected
        ):
            days_from_start = threshold / daily_rate
            forecasts.append(
                ThresholdCrossing(
                    threshold_kwh=threshold,
                    estimated_at=cycle.cycle_start
                    + timedelta(days=float(days_from_start)),
                    method=ProjectionMethod.RUN_RATE,
                )
            )
        return tuple(forecasts)

    def _warning(
        self,
        current: Decimal,
        projected: Decimal,
        threshold: Decimal | None,
        remaining: Decimal | None,
    ) -> ThresholdWarning:
        highest_threshold = max(
            slab.to_kwh for slab in self._tariff.slabs if slab.to_kwh is not None
        )
        if current > highest_threshold:
            return ThresholdWarning.THRESHOLD_ALREADY_CROSSED
        if remaining is not None and remaining <= self._policy.near_threshold_kwh:
            return ThresholdWarning.NEAR_THRESHOLD
        if threshold is not None and projected > threshold:
            return ThresholdWarning.PROJECTED_TO_CROSS
        return ThresholdWarning.SAFE_MARGIN

    @staticmethod
    def _format_kwh(value: Decimal) -> str:
        return format(value.normalize(), "f")
