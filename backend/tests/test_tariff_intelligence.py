from datetime import date
from decimal import Decimal

import pytest

from app.engines import TariffEngine
from app.models import (
    EnergyImpactType,
    EnergyScenario,
    ProjectionMethod,
    TargetStatus,
    TariffPlan,
    TariffSlab,
    TariffType,
    ThresholdWarning,
)
from app.repositories import FixtureEnergyRepository
from app.services import TariffIntelligenceService
from app.tariffs import illustrative_demo_tariff


@pytest.fixture
def tariff():
    return illustrative_demo_tariff()


@pytest.fixture
def engine():
    return TariffEngine()


def service(scenario: EnergyScenario = EnergyScenario.NORMAL_CURRENT_CYCLE):
    return TariffIntelligenceService(
        FixtureEnergyRepository(scenario), illustrative_demo_tariff()
    )


def test_tariff_fixture_is_explicitly_illustrative_demo(tariff) -> None:
    assert tariff.tariff_id == "ILLUSTRATIVE_DEMO_TARIFF"
    assert tariff.is_demo is True
    assert "not a real utility tariff" in tariff.source
    assert tariff.currency == "INR"
    assert tariff.time_of_day_windows == ()


@pytest.mark.parametrize(
    ("usage", "charge"),
    [
        ("0", "0.00"),
        ("50", "150.00"),
        ("100", "300.00"),
        ("100.01", "300.05"),
        ("150", "525.00"),
        ("200", "750.00"),
        ("250", "1050.00"),
        ("299", "1344.00"),
        ("300", "1350.00"),
        ("301", "1358.00"),
        ("350", "1750.00"),
    ],
)
def test_telescopic_boundaries(usage, charge, tariff, engine) -> None:
    assert engine.calculate(tariff, usage).energy_charge == Decimal(charge)


def test_slab_breakdown_totals_equal_energy_charge(tariff, engine) -> None:
    calculation = engine.calculate(tariff, "304.29")

    assert sum(item.charge for item in calculation.slab_breakdown) == (
        calculation.energy_charge
    )
    assert [item.units_charged for item in calculation.slab_breakdown] == [
        Decimal("100.000"),
        Decimal("100.000"),
        Decimal("100.000"),
        Decimal("4.290"),
    ]


def test_decimal_money_rounding_is_half_up(tariff, engine) -> None:
    calculation = engine.calculate(tariff, "100.01")

    assert calculation.slab_breakdown[1].charge == Decimal("0.05")
    assert calculation.energy_charge.as_tuple().exponent == -2


def test_only_incremental_units_above_300_receive_eight_rate(tariff, engine) -> None:
    at_boundary = engine.calculate(tariff, 300)
    above = engine.calculate(tariff, 301)

    assert above.energy_charge - at_boundary.energy_charge == Decimal("8.00")
    assert above.slab_breakdown[-1].units_charged == Decimal("1.000")
    assert above.slab_breakdown[-1].rate_per_kwh == Decimal("8.00")


def test_non_telescopic_structure_charges_all_units_at_reached_rate(engine) -> None:
    plan = TariffPlan(
        tariff_id="TEST_THRESHOLD",
        name="Test threshold plan",
        tariff_type=TariffType.NON_TELESCOPIC,
        currency="INR",
        slabs=(
            TariffSlab(from_kwh=0, to_kwh=100, rate_per_kwh=3),
            TariffSlab(from_kwh=100, to_kwh=None, rate_per_kwh=5),
        ),
        source="test",
        effective_from=date(2026, 1, 1),
        is_demo=True,
    )

    calculation = engine.calculate(plan, 150)

    assert calculation.energy_charge == Decimal("750.00")
    assert len(calculation.slab_breakdown) == 1
    assert calculation.slab_breakdown[0].units_charged == Decimal("150.000")


def test_current_tariff_status_at_142_kwh() -> None:
    result = service().get_status()

    assert result.current_usage_kwh == Decimal("142.000")
    assert result.current_slab == "100_TO_200_KWH"
    assert result.current_estimated_energy_charge == Decimal("489.00")
    assert result.next_threshold_kwh == Decimal("200")
    assert result.units_until_next_threshold == Decimal("58.000")
    assert result.current_marginal_rate == Decimal("4.50")
    assert result.next_marginal_rate == Decimal("6.00")


def test_projected_status_crosses_200_and_300_at_run_rate() -> None:
    result = service().get_status()

    assert result.projected_month_end_kwh == Decimal("304.290")
    assert result.projected_slab == "ABOVE_300_KWH"
    assert result.projected_estimated_energy_charge == Decimal("1384.32")
    assert result.threshold_warning is ThresholdWarning.PROJECTED_TO_CROSS
    assert [item.threshold_kwh for item in result.expected_threshold_crossings] == [
        Decimal("200"),
        Decimal("300"),
    ]
    assert all(
        item.method is ProjectionMethod.RUN_RATE
        for item in result.expected_threshold_crossings
    )
    assert result.expected_threshold_crossings[-1].estimated_at.date().isoformat() == (
        "2026-09-30"
    )


def test_near_threshold_status() -> None:
    result = service(EnergyScenario.NEAR_THRESHOLD).get_status()

    assert result.current_usage_kwh == Decimal("296.000")
    assert result.units_until_next_threshold == Decimal("4.000")
    assert result.threshold_warning is ThresholdWarning.NEAR_THRESHOLD


def test_safe_margin_status_with_distant_threshold() -> None:
    plan = TariffPlan(
        tariff_id="SAFE_TEST",
        name="Safe margin test",
        tariff_type=TariffType.TELESCOPIC,
        currency="INR",
        slabs=(
            TariffSlab(from_kwh=0, to_kwh=500, rate_per_kwh=3),
            TariffSlab(from_kwh=500, to_kwh=None, rate_per_kwh=4),
        ),
        source="test",
        effective_from=date(2026, 1, 1),
        is_demo=True,
    )

    result = TariffIntelligenceService(FixtureEnergyRepository(), plan).get_status()

    assert result.threshold_warning is ThresholdWarning.SAFE_MARGIN


def test_already_crossed_status() -> None:
    repository = FixtureEnergyRepository(EnergyScenario.NEAR_THRESHOLD)
    repository.clock.advance_days(1)

    result = TariffIntelligenceService(
        repository, illustrative_demo_tariff()
    ).get_status()

    assert result.current_usage_kwh == Decimal("306.000")
    assert result.threshold_warning is ThresholdWarning.THRESHOLD_ALREADY_CROSSED


def test_normal_dishwasher_impact_does_not_cross_threshold() -> None:
    result = service().estimate_load_impact("dishwasher")

    assert result.estimated_operation_kwh == Decimal("5.000")
    assert result.before_usage_kwh == Decimal("142.000")
    assert result.after_usage_kwh == Decimal("147.000")
    assert result.threshold_crossed is False
    assert result.estimated_incremental_energy_charge == Decimal("22.50")
    assert result.informative_only is True


def test_near_threshold_dishwasher_crosses_only_incremental_slab() -> None:
    result = service(EnergyScenario.NEAR_THRESHOLD).estimate_load_impact("dishwasher")

    assert result.before_usage_kwh == Decimal("296.000")
    assert result.after_usage_kwh == Decimal("301.000")
    assert result.threshold_crossed is True
    assert result.crossed_thresholds_kwh == (Decimal("300"),)
    assert result.estimated_incremental_energy_charge == Decimal("32.00")
    assert "only units above" in result.speakable_summary


def test_target_300_calculation_in_normal_scenario() -> None:
    result = service().suggest_actions(300)

    assert result.target_status is TargetStatus.ACHIEVABLE_WITH_REDUCTION
    assert result.remaining_kwh_budget == Decimal("158.000")
    assert result.remaining_days == Decimal("16.000")
    assert result.required_average_daily_kwh == Decimal("9.88")
    assert result.current_daily_run_rate_kwh == Decimal("10.14")


def test_near_threshold_target_is_unlikely_at_current_rate() -> None:
    result = service(EnergyScenario.NEAR_THRESHOLD).suggest_actions(300)

    assert result.target_status is TargetStatus.UNLIKELY_AT_CURRENT_RATE
    assert result.remaining_kwh_budget == Decimal("4.000")
    assert result.required_average_daily_kwh == Decimal("1.33")
    assert result.current_daily_run_rate_kwh == Decimal("10.96")


def test_target_already_exceeded_behavior() -> None:
    result = service(EnergyScenario.NEAR_THRESHOLD).suggest_actions(250)

    assert result.target_status is TargetStatus.TARGET_ALREADY_EXCEEDED
    assert result.remaining_kwh_budget == Decimal("0")


def test_recommendations_rank_ac_from_runtime_evidence() -> None:
    result = service().suggest_actions(300)
    first = result.recommendations[0]

    assert first.rank == 1
    assert "air-conditioner runtime" in first.action
    assert "21 hours" in first.reason
    assert first.evidence_source == "DEVICE_STATE_HISTORY"
    assert first.impact_type is EnergyImpactType.ESTIMATED
    assert first.estimated_reduction_kwh == Decimal("1.500")
    assert "measured AC" not in (first.action + first.reason)


def test_slab_only_recommendations_do_not_claim_time_of_day_savings() -> None:
    result = service().suggest_actions(300)
    text = " ".join(
        item.action + " " + item.reason for item in result.recommendations
    ).lower()

    assert "night" not in text
    assert "time-of-day" not in text


def test_normal_and_near_threshold_scenarios_reset_deterministically() -> None:
    for scenario in EnergyScenario:
        repository = FixtureEnergyRepository(scenario)
        first = TariffIntelligenceService(
            repository, illustrative_demo_tariff()
        ).get_status()
        repository.clock.advance_hours(1)
        repository.reset()
        second = TariffIntelligenceService(
            repository, illustrative_demo_tariff()
        ).get_status()
        assert second == first
