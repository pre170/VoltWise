# VoltWise demo UI

## What the browser represents

The web app is an **Alexa+ experience simulation** for judging and local demos.
It is a text conversation surface with a synchronized evidence panel. Normal
conversation uses `POST /api/sim/chat`; the FastAPI simulator gateway then uses
the official MCP client over real Streamable HTTP. The browser is not itself an
Alexa+ client. It simulates the conversational experience while exercising the
same MCP capabilities intended for an MCP host. No certification, real Alexa+
execution, AWS service, Alexa device, microphone, notification, technician, or
maintenance workflow is claimed.

## Three-minute judge flow

Each numbered scenario starts from its own reset. Results from separate scenes
must not be narrated as one continuous device recovery.

1. Run `start-voltwise.bat`, then open `http://127.0.0.1:5173`. Confirm the
   header shows **Connected** and the compact disclosure says the Alexa+
   experience and telemetry are simulated while MCP is real. The initial heater
   is OFF and ready to verify; no verification outcome is shown yet.
2. **Heater failure first:** open **Demo setup**, choose **Heater failure**, then
   select **Turn on & verify heater**. The right panel progresses through
   command, electrical evidence, evidence diagnosis, and conclusion over about
   9.6 seconds. This is presentation pacing over one completed MCP operation; it
   does not send extra heater commands. Point out the difference between the
   device report (`ON`) and the independent electrical response (`Electrical
   response not verified`). Open **Get diagnostic summary** to show the copyable
   evidence handoff; no technician is contacted. Select **Diagnose heater
   safely** only when demonstrating the separate bounded-retry workflow. Expand **Technical
   evidence** to show the real MCP call and structured result.
3. Open **Demo setup** and select **Reset demo**. Then choose **Recovery** and
   select **Diagnose heater** directly. Do not run a separate verification first,
   because that would consume the fixture's initial no-draw observation. This is
   a separate deterministic scene: diagnosis observes the initial failure, uses
   one safe retry, and verifies the final electrical response.
4. Open **Demo setup** and select **Reset demo**. Then choose **Safety stop** and
   run **Turn on & verify heater**. Show the high reading labelled **Before
   cutoff**, the final simulated OFF state, and the absence of a retry. This is
   simulated policy enforcement, not certified physical electrical protection.
5. Open **Demo setup** and select **Reset demo**. Select **Why is our usage
   higher?** to show the ranked observed contributor, estimated energy impact,
   provenance, and explicitly unattributed remainder.
6. Expand **Technical evidence**. Show the tool name, arguments, Streamable HTTP
   transport, negotiated protocol, result summary, and duration. MCP traces are
   real; **Application events** are listed separately. Finish with **Reset demo**
   so the browser returns to its neutral deterministic state.

Optional energy follow-up after another reset: use **How are we doing this
month?**, **How's my tariff looking?**, and **Can we stay under 300 units?** to
show equivalent-period comparison, incremental tariff wording, and target
guidance.

## Supported utterances

Routing is intentionally bounded. Equivalent wording matching these patterns is
accepted; unsupported requests receive a capability reminder rather than a
fabricated answer.

| Example utterance | Intent | MCP tool selected by `/api/sim/chat` |
|---|---|---|
| How are we doing this month? | Energy comparison | `power_compare_periods` |
| Why is it higher? | Usage explanation | `power_explain_usage_change` |
| How's my tariff looking? | Tariff status | `power_get_tariff_status` |
| What will my bill be? | Bill forecast | `power_forecast_bill` |
| How can we reduce usage? | Suggestions | `power_suggest_actions` |
| Can we stay under 300 units? | 300 kWh target guidance | `power_suggest_actions` with target 300 |
| Turn on the heater. | Command and verify | `power_turn_on_and_verify` |
| Diagnose the heater. | Safe diagnostic | `power_run_diagnostic` |

## Evidence views

- Energy comparison: current and equivalent previous-period bars plus run-rate
  projection inputs.
- Usage explanation: ranked device evidence, provenance labels, and unattributed
  household change.
- Tariff: current/projected positions against 100/200/300 kWh thresholds with
  marginal-rate wording.
- Target: remaining budget ring, required daily average, current run rate, and
  backend-ranked actions.
- Verification: requested/reported state and expected/observed power.
- Diagnostic: all six workflow stages, API-reported wattage per attempt, retry
  count, classification, safety action, and final status.

## Demo controls and presets

The drawer calls `/api/demo/*`; it never mutates UI-only copies of backend
state. Primary faults are `NONE`, `NO_DRAW`, `NO_DRAW_THEN_RECOVER`, and
`HIGH_DRAW`. Presets reset
the deterministic simulator before selecting Normal, Failure, Recovery, Safety
stop, or Tariff edge conditions. Demo controls remain REST calls. The MCP trace
refreshes from `GET /api/sim/traces`, while application events continue to come
from `GET /api/events`.

**Reset demo** is the canonical reset during an active browser demonstration. It
restores the normal backend fixture and clears the current conversation,
in-scene device state, open evidence, and live result sequence. Persisted MCP
traces and application events remain available only as historical technical
evidence; they are not presented as the new current result.
