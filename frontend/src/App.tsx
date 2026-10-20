import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityTimeline } from "./components/ActivityTimeline";
import { ConversationPanel, type Message } from "./components/ConversationPanel";
import { DemoControls } from "./components/DemoControls";
import { DigitalHome } from "./components/DigitalHome";
import { EvidencePanel } from "./components/EvidencePanel";
import { Header } from "./components/Header";
import { VoltWiseActivity } from "./components/VoltWiseActivity";
import { VerificationExperience, type VerificationPresentationStage } from "./components/VerificationExperience";
import { ApiError, api } from "./services/api";
import { scheduleVerificationPresentation } from "./services/verificationPresentation";
import type { ActivityEvent, DemoState, Evidence, HouseholdOverview, MCPTrace, SimulatorChatResponse, VerificationResult } from "./types/api";

// Kept as a hidden sentinel so the landing layout does not need a separate
// conversation-state flag. The judge-facing experience is a command surface,
// not an assistant greeting or open-ended chatbot.
const LANDING_SENTINEL: Message = { id: 1, role: "assistant", text: "Alexa+ command surface ready." };

type HeaterPresentation = {
  runKey: number;
  startedAt: number;
  stage: VerificationPresentationStage;
  data: VerificationResult | null;
  traceId: string | null;
  assistantMessage: string | null;
};

const isHeaterVerificationRequest = (utterance: string) => {
  const value = utterance.toLowerCase();
  return value.includes("heater") && !value.includes("diagnos") && (value.includes("turn on") || value.includes("switch on"));
};

const reducedMotionPreferred = () => typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function evidenceFromChat(response: SimulatorChatResponse): Evidence | null {
  switch (response.intent) {
    case "ENERGY_COMPARISON": return { kind: "energy", data: response.result as unknown as Extract<Evidence, { kind: "energy" }>["data"] };
    case "USAGE_EXPLANATION": return { kind: "usage", data: response.result as unknown as Extract<Evidence, { kind: "usage" }>["data"] };
    case "TARIFF_STATUS": return { kind: "tariff", data: response.result as unknown as Extract<Evidence, { kind: "tariff" }>["data"] };
    case "TARGET_300": return { kind: "target", data: response.result as unknown as Extract<Evidence, { kind: "target" }>["data"] };
    case "VERIFY_HEATER": return { kind: "verification", data: response.result as unknown as Extract<Evidence, { kind: "verification" }>["data"] };
    case "DIAGNOSE_HEATER": return { kind: "diagnostic", data: response.result as unknown as Extract<Evidence, { kind: "diagnostic" }>["data"] };
    default: return null;
  }
}

export default function App() {
  const nextId = useRef(2);
  const [messages, setMessages] = useState<Message[]>([LANDING_SENTINEL]);
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [currentError, setCurrentError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [lastVerification, setLastVerification] = useState<VerificationResult | null>(null);
  const [overview, setOverview] = useState<HouseholdOverview | null>(null);
  const [resultOverviewFresh, setResultOverviewFresh] = useState(false);
  const [demoState, setDemoState] = useState<DemoState | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [traces, setTraces] = useState<MCPTrace[]>([]);
  const [controlsOpen, setControlsOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [heaterPresentation, setHeaterPresentation] = useState<HeaterPresentation | null>(null);
  const runGeneration = useRef(0);
  const announcedRuns = useRef(new Set<number>());
  const [deviceStates, setDeviceStates] = useState<Record<string, "OFF" | "ON">>({
    light: "OFF",
    fan: "OFF",
    tv: "OFF",
    ac: "OFF",
    dishwasher: "OFF",
  });
  const [activeDevice, setActiveDevice] = useState<string | null>(null);

  const addMessage = useCallback((role: Message["role"], text: string) => {
    setMessages((current) => [...current, { id: nextId.current++, role, text }]);
  }, []);
  const refreshActivity = useCallback(async () => {
    const [traceResult, eventResult] = await Promise.allSettled([api.traces(), api.events()]);
    if (traceResult.status === "fulfilled") setTraces(traceResult.value);
    if (eventResult.status === "fulfilled") setEvents(eventResult.value);
  }, []);
  const connect = useCallback(async () => {
    setChecking(true);
    try {
      await api.health();
      const [home, state, activity, mcpTraces] = await Promise.all([api.overview(), api.demoState(), api.events(), api.traces()]);
      setConnected(true); setEvidence(null); setOverview(home); setResultOverviewFresh(false); setDemoState(state); setEvents(activity); setTraces(mcpTraces);
    } catch { setConnected(false); } finally { setChecking(false); }
  }, []);
  useEffect(() => { void connect(); }, [connect]);

  useEffect(() => {
    const presentation = heaterPresentation;
    if (!presentation?.data || presentation.stage === "final") return;

    return scheduleVerificationPresentation(presentation.startedAt, (stage) => {
      setHeaterPresentation((current) => current?.runKey === presentation.runKey ? { ...current, stage } : current);
      if (stage === "final" && !announcedRuns.current.has(presentation.runKey)) {
        announcedRuns.current.add(presentation.runKey);
        if (presentation.assistantMessage) addMessage("assistant", presentation.assistantMessage);
      }
    });
  }, [heaterPresentation?.runKey, heaterPresentation?.data, addMessage]);

  const send = async (utterance: string) => {
    if (busy || !connected) return;
    const runKey = ++runGeneration.current;
    const startedAt = Date.now();
    const heaterVerificationRequest = isHeaterVerificationRequest(utterance);
    setHeaterPresentation(heaterVerificationRequest ? { runKey, startedAt, stage: "command", data: null, traceId: null, assistantMessage: null } : null);
    setCurrentRunId(null);
    addMessage("user", utterance);
    setEvidence(null);
    setResultOverviewFresh(false);
    setActiveDevice(null);
    setCurrentError(null);
    setBusy(true); setProgress("Working through VoltWise…");
    try {
      const response = await api.simChat(utterance);
      if (runGeneration.current !== runKey) return;
      const nextEvidence = evidenceFromChat(response);
      setEvidence(nextEvidence);
      if (nextEvidence?.kind === "verification") setLastVerification(nextEvidence.data);
      if (response.intent === "CONTROL_DEVICE" && response.result) {
        const res = response.result as { device?: string; command?: string; reported_state?: string };
        if (res.device && res.reported_state) {
          const st = res.reported_state === "ON" ? "ON" : "OFF";
          setDeviceStates((prev) => ({ ...prev, [res.device!]: st }));
          setActiveDevice(res.device);
        }
      } else if (response.intent === "VERIFY_HEATER" || response.intent === "DIAGNOSE_HEATER") {
        setActiveDevice("heater");
      }
      setCurrentRunId(response.trace_id);
      try {
        const home = await api.overview();
        if (runGeneration.current !== runKey) return;
        setOverview(home);
        setResultOverviewFresh(true);
      } catch { /* mock fallback safe */ }
      await refreshActivity();
      if (runGeneration.current !== runKey) return;
      if (heaterVerificationRequest && nextEvidence?.kind === "verification") {
        const highDrawSafetyStop = /high draw/i.test(nextEvidence.data.reason) && /power was cut/i.test(nextEvidence.data.reason);
        const immediate = highDrawSafetyStop || reducedMotionPreferred();
        setHeaterPresentation({ runKey, startedAt, stage: immediate ? "final" : "command", data: nextEvidence.data, traceId: response.trace_id, assistantMessage: response.message });
        if (immediate && !announcedRuns.current.has(runKey)) {
          announcedRuns.current.add(runKey);
          addMessage("assistant", response.message);
        }
      } else {
        addMessage("assistant", response.message);
      }
    } catch (error) {
      if (runGeneration.current !== runKey) return;
      setEvidence(null);
      setHeaterPresentation(null);
      setActiveDevice(null);
      const message = error instanceof ApiError && error.code === "MCP_SERVICE_UNAVAILABLE"
        ? "VoltWise is temporarily unavailable. Please try again."
        : error instanceof ApiError ? error.message : "VoltWise couldn't complete that request.";
      setCurrentError(message);
      addMessage("assistant", message);
      await refreshActivity();
    }
    finally {
      if (runGeneration.current === runKey) { setBusy(false); setProgress(""); }
    }
  };

  const runControl = async (operation: () => Promise<DemoState>, confirmation: string) => {
    runGeneration.current += 1;
    setHeaterPresentation(null);
    setCurrentRunId(null);
    setBusy(true);
    try { const state = await operation(); setDemoState(state); setEvidence(null); setResultOverviewFresh(false); setOverview(await api.overview()); addMessage("assistant", confirmation); await refreshActivity(); }
    catch (error) { addMessage("assistant", error instanceof ApiError ? error.message : "The demo control failed."); }
    finally { setBusy(false); }
  };
  const reset = async () => {
    runGeneration.current += 1;
    setHeaterPresentation(null);
    setCurrentRunId(null);
    setBusy(true);
    try {
      const state = await api.resetDemo(); setDemoState(state); setEvidence(null); setLastVerification(null); setResultOverviewFresh(false); setOverview(await api.overview()); setActivityOpen(false);
      setCurrentError(null);
      setDeviceStates({ light: "OFF", fan: "OFF", tv: "OFF", ac: "OFF", dishwasher: "OFF" });
      setActiveDevice(null);
      setMessages([LANDING_SENTINEL]); nextId.current = 2;
      await refreshActivity();
    } finally { setBusy(false); }
  };
  const preset = async (name: "NORMAL" | "FAILURE" | "RECOVERY" | "SAFETY" | "TARIFF") => {
    runGeneration.current += 1;
    setHeaterPresentation(null);
    setCurrentRunId(null);
    setBusy(true);
    try {
      await api.resetDemo(); if (name === "TARIFF") await api.setScenario("NEAR_THRESHOLD");
      const faults: Partial<Record<typeof name, string>> = { FAILURE: "NO_DRAW", RECOVERY: "NO_DRAW_THEN_RECOVER", SAFETY: "HIGH_DRAW" };
      if (faults[name]) await api.setFault(faults[name]!);
      const [state, home] = await Promise.all([api.demoState(), api.overview()]); setDemoState(state); setEvidence(null); setLastVerification(null); setResultOverviewFresh(false); setOverview(home); setActivityOpen(false);
      setCurrentError(null);
      setDeviceStates({ light: "OFF", fan: "OFF", tv: "OFF", ac: "OFF", dishwasher: "OFF" });
      setActiveDevice(null);
      setMessages([LANDING_SENTINEL]); nextId.current = 2;
      addMessage("assistant", `${name.charAt(0) + name.slice(1).toLowerCase()} demo scene is ready.`); setControlsOpen(false); await refreshActivity();
    } catch (error) { addMessage("assistant", error instanceof ApiError ? error.message : "The preset failed."); }
    finally { setBusy(false); }
  };

  const presentationPending = Boolean(heaterPresentation && heaterPresentation.stage !== "final");
  const visibleEvidence = presentationPending && evidence?.kind === "verification" ? null : evidence;
  const homeEvidence = presentationPending && heaterPresentation?.data
    ? { kind: "verification" as const, data: heaterPresentation.data }
    : visibleEvidence;
  const hasContext = evidence !== null || heaterPresentation !== null;
  const presentationProgress = heaterPresentation?.stage === "command" ? "Turning on the living room heater…"
    : heaterPresentation?.stage === "evidence" ? "Checking the heater's electrical draw…"
    : heaterPresentation?.stage === "diagnosis" ? "Checking electrical evidence and telemetry…"
    : progress;

  return <div className="app-shell">
    <Header connected={connected} onOpenControls={() => setControlsOpen(true)} />
    <main className="workspace">
      <ConversationPanel
        messages={messages}
        busy={busy || checking}
        progress={checking ? "Connecting to VoltWise…" : progress}
        connected={connected}
        hasContext={hasContext}
        home={
          <DigitalHome
            overview={overview}
            evidence={homeEvidence}
            previousVerification={lastVerification}
            busy={busy || checking || presentationPending}
            lastCommand={[...messages].reverse().find((message) => message.role === "user")?.text ?? null}
            lightState={deviceStates.light}
            fanState={deviceStates.fan}
            tvState={deviceStates.tv}
            acState={deviceStates.ac}
            dishwasherState={deviceStates.dishwasher}
            activeDevice={activeDevice}
            resultOverviewFresh={resultOverviewFresh}
            verificationPresentationStage={heaterPresentation?.stage ?? null}
            onDeviceCommand={send}
          />
        }
        prioritizeDiagnosis={(heaterPresentation?.stage === "final" && evidence?.kind === "verification" && evidence.data.verification !== "VERIFIED" && !/power was cut/i.test(evidence.data.reason)) || (evidence === null && heaterPresentation === null && demoState?.heater_fault === "NO_DRAW_THEN_RECOVER")}
        context={heaterPresentation && (!heaterPresentation.data || !(/high draw/i.test(heaterPresentation.data.reason) && /power was cut/i.test(heaterPresentation.data.reason)))
          ? <VerificationExperience stage={heaterPresentation.stage} data={heaterPresentation.data} runId={heaterPresentation.traceId} onDiagnose={() => void send("Diagnose the heater")} />
          : evidence ? <EvidencePanel evidence={evidence} previousVerification={lastVerification} finalHeaterState={resultOverviewFresh ? overview?.devices.find((device) => device.device_id === "heater")?.reported_state ?? null : null} finalHeaterWatts={resultOverviewFresh ? overview?.devices.find((device) => device.device_id === "heater")?.current_watts ?? null : null} runId={currentRunId} onDiagnose={() => void send("Diagnose the heater")} /> : null}
        activity={
          <VoltWiseActivity
            latestTrace={traces[0] ?? null}
            lastCommand={[...messages].reverse().find((message) => message.role === "user")?.text ?? null}
            busy={busy || checking || presentationPending}
            progress={checking ? "Connecting to VoltWise…" : presentationProgress}
            evidence={visibleEvidence}
            error={currentError}
            activeDevice={activeDevice}
            deviceStates={deviceStates}
          />
        }
        technical={<ActivityTimeline traces={traces} events={events} evidence={visibleEvidence} lastCommand={[...messages].reverse().find((message) => message.role === "user")?.text ?? null} classification={evidence?.kind === "diagnostic" ? evidence.data.diagnostic_classification : null} open={activityOpen} onToggle={() => setActivityOpen((value) => !value)} />}
        onSend={send}
        onRetry={connect}
      />
    </main>
    <DemoControls open={controlsOpen} busy={busy} state={demoState} onClose={() => setControlsOpen(false)} onReset={reset} onScenario={(scenario) => runControl(() => api.setScenario(scenario), "The energy scenario is ready.")} onFault={(fault) => runControl(() => api.setFault(fault), "The heater demo state is ready.")} onPreset={preset} />
  </div>;
}
