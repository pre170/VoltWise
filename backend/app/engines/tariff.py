from decimal import Decimal, ROUND_HALF_UP

from app.models import SlabCharge, TariffCalculation, TariffPlan, TariffSlab, TariffType


MONEY_QUANTUM = Decimal("0.01")
ENERGY_QUANTUM = Decimal("0.001")


class TariffEngine:
    @staticmethod
    def energy(value: Decimal | float | int | str) -> Decimal:
        return Decimal(str(value)).quantize(ENERGY_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def money(value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    def calculate(
        self, plan: TariffPlan, consumption_kwh: Decimal | float | int | str
    ) -> TariffCalculation:
        consumption = self.energy(consumption_kwh)
        if consumption < 0:
            raise ValueError("Consumption cannot be negative")
        if plan.tariff_type is TariffType.TELESCOPIC:
            breakdown = self._telescopic_breakdown(plan, consumption)
        else:
            breakdown = self._non_telescopic_breakdown(plan, consumption)
        energy_charge = self.money(sum((item.charge for item in breakdown), Decimal("0")))
        estimated_total = self.money(
            energy_charge + plan.fixed_charge + plan.taxes_or_adjustments
        )
        return TariffCalculation(
            consumption_kwh=consumption,
            energy_charge=energy_charge,
            fixed_charge=self.money(plan.fixed_charge),
            taxes_or_adjustments=self.money(plan.taxes_or_adjustments),
            estimated_total=estimated_total,
            currency=plan.currency,
            tariff_type=plan.tariff_type,
            slab_breakdown=breakdown,
        )

    def slab_for(self, plan: TariffPlan, consumption_kwh: Decimal | float) -> TariffSlab:
        consumption = self.energy(consumption_kwh)
        if consumption < 0:
            raise ValueError("Consumption cannot be negative")
        if consumption == 0:
            return plan.slabs[0]
        for slab in plan.slabs:
            if consumption > slab.from_kwh and (
                slab.to_kwh is None or consumption <= slab.to_kwh
            ):
                return slab
        return plan.slabs[-1]

    def slab_label(self, plan: TariffPlan, consumption_kwh: Decimal | float) -> str:
        slab = self.slab_for(plan, consumption_kwh)
        if slab.to_kwh is None:
            return f"ABOVE_{self._plain(slab.from_kwh)}_KWH"
        return f"{self._plain(slab.from_kwh)}_TO_{self._plain(slab.to_kwh)}_KWH"

    def next_threshold(
        self, plan: TariffPlan, consumption_kwh: Decimal | float
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        consumption = self.energy(consumption_kwh)
        slab = self.slab_for(plan, consumption)
        if slab.to_kwh is None:
            return None, None, None
        current_index = plan.slabs.index(slab)
        next_rate = plan.slabs[current_index + 1].rate_per_kwh
        return slab.to_kwh, max(Decimal("0"), slab.to_kwh - consumption), next_rate

    def thresholds_crossed(
        self, plan: TariffPlan, before: Decimal | float, after: Decimal | float
    ) -> tuple[Decimal, ...]:
        lower = self.energy(before)
        upper = self.energy(after)
        if upper <= lower:
            return ()
        return tuple(
            slab.to_kwh
            for slab in plan.slabs
            if slab.to_kwh is not None and lower < slab.to_kwh < upper
        )

    def _telescopic_breakdown(
        self, plan: TariffPlan, consumption: Decimal
    ) -> tuple[SlabCharge, ...]:
        items: list[SlabCharge] = []
        for slab in plan.slabs:
            available = consumption - slab.from_kwh
            if available <= 0:
                units = Decimal("0")
            elif slab.to_kwh is None:
                units = available
            else:
                units = min(available, slab.to_kwh - slab.from_kwh)
            units = units.quantize(ENERGY_QUANTUM)
            items.append(
                SlabCharge(
                    from_kwh=slab.from_kwh,
                    to_kwh=slab.to_kwh,
                    units_charged=units,
                    rate_per_kwh=slab.rate_per_kwh,
                    charge=self.money(units * slab.rate_per_kwh),
                )
            )
        return tuple(items)

    def _non_telescopic_breakdown(
        self, plan: TariffPlan, consumption: Decimal
    ) -> tuple[SlabCharge, ...]:
        slab = self.slab_for(plan, consumption)
        return (
            SlabCharge(
                from_kwh=slab.from_kwh,
                to_kwh=slab.to_kwh,
                units_charged=consumption,
                rate_per_kwh=slab.rate_per_kwh,
                charge=self.money(consumption * slab.rate_per_kwh),
            ),
        )

    @staticmethod
    def _plain(value: Decimal) -> str:
        rendered = format(value, "f")
        return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered
