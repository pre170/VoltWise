import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { comparison, demoState, diagnostic, events, explanation, overview, target, tariff, trace, verification } from "./fixtures";
import type { MCPTrace, VerificationResult } from "../types/api";

let offline = false;
let mcpUnavailable = false;
let traces: MCPTrace[] = [];
let heaterFault = "NO_DRAW";
let energyScenario = "NORMAL_CURRENT_CYCLE";
let protocolVersion = "2025-11-25";
let failNextOverview = false;
const json = (data: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }));

function currentDemoState() { return { ...demoState, heater_fault: heaterFault, energy_scenario: energyScenario }; }
function verificationForFault(): VerificationResult {
  if (heaterFault === "NONE") return { ...verification, verification: "VERIFIED", observed_power_watts: 1502, observed_power_delta_watts: 1500, diagnostic_classification: "OK", reason: "Expected response detected.", speakable_summary: "The heater is on and drawing normal power." };
  if (heaterFault === "HIGH_DRAW") return { ...verification, observed_power_watts: 2200, observed_power_delta_watts: 2198, diagnostic_classification: "ABNORMAL_HIGH_DRAW", reason: "Abnormal high draw detected; simulated power was cut.", speakable_summary: "The heater reported on, exceeded its configured safety limit, and simulated power was cut without retrying." };
  return verification;
}

function installFetch() {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (offline) throw new TypeError("offline");
    const path = new URL(String(input)).pathname;
    if (path === "/api/health") return json({ status: "ok", service: "voltwise", mode: "simulation" });
    if (path === "/api/household/overview") {
      if (failNextOverview) { failNextOverview = false; throw new TypeError("overview unavailable"); }
      return json({ ...overview, energy_scenario: energyScenario });
    }
    if (path === "/api/demo/state") return json(currentDemoState());
    if (path === "/api/demo/reset") { heaterFault = "NONE"; energyScenario = "NORMAL_CURRENT_CYCLE"; return json(currentDemoState()); }
    if (path === "/api/demo/device-fault") { heaterFault = String(JSON.parse(String(init?.body)).fault); return json(currentDemoState()); }
    if (path === "/api/demo/energy-scenario") { energyScenario = String(JSON.parse(String(init?.body)).scenario); return json(currentDemoState()); }
    if (path === "/api/events") return json(events);
    if (path === "/api/sim/traces") return json(traces);
    if (path === "/api/sim/chat") {
      if (mcpUnavailable) return json({ error: { code: "MCP_SERVICE_UNAVAILABLE", message: "VoltWise's MCP service is temporarily unavailable." } }, 503);
      const message = String(JSON.parse(String(init?.body)).message).toLowerCase();
      let intent = "ENERGY_COMPARISON", tool = "power_compare_periods", args: Record<string, string | number | boolean | null> = {}, result: Record<string, unknown> = comparison;
      const cmd = message.includes("off") ? "TURN_OFF" : "TURN_ON";
      if (message.includes("why")) { intent = "USAGE_EXPLANATION"; tool = "power_explain_usage_change"; result = explanation; }
      else if (message.includes("bill")) { intent = "BILL_FORECAST"; tool = "power_forecast_bill"; result = { projected: { energy_charge: "1384.32" }, speakable_summary: "Your projected energy charge is 1,384 rupees." }; }
      else if (message.includes("tariff")) { intent = "TARIFF_STATUS"; tool = "power_get_tariff_status"; result = tariff; }
      else if (message.includes("300")) { intent = "TARGET_300"; tool = "power_suggest_actions"; args = { target_kwh: 300 }; result = target; }
      else if (message.includes("diagnose")) {
        intent = "DIAGNOSE_HEATER"; tool = "power_run_diagnostic"; args = { device: "heater" };
        result = diagnostic(heaterFault === "NO_DRAW_THEN_RECOVER" ? "RECOVERED" : heaterFault === "HIGH_DRAW" ? "SAFETY_STOP" : "UNRESOLVED") as unknown as Record<string, unknown>;
      }
      else if (message.includes("heater")) { intent = "VERIFY_HEATER"; tool = "power_turn_on_and_verify"; args = { device: "heater" }; result = verificationForFault() as unknown as Record<string, unknown>; }
      else if (message.includes("light")) {
        intent = "CONTROL_DEVICE"; tool = "power_control_device"; args = { device: "light", command: cmd };
        result = { device: "light", name: "Living Room Light", command: cmd, reported_state: message.includes("off") ? "OFF" : "ON", success: true, speakable_summary: `Turned ${message.includes("off") ? "off" : "on"} the living room light.` };
      }
      else if (message.includes("fan")) {
        intent = "CONTROL_DEVICE"; tool = "power_control_device"; args = { device: "fan", command: cmd };
        result = { device: "fan", name: "Ceiling Fan", command: cmd, reported_state: message.includes("off") ? "OFF" : "ON", success: true, speakable_summary: `Turned ${message.includes("off") ? "off" : "on"} the ceiling fan.` };
      }
      else if (message.includes("tv")) {
        intent = "CONTROL_DEVICE"; tool = "power_control_device"; args = { device: "tv", command: cmd };
        result = { device: "tv", name: "TV", command: cmd, reported_state: message.includes("off") ? "OFF" : "ON", success: true, speakable_summary: `Turned ${message.includes("off") ? "off" : "on"} the tv.` };
      }
      else if (message.includes("ac") || message.includes("air conditioner")) {
        intent = "CONTROL_DEVICE"; tool = "power_control_device"; args = { device: "ac", command: cmd };
        result = { device: "ac", name: "Air Conditioner", command: cmd, reported_state: message.includes("off") ? "OFF" : "ON", success: true, speakable_summary: `Turned ${message.includes("off") ? "off" : "on"} the air conditioner.` };
      }
      else if (message.includes("weather")) return json({ error: { code: "UNSUPPORTED_SIMULATION_INTENT", message: "This simulation supports the VoltWise demo commands shown below." } }, 400);
      const nextTrace: MCPTrace = { ...trace, trace_id: `trace-${traces.length + 1}`, protocol_version: protocolVersion, intent, tool_name: tool, tool_arguments: args, result_summary: String(result.speakable_summary) };
      traces = [nextTrace, ...traces];
      return json({ message: result.speakable_summary, intent, tool_call: { name: tool, arguments: args }, result, trace_id: nextTrace.trace_id });
    }
    return json({ error: { message: "Not found" } }, 404);
  }) as typeof fetch;
}

async function ready() { installFetch(); render(<App />); await screen.findByText("Connected"); }
async function choose(name: string) { await userEvent.click(screen.getByRole("button", { name })); }
async function loadPreset(name: string) { await choose("Demo setup"); await choose(name); }

beforeEach(() => { offline = false; mcpUnavailable = false; traces = []; heaterFault = "NO_DRAW"; energyScenario = "NORMAL_CURRENT_CYCLE"; protocolVersion = "2025-11-25"; failNextOverview = false; vi.restoreAllMocks(); });

describe("judge-facing VoltWise experience", () => {
  it("shows the digital-home product header", async () => { await ready(); expect(screen.getByRole("heading", { name: "VoltWise" })).toBeInTheDocument(); expect(screen.getByText("Digital Home · physical-outcome verification")).toBeInTheDocument(); const disclosure = screen.getByLabelText("Alexa+ experience simulated. Smart-home telemetry simulated. MCP integration real."); expect(disclosure).toHaveTextContent("Alexa+ Simulated"); expect(disclosure).toHaveTextContent("Telemetry Simulated"); expect(disclosure).toHaveTextContent("MCP Real"); });
  it("shows the connected state", async () => { await ready(); expect(screen.getByText("Connected")).toBeInTheDocument(); });
  it("does not present a persisted trace as a current initial success", async () => { traces = [trace]; await ready(); const activity = screen.getByLabelText("VoltWise MCP live activity"); expect(within(activity).getByText("MCP route")).toBeInTheDocument(); expect(within(activity).getByText(/evidence appears after a command/)).toBeInTheDocument(); expect(within(activity).queryByText("Execution completed")).not.toBeInTheDocument(); expect(within(activity).queryByText("Confirmed")).not.toBeInTheDocument(); });
  it("visibly frames the landing around reported versus physical state", async () => { await ready(); const tagline = screen.getByRole("heading", { name: "A device can report ON. VoltWise verifies the electrical response." }); expect(tagline).toBeVisible(); expect(screen.getByText(/Independent electrical evidence verifies the physical outcome/)).toBeInTheDocument(); expect(screen.getByText("Smart-home telemetry simulated")).toBeVisible(); });
  it("does not frame the command surface as a chatbot greeting", async () => { await ready(); expect(screen.queryByText(/Hi, I'm VoltWise/i)).not.toBeInTheDocument(); expect(screen.queryByText(/How can I help/i)).not.toBeInTheDocument(); });
  it("shows one primary verification action and three supporting landing actions", async () => { await ready(); const actions = screen.getByLabelText("Suggested prompts"); expect(actions).toHaveClass("landing-actions"); expect(within(actions).getAllByRole("button")).toHaveLength(3); expect(screen.getByLabelText("Ready to verify heater")).toContainElement(screen.getByRole("button", { name: "Turn on the heater" })); });
  it("renders the digital home and actual overview devices", async () => { await ready(); const home = screen.getByLabelText("VoltWise digital home"); expect(home).toBeInTheDocument(); for (const device of ["Living Room Heater", "Air Conditioner", "TV", "Refrigerator", "Dishwasher"]) expect(within(home).getByText(device)).toBeInTheDocument(); });
  it("has the conversation composer", async () => { await ready(); expect(screen.getByLabelText("Message VoltWise")).toBeEnabled(); });
  it("shows the gateway unsupported-message response", async () => { await ready(); await userEvent.type(screen.getByLabelText("Message VoltWise"), "weather tomorrow"); await userEvent.keyboard("{Enter}"); expect(await screen.findByText(/supports the VoltWise demo commands/)).toBeInTheDocument(); });

  it("renders one energy contextual card", async () => { await ready(); await choose("How are we doing this month?"); const card = await screen.findByLabelText("Energy this cycle"); expect(within(card).getByText("142")).toBeInTheDocument(); expect(within(card).getByText("↑ 20.3%")).toBeInTheDocument(); expect(within(card).getByText("304.29 kWh")).toBeInTheDocument(); });
  it("renders the usage contributor and provenance", async () => { await ready(); await choose("Why is our usage higher?"); const card = await screen.findByLabelText("Usage explanation"); expect(within(card).getByRole("heading", { name: "Air Conditioner" })).toBeInTheDocument(); expect(within(card).getByText("73")).toBeInTheDocument(); expect(within(card).getByText("52")).toBeInTheDocument(); expect(within(card).getByText("15.75 kWh")).toBeInTheDocument(); expect(within(card).getByText(/ESTIMATED/)).toBeInTheDocument(); expect(within(card).getByText(/State history/)).toBeInTheDocument(); });
  it("shows known and unattributed usage honestly", async () => { await ready(); await choose("Why is our usage higher?"); const card = await screen.findByLabelText("Usage explanation"); expect(within(card).getByText("19.35 kWh")).toBeInTheDocument(); expect(within(card).getByText("4.65 kWh")).toBeInTheDocument(); expect(within(card).getByText(/cannot be attributed to monitored devices/)).toBeInTheDocument(); });
  it("renders the tariff projection without the full bill calculation", async () => { await ready(); await choose("How's my tariff looking?"); const card = await screen.findByLabelText("Tariff outlook"); expect(within(card).getByLabelText("Current 142 kWh, projected 304.29 kWh")).toBeInTheDocument(); expect(within(card).getByText("projected to cross")).toBeInTheDocument(); expect(within(card).getByText(/Only additional units/)).toBeInTheDocument(); expect(within(card).queryByText("₹1,384.32")).not.toBeInTheDocument(); });
  it("keeps target guidance available through chat", async () => { await ready(); await userEvent.type(screen.getByLabelText("Message VoltWise"), "Can I stay under 300 kWh?"); await userEvent.keyboard("{Enter}"); expect(await screen.findByLabelText("Target plan")).toBeInTheDocument(); expect(screen.getByText("Reduce unnecessary air-conditioner runtime.")).toBeInTheDocument(); });

  it("renders heater verification as the hero card", async () => { await ready(); await choose("Turn on the heater"); const card = await screen.findByLabelText("Device verification"); expect(within(card).getByRole("heading", { name: "Living Room Heater" })).toBeInTheDocument(); expect(within(card).getByText("Electrical response not verified")).toBeInTheDocument(); });
  it("updates the heater in the home from the verification response", async () => { await ready(); await choose("Turn on the heater"); expect(await screen.findByLabelText(/Living Room Heater, reported ON, Electrical response not verified/)).toBeInTheDocument(); });
  it("does not show physical heating success for NO_DRAW", async () => { await ready(); await choose("Turn on the heater"); await screen.findByLabelText(/Living Room Heater, reported ON, Electrical response not verified/); const home = screen.getByLabelText("VoltWise digital home"); expect(home).toHaveClass("home-no-draw"); expect(home.querySelector(".physical-heater.no-draw")).toBeInTheDocument(); expect(home.querySelector(".physical-heater.verified")).not.toBeInTheDocument(); });
  it("shows expected and observed power", async () => { await ready(); await choose("Turn on the heater"); const comparison = await screen.findByLabelText("Expected 1500 watts, observed 7 watts"); expect(within(comparison).getByText("≈1,500 W")).toBeInTheDocument(); expect(within(comparison).getByText("7 W")).toBeInTheDocument(); });
  it("explains failed verification from returned readings", async () => { await ready(); await choose("Turn on the heater"); const card = await screen.findByLabelText("Device verification"); expect(within(card).getByText("The heater reports ON, but I'm only seeing 7 watts against an expected 1,500 watts. I couldn't verify normal electrical operation.")).toBeInTheDocument(); });
  it("uses a concise current-outcome activity summary", async () => { await ready(); await choose("Turn on the heater"); const activity = await screen.findByLabelText("VoltWise MCP live activity"); expect(within(activity).getByText("Current outcome")).toBeInTheDocument(); expect(within(activity).getByText("Electrical response not verified")).toBeInTheDocument(); expect(activity.querySelector(".pipeline-rail")).not.toBeInTheDocument(); });
  it("prioritizes one Diagnose heater CTA after failure", async () => { await ready(); await choose("Turn on the heater"); expect(await screen.findAllByRole("button", { name: /Diagnose heater/ })).toHaveLength(1); expect(screen.queryByRole("button", { name: "How are we doing this month?" })).not.toBeInTheDocument(); });
  it("runs diagnosis from the primary CTA", async () => { await ready(); await choose("Turn on the heater"); const buttons = await screen.findAllByRole("button", { name: /Diagnose heater/ }); await userEvent.click(buttons[0]); expect(await screen.findByRole("heading", { name: "Needs attention" })).toBeInTheDocument(); });
  it("shows all diagnostic stages in consumer language", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click((await screen.findAllByRole("button", { name: /Diagnose heater/ }))[0]); const flow = await screen.findByLabelText("Diagnostic workflow"); for (const label of ["Command", "Verify", "Diagnose", "Safe retry", "Re-verify", "Result"]) expect(within(flow).getByText(label)).toBeInTheDocument(); expect(within(flow).getByText("No expected electrical response")).toBeInTheDocument(); expect(within(flow).queryByText("NO_ELECTRICAL_RESPONSE")).not.toBeInTheDocument(); });
  it("shows the unresolved result and bounded retry", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click((await screen.findAllByRole("button", { name: /Diagnose heater/ }))[0]); expect(await screen.findByText("The heater still reports ON, but VoltWise can't verify normal electrical operation. I stopped after one safe retry.")).toBeInTheDocument(); expect(screen.getAllByText("1 / 1").length).toBeGreaterThan(0); });

  it("shows a satisfying recovery result", async () => { await ready(); await loadPreset("Recovery"); await choose("Diagnose heater"); expect(await screen.findByRole("heading", { name: "Recovered" })).toBeInTheDocument(); expect(screen.getByText("After one retry, the heater's electrical response is now within the expected range.")).toBeInTheDocument(); expect(screen.getByText("≈1,500 W", { selector: ".diagnostic-facts strong" })).toBeInTheDocument(); });
  it("renders recovered heater as electrically verified in the home", async () => { await ready(); await loadPreset("Recovery"); await choose("Diagnose heater"); expect(await screen.findByLabelText(/Living Room Heater, reported ON, Electrical response verified/)).toBeInTheDocument(); });
  it("shows failure, one safe retry, re-verification, then physical recovery", async () => { await ready(); await loadPreset("Recovery"); await choose("Diagnose heater"); const flow = await screen.findByLabelText("Diagnostic workflow"); expect(within(flow).getByText("Failed")).toBeInTheDocument(); expect(within(flow).getByText("1 of 1")).toBeInTheDocument(); expect(within(flow).getByText("Verified")).toBeInTheDocument(); const home = screen.getByLabelText("VoltWise digital home"); expect(home).toHaveClass("home-verified"); expect(home.querySelector(".physical-heater.verified .heat-waves")).toBeInTheDocument(); });
  it("shows safety stop without retrying", async () => { await ready(); await loadPreset("Safety stop"); await choose("Turn on the heater"); const input = screen.getByLabelText("Message VoltWise"); await userEvent.type(input, "Diagnose the heater"); await userEvent.keyboard("{Enter}"); expect(await screen.findByRole("heading", { name: "Safety stop" })).toBeInTheDocument(); expect(screen.getByText(/switched off without retrying/)).toBeInTheDocument(); const transition = screen.getByLabelText("Safety cutoff outcome"); expect(within(transition).getByText("Before cutoff")).toBeInTheDocument(); expect(within(transition).getByText("After cutoff")).toBeInTheDocument(); expect(within(transition).getByText("Heater reported ON · ≈2,200 W")).toBeInTheDocument(); expect(within(transition).getByText("Heater OFF · 2 W standby")).toBeInTheDocument(); expect(within(transition).getByText("Safety stop · zero retries")).toBeInTheDocument(); });
  it("presents a direct high-draw cutoff without treating reported ON as success", async () => { await ready(); await loadPreset("Safety stop"); await choose("Turn on the heater"); const card = await screen.findByLabelText("Device verification"); expect(within(card).getByText("Safety stop", { selector: ".verification-outcome strong" })).toBeInTheDocument(); const transition = within(card).getByLabelText("Safety cutoff outcome"); expect(within(transition).getByText("Before cutoff")).toBeInTheDocument(); expect(within(transition).getByText("After cutoff")).toBeInTheDocument(); expect(within(transition).getByText("Heater reported ON · ≈2,200 W")).toBeInTheDocument(); expect(within(transition).getByText("Heater OFF · 2 W standby")).toBeInTheDocument(); expect(within(transition).getByText("Safety stop · zero retries")).toBeInTheDocument(); expect(within(card).getByText("Final simulated state")).toBeInTheDocument(); expect(within(card).getByText("OFF")).toBeInTheDocument(); expect(screen.queryByText(/expected electrical response wasn't detected/)).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: /Diagnose heater/ })).not.toBeInTheDocument(); expect(screen.getByLabelText(/Living Room Heater, final simulated state OFF, Safety stop/)).toBeInTheDocument(); });
  it("does not infer final cutoff telemetry when the overview refresh fails", async () => { await ready(); await loadPreset("Safety stop"); failNextOverview = true; await choose("Turn on the heater"); const transition = await screen.findByLabelText("Safety cutoff outcome"); expect(within(transition).getByText(/standby reading unavailable/)).toBeInTheDocument(); const card = screen.getByLabelText("Device verification"); expect(within(card).getByText("Unavailable")).toBeInTheDocument(); expect(within(card).queryByText("Heater OFF · 2 W standby")).not.toBeInTheDocument(); });
  it("shows the in-home simulated electrical observation path for verification", async () => { await ready(); await choose("Turn on the heater"); expect(await screen.findByText("Monitoring simulated electrical telemetry…")).toBeInTheDocument(); expect(screen.getByText("Electrical response checked independently from the reported state.")).toBeInTheDocument(); const evidence = screen.getByLabelText(/Living Room Heater, reported ON, Electrical response not verified/); expect(within(evidence).getByText("ON")).toBeInTheDocument(); expect(within(evidence).getByText("7 W")).toBeInTheDocument(); });
  it("does not style a device-reported ON as an electrically verified result", async () => { await ready(); await choose("Turn on the heater"); const card = await screen.findByLabelText("Device verification"); const reported = within(card).getByText("ON", { selector: ".reported-only" }); expect(reported).toBeInTheDocument(); expect(within(reported).getByLabelText("on is device-reported, not verified")).toHaveTextContent("•"); expect(reported).not.toHaveClass("verified-state"); });
  it("renders safety stop and power cut in the home", async () => { await ready(); await loadPreset("Safety stop"); await choose("Turn on the heater"); const heater = await screen.findByLabelText(/Living Room Heater, final simulated state OFF, Safety stop · power cut/); expect(within(heater).getByText("Before cutoff")).toBeInTheDocument(); expect(within(heater).getByText("≈1,900 W")).toBeInTheDocument(); });
  it("never describes HIGH_DRAW as no electrical response", async () => { await ready(); await loadPreset("Safety stop"); await userEvent.type(screen.getByLabelText("Message VoltWise"), "Diagnose the heater"); await userEvent.keyboard("{Enter}"); await screen.findByRole("heading", { name: "Safety stop" }); expect(screen.queryByText(/no expected electrical response/i)).not.toBeInTheDocument(); expect(screen.getByText("Unusually high electrical draw")).toBeInTheDocument(); expect(screen.getAllByText("Skipped").length).toBeGreaterThan(0); });
  it("highlights the AC using returned contribution evidence", async () => { await ready(); await choose("Why is our usage higher?"); const ac = await screen.findByLabelText("Air Conditioner, largest identified contributor"); expect(ac).toHaveTextContent("+21 h"); expect(ac).toHaveTextContent("15.75 kWh estimated"); });

  it("replaces a high-draw result with the current energy explanation", async () => {
    await ready(); await loadPreset("Safety stop"); await choose("Turn on the heater");
    await screen.findByLabelText("Device verification");
    await choose("Why is our usage higher?");
    expect(await screen.findByLabelText("Usage explanation")).toBeInTheDocument();
    expect(screen.queryByLabelText("Device verification")).not.toBeInTheDocument();
    expect(screen.getByText("Main contributor identified")).toBeInTheDocument();
    expect(screen.queryByText("State confirmed")).not.toBeInTheDocument();
  });

  it("clears usage evidence for a subsequent text-only bill forecast", async () => {
    await ready(); await choose("Why is our usage higher?");
    await screen.findByLabelText("Usage explanation");
    const input = screen.getByLabelText("Message VoltWise");
    await userEvent.type(input, "What will my bill be?"); await userEvent.keyboard("{Enter}");
    expect(await screen.findByText("Your projected energy charge is 1,384 rupees.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Usage explanation")).not.toBeInTheDocument();
  });

  it("clears successful verification when the next MCP request fails", async () => {
    await ready(); await loadPreset("Normal"); await choose("Turn on the heater");
    const verifiedCard = await screen.findByLabelText("Device verification");
    expect(within(verifiedCard).getByText("Electrical response verified")).toBeInTheDocument();
    mcpUnavailable = true;
    const input = screen.getByLabelText("Message VoltWise");
    await userEvent.type(input, "Why is our usage higher?"); await userEvent.keyboard("{Enter}");
    expect((await screen.findAllByText("VoltWise is temporarily unavailable. Please try again.")).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText("Device verification")).not.toBeInTheDocument();
    const activity = screen.getByLabelText("VoltWise MCP live activity");
    expect(within(activity).getByText("Request failed")).toBeInTheDocument();
    expect(within(activity).queryByText("Confirmed")).not.toBeInTheDocument();
  });

  it("shows only the new result after reset and another command", async () => {
    await ready(); await choose("Turn on the heater"); await screen.findByLabelText("Device verification");
    await choose("Demo setup"); await choose("Reset demo");
    await choose("How are we doing this month?");
    expect(await screen.findByLabelText("Energy this cycle")).toBeInTheDocument();
    expect(screen.queryByLabelText("Device verification")).not.toBeInTheDocument();
  });

  it("keeps technical evidence collapsed by default", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click((await screen.findAllByRole("button", { name: /Diagnose heater/ }))[0]); expect(screen.queryByLabelText("Latest MCP trace route")).not.toBeInTheDocument(); expect(screen.getByRole("button", { name: "View technical evidence" })).toHaveAttribute("aria-expanded", "false"); });
  it("renders real MCP trace fields when expanded", async () => { await ready(); await choose("How are we doing this month?"); await userEvent.click(screen.getByRole("button", { name: "View technical evidence" })); expect(screen.getAllByText("power_compare_periods").length).toBeGreaterThan(0); expect(screen.getAllByText("Streamable HTTP").length).toBeGreaterThan(0); expect(screen.getAllByText("2025-11-25").length).toBeGreaterThan(0); expect(screen.getAllByText(/84\.2\s*ms/).length).toBeGreaterThan(0); expect(screen.getAllByText("Success").length).toBeGreaterThan(0); });
  it("renders the real MCP call as a visual route", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click(screen.getByRole("button", { name: "View technical evidence" })); const route = screen.getByLabelText("Latest MCP trace route"); for (const value of ["Alexa+", "power_turn_on_and_verify", "Streamable HTTP", "VoltWise", "Structured result"]) expect(within(route).getByText(value)).toBeInTheDocument(); });
  it("shows real arguments and raw classification only in technical evidence", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click((await screen.findAllByRole("button", { name: /Diagnose heater/ }))[0]); await userEvent.click(screen.getByRole("button", { name: "View technical evidence" })); expect(screen.getByLabelText("Arguments for power_run_diagnostic")).toHaveTextContent('{"device":"heater"}'); expect(screen.getByText("NO_ELECTRICAL_RESPONSE")).toBeInTheDocument(); });
  it("keeps application events separately labelled", async () => { await ready(); await choose("Turn on the heater"); await userEvent.click((await screen.findAllByRole("button", { name: /Diagnose heater/ }))[0]); await userEvent.click(screen.getByRole("button", { name: "View technical evidence" })); expect(screen.getByText(/Application events · 1/)).toBeInTheDocument(); });

  it("opens compact simulation controls with judge scenes", async () => { await ready(); await choose("Demo setup"); const dialog = screen.getByRole("dialog", { name: "Simulation controls" }); for (const label of ["Normal", "Heater failure", "Recovery", "Safety stop", "Tariff edge"]) expect(within(dialog).getByRole("button", { name: label })).toBeInTheDocument(); });
  it("makes heater verification the single primary landing action without inventing an outcome", async () => { await ready(); const action = screen.getByRole("button", { name: "Turn on the heater" }); expect(action).toHaveClass("ready-action"); expect(action).toHaveTextContent("Turn on & verify heater"); expect(screen.getAllByRole("button", { name: "Turn on the heater" })).toHaveLength(1); expect(screen.queryByText("Electrical response verified")).not.toBeInTheDocument(); expect(screen.queryByText("Electrical response not verified")).not.toBeInTheDocument(); });
  it("uses native keyboard-activatable appliance hotspots", async () => { await ready(); const light = screen.getByRole("button", { name: "Living Room Light, OFF" }); light.focus(); await userEvent.keyboard("{Enter}"); expect(await screen.findByRole("button", { name: "Living Room Light, ON" })).toBeInTheDocument(); });
  it("closes simulation controls with Escape and restores trigger focus", async () => { await ready(); const trigger = screen.getByRole("button", { name: "Demo setup" }); await userEvent.click(trigger); expect(screen.getByRole("button", { name: "Close simulation controls" })).toHaveFocus(); await userEvent.keyboard("{Escape}"); expect(screen.queryByRole("dialog", { name: "Simulation controls" })).not.toBeInTheDocument(); expect(trigger).toHaveFocus(); });
  it("keeps the compact simulation and MCP disclosure in the document", async () => { await ready(); const disclosure = screen.getByLabelText("Alexa+ experience simulated. Smart-home telemetry simulated. MCP integration real."); expect(within(disclosure).getAllByText("Simulated")).toHaveLength(2); expect(within(disclosure).getByText("Real")).toBeInTheDocument(); });
  it("closes simulation controls after choosing a preset", async () => { await ready(); await loadPreset("Heater failure"); expect(screen.queryByRole("dialog", { name: "Simulation controls" })).not.toBeInTheDocument(); });
  it("keeps demo controls on REST endpoints", async () => { await ready(); await loadPreset("Heater failure"); const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map((call) => new URL(String(call[0])).pathname); expect(calls).toContain("/api/demo/reset"); expect(calls).toContain("/api/demo/device-fault"); });
  it("reset clears current interaction while preserving historical MCP audit evidence", async () => { await ready(); await choose("Turn on the heater"); await screen.findByLabelText("Device verification"); await choose("Demo setup"); await choose("Reset demo"); await screen.findByLabelText(/Living Room Heater, reported OFF, Ready to verify/); expect(screen.queryByText("You asked")).not.toBeInTheDocument(); expect(screen.queryByLabelText("Recent result sequence")).not.toBeInTheDocument(); expect(screen.getByText("MCP route")).toBeInTheDocument(); await choose("View technical evidence"); expect(screen.getByLabelText("Latest MCP trace route")).toBeInTheDocument(); expect(screen.getAllByText("power_turn_on_and_verify").length).toBeGreaterThan(0); });
  it("shows an elegant offline recovery state", async () => { offline = true; installFetch(); render(<App />); expect(await screen.findByText("VoltWise is offline")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Retry connection" })).toBeInTheDocument(); });
  it("shows a consumer-safe MCP unavailable message", async () => { mcpUnavailable = true; await ready(); await choose("How are we doing this month?"); expect((await screen.findAllByText("VoltWise is temporarily unavailable. Please try again.")).length).toBeGreaterThan(0); expect(screen.queryByText(/MCP service/)).not.toBeInTheDocument(); });
  it("does not fabricate a successful device state when MCP is unavailable", async () => { mcpUnavailable = true; await ready(); await choose("Turn on the heater"); await screen.findAllByText("VoltWise is temporarily unavailable. Please try again."); const home = screen.getByLabelText("VoltWise digital home"); expect(within(home).queryByLabelText(/Electrical response verified/)).not.toBeInTheDocument(); expect(within(home).getByLabelText(/Ready to verify/)).toBeInTheDocument(); });
  it("routes supported conversation only through the simulator gateway", async () => { await ready(); await choose("How are we doing this month?"); await screen.findByLabelText("Energy this cycle"); const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map((call) => new URL(String(call[0])).pathname); expect(calls).toContain("/api/sim/chat"); expect(calls).not.toContain("/api/energy/comparison"); });
  it("never calls individual device APIs for heater conversation", async () => { await ready(); await choose("Turn on the heater"); await screen.findByLabelText("Device verification"); const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls.map((call) => new URL(String(call[0])).pathname); expect(calls).toContain("/api/sim/chat"); expect(calls).not.toContain("/api/devices/heater/turn-on-and-verify"); });
  it("does not issue an automatic extra heater command during the presentation", async () => { await ready(); await choose("Turn on the heater"); await screen.findByLabelText("Verification conclusion"); const chatCalls = (fetch as ReturnType<typeof vi.fn>).mock.calls.filter((call) => new URL(String(call[0])).pathname === "/api/sim/chat"); expect(chatCalls).toHaveLength(1); expect(JSON.parse(String(chatCalls[0][1]?.body)).message).toBe("Turn on the heater"); });
  it("uses the reduced-motion path without theatrical stage delays", async () => { await ready(); await choose("Turn on the heater"); expect(await screen.findByLabelText("Verification conclusion")).toBeInTheDocument(); expect(screen.getByLabelText("Heater verification timeline").querySelectorAll("li.completed")).toHaveLength(3); });
  it("shows a high-draw safety cutoff immediately even when normal motion is enabled", async () => { vi.spyOn(window, "matchMedia").mockImplementation((query) => ({ matches: false, media: query } as MediaQueryList)); await ready(); await loadPreset("Safety stop"); await choose("Turn on the heater"); expect(await screen.findByText("Safety stop", { selector: ".verification-outcome strong" })).toBeInTheDocument(); expect(screen.queryByLabelText("Heater verification timeline")).not.toBeInTheDocument(); });
  it("uses backend-provided protocol presentation", async () => { protocolVersion = "negotiated-test-version"; await ready(); await choose("How are we doing this month?"); await userEvent.click(screen.getByRole("button", { name: "View technical evidence" })); expect(screen.getByText("negotiated-test-version")).toBeInTheDocument(); });
  it("keeps suggested actions available without horizontal-only structure", async () => { await ready(); await choose("How are we doing this month?"); const actions = screen.getByLabelText("Suggested prompts"); expect(actions).toHaveClass("suggested-actions"); expect(actions).not.toHaveClass("quick-actions"); });
  it("retains responsive disclosure and controls after context changes", async () => { await ready(); await choose("Why is our usage higher?"); expect(await screen.findByLabelText("Usage explanation")).toBeInTheDocument(); expect(screen.getByRole("button", { name: "View technical evidence" })).toBeInTheDocument(); expect(screen.getByRole("button", { name: "Demo setup" })).toBeInTheDocument(); });
  it("waits for async demo control calls before asserting state", async () => { await ready(); await loadPreset("Tariff edge"); await waitFor(() => expect(energyScenario).toBe("NEAR_THRESHOLD")); });
  it("exposes only backend-supported demo values", async () => { await ready(); await choose("Demo setup"); const dialog = screen.getByRole("dialog", { name: "Simulation controls" }); for (const value of ["normal current cycle", "near threshold", "none", "no draw", "no draw then recover", "high draw"]) expect(within(dialog).getByRole("button", { name: value })).toBeInTheDocument(); expect(within(dialog).queryByRole("button", { name: "high usage" })).not.toBeInTheDocument(); expect(within(dialog).queryByRole("button", { name: "unavailable" })).not.toBeInTheDocument(); });
  it("controls simulated household devices and visually updates the home", async () => {
    await ready();
    const messageInput = screen.getByLabelText("Message VoltWise");
    await userEvent.type(messageInput, "Turn on the living room light");
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByLabelText(/Living Room Light, ON/)).toBeInTheDocument();

    await userEvent.type(messageInput, "Turn on the fan");
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByLabelText(/Ceiling Fan, ON/)).toBeInTheDocument();

    await userEvent.type(messageInput, "Turn on the TV");
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByLabelText(/TV, ON/)).toBeInTheDocument();
  });
});
