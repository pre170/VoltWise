# MCP tools

VoltWise uses MCP Python SDK 2.3.0. One MCP tool registry is available over both
stdio and the SDK's real Streamable HTTP transport. Every result is a typed,
structured payload with deterministic speakable text.

The registry contains the eight VoltWise intelligence and verification tools
documented below plus the existing supporting `power_control_device` tool used
for ordinary simulated-home commands. It therefore exposes nine tools in total.

```text
MCP client -> stdio -> VoltWise MCP -> VoltWiseApplication

Remote MCP client -> Streamable HTTP -> VoltWise MCP -> VoltWiseApplication
```

Start stdio with `.\.venv\Scripts\voltwise-mcp.exe`. Start Streamable HTTP
with `.\.venv\Scripts\voltwise-mcp-http.exe`; its default endpoint is
`http://127.0.0.1:8000/mcp`. The HTTP command is a standalone ASGI server, so
configure `VOLTWISE_MCP_PORT=8001` if the FastAPI REST server already occupies
8000.

The official client integration test negotiated protocol `2025-11-25`. SDK
2.3.0 advertises initialize-handshake support for `2024-11-05`, `2025-03-26`,
`2025-06-18`, and `2025-11-25`, plus a distinct modern `2026-07-28` mode.

Streamable HTTP security defaults:

- SDK Host validation allows `127.0.0.1:*` and `localhost:*`.
- SDK Origin validation allows local HTTP origins; an absent Origin is valid.
- SDK body-size enforcement defaults to 1 MiB.
- `VOLTWISE_MCP_BEARER_TOKEN`, when set, requires an exact bearer token.
- Allowed hosts, origins, host, port, path, and body limit are environment
  configurable; no credential is stored in source.

For an authenticated official client, create the SDK client's HTTP client with
an `Authorization: Bearer <token>` default header and pass it to
`streamable_http_client`. Streamable HTTP has session semantics; a plain curl
example is intentionally not presented as a functional MCP client.

## `power_turn_on_and_verify`

Input:

```json
{"device": "heater"}
```

Sends one ON command and checks the settled device-level power reading.

## Supporting tool: `power_control_device`

Input:

```json
{"device": "ac", "command": "TURN_ON"}
```

Controls an ordinary simulated-home device. It is used by the bounded browser
intent router for light, fan, TV, AC, and dishwasher commands and does not
replace any verification or energy-intelligence tool.

## `power_run_diagnostic`

Input:

```json
{"device": "heater"}
```

Runs verification, telemetry-based diagnosis, policy-controlled recovery,
re-verification, and in-memory audit recording.

## `power_compare_periods`

No input arguments. Compares the current elapsed billing-cycle period with the
same number of days in the previous cycle. Returns household kWh, difference,
percentage change, elapsed days, a run-rate projection, evidence source, and a
speakable summary.

## `power_explain_usage_change`

No input arguments. Returns measured household change, ranked contributors,
runtime comparisons, metered-simulated (`MEASURED`) or `ESTIMATED` impact provenance, unattributed
energy, attribution-overage handling, limitations, and a speakable summary.

## `power_get_tariff_status`

No input arguments. Returns current and projected slab positions, marginal
rates, the next threshold, remaining units, run-rate crossing forecasts,
estimated energy charges, and a threshold warning. The result identifies the
tariff as an illustrative demo.

## `power_forecast_bill`

No input arguments. Returns current and projected itemized tariff calculations.
The amounts are estimated energy charges, not promises about a complete utility
bill.

## `power_estimate_load_impact`

Input:

```json
{"device": "dishwasher"}
```

Returns configured operation energy, usage and charge before/after, crossed
thresholds, and an informative-only summary. In the `NEAR_THRESHOLD` scenario,
the 5 kWh demo dishwasher cycle moves usage from 296 to 301 kWh.

## `power_suggest_actions`

Optional input:

```json
{"target_kwh": 300}
```

Returns target feasibility, remaining budget, required remaining daily average,
current run rate, and ranked evidence-based actions. It does not require
permission for ordinary energy use and does not claim time-of-day savings under
the configured slab-only tariff.

MCP functions contain no calculation logic. They delegate to the shared
`VoltWiseApplication`, which is also used by the HTTP adapter. MCP calls now
produce the same persisted application events as equivalent HTTP calls while
retaining all existing tool contracts.

