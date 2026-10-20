import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { VerificationResult } from "../types/api";
import "./VerificationExperience.css";

export type VerificationPresentationStage = "command" | "evidence" | "diagnosis" | "final";

const stageOrder: VerificationPresentationStage[] = ["command", "evidence", "diagnosis", "final"];
const n = (value: number) => value.toLocaleString("en-IN", { maximumFractionDigits: 0 });

const classificationName = (value: string) => ({
  NO_ELECTRICAL_RESPONSE: "Expected electrical response not detected",
  STANDBY_ONLY: "Electrical draw remained near standby",
  START_THEN_STOP: "Electrical response started, then stopped",
  NOT_REACHING_EXPECTED_LOAD: "Electrical draw did not reach the expected range",
  CONNECTIVITY_FAILURE: "Telemetry unavailable",
  ABNORMAL_HIGH_DRAW: "Unsafe high electrical draw",
  OK: "Electrical response is within the expected range",
}[value] ?? value.replaceAll("_", " ").toLowerCase());

export type TechnicianEvidence = {
  appliance: string;
  reportedState: string;
  expectedWatts: number | null;
  observedWatts: number | null;
  telemetryAvailable: boolean | null;
  diagnosticOutcome: string;
  retries: number;
  safetyStop: boolean;
  runId: string | null;
};

export function TechnicianHandoff({ evidence }: { evidence: TechnicianEvidence }) {
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setOpen(false);
    setDismissed(false);
    setCopyState("idle");
  }, [evidence.runId]);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const handleDialogKeys = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        window.setTimeout(() => triggerRef.current?.focus(), 0);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])") ?? []);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", handleDialogKeys);
    return () => window.removeEventListener("keydown", handleDialogKeys);
  }, [open]);

  if (dismissed) return null;

  const telemetry = evidence.telemetryAvailable == null
    ? "Not reported"
    : evidence.telemetryAvailable ? "Available" : "Unavailable";
  const summary = [
    "VoltWise diagnostic handoff",
    `Appliance: ${evidence.appliance}`,
    `Device-reported state: ${evidence.reportedState}`,
    `Expected electrical draw: ${evidence.expectedWatts == null ? "Not available" : `${n(evidence.expectedWatts)} W`}`,
    `Observed electrical draw: ${evidence.observedWatts == null ? "Not available" : `${n(evidence.observedWatts)} W`}`,
    `Telemetry status: ${telemetry}`,
    `Diagnostic outcome: ${evidence.diagnosticOutcome}`,
    `Retry attempts: ${evidence.retries}`,
    `Safety stop: ${evidence.safetyStop ? "Yes" : "No"}`,
    `Run identifier: ${evidence.runId ?? "Not available"}`,
    "VoltWise uses simulated smart-home telemetry. Share this summary with a qualified technician for independent inspection.",
  ].join("\n");

  const copy = async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(summary);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  };

  const close = () => {
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  };

  return <section className="technician-offer" aria-label="Technician help">
    <div className="technician-offer-copy">
      <span className="next-step-label">What you can do next</span>
      <strong>Would you like a diagnostic summary for a technician?</strong>
      <span>No technician is contacted. You can share the report with a qualified technician.</span>
    </div>
    <div className="technician-actions">
      <button ref={triggerRef} type="button" className="technician-primary" onClick={() => setOpen(true)}>Get diagnostic summary</button>
      <button type="button" onClick={() => setDismissed(true)}>Not now</button>
    </div>
    {open && createPortal(<div className="technician-dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && close()}>
    <div ref={dialogRef} className="technician-handoff" role="dialog" aria-modal="true" aria-label="Technician handoff summary">
      <header><div><span>Diagnostic handoff</span><h3 id="technician-summary-title">Share with a qualified technician</h3></div><button ref={closeRef} type="button" className="handoff-close" onClick={close} aria-label="Close diagnostic summary">×</button></header>
      <div><span>Appliance</span><strong>{evidence.appliance}</strong></div>
      <div><span>Device-reported state</span><strong>{evidence.reportedState}</strong></div>
      <div><span>Expected draw</span><strong>{evidence.expectedWatts == null ? "Unavailable" : `≈${n(evidence.expectedWatts)} W`}</strong></div>
      <div><span>Observed draw</span><strong>{evidence.observedWatts == null ? "Unavailable" : `${evidence.observedWatts >= 1000 ? "≈" : ""}${n(evidence.observedWatts)} W`}</strong></div>
      <div><span>Telemetry</span><strong>{telemetry}</strong></div>
      <div><span>Diagnostic outcome</span><strong>{evidence.diagnosticOutcome}</strong></div>
      <div><span>Retry attempts</span><strong>{evidence.retries}</strong></div>
      <div><span>Safety stop</span><strong>{evidence.safetyStop ? "Yes" : "No"}</strong></div>
      <div className="handoff-run"><span>Run identifier</span><code>{evidence.runId ?? "Unavailable"}</code></div>
      <p>This is a simulated diagnostic report. Share it with a qualified technician for independent inspection.</p>
      <footer><button type="button" className="copy-summary" onClick={() => void copy()}>Copy diagnostic summary</button>
      <span className="copy-status" role="status">{copyState === "copied" ? "Diagnostic summary copied." : copyState === "failed" ? "Clipboard unavailable. Select the report details manually." : ""}</span></footer>
    </div></div>, document.body)}
  </section>;
}

type Props = {
  stage: VerificationPresentationStage;
  data: VerificationResult | null;
  runId: string | null;
  onDiagnose: () => void;
};

export function VerificationExperience({ stage, data, runId, onDiagnose }: Props) {
  const currentIndex = stageOrder.indexOf(stage);
  const failed = data?.verification === "FAILED";
  const evidenceVisible = currentIndex >= 1 && data != null;
  const diagnosisVisible = currentIndex >= 2 && data != null;
  const finalVisible = currentIndex >= 3 && data != null;
  const outcome = data ? classificationName(data.diagnostic_classification) : null;

  const finalTitle = data?.verification === "VERIFIED"
    ? "Electrical response verified"
    : "Electrical response not verified";
  const finalCopy = data?.verification === "VERIFIED"
    ? `The heater reports ${data.reported_state}, and I observed approximately ${n(data.observed_power_watts)} watts within its expected electrical range.`
    : data
      ? `The heater reports ${data.reported_state}, but I'm only seeing ${n(data.observed_power_watts)} watts against an expected ${n(data.expected_power_watts)} watts. I couldn't verify normal electrical operation.`
      : "";
  const stageTitle = stage === "command" ? "Turning on the living room heater…"
    : stage === "evidence" ? "Checking electrical draw…"
    : stage === "diagnosis" ? "Assessing the evidence…"
    : "Conclusion ready";

  return <article className={`context-card verification-experience stage-${stage} ${failed ? "failed" : data ? "verified" : "pending"}`} aria-label="Device verification">
    <div className="agent-heading">
      <div><p className="card-kicker">VoltWise agent activity</p><h2>Living Room Heater</h2><p className="agent-current-stage">{stageTitle}</p></div>
      <span className={`agent-state stage-${stage}`}>{stage === "final" ? "Complete" : "In progress"}</span>
    </div>

    <ol className="agent-stage-list" aria-label="Heater verification timeline">
      {[
        ["command", "Command received", "Waiting for electrical response…"],
        ["evidence", "Checking electrical response", evidenceVisible ? "Evidence checked" : "Waiting"],
        ["diagnosis", "Diagnosing evidence", diagnosisVisible ? "Assessment complete" : "Waiting"],
        ["final", "Verification concluded", finalVisible ? "Ready" : "Waiting"],
      ].map(([key, label, detail], index) => <li key={key} className={index < currentIndex ? "completed" : index === currentIndex ? "active" : "pending"} aria-current={index === currentIndex ? "step" : undefined}>
        <i aria-hidden="true">{index < currentIndex ? "✓" : index + 1}</i><div><strong>{label}</strong><span>{detail}</span></div>
      </li>)}
    </ol>

    {stage === "command" && <div className="agent-waiting" role="status"><i/><div><strong>Command sent through VoltWise</strong><span>The result will appear after the MCP operation confirms the device report.</span></div></div>}

    {evidenceVisible && <section className="agent-electrical-evidence" aria-label={`Expected ${data.expected_power_watts} watts, observed ${data.observed_power_watts} watts`}>
      <p className="checking-line">Electrical response checked independently from the reported state.</p>
      <div className="reported-evidence"><span>Device-reported state</span><strong className={failed ? "reported-only" : "verified-state"}>{data.reported_state}<i aria-label={`${data.reported_state.toLowerCase()} is device-reported, not verified`}>•</i></strong></div>
      <div className="agent-power-values">
        <div><span>Expected</span><strong>≈{n(data.expected_power_watts)} W</strong></div>
        <div className={failed ? "failed-reading" : "verified-reading"}><span>Observed</span><strong>{data.observed_power_watts >= 1000 ? "≈" : ""}{n(data.observed_power_watts)} W</strong></div>
      </div>
      <p className={failed ? "evidence-finding failed" : "evidence-finding verified"}>{failed ? "Expected electrical response not detected." : "Expected electrical response detected."}</p>
    </section>}

    {diagnosisVisible && <section className="agent-diagnosis" aria-label="Electrical evidence diagnosis">
      <div><span>Telemetry</span><strong>{data.telemetry_available ? "Available" : "Unavailable"}</strong></div>
      <div><span>Electrical response</span><strong className={failed ? "failed-text" : "verified-text"}>{failed ? "Not verified" : "Verified"}</strong></div>
      <div><span>Observed draw</span><strong>{n(data.observed_power_watts)} W</strong></div>
      <p><span>Diagnostic outcome</span><strong>{outcome}</strong></p>
    </section>}

    {finalVisible && <>
      <section className={`agent-conclusion ${failed ? "failed" : "verified"}`} aria-label="Verification conclusion">
        <span aria-hidden="true">{failed ? "!" : "✓"}</span><div><strong>{finalTitle}</strong><p>Expected {n(data.expected_power_watts)} W <i aria-hidden="true">|</i> Observed {n(data.observed_power_watts)} W</p></div>
      </section>
      <section className="assistant-response" aria-label="VoltWise assistant response"><span>What VoltWise found</span><h3>VoltWise assistant</h3><p>{finalCopy}</p>{failed && <small>{data.telemetry_available ? "Telemetry was available for this simulated check." : "Telemetry was unavailable during this simulated check."}</small>}</section>
      {failed && <button type="button" className="primary-action" onClick={onDiagnose}>Diagnose heater safely <span aria-hidden="true">→</span></button>}
      {failed && <TechnicianHandoff evidence={{
        appliance: "Living room heater",
        reportedState: data.reported_state,
        expectedWatts: data.expected_power_watts,
        observedWatts: data.observed_power_watts,
        telemetryAvailable: data.telemetry_available,
        diagnosticOutcome: outcome ?? "Unavailable",
        retries: 0,
        safetyStop: false,
        runId,
      }} />}
    </>}
  </article>;
}
