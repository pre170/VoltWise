# Safety and evidence policy

VoltWise distinguishes command acknowledgement from physical outcome. A device
reporting `ON` is not sufficient: verification also requires measured power in
the device profile's acceptable running range.

Device-power evidence is strong but still does not reveal the exact failed
component. Diagnostics classify observable behavior—offline, standby-only,
start-then-stop, high draw, underpowered, or no expected response. User-facing
language therefore says “observed,” “consistent with,” “cannot verify,” and
“may require inspection.”

## Heater policy in this demo

- Maximum retries: one.
- Retry is allowed for non-high-draw verification failures.
- Automatic power cycling is not allowed.
- Cooldown is zero because this simulated resistive heater profile has no
  compressor timing requirement. This does not establish a policy for future
  device types.
- A reading at or above 1900 W is classified as abnormal high draw.
- High draw causes an immediate simulated power cut and safety stop, with zero
  retries.

All decisions and attempts are returned as typed in-memory audit events. They
are not persisted in this phase.

