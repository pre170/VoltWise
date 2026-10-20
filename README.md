# VoltWise — Energy-Aware Physical Outcome Verification

> **Amazon Developer Hackathon Submission**  
> *Your smart home says it's ON. VoltWise checks if it actually happened.*

---

## Overview: The "Beyond ON" Problem

In contemporary smart-home platforms, commanding a device to turn on returns a simple acknowledgement: `"Living room heater is ON"`. However, this acknowledgement answers only one question: **did the device accept the radio command?**

It does **not** prove that the expected physical or electrical response occurred:
- A heater can acknowledge `ON` while stuck in an idle standby draw (~7 W instead of ~1,500 W).
- A malfunctioning appliance can draw hazardous, abnormal current (~2,200 W exceeding safety thresholds).
- A household can experience unexplained bill spikes without transparent, non-hallucinatory attribution of which appliances contributed and what remained unattributed.

**VoltWise** bridges this gap. Built for an intelligent conversational assistant experience, VoltWise treats the command, the reported state, physical electrical observations, safety policy decisions, and verified outcomes as distinct, verifiable layers of evidence.

---

## Real Architecture vs. Simulated Demonstration Boundaries

To ensure complete technical honesty and transparency for hackathon evaluation, VoltWise strictly delineates what is real software and what is a simulated test fixture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SIMULATED JUDGING SURFACE (BROWSER)                  │
│  React 19 + TypeScript + Vite Interactive "Digital Home" & Chat UI     │
│  (Simulated Alexa-style conversational interaction; NOT native Alexa+) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP POST /api/sim/chat
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   REAL FASTAPI SIMULATOR GATEWAY                       │
│  - Parses natural language intent (e.g. "Alexa, what's causing...")   │
│  - Deterministically selects matching tool and typed arguments         │
│  - Opens official MCP ClientSession over Streamable HTTP               │
│  - NO backdoor/direct application fallback if MCP is unavailable       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Real MCP ClientSession
                                    │ Streamable HTTP (Port 8001 / /mcp)
                                    │ Protocol 2025-11-25
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 REAL MODEL CONTEXT PROTOCOL (MCP) SERVER               │
│  Official Python SDK 2.3.0 Streamable HTTP Transport                  │
│  Full 9-Tool Registry (Verification, Diagnostics, Energy & Tariffs)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Typed Function Calls
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 REAL APPLICATION ENGINES & LOGIC                       │
│  - VerificationService: Compares expected vs observed electrical draw  │
│  - DiagnosticEngine: Classifies behavior (offline, standby, abnormal)  │
│  - SafetyEngine: Zero-retry cutoff if draw exceeds safe threshold      │
│  - EnergyUsageEngine & TariffEngine: Decimal slab & run-rate analytics │
│  - SQLiteEventRepository & TraceRepository: Full persisted audit trail │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Telemetry & State Polling
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            SIMULATED ELECTRICAL TELEMETRY & APPLIANCE FIXTURES         │
│  - Deterministic resistive heater, AC, TV, fan, and light profiles     │
│  - Standby (7 W), operating (1,500 W), and high-draw (2,200 W) faults  │
│  - Deterministic 30-day billing cycle historical telemetry fixtures   │
└────────────────────────────────────────────────────────────────────────┘
```

### What is 100% Real
1. **Model Context Protocol (MCP) Server & Client**: Built on the official Python `mcp` SDK (2.3.0). Exposes tools over standard `stdio` and real `Streamable HTTP` transports. The client negotiates protocol version `2025-11-25` over live network connections.
2. **Simulator Gateway**: The FastAPI backend communicates with the MCP server exclusively through the official `mcp.client.session.ClientSession` and `streamable_http_client`. There is zero in-process bypass or direct application fallback.
3. **Verification & Diagnostic Engines**: Full deterministic physics rules, range checks, transient peak detection, safe retry bounds, and safety stop orchestration.
4. **Energy & Tariff Intelligence**: Exact timestamp boundary comparisons, run-rate projections, non-hallucinatory attribution accounting (measuring vs estimating vs preserving unattributed kWh), and `Decimal` slab tariff math.
5. **Audit Trails**: Real SQLite database persistence for application events and MCP traces.

### What is Simulated (Explicit Disclosures)
- **Simulated Alexa-Style UI**: The judge-facing browser UI simulates how an Alexa+ conversational agent would present this data. It is **not** a native Alexa+ deployment, Alexa Skill, or certified Amazon device package.
- **Simulated Electrical Telemetry**: Smart plugs, household meters, appliance states, and electrical wattages are deterministic software fixtures. There is **no physical smart-plug hardware** or physical IoT bench connected.
- **Simulated Electrical Cutoff**: The safety cutoff is an immediate software state change (`0 W`, state `OFF`, zero retries). It does **not** represent a certified physical circuit breaker, relay hardware, or UL/CE production electrical safety certification.
- **Illustrative Tariff**: The configured 300 kWh threshold slab tariff is an illustrative model for demonstration purposes, not live utility tariff data.

---

## The 9 Actual MCP Tools

VoltWise exposes nine tools in a unified registry accessible via `stdio` and `Streamable HTTP` (`/mcp`):

| # | MCP Tool Name | Arguments | Description & Return Contract |
|---|---------------|-----------|-------------------------------|
| 1 | `power_turn_on_and_verify` | `device: str` | Turns on a device and checks whether observed electrical power settles within expected operational bounds. Returns `VerificationResult`. |
| 2 | `power_run_diagnostic` | `device: str` | Executes full verification, diagnoses electrical failure modes, enforces safe retry policies, and returns `DiagnosticWorkflowResult` with technician handoff copy. |
| 3 | `power_compare_periods` | *none* | Compares current-cycle energy with the equivalent elapsed period from the previous billing cycle. Returns `PeriodComparisonResult`. |
| 4 | `power_explain_usage_change` | *none* | Ranks observed appliance contributors, estimates runtime impacts, and preserves unattributed consumption. Returns `UsageChangeExplanation`. |
| 5 | `power_get_tariff_status` | *none* | Computes current slab position, projected end-of-month consumption, marginal rates, and threshold crossing dates. Returns `TariffStatus`. |
| 6 | `power_forecast_bill` | *none* | Itemizes current energy charges and forecasts billing cycle totals using exact Decimal calculations. Returns `BillForecast`. |
| 7 | `power_estimate_load_impact` | `device: str` | Projects incremental kWh and financial impact of running a specific appliance cycle (e.g. dishwasher). Returns `LoadImpactResult`. |
| 8 | `power_suggest_actions` | `target_kwh: float \| null` | Evaluates target consumption feasibility and ranks evidence-based actions without demanding lifestyle compromises. Returns `ActionSuggestions`. |
| 9 | `power_control_device` | `device: str`, `command: str` | Supporting tool for ordinary simulated-home appliances (living room light, ceiling fan, TV, AC). Returns `DeviceControlResult`. |

---

## Installation & Local Startup

### Prerequisites
- **Operating System**: Windows 10/11 (with PowerShell 5.1+) or Linux / macOS
- **Python**: Version `3.12`
- **Node.js**: Version `24` (requires Node 24.15 or later)
- **Docker**: Optional (for single-port container packaging)

---

### Method A: One-Click Windows Launcher (Recommended)

1. Clone or extract the repository:
   ```powershell
   cd VoltWise
   ```
2. Initialize Python virtual environment and frontend dependencies:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python -m pip install -e ".[dev]"
   cd frontend
   npm.cmd ci
   cd ..
   ```
3. Run the automated launcher:
   ```powershell
   .\start-voltwise.bat
   ```
   *The launcher verifies port availability, starts the MCP Streamable HTTP server on port 8001, validates official client readiness across all tools, starts the FastAPI REST gateway on port 8000, starts the Vite frontend on port 5173, resets the demo state, and opens your default browser.*

4. To stop all background demo processes cleanly:
   ```powershell
   .\stop-voltwise.bat
   ```

---

### Method B: Manual Multi-Terminal Startup

#### Terminal 1 — Real MCP Server (Port 8001)
```powershell
$env:VOLTWISE_MCP_PORT = "8001"
.\.venv\Scripts\voltwise-mcp-http.exe
```

#### Terminal 2 — FastAPI REST API & Simulator Gateway (Port 8000)
```powershell
$env:VOLTWISE_MCP_URL = "http://127.0.0.1:8001/mcp"
.\.venv\Scripts\voltwise-api.exe
```

#### Terminal 3 — Vite Frontend (Port 5173)
```powershell
cd frontend
npm.cmd run dev
```
Open **`http://127.0.0.1:5173`** in any modern web browser.

---

### Method C: Single-Port Production Container (Docker)

VoltWise includes a self-contained multi-stage `Dockerfile` that packages the compiled React frontend, FastAPI backend, and MCP server into a single non-root container running on port `8080`:

```powershell
docker build -t voltwise .
docker run --rm -p 8080:8080 -v voltwise-data:/data voltwise
```

Open **`http://127.0.0.1:8080`**. Health check is available at `/health`, REST API at `/api/...`, and MCP at `/mcp`.

---

## The Five Canonical Demo Scenarios

Use the **Demo setup** preset selector in the judge UI (or command the simulated assistant) to reproduce all 5 core demonstration flows:

### Scenario 1: Heater Electrical Response Failure (`NO_DRAW`)
- **Initial Setup**: Select **No draw fault** preset (or click **Reset demo**).
- **User Action**: Type `"Turn the heater on"` or click the **Turn on heater** quick action.
- **Observed Behavior**:
  - The living room heater UI reports `ON`.
  - Electrical telemetry observation detects only **~7 W** (idle standby power) instead of the nominal **~1,500 W**.
  - VoltWise flags the failure: **"Not verified: Living room heater acknowledged ON, but electrical draw is only 7 W"**.
  - The floorplan tile highlights the device in an unverified warning state.

### Scenario 2: Diagnostic Telemetry & Technician Handoff Copy
- **Initial Setup**: Follows Scenario 1 while the heater is in the unverified state.
- **User Action**: Type `"Check what's wrong with the heater"` or click **Diagnose heater**.
- **Observed Behavior**:
  - VoltWise invokes the MCP `power_run_diagnostic` tool.
  - The diagnostic engine analyzes power history, identifies standby-only draw without mechanical heat generation, and classifies the root fault.
  - Generates clear, field-ready **Technician Handoff Copy** (component checks, element resistance, relay continuity) without human speculation.

### Scenario 3: Bounded Recovery After Single Safe Retry (`NO_DRAW_THEN_RECOVER`)
- **Initial Setup**: Select **Recovery demo** preset in the Demo setup dropdown.
- **User Action**: Type `"Check what's wrong with the heater"`.
- **Observed Behavior**:
  - Initial electrical verification fails at ~7 W.
  - Safety policy confirms the failure is non-hazardous and authorizes **exactly one safe retry**.
  - VoltWise cycles the simulated control and re-verifies electrical response.
  - Re-verification detects **~1,500 W** normal operating draw.
  - Status updates to **"Physically Verified: Living Room Heater is drawing 1,500 W"**, successfully recovering without human intervention.

### Scenario 4: High-Draw Safety Cutoff (`HIGH_DRAW`)
- **Initial Setup**: Select **High draw fault** preset.
- **User Action**: Type `"Turn the heater on"`.
- **Observed Behavior**:
  - Telemetry detects an unsafe surge to **~2,200 W** (exceeding nominal 1,500 W and the 1,900 W safety ceiling).
  - Safety engine executes an **immediate software safety cutoff**:
    - Simulated power cut to **0 W**.
    - Device forced to **OFF**.
    - **Zero retries** permitted by safety policy.
  - Display alerts the user with an urgent safety stoppage warning and preserves the triggering electrical evidence in the audit log.

### Scenario 5: Conversational Natural-Language Energy Intelligence
- **Initial Setup**: Click **Reset demo** to restore the canonical `NORMAL_CURRENT_CYCLE` scenario.
- **User Action**: Type:
  > *"Alexa, what's causing my electricity usage to increase?"*  
  *(Also accepts natural variants: "Why is my electricity bill going up?", "What's using more electricity?", "Why did my energy usage increase?")*
- **Observed Behavior**:
  - Routed through MCP `power_explain_usage_change`.
  - Transparent accounting explains:
    - Current period usage: **142.0 kWh** vs previous equivalent period: **118.0 kWh** (**+24.0 kWh / +20.34%** increase).
    - Ranked primary contributor: Air Conditioner (+21 hours runtime = **15.75 kWh** estimated contribution).
    - Other auxiliary loads: **3.60 kWh**.
    - Unattributed consumption: **4.65 kWh** (honestly reported as unexplained household variation rather than hallucinating fake appliance IDs).

---

## Verification & Test Suites

VoltWise maintains thorough test coverage across backend engines, REST APIs, MCP transports, and frontend components.

### Backend Validation (169 Tests Passing)
Run pytest from the repository root:
```powershell
.\.venv\Scripts\python -m pytest
```
*Tests cover: physical verification rules, safety engine cutoff triggers, one-retry boundary limits, tariff slab quantization, billing run-rate forecasting, MCP Streamable HTTP protocol negotiation (2025-11-25), and simulator gateway routing.*

### Frontend Validation (74 Tests Passing)
Run Vitest from the `frontend/` directory:
```powershell
cd frontend
npm.cmd test -- --run
```
*Tests cover: judge UI interactions, appliance control, high-draw safety presentation, energy explanation cards, live MCP technical traces, and keyboard accessibility.*

### Production Build Validation
Verify TypeScript types and Vite production bundling:
```powershell
cd frontend
npm.cmd run build
```

---

## Configuration & Environment Variables

Default development settings operate out of the box on `localhost` without requiring any `.env` file. To customize, copy `.env.example` to `.env` or set environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `VOLTWISE_MODE` | `SIMULATION` | Runtime mode (`SIMULATION` or `PRODUCTION`). |
| `VOLTWISE_DB_PATH` | `data/voltwise.db` | Path to the SQLite event and trace database. |
| `VOLTWISE_MCP_HOST` | `127.0.0.1` | Bind address for the MCP Streamable HTTP server. |
| `VOLTWISE_MCP_PORT` | `8001` | Port for the standalone MCP HTTP server. |
| `VOLTWISE_MCP_URL` | `http://127.0.0.1:8001/mcp` | URL used by the REST gateway to reach MCP. |
| `VOLTWISE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Permitted browser origins. |
| `VOLTWISE_PUBLIC_DEMO` | `false` | Enables HTTP Basic challenge and bearer tokens for public demo staging. |

---

## Security & Privacy Hygiene

This release distribution is prepared for public GitHub publication:
- **No private keys, API secrets, or passwords**: Authentication tokens in `.env.example` are blank placeholders.
- **No runtime databases committed**: `.db` files are strictly excluded; the database directory is initialized automatically at startup.
- **No machine-specific paths**: All paths in scripts and configuration are relative to project root.
- **Sanitized release tree**: `node_modules`, `.venv`, `.pytest_cache`, temporary video artifacts, screen captures, and build caches are purged from the repository.

---

## License

This project is licensed under the terms of the **MIT License**. See the [LICENSE](LICENSE) file for full details.
