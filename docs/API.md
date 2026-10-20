# VoltWise HTTP API

## Startup

```powershell
cd path\to\VoltWise
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\uvicorn.exe app.api.app:app --reload --port 8000
```

Interactive OpenAPI documentation is at `http://127.0.0.1:8000/docs`; the schema
is at `/openapi.json`.

## Application architecture

FastAPI's domain routes and MCP are adapters over the same application logic.
The simulator gateway is different from a domain route: it uses the official
MCP client to invoke the standalone Streamable HTTP server. Its intent router
only selects a tool and arguments. It does not call domain services or REST
routes as a fallback.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Service health and mode |
| GET | `/api/household/overview` | Dashboard-ready household snapshot |
| GET | `/api/devices` | Devices and typed capabilities |
| GET | `/api/devices/{device_id}` | Device state, runtime, and evidence |
| POST | `/api/devices/{device_id}/turn-on-and-verify` | Shared verification workflow |
| POST | `/api/devices/{device_id}/diagnose` | Shared diagnostic/recovery workflow |
| GET | `/api/energy/comparison` | Equivalent-period comparison |
| GET | `/api/energy/explanation` | Usage-change explanation |
| GET | `/api/tariff/status` | Current/projected tariff position |
| GET | `/api/tariff/forecast` | Itemized energy-charge forecast |
| GET | `/api/tariff/load-impact/{device_id}` | Estimated operation impact |
| POST | `/api/tariff/recommendations` | Optional target guidance |
| GET | `/api/events?limit=50` | Recent persisted audit events |
| POST | `/api/sim/chat` | Route a browser utterance through real MCP |
| GET | `/api/sim/traces?limit=30` | Recent persisted MCP call traces |

Recommendations accept `{"target_kwh": 300}`. Errors use:

```json
{"error":{"code":"DEVICE_NOT_FOUND","message":"Unknown device: xyz"}}
```

Simulator chat accepts:

```json
{"message":"How are we doing this month?"}
```

Its typed response contains `message`, `intent`, `tool_call`, the real
structured MCP `result`, and `trace_id`. If MCP is unavailable it returns HTTP
503 with code `MCP_SERVICE_UNAVAILABLE`; it does not silently use a direct
domain path. `VOLTWISE_MCP_URL` defaults to
`http://127.0.0.1:8001/mcp`. `VOLTWISE_MCP_BEARER_TOKEN`, when configured, is
sent only as the official MCP client's Authorization header and is never stored
in a trace.

The `mcp_traces` SQLite table stores `trace_id`, `timestamp`, `transport`,
`protocol_version`, `intent`, `tool_name`, intentionally serialized tool
arguments, `result_summary`, actual duration, success, and a safe error type.
These records are distinct from `/api/events` application events.

## Simulation controls

These routes are mounted only in simulation mode:

| Method | Path | Body |
|---|---|---|
| GET | `/api/demo/state` | none |
| POST | `/api/demo/reset` | none |
| POST | `/api/demo/energy-scenario` | `{"scenario":"NEAR_THRESHOLD"}` |
| POST | `/api/demo/device-fault` | `{"device":"heater","fault":"NO_DRAW"}` |

Scenario and fault changes take effect immediately without restarting the API.
Reset restores `NORMAL_CURRENT_CYCLE`, `NONE`, the canonical simulation time,
and the heater's initial OFF/2 W state.

## Persistence and configuration

SQLite initializes automatically at `data/voltwise.db`. It stores application
events and selected demo state, not raw fixture telemetry. Tests inject isolated
temporary databases.

Environment variables:

- `VOLTWISE_MODE=SIMULATION`
- `VOLTWISE_DB_PATH=data/voltwise.db`
- `VOLTWISE_CORS_ORIGINS=http://localhost:5173`
- `VOLTWISE_ENERGY_SCENARIO=NORMAL_CURRENT_CYCLE`
- `VOLTWISE_HEATER_FAULT=NONE`
- `VOLTWISE_MCP_URL=http://127.0.0.1:8001/mcp`
- `VOLTWISE_MCP_CLIENT_TIMEOUT_SECONDS=8`
- `VOLTWISE_MCP_BEARER_TOKEN` (optional; shared with the MCP server)

CORS uses explicit origins; wildcard access is not enabled.
