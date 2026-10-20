# VoltWise web experience

This React + TypeScript + Vite app is the judge-facing Alexa+ experience
simulation for VoltWise. It calls the existing FastAPI service and renders the
evidence behind every backend-generated answer. It does not emulate a
microphone, Alexa hardware, MCP host, or AWS runtime.

## Start locally

Use the checked three-service launcher from the repository root. It starts the
real MCP server, REST simulator gateway, and frontend, then resets the demo:

```powershell
.\start-voltwise.bat
```

Open `http://127.0.0.1:5173`. The default API URL is
`http://127.0.0.1:8000`. To override it, copy `.env.example` to `.env.local`
and set `VITE_API_BASE_URL`.

## Validate

```powershell
npm.cmd test
npm.cmd run build
```

The test suite covers startup and offline states, all six supported intents,
evidence rendering, verified/failed/recovered/safety outcomes, presets, reset,
errors, event history, and responsive interaction primitives.

## Architecture boundary

The browser sends bounded demo utterances to `POST /api/sim/chat`. The gateway
selects a tool deterministically, then uses the official MCP client over real
Streamable HTTP to invoke VoltWise. It does not fall back to direct application
calls when MCP is unavailable. All energy values, classifications, tariff math,
recommendations, safety decisions, events, and speakable summaries come from
the backend. The Alexa+ experience and smart-home telemetry are simulated; the
MCP integration and deterministic VoltWise logic are real.

See [`../docs/DEMO_UI.md`](../docs/DEMO_UI.md) for the demo script and complete
utterance list.
