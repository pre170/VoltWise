# Architecture

VoltWise has three business paths composed once inside `VoltWiseApplication`:

```text
Device command path
  SimulatedDeviceConnector
    -> VerificationService
    -> DiagnosticEngine
    -> SafetyEngine
    -> DiagnosticWorkflowService

Energy intelligence path
  FixtureEnergyRepository
    -> whole-home cumulative readings
    -> device state transitions
    -> optional device cumulative-energy readings
    -> BillingCycle + SimulationClock
  RuntimeEngine + EnergyUsageEngine + UsageAnalysisEngine
    -> EnergyIntelligenceService

Tariff intelligence path
  illustrative TariffPlan + energy intelligence
    -> TariffEngine (Decimal slab calculations)
    -> TariffIntelligenceService
       -> status + crossing forecast
       -> energy-charge forecast
       -> load impact
       -> target and evidence-based actions

All paths -> typed application results
```

## Shared application adapters and simulator gateway

```text
MCP host ------> stdio ------------------------\
                                                -> shared MCP tool registry -> VoltWiseApplication
Remote client -> Streamable HTTP --------------/                                  |
                                                                                   -> SQLiteEventRepository

Browser -> POST /api/sim/chat -> FastAPI Simulator Gateway
                                  -> official MCP ClientSession
                                  -> Streamable HTTP
                                  -> shared MCP tool registry
                                  -> VoltWiseApplication

Browser demo controls -> FastAPI domain REST adapter -> VoltWiseApplication
```

Both MCP transports expose one nine-tool registry: the eight VoltWise
intelligence and verification tools plus the supporting
`power_control_device` tool for ordinary simulated-home commands. There is no
second HTTP tool registry. For judge-facing conversation, the browser
sends only a message to the typed simulator gateway. Its deterministic router
selects an intent, tool name, and arguments, then the official MCP
`ClientSession` executes the real remote tool. The router and gateway contain no
verification, diagnostic, energy, tariff, or recommendation calculations.

The browser itself is not an Alexa+ client. It is a hackathon simulation of the
Alexa+ conversational experience. The simulator gateway behaves as the MCP
client so the demonstration exercises the same MCP tools intended for an MCP
host. No Alexa+ certification or real Alexa+ execution is claimed.

`voltwise-mcp` owns stdio. `voltwise-mcp-http` builds the official SDK
Streamable HTTP Starlette application and runs it with Uvicorn. The latter is a
standalone ASGI process rather than a route that merely resembles MCP. This
keeps the existing FastAPI lifecycle and CORS configuration intact. The default
MCP URL is `http://127.0.0.1:8000/mcp`; choose another configured port when the
REST API is running concurrently.

The SDK transport applies Host/Origin validation and a 1 MiB request-body limit
by default. VoltWise adds a narrow constant-time fixed bearer-token check when
`VOLTWISE_MCP_BEARER_TOKEN` is configured. This is development/controlled
deployment authentication, not OAuth authorization or a public deployment.

With MCP Python SDK 2.3.0, the official initialize-based client/server test
negotiates protocol `2025-11-25`. The SDK also exposes a separate modern
`2026-07-28` mode; VoltWise does not misreport that as the initialize result.

`SQLiteEventRepository` persists sanitized application events plus the selected
energy scenario and heater fault. Recreating the application against the same
database restores demo selection. Raw deterministic fixture telemetry is not
migrated into SQLite.

`SQLiteMCPTraceRepository` separately persists real simulator-gateway attempts:
trace ID, timestamp, transport, negotiated protocol when available, selected
intent/tool/arguments, result summary, measured duration, success, and a safe
error type. It never stores bearer tokens, Authorization headers, or arbitrary
request headers. Failed MCP calls are recorded as failures and are never
silently replaced by REST or direct application calls.

Because the REST demo controls and MCP server normally run in separate local
processes, each real MCP tool request adopts any changed scenario/fault from the
shared SQLite application-state records before executing. It refreshes only
when the persisted selection differs, so multi-attempt diagnostic state remains
intact within a tool call.

## Single-origin container composition

The deployment entry point is `app.deployment:main`. One Uvicorn listener
routes `/api/...` and `/health` to FastAPI, `/mcp` to the SDK Streamable HTTP
application, and all other non-file paths to the compiled React SPA. The
gateway still opens an official MCP client session to the loopback `/mcp` URL;
the composition does not replace MCP with an in-process function call.

The deployment factory binds its FastAPI and MCP adapters to one explicitly
constructed `VoltWiseApplication`, so a configured SQLite path is shared by
both. The MCP binding is request-local, leaving standalone stdio and HTTP
server behavior unchanged. This package intentionally runs one worker and one
instance because demo selection, transient devices, and MCP sessions are not
partitioned per judge.

FastAPI exposes typed response models, structured errors, OpenAPI, and explicit
development CORS origins. Demo routes are mounted only in `SIMULATION` mode.
`PRODUCTION` is reserved but no production connector exists yet.

## Energy boundaries

`EnergyRepository` isolates analysis from fixture storage. Its current in-memory
implementation provides five devices with different capabilities: AC, heater,
refrigerator, TV, and dishwasher. It can later be replaced without changing the
engines.

`EnergyUsageEngine` calculates household kWh from cumulative readings at exact
period boundaries. It compares the first 14 current-cycle days with exactly 14
days of the previous cycle and uses a clearly labelled run-rate projection.

`RuntimeEngine` derives ON duration from state transitions, including states
spanning period boundaries. It rejects conflicting or repeated transitions.

`UsageAnalysisEngine` ranks positive observed impacts. Dedicated energy meters
produce `MEASURED` impacts; runtime multiplied by configured nominal power
produces `ESTIMATED` impacts. Any remaining household increase is unattributed.
If contributor totals exceed household change, the result reports an attribution
overage instead of presenting false precision.

## Tariff boundaries

`TariffEngine` is independent from household fixtures. It supports incremental
`TELESCOPIC` slabs and configurable `NON_TELESCOPIC` threshold plans. Currency
uses `Decimal`, with energy quantized to 0.001 kWh and money to 0.01.

`TariffIntelligenceService` combines the existing run-rate projection with a
typed tariff. Threshold proximity is governed by `TariffAwarenessPolicy`, not a
scattered constant. Appliance impact remains informative and never blocks
control. Recommendations use existing runtime and unattributed-energy evidence.

`NORMAL_CURRENT_CYCLE` remains the default deterministic scenario. The typed
`NEAR_THRESHOLD` scenario contains 296 kWh at day 27 and is selected through
`VOLTWISE_ENERGY_SCENARIO` without source edits.

## Existing diagnostic path

The simulator produces telemetry but never provides its fault name to the
diagnostic engine. High draw cuts simulated power and forbids retry. Other
failures receive at most one policy-permitted retry. All attempts are audited.

Complete real-utility billing, raw telemetry persistence, AWS, technicians,
maintenance, notifications, real voice capture, and real integrations remain
out of scope. The web frontend is a judge-facing Alexa+ experience simulation
over the HTTP adapter; it is not a production Alexa client.

