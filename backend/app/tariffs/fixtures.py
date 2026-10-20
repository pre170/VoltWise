from datetime import date
from decimal import Decimal

from app.models import TariffPlan, TariffSlab, TariffType


def illustrative_demo_tariff() -> TariffPlan:
    """Illustrative values only; this is not a real utility tariff."""
    return TariffPlan(
        tariff_id="ILLUSTRATIVE_DEMO_TARIFF",
        name="Illustrative Incremental Household Tariff",
        tariff_type=TariffType.TELESCOPIC,
        currency="INR",
        slabs=(
            TariffSlab(
                from_kwh=Decimal("0"),
                to_kwh=Decimal("100"),
                rate_per_kwh=Decimal("3.00"),
            ),
            TariffSlab(
                from_kwh=Decimal("100"),
                to_kwh=Decimal("200"),
                rate_per_kwh=Decimal("4.50"),
            ),
            TariffSlab(
                from_kwh=Decimal("200"),
                to_kwh=Decimal("300"),
                rate_per_kwh=Decimal("6.00"),
            ),
            TariffSlab(
                from_kwh=Decimal("300"),
                to_kwh=None,
                rate_per_kwh=Decimal("8.00"),
            ),
        ),
        fixed_charge=Decimal("0.00"),
        taxes_or_adjustments=Decimal("0.00"),
        time_of_day_windows=(),
        source="VoltWise illustrative demo fixture; not a real utility tariff",
        effective_from=date(2026, 1, 1),
        is_demo=True,
    )
