# Energy model

## Evidence types

VoltWise deliberately separates three kinds of evidence:

1. **Whole-home meter:** timestamped household watts and cumulative kWh. This is
   authoritative for total household consumption, but cannot identify which
   appliance used the energy.
2. **Device state history:** timestamped ON/OFF transitions. Runtime is derived
   from transitions and can support an energy estimate when a nominal device
   power is configured. Runtime is not a direct energy measurement.
3. **Device energy meter:** cumulative kWh for a specifically metered device.
   Period deltas use the structured `MEASURED` value, meaning metered
   (simulated) device impacts in this prototype.

The AC, TV, and dishwasher use state-derived estimates. The heater and
refrigerator have simulated device energy meters. Capabilities are typed per
device rather than assumed globally.

## Runtime

Runtime is calculated by integrating ON intervals inside the requested period.
The engine considers the last known state at the start boundary and closes an
open ON interval at the end boundary. Empty history safely yields zero. Invalid
periods and contradictory transition sequences are rejected.

## Household period consumption

Household kWh is the difference between cumulative meter readings at exact start
and end boundaries. The current elapsed interval is applied to the previous
billing-cycle start, ensuring equivalent-period comparison rather than comparing
a partial month with a full month.

## Measured, estimated, and unattributed energy

Simulated device-meter differences use `MEASURED` (metered, simulated). For devices without a meter, runtime
change multiplied by configured nominal kW is `ESTIMATED`. Estimates indicate a
plausible impact, not proof that a device caused the household increase.

Positive device impacts are ranked, but VoltWise does not force them to sum to
the whole-home change. The remainder is `unattributed_kwh`, representing
unmonitored loads, baseline changes, and estimation error. If known impacts
exceed the household change, `attribution_overage_kwh` exposes that mismatch and
the limitations explain it.

Correlation is not causation. A simultaneous runtime and household increase is
useful evidence, but it does not prove exclusive responsibility.

## Projection

The initial forecast is a simple run rate:

```text
projected kWh = current period kWh / elapsed days * total cycle days
```

The response labels the method `RUN_RATE`. It is deterministic arithmetic, not
machine learning, and it does not account for weather or future behavior.

The same projection feeds tariff threshold and energy-charge forecasts. This
does not make the projection more certain; tariff outputs retain the run-rate
method and estimated wording.

## Deterministic scenarios

`NORMAL_CURRENT_CYCLE` contains 142 kWh after 14 days and remains the default.
`NEAR_THRESHOLD` contains 296 kWh after 27 days, leaving three days in the same
cycle. Both are generated as cumulative meter histories and reset identically.
