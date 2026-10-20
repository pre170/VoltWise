from datetime import datetime

from app.models import (
    AnalysisConfidence,
    ContributorReason,
    DeviceEnergyReading,
    EnergyImpactType,
    EvidenceSource,
    UsageChangeExplanation,
    UsageContributor,
)
from app.repositories import EnergyRepository

from .energy_usage import EnergyUsageEngine
from .runtime import RuntimeEngine


class UsageAnalysisEngine:
    def __init__(self, repository: EnergyRepository) -> None:
        self._repository = repository
        self._usage = EnergyUsageEngine(repository)
        self._runtime = RuntimeEngine()

    def explain_change(self) -> UsageChangeExplanation:
        comparison = self._usage.compare_equivalent_periods()
        cycle = self._repository.get_billing_cycle()
        elapsed = cycle.current_simulated_at - cycle.cycle_start
        previous_end = cycle.previous_cycle_start + elapsed
        contributors: list[UsageContributor] = []

        for device in self._repository.get_devices():
            capabilities = device.capabilities
            if not (capabilities.supports_state_history and capabilities.supports_runtime):
                continue
            current_runtime = self._runtime.calculate_hours(
                self._repository.get_device_state_history(
                    device.device_id, cycle.cycle_start, cycle.current_simulated_at
                ),
                cycle.cycle_start,
                cycle.current_simulated_at,
            )
            previous_runtime = self._runtime.calculate_hours(
                self._repository.get_device_state_history(
                    device.device_id, cycle.previous_cycle_start, previous_end
                ),
                cycle.previous_cycle_start,
                previous_end,
            )
            runtime_change = round(current_runtime - previous_runtime, 3)
            runtime_percent = EnergyUsageEngine.percent_change(runtime_change, previous_runtime)

            if capabilities.supports_device_energy:
                current_energy = self._device_energy_delta(
                    self._repository.get_device_energy_readings(
                        device.device_id, cycle.cycle_start, cycle.current_simulated_at
                    ),
                    cycle.cycle_start,
                    cycle.current_simulated_at,
                )
                previous_energy = self._device_energy_delta(
                    self._repository.get_device_energy_readings(
                        device.device_id, cycle.previous_cycle_start, previous_end
                    ),
                    cycle.previous_cycle_start,
                    previous_end,
                )
                impact = round(current_energy - previous_energy, 3)
                impact_type = EnergyImpactType.MEASURED
                source = EvidenceSource.DEVICE_ENERGY_METER
                reason = ContributorReason.MEASURED_ENERGY_INCREASE
            elif device.nominal_power_kw is not None:
                impact = round(runtime_change * device.nominal_power_kw, 3)
                impact_type = EnergyImpactType.ESTIMATED
                source = EvidenceSource.DEVICE_STATE_HISTORY
                reason = ContributorReason.RUNTIME_INCREASE
            else:
                continue

            if impact <= 0:
                continue
            contributors.append(
                UsageContributor(
                    device_id=device.device_id,
                    device=device.name,
                    reason=reason,
                    current_runtime_hours=current_runtime,
                    previous_runtime_hours=previous_runtime,
                    runtime_change_hours=runtime_change,
                    runtime_change_percent=runtime_percent,
                    energy_impact_kwh=impact,
                    energy_impact_type=impact_type,
                    evidence_source=source,
                    confidence=(
                        AnalysisConfidence.HIGH
                        if impact_type is EnergyImpactType.MEASURED or capabilities.supports_state_history
                        else AnalysisConfidence.MEDIUM
                    ),
                )
            )

        contributors.sort(key=lambda item: item.energy_impact_kwh, reverse=True)
        known = round(sum(item.energy_impact_kwh for item in contributors), 3)
        household_increase = max(0.0, comparison.difference_kwh)
        unattributed = round(max(0.0, household_increase - known), 3)
        overage = round(max(0.0, known - household_increase), 3)
        limitations = [
            "Whole-home readings do not identify individual appliances.",
            "Runtime-based energy impacts are estimates from configured nominal power.",
            "Correlation and runtime changes are evidence, not proof of causation.",
        ]
        if overage:
            limitations.append(
                "Estimated and measured contributor changes exceed the household change; impacts overlap or estimates are imprecise."
            )
        if contributors:
            primary = contributors[0]
            summary = (
                f"{primary.device} is the strongest observed contributor. Its runtime "
                f"increased by about {primary.runtime_change_hours:.0f} hours compared "
                "with the same period last cycle."
            )
            if unattributed:
                summary += " Some of the additional household usage remains unattributed."
        else:
            summary = "No monitored device explains the measured household usage change."

        return UsageChangeExplanation(
            household_change_kwh=comparison.difference_kwh,
            household_change_percent=comparison.change_percent,
            contributors=tuple(contributors),
            known_contribution_kwh=known,
            unattributed_kwh=unattributed,
            attribution_overage_kwh=overage,
            limitations=tuple(limitations),
            speakable_summary=summary,
            current_kwh=comparison.current_kwh,
            previous_equivalent_kwh=comparison.previous_equivalent_kwh,
        )

    @staticmethod
    def _device_energy_delta(
        readings: tuple[DeviceEnergyReading, ...] | list[DeviceEnergyReading],
        start: datetime,
        end: datetime,
    ) -> float:
        by_time = {reading.timestamp: reading for reading in readings}
        if start not in by_time or end not in by_time:
            raise ValueError("Device energy readings require exact period boundaries")
        delta = by_time[end].cumulative_kwh - by_time[start].cumulative_kwh
        if delta < 0:
            raise ValueError("Device cumulative energy reading decreased")
        return round(delta, 3)
