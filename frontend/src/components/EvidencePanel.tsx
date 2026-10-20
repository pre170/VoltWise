import type { CSSProperties } from "react";
import type { Evidence, VerificationResult } from "../types/api";
import { TechnicianHandoff } from "./VerificationExperience";
import "./EvidencePanel.css";

const n = (value: string | number, digits = 0) => Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits });
const deviceName = (value: string) => value.toLowerCase() === "heater" ? "Living Room Heater" : value;
const words = (value: string) => value.replaceAll("_", " ").toLowerCase();
const pct = (value: number, max: number) => `${Math.min(Math.max(value / Math.max(max, 1) * 100, 0), 100)}%`;

function Energy({ data }: { data: Extract<Evidence, { kind: "energy" }>["data"] }) {
  return <article className="context-card energy-card" aria-label="Energy this cycle">
    <p className="card-kicker">Energy this cycle</p>
    <div className="energy-hero"><strong>{n(data.current_kwh)}</strong><span>kWh</span></div>
    <div className="change-line"><b>↑ {n(data.change_percent ?? 0, 1)}%</b><span>vs same point last cycle</span></div>
    <div className="energy-support"><div><span>Previous</span><strong>{n(data.previous_equivalent_kwh)} kWh</strong></div><div><span>Projected</span><strong>{n(data.projection.projected_kwh, 2)} kWh</strong></div></div>
  </article>;
}

function Usage({ data }: { data: Extract<Evidence, { kind: "usage" }>["data"] }) {
  const top = data.contributors[0];
  const currentKwh = data.current_kwh ?? 142;
  const previousKwh = data.previous_equivalent_kwh ?? 118;
  const changeKwh = data.household_change_kwh;
  return <article className="context-card usage-card" aria-label="Usage explanation">
    <p className="card-kicker">Energy increase explanation</p>
    <div className="energy-support" style={{ marginTop: 0, marginBottom: "16px", paddingTop: 0, borderTop: "none", gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
      <div><span>Current cycle</span><strong>{n(currentKwh)} kWh</strong></div>
      <div style={{ paddingLeft: "18px", borderLeft: "1px solid rgba(135, 175, 215, 0.16)" }}><span>Previous cycle</span><strong>{n(previousKwh)} kWh</strong></div>
      <div style={{ paddingLeft: "18px", borderLeft: "1px solid rgba(135, 175, 215, 0.16)" }}><span>Total increase</span><strong style={{ color: "var(--vw-warning)" }}>+{n(changeKwh)} kWh</strong></div>
    </div>
    {top ? <>
      <h2>{top.device}</h2>
      <div className="runtime-comparison"><div><strong>{n(top.current_runtime_hours)}</strong><span>hours this cycle</span></div><div><strong>{n(top.previous_runtime_hours)}</strong><span>hours previous</span></div><div className="runtime-change"><strong>+{n(top.runtime_change_hours)}</strong><span>hours</span></div></div>
      <div className="contribution"><span>{top.energy_impact_type === "ESTIMATED" ? "Estimated contribution" : "Metered contribution (simulated)"}</span><strong>{n(top.energy_impact_kwh, 2)} kWh</strong><small><b>{top.energy_impact_type}</b> · State history</small></div>
    </> : <p>No monitored-device contributor was identified.</p>}
    <div className="unattributed"><div><span>Known contributors</span><strong>{n(data.known_contribution_kwh, 2)} kWh</strong></div><div><span>Unattributed</span><strong>{n(data.unattributed_kwh, 2)} kWh</strong></div><p>Some household usage cannot be attributed to monitored devices.</p></div>
  </article>;
}

function Tariff({ data }: { data: Extract<Evidence, { kind: "tariff" }>["data"] }) {
  const current = Number(data.current_usage_kwh);
  const projected = Number(data.projected_month_end_kwh);
  const scaleMax = Math.max(330, projected + 8);
  const positions = { "--current": pct(current, scaleMax), "--projected": pct(projected, scaleMax) } as CSSProperties;
  return <article className="context-card tariff-card" aria-label="Tariff outlook">
    <p className="card-kicker">Illustrative demo tariff</p>
    <div className="tariff-scale" style={positions} aria-label={`Current ${current} kWh, projected ${projected} kWh`}>
      <div className="scale-labels"><span>0</span><span>100</span><span>200</span><span>300+</span></div>
      <div className="scale-line"><i className="current-pin" /><i className="projected-pin" /></div>
      <div className="scale-readings"><div><span>Current</span><strong>{n(current)} kWh</strong></div><div><span>Projected</span><strong>{n(projected, 2)} kWh</strong></div></div>
    </div>
    <div className="tariff-conclusion"><strong>{words(data.threshold_warning)}</strong><p>At your current run rate, you're projected to enter the next marginal slab.</p></div>
    <p className="tariff-note">Only additional units in the higher slab receive the higher marginal rate.</p>
  </article>;
}

function Target({ data }: { data: Extract<Evidence, { kind: "target" }>["data"] }) {
  return <article className="context-card target-card" aria-label="Target plan">
    <p className="card-kicker">Your target plan</p><h2>Stay under {n(data.target_kwh ?? 0)} kWh</h2>
    <div className="target-stats"><div><strong>{n(data.remaining_kwh_budget ?? 0)} kWh</strong><span>remaining</span></div><div><strong>{n(data.remaining_days)} days</strong><span>left</span></div><div><strong>{n(data.required_average_daily_kwh ?? 0, 2)} kWh</strong><span>daily allowance</span></div></div>
    <ol className="recommendations">{data.recommendations.slice(0, 3).map((item) => <li key={item.rank}><span>{item.rank}</span><div><strong>{item.action}</strong><p>{item.reason}</p></div>{item.estimated_reduction_kwh && <b>{item.estimated_reduction_kwh} kWh</b>}</li>)}</ol>
  </article>;
}

function PowerComparison({ expected, observed, tone = "danger", observedLabel = "Observed" }: { expected: number; observed: number; tone?: "danger" | "success"; observedLabel?: string }) {
  const max = Math.max(expected, observed, 1);
  return <div className={`power-comparison ${tone}`} aria-label={`Expected ${expected} watts, observed ${observed} watts`}>
    <div><span>Expected</span><strong>≈{n(expected)} W</strong><i><b style={{ width: pct(expected, max) }} /></i></div>
    <div><span>{observedLabel}</span><strong>{observed >= 1000 ? "≈" : ""}{n(observed)} W</strong><i><b style={{ width: pct(observed, max) }} /></i></div>
  </div>;
}

function SafetyTransition({ beforeState, beforeWatts, afterState, afterWatts, retries }: { beforeState: string; beforeWatts: number; afterState: string | null; afterWatts: number | null; retries: number }) {
  return <div className="safety-transition" aria-label="Safety cutoff outcome">
    <div><span>Before cutoff</span><strong>Heater reported {beforeState} · ≈{n(beforeWatts)} W</strong></div>
    <i aria-hidden="true">→</i>
    <div><span>After cutoff</span><strong>Heater {afterState ?? "unknown"} · {afterWatts == null ? "standby reading unavailable" : `${n(afterWatts)} W standby`}</strong></div>
    <div className="safety-outcome"><span>Outcome</span><strong>Safety stop · {retries === 0 ? "zero retries" : `${retries} retries`}</strong></div>
  </div>;
}

function Verification({ data, finalHeaterState, finalHeaterWatts, onDiagnose }: { data: Extract<Evidence, { kind: "verification" }>["data"]; finalHeaterState: string | null; finalHeaterWatts: number | null; onDiagnose: () => void }) {
  const failed = data.verification !== "VERIFIED";
  const highDraw = failed && /high draw/i.test(data.reason);
  const powerCut = highDraw && /power was cut/i.test(data.reason);
  const outcomeTitle = !failed ? "Electrical response verified" : powerCut ? "Safety stop" : highDraw ? "Abnormal high draw" : "Electrical response not verified";
  const outcomeCopy = !failed
    ? `The heater's ${n(data.observed_power_watts)} W electrical response is within the expected range.`
    : powerCut
      ? `An unusually high ${n(data.observed_power_watts)} W electrical draw was detected. The simulated heater was switched off without retrying.`
      : highDraw
        ? data.reason
        : `The heater reports ${data.reported_state}, but its electrical draw is only ${n(data.observed_power_watts)} W against an expected ${n(data.expected_power_watts)} W. The electrical response is not verified.`;
  return <article className={`context-card verification-card ${failed ? highDraw ? "high-draw" : "failed" : "verified"}`} aria-label="Device verification">
    <p className="card-kicker">Device verification</p>
    <div className="device-title"><div><h2>{deviceName(data.device)}</h2><span>{powerCut ? "Final simulated state" : "Reported state"}</span></div><strong className={powerCut ? "cutoff-state" : failed ? "reported-only" : "verified-state"}>{powerCut ? finalHeaterState ?? "Unavailable" : data.reported_state} <i aria-label={powerCut ? finalHeaterState ? "final simulated off" : "final simulated state unavailable" : failed ? `${data.reported_state.toLowerCase()} is device-reported, not verified` : "reported on and electrically verified"}>{powerCut ? "×" : failed ? "•" : "✓"}</i></strong></div>
    <p className="checking-line">Electrical response checked independently from the reported state.</p>
    <PowerComparison expected={data.expected_power_watts} observed={data.observed_power_watts} tone={failed ? "danger" : "success"} observedLabel={powerCut ? "Unsafe observation" : "Observed"} />
    {powerCut && <SafetyTransition beforeState={data.reported_state} beforeWatts={data.observed_power_watts} afterState={finalHeaterState} afterWatts={finalHeaterWatts} retries={0} />}
    <div className="verification-outcome"><span aria-hidden="true">{failed ? "!" : "✓"}</span><div><strong>{outcomeTitle}</strong><p>{outcomeCopy}</p></div></div>
    {failed && !powerCut && <button className="primary-action" onClick={onDiagnose}>Diagnose heater <span aria-hidden="true">→</span></button>}
    <div className="verification-progress" aria-label="Verification progress">
      <span className="done">Observe</span><i>→</i>
      <span className="done">Reason</span><i>→</i>
      <span className={powerCut ? "done" : failed ? "current" : "skipped"} aria-current={failed && !powerCut ? "step" : undefined}>Act safely</span><i>→</i>
      <span className={!failed ? "verified" : powerCut ? "skipped" : "failed"}>Verify</span>
    </div>
  </article>;
}

const friendlyClassification = (classification: string) => ({
  NO_ELECTRICAL_RESPONSE: "No expected electrical response",
  ABNORMAL_HIGH_DRAW: "Unusually high electrical draw",
  UNDERPOWERED: "Power is below the normal range",
  START_THEN_STOP: "Power started, then stopped",
  DEVICE_UNAVAILABLE: "Device is unavailable",
  OK: "Electrical response looks normal",
}[classification] ?? words(classification));

function Diagnostic({ data, previousVerification, finalHeaterState, finalHeaterWatts, runId }: { data: Extract<Evidence, { kind: "diagnostic" }>["data"]; previousVerification: VerificationResult | null; finalHeaterState: string | null; finalHeaterWatts: number | null; runId: string | null }) {
  const first = data.attempts[0];
  const last = data.attempts[data.attempts.length - 1] ?? first;
  const recovered = data.final_status === "RECOVERED";
  const safety = data.final_status === "SAFETY_STOP";
  const verified = data.final_status === "VERIFIED";
  const triggerWatts = Math.max(...data.attempts.flatMap((attempt) => attempt.power_samples_watts), last?.observed_watts ?? 0);
  const retryAllowance = Math.max(data.attempts.length - 1, data.retries_used);
  const classification = friendlyClassification(first?.diagnostic_classification ?? data.diagnostic_classification);
  const result = recovered ? "Recovered" : safety ? "Safety stop" : verified ? "Working normally" : data.resolved ? "Resolved" : "Needs attention";
  const finalMessage = recovered
    ? `After ${data.retries_used === 1 ? "one retry" : `${data.retries_used} retries`}, the heater's electrical response is now within the expected range.`
    : safety
      ? `An unusually high ${n(triggerWatts)} W electrical draw was detected. The simulated heater was switched off without retrying.`
      : verified
        ? data.speakable_summary
        : `The heater still reports ${last?.reported_state ?? "ON"}, but VoltWise can't verify normal electrical operation. I stopped after ${data.retries_used === 1 ? "one safe retry" : `${data.retries_used} safe retries`}.`;
  const stages = [
    { label: "Command", value: "Sent", state: "done" },
    { label: "Verify", value: data.initial_verification === "FAILED" ? "Failed" : "Verified", state: data.initial_verification === "FAILED" ? "failed" : "done" },
    { label: "Diagnose", value: classification, state: safety ? "safety" : first?.diagnostic_classification === "OK" ? "done" : "attention" },
    { label: "Safe retry", value: safety || data.retries_used === 0 ? "Skipped" : `${data.retries_used} of ${retryAllowance}`, state: safety ? "skipped" : "done" },
    { label: "Re-verify", value: safety ? "Not attempted" : last?.verification === "VERIFIED" ? "Verified" : "Failed", state: safety ? "skipped" : last?.verification === "VERIFIED" ? "verified" : "failed" },
    { label: "Result", value: result, state: recovered || verified ? "verified" : safety ? "safety" : "danger" },
  ];
  return <article className={`context-card diagnostic-card ${recovered || verified ? "recovered" : safety ? "safety" : "unresolved"}`} aria-label="Heater diagnostic">
    <div className="diagnostic-heading"><div><p className="card-kicker">Heater diagnostic</p><h2>{result}</h2></div><span className="result-symbol" aria-hidden="true">{recovered || verified ? "✓" : safety ? "!" : "×"}</span></div>
    <ol className="diagnostic-flow" aria-label="Diagnostic workflow">{stages.map((stage, index) => <li key={stage.label} className={stage.state}><div className="stage-top"><span>{stage.label}</span><i aria-hidden="true">{stage.state === "done" || stage.state === "verified" ? "✓" : stage.state === "failed" ? "×" : stage.state === "skipped" ? "—" : "!"}</i></div><strong>{stage.value}</strong>{index < stages.length - 1 && <b className="flow-arrow" aria-hidden="true">→</b>}</li>)}</ol>
    {safety ? <SafetyTransition beforeState={first?.reported_state ?? "ON"} beforeWatts={triggerWatts} afterState={finalHeaterState} afterWatts={finalHeaterWatts} retries={data.retries_used} /> : <div className="diagnostic-facts">
      <div><span>Reported</span><strong>{last?.reported_state ?? "Unavailable"}</strong></div>
      {previousVerification && <div><span>Expected</span><strong>≈{n(previousVerification.expected_power_watts)} W</strong></div>}
      <div><span>Observed</span><strong>{(last?.observed_watts ?? 0) >= 1000 ? "≈" : ""}{n(last?.observed_watts ?? 0)} W</strong></div>
      <div><span>Safe retries</span><strong>{data.retries_used} / {retryAllowance}</strong></div>
    </div>}
    <p className="diagnostic-message">{finalMessage}</p>
    {!recovered && !verified && !safety && <TechnicianHandoff evidence={{
      appliance: "Living room heater",
      reportedState: last?.reported_state ?? "Unavailable",
      expectedWatts: previousVerification?.expected_power_watts ?? null,
      observedWatts: last?.observed_watts ?? null,
      telemetryAvailable: last?.available ?? null,
      diagnosticOutcome: friendlyClassification(last?.diagnostic_classification ?? data.diagnostic_classification),
      retries: data.retries_used,
      safetyStop: false,
      runId,
    }} />}
  </article>;
}

type Props = { evidence: Evidence; previousVerification: VerificationResult | null; finalHeaterState: string | null; finalHeaterWatts: number | null; runId?: string | null; onDiagnose: () => void };

export function EvidencePanel({ evidence, previousVerification, finalHeaterState, finalHeaterWatts, runId = null, onDiagnose }: Props) {
  if (evidence.kind === "energy") return <Energy data={evidence.data} />;
  if (evidence.kind === "usage") return <Usage data={evidence.data} />;
  if (evidence.kind === "tariff") return <Tariff data={evidence.data} />;
  if (evidence.kind === "target") return <Target data={evidence.data} />;
  if (evidence.kind === "verification") return <Verification data={evidence.data} finalHeaterState={finalHeaterState} finalHeaterWatts={finalHeaterWatts} onDiagnose={onDiagnose} />;
  if (evidence.kind === "diagnostic") return <Diagnostic data={evidence.data} previousVerification={previousVerification} finalHeaterState={finalHeaterState} finalHeaterWatts={finalHeaterWatts} runId={runId} />;
  return null;
}
