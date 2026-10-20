from datetime import datetime, timedelta

import pytest

from app.engines import EnergyUsageEngine, RuntimeEngine, UsageAnalysisEngine
from app.models import (
    DeviceStateTransition,
    EnergyImpactType,
    EvidenceSource,
    ProjectionMethod,
    ReportedState,
    WholeHomeReading,
)
from app.repositories import FixtureEnergyRepository


def transition(at: datetime, state: ReportedState) -> DeviceStateTransition:
    return DeviceStateTransition(device_id="test", timestamp=at, state=state)


def test_whole_home_readings_are_deterministic() -> None:
    first = FixtureEnergyRepository()
    second = FixtureEnergyRepository()
    cycle = first.get_billing_cycle()

    assert first.get_household_readings(
        cycle.previous_cycle_start, cycle.cycle_end
    ) == second.get_household_readings(cycle.previous_cycle_start, cycle.cycle_end)


def test_repository_reset_restores_seeded_household_state() -> None:
    repository = FixtureEnergyRepository()
    original = repository.get_household_readings(
        repository.PREVIOUS_START, repository.CURRENT_END
    )
    repository.clock.advance_days(3)

    repository.reset()

    assert repository.clock.now == repository.DEMO_NOW
    assert repository.get_household_readings(
        repository.PREVIOUS_START, repository.CURRENT_END
    ) == original


def test_runtime_calculates_multiple_transitions() -> None:
    start = datetime(2026, 1, 1)
    history = [
        transition(start, ReportedState.OFF),
        transition(start + timedelta(hours=1), ReportedState.ON),
        transition(start + timedelta(hours=3), ReportedState.OFF),
        transition(start + timedelta(hours=5), ReportedState.ON),
        transition(start + timedelta(hours=6, minutes=30), ReportedState.OFF),
    ]

    assert RuntimeEngine.calculate_hours(history, start, start + timedelta(hours=8)) == 3.5


def test_runtime_handles_period_beginning_while_already_on() -> None:
    start = datetime(2026, 1, 1, 12)
    history = [
        transition(start - timedelta(hours=2), ReportedState.ON),
        transition(start + timedelta(hours=2), ReportedState.OFF),
    ]

    assert RuntimeEngine.calculate_hours(history, start, start + timedelta(hours=4)) == 2.0


def test_runtime_handles_device_still_on_at_period_end() -> None:
    start = datetime(2026, 1, 1)
    history = [transition(start + timedelta(hours=1), ReportedState.ON)]

    assert RuntimeEngine.calculate_hours(history, start, start + timedelta(hours=4)) == 3.0


def test_runtime_empty_history_is_zero() -> None:
    start = datetime(2026, 1, 1)
    assert RuntimeEngine.calculate_hours([], start, start + timedelta(days=1)) == 0.0


def test_runtime_rejects_repeated_impossible_transition() -> None:
    start = datetime(2026, 1, 1)
    history = [
        transition(start + timedelta(hours=1), ReportedState.ON),
        transition(start + timedelta(hours=2), ReportedState.ON),
    ]

    with pytest.raises(ValueError, match="repeated state"):
        RuntimeEngine.calculate_hours(history, start, start + timedelta(hours=4))


def test_current_and_equivalent_previous_energy_are_derived_from_boundaries() -> None:
    result = EnergyUsageEngine(FixtureEnergyRepository()).compare_equivalent_periods()

    assert result.current_kwh == 142.0
    assert result.previous_equivalent_kwh == 118.0
    assert result.difference_kwh == 24.0
    assert result.elapsed_days == 14.0
    assert result.evidence_source is EvidenceSource.WHOLE_HOME_METER


def test_period_energy_uses_cumulative_delta_not_absolute_value() -> None:
    start = datetime(2026, 1, 1)
    end = start + timedelta(days=1)
    readings = [
        WholeHomeReading(timestamp=start, instantaneous_watts=500, cumulative_kwh=900),
        WholeHomeReading(timestamp=end, instantaneous_watts=600, cumulative_kwh=910),
    ]

    assert EnergyUsageEngine.period_kwh(readings, start, end) == 10.0


def test_percentage_change_and_zero_baseline_are_safe() -> None:
    assert EnergyUsageEngine.percent_change(24.0, 118.0) == 20.34
    assert EnergyUsageEngine.percent_change(10.0, 0.0) is None


def test_month_end_projection_is_simple_run_rate() -> None:
    projection = EnergyUsageEngine(
        FixtureEnergyRepository()
    ).compare_equivalent_periods().projection

    assert projection.projected_kwh == 304.29
    assert projection.method is ProjectionMethod.RUN_RATE
    assert projection.days_elapsed == 14.0
    assert projection.cycle_days == 30.0


def test_canonical_ac_runtime_is_higher_and_others_are_near_baseline() -> None:
    repository = FixtureEnergyRepository()
    cycle = repository.get_billing_cycle()
    previous_end = cycle.previous_cycle_start + (
        cycle.current_simulated_at - cycle.cycle_start
    )
    runtimes = {}
    for device in repository.get_devices():
        current = RuntimeEngine.calculate_hours(
            repository.get_device_state_history(
                device.device_id, cycle.cycle_start, cycle.current_simulated_at
            ),
            cycle.cycle_start,
            cycle.current_simulated_at,
        )
        previous = RuntimeEngine.calculate_hours(
            repository.get_device_state_history(
                device.device_id, cycle.previous_cycle_start, previous_end
            ),
            cycle.previous_cycle_start,
            previous_end,
        )
        runtimes[device.device_id] = (current, previous)

    assert runtimes["ac"] == (73.0, 52.0)
    assert all(
        abs(current - previous) <= 2.0
        for device, (current, previous) in runtimes.items()
        if device != "ac"
    )


def test_household_devices_have_distinct_capabilities() -> None:
    devices = {item.device_id: item for item in FixtureEnergyRepository().get_devices()}

    assert devices["ac"].capabilities.supports_device_energy is False
    assert devices["heater"].capabilities.supports_device_energy is True
    assert devices["dishwasher"].capabilities.has_estimated_cycle_energy is True


def test_ac_ranks_first_and_impact_is_explicitly_estimated() -> None:
    result = UsageAnalysisEngine(FixtureEnergyRepository()).explain_change()
    ac = result.contributors[0]

    assert ac.device_id == "ac"
    assert ac.runtime_change_hours == 21.0
    assert ac.energy_impact_kwh == 15.75
    assert ac.energy_impact_type is EnergyImpactType.ESTIMATED
    assert ac.evidence_source is EvidenceSource.DEVICE_STATE_HISTORY


def test_measured_device_impacts_are_labelled_measured() -> None:
    result = UsageAnalysisEngine(FixtureEnergyRepository()).explain_change()
    contributors = {item.device_id: item for item in result.contributors}

    assert contributors["heater"].energy_impact_type is EnergyImpactType.MEASURED
    assert contributors["refrigerator"].energy_impact_type is EnergyImpactType.MEASURED
    assert contributors["heater"].evidence_source is EvidenceSource.DEVICE_ENERGY_METER


def test_unexplained_usage_remains_unattributed() -> None:
    result = UsageAnalysisEngine(FixtureEnergyRepository()).explain_change()

    assert result.household_change_kwh == 24.0
    assert result.known_contribution_kwh == 19.35
    assert result.unattributed_kwh == 4.65
    assert result.attribution_overage_kwh == 0.0
    assert result.known_contribution_kwh + result.unattributed_kwh == pytest.approx(
        result.household_change_kwh
    )
    assert "unattributed" in result.speakable_summary

