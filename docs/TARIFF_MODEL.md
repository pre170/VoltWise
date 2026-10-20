# Tariff model

## Illustrative tariff only

`ILLUSTRATIVE_DEMO_TARIFF` is a VoltWise fixture, not a Telangana, Hyderabad, or
other real utility tariff. It uses INR solely for demonstration:

| Consumption interval | Marginal rate |
|---|---:|
| 0 < usage <= 100 kWh | INR 3.00/kWh |
| 100 < usage <= 200 kWh | INR 4.50/kWh |
| 200 < usage <= 300 kWh | INR 6.00/kWh |
| usage > 300 kWh | INR 8.00/kWh |

Zero usage has zero charge. Energy is quantized to 0.001 kWh and currency to
0.01 using Decimal half-up rounding.

## Telescopic and non-telescopic structures

For the configured telescopic/incremental plan, each block is charged only at
its own marginal rate. At 301 kWh, the first 300 kWh retain their lower slab
rates and only 1 kWh receives the INR 8 rate.

The model and engine also support a `NON_TELESCOPIC` plan in which all consumed
units use the configured rate for the threshold reached. This capability does
not imply that any specific real tariff uses that formula; a verified plan must
configure it explicitly.

## Energy charge versus utility bill

VoltWise reports an **estimated energy charge**. A complete bill can include
fixed charges, taxes, duties, rebates, demand charges, fuel adjustments, and
other utility rules. The demo plan configures fixed charges and adjustments as
zero and does not call its result a final electricity bill.

## Thresholds and forecast

`TariffAwarenessPolicy` defines a 10 kWh near-threshold window. Status may be
`SAFE_MARGIN`, `PROJECTED_TO_CROSS`, `NEAR_THRESHOLD`, or
`THRESHOLD_ALREADY_CROSSED`. Crossing time uses the current average daily run
rate and is labelled `RUN_RATE`; it is an estimate, not a guarantee.

## Time of day

The illustrative plan has no time-of-day windows. Moving an operation from
afternoon to night therefore does not save money under this plan, and VoltWise
does not recommend it as a monetary action. Recommendations focus on supported
energy reduction, billing-cycle consequences, and unmonitored load review.

## Future real tariff requirements

A production tariff must come from an authoritative utility or regulator and
include jurisdiction, customer class, source URL or document, effective dates,
boundary semantics, taxes, adjustments, fixed charges, and time-of-day rules.
Expired or incomplete tariff configurations must not be presented as current.
