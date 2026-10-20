# VoltWise submission video script

Target length: **2:40**. Read at a calm pace and let the evidence remain visible.
Every scene begins with **Reset demo**; scenes are independent fixtures.

## 0:00-0:15 - The problem

**Screen:** Neutral Digital Home landing view and Ready to Verify panel.

**Narration:** "Smart-home devices can report that a command succeeded without
proving the expected electrical response occurred. VoltWise checks the
evidence. This Alexa+ experience and its household telemetry are simulated; the
MCP client-server integration is real."

## 0:15-0:45 - Failed verification

**Screen:** Demo setup -> Heater failure -> Turn on & verify heater. Hold on the
result panel.

**Narration:** "Here the simulated heater accepts the command and reports ON.
VoltWise separately expects about fifteen hundred watts, but observes only
seven. Reported ON is neutral evidence, not proof. The electrical response is
not verified, and the UI preserves both the expected and observed readings."

## 0:45-1:15 - Bounded recovery

**Screen:** Reset demo -> Demo setup -> Recovery -> Diagnose heater. Do not run
Turn on & verify first. Hold on the two attempts and RECOVERED result.

**Narration:** "This is a separate recoverable fixture. Diagnosis first observes
the same no-draw failure. Policy permits one safe retry, then re-verification
observes about fifteen hundred watts. Recovery is reported only after that new
electrical evidence verifies the expected response."

## 1:15-1:40 - Simulated safety stop

**Screen:** Reset demo -> Demo setup -> Safety stop -> Turn on & verify heater.
Point to 2,200 W, 1,900 W threshold, Before cutoff, zero retry, and final OFF.

**Narration:** "In the high-draw fixture, a valid twenty-two-hundred-watt sample
exceeds the configured nineteen-hundred-watt limit. VoltWise invokes its
simulated cutoff, performs zero retries, preserves the triggering sample as
before-cutoff evidence, and shows the final simulated device state as OFF. This
is a software demonstration, not certified physical electrical protection."

## 1:40-2:05 - Energy explanation

**Screen:** Reset demo -> Why is our usage higher? Show the comparison and
ranked attribution.

**Narration:** "VoltWise also explains energy changes without pretending a
whole-home meter identifies every load. The current equivalent period is one
hundred forty-two kilowatt-hours versus one hundred eighteen. Increased air
conditioner runtime contributes an estimated fifteen point seven five
kilowatt-hours, while four point six five remains explicitly unattributed."

## 2:05-2:30 - Real MCP evidence

**Screen:** Expand Technical evidence for the energy response. Show tool name,
transport, negotiated protocol, duration, and structured result.

**Narration:** "This technical evidence comes from a real official MCP client
calling VoltWise tools over Streamable HTTP. The server exposes nine tools and
this session negotiated protocol twenty twenty-five dash eleven dash twenty-five.
The browser simulates an Alexa+ conversation, while the MCP request, tool
execution, structured result, and trace are real."

## 2:30-2:40 - Close

**Screen:** Return attention to the Digital Home and disclosure badges.

**Narration:** "VoltWise: Your smart home says it's ON. VoltWise checks if it
actually happened."

