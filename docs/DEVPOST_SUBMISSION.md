# Devpost submission copy

## Project title

VoltWise

## Tagline

Your smart home says it's ON. VoltWise checks if it actually happened.

## Inspiration

A smart-home command acknowledgement answers only one question: did the device
accept the command? It does not prove that the expected physical response
followed. A heater can report ON while drawing standby power, or it can produce
an unsafe electrical response. VoltWise explores how an agent can treat the
command, observation, policy decision, and final verification as distinct
evidence.

## What it does

VoltWise is a deterministic Alexa+ experience prototype for household energy
and device verification. In its heater demonstration it:

- sends a simulated device command and records the device-reported state;
- compares simulated electrical observations with an expected operating range;
- identifies no-draw, unavailable-telemetry, and abnormal high-draw outcomes;
- permits at most one policy-authorized retry for a recoverable no-draw fault;
- triggers a simulated cutoff, with no retry, when a valid sample exceeds the
  configured high-draw limit; and
- preserves the before-cutoff observation and final simulated OFF state.

VoltWise also compares equivalent billing periods, estimates contributors to a
change in household use, leaves unexplained usage unattributed, forecasts an
illustrative bill, and ranks practical actions. It never presents estimated
appliance attribution as direct whole-home measurement.

The browser clearly distinguishes three facts: the Alexa+ experience is
simulated, smart-home telemetry is simulated, and MCP integration is real. The
cutoff is a software simulation and is not certified physical electrical
protection.

## How we built it

The backend uses Python 3.12, FastAPI, Pydantic, SQLite, and the official MCP
Python SDK. A real MCP server exposes nine tools over Streamable HTTP. The
FastAPI conversation gateway selects a bounded intent, creates an official MCP
client session, calls the selected tool, and returns its structured content and
trace. It does not fall back to direct application calls when MCP is down.

The application layer contains deterministic device and meter connectors,
verification and diagnostic engines, safety policy, energy comparison and
attribution logic, Decimal-based tariff calculations, and event audit records.
The React 19 and TypeScript frontend is built with Vite and renders a responsive
Digital Home, conversation flow, evidence panels, and technical MCP trace.

The recommended Windows launcher starts three local processes in dependency
order: MCP on port 8001, REST/API gateway on port 8000, and Vite on port 5173.
It verifies MCP with the official client before opening the demo. A separate
single-port container package exists for reproducible packaging, but no AWS or
other hosted deployment is claimed.

## Challenges

The hardest part was maintaining evidence boundaries. A reported ON state
could not be allowed to become a verified physical outcome. A transient unsafe
peak also had to remain decisive even if a later sample looked normal or the
connector separately reported telemetry unavailable. That required safety
classification to examine valid observations before availability context,
preserve the trigger, cut simulated power, and prohibit retry.

Recovery introduced a different boundary: the system may retry only once and
may claim recovery only after fresh post-retry evidence passes verification.
The UI then had to distinguish historical before-cutoff readings from final
state, and clear stale evidence between unrelated requests.

Finally, keeping the MCP claim honest required an actual official client/server
round trip over Streamable HTTP while retaining deterministic fixtures suitable
for a short repeatable judge demo.

## Accomplishments

- A reproducible five-scene demo: neutral landing, no-draw failure, one-retry
  recovery, high-draw safety stop, and energy explanation.
- Real Streamable HTTP MCP discovery and execution across a nine-tool registry.
- Safety invariants covering unsafe transient peaks, unavailable telemetry,
  zero retry after cutoff, final OFF state, and preserved audit evidence.
- Accessible keyboard-operable appliance hotspots, visible focus, responsive
  laptop layouts, reduced-motion support, and clear simulation disclosures.
- On October 20, 2026, the release workspace passed 161 backend tests, 63
  frontend tests, the production build, and focused real-MCP smoke checks.

## What we learned

Agentic control becomes credible when every conclusion names its evidence and
every action has a boundary. Command acknowledgement, reported state,
electrical observation, policy decision, and verified outcome are different
facts. MCP structured results made those facts easier to transport without
flattening them into reassuring prose. Deterministic resettable fixtures also
made safety behavior demonstrable and regression-testable.

## What's next

Future work could connect VoltWise to an Alexa+ integration path when an
appropriate supported interface is available, ingest compatible smart-plug or
circuit telemetry with explicit provenance, and extend verified-response
policies to more appliance types. Those integrations are not part of this
submission.

## Product feedback

### Verified developer experience

The official MCP Python SDK provided a consistent way to initialize a session,
discover tools, invoke structured operations, and use Streamable HTTP. The same
tool contracts worked in direct integration tests and through the local
conversation gateway. Transport-level traces were especially useful for
showing judges which parts of the demonstration were real.

### Suggestions

For Alexa+ developers, a single public reference path showing how an Alexa+
experience should securely discover and call a remote MCP server would reduce
ambiguity between conversational prototyping and production integration. A
small end-to-end sample covering authentication, structured errors, local
testing, and submission disclosure language would also help teams make precise
claims. These are suggestions based on this prototype; we did not receive or
claim private Amazon support, production Alexa+ API access, or certification.

## Demo instructions

Prerequisites are Windows 10/11, Python 3.12, and Node.js 24. From the repository
root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
cd frontend
npm.cmd ci
cd ..
.\start-voltwise.bat
```

Open `http://127.0.0.1:5173`. Follow [DEMO_UI.md](DEMO_UI.md), resetting before
each independent scene. For Recovery, select the preset and run **Diagnose
heater** directly; do not consume its first observation with a separate command.
Run `stop-voltwise.bat` when finished.

## Submission links

- GitHub repository: **[ADD GITHUB URL]**
- YouTube or Vimeo video: **[ADD YOUTUBE OR VIMEO URL]**
- Optional live deployment: **[ADD LIVE URL OR STATE "Local demo"]**

## Manual rule verification required

No authoritative Amazon Developer Hackathon 2026 rules or Devpost field schema
is stored in this repository. Before submission, manually verify current
eligibility, track selection, deadline/time zone, team-member requirements,
video visibility and duration rules, repository visibility/licensing rules,
required media, and any mandatory product-feedback fields on the official event
and Devpost pages. This draft does not guess at fields that could not be
verified locally.

