import type { Evidence, MCPTrace } from "../types/api";
import "./VoltWiseActivity.css";

type Props = {
  latestTrace: MCPTrace | null;
  lastCommand: string | null;
  busy: boolean;
  progress: string;
  evidence: Evidence | null;
  error: string | null;
  activeDevice: string | null;
  deviceStates: Record<string, string>;
};

const watts = (value: number) => `${value >= 1000 ? "≈" : ""}${value.toLocaleString()} W`;

export function VoltWiseActivity({ latestTrace, lastCommand, busy, progress, evidence, error, activeDevice, deviceStates }: Props) {
  // Persisted traces remain in Technical evidence. They must not appear to be
  // the result of a command in a freshly reset scene.
  if (!busy && !lastCommand && !evidence) {
    return <div className="voltwise-activity idle" aria-label="VoltWise MCP live activity">
      <div className="activity-mcp-badge">
        <span className="live-dot" />
        <strong className="badge-title">MCP route</strong>
        <span className="badge-meta">Streamable HTTP · evidence appears after a command</span>
      </div>
      <div className="activity-hint">Ready for commands. Try <strong>"Turn on the light"</strong>, <strong>"Turn on the fan"</strong>, or <strong>"Turn on the heater"</strong>.</div>
    </div>;
  }

  let title = busy ? "Working through VoltWise…" : "Completed";
  let detail = busy ? progress : "The current request completed.";
  let tone: "success" | "warning" | "danger" | "safety" | "neutral" = "neutral";

  if (error) {
    title = "Request failed";
    detail = "The current request could not be completed.";
    tone = "danger";
  } else if (evidence?.kind === "verification") {
    const result = evidence.data;
    if (result.verification === "VERIFIED") {
      title = "Electrical response verified";
      detail = `${watts(result.observed_power_watts)} is within the expected electrical range.`;
      tone = "success";
    } else if (/high draw/i.test(result.reason)) {
      title = /power was cut/i.test(result.reason) ? "Safety stop" : "Abnormal high draw";
      detail = `${watts(result.observed_power_watts)} was observed${/power was cut/i.test(result.reason) ? "; simulated power was cut without retrying." : "."}`;
      tone = /power was cut/i.test(result.reason) ? "safety" : "danger";
    } else {
      title = "Electrical response not verified";
      detail = `Reported ${result.reported_state}; ${watts(result.observed_power_watts)} observed against ≈${result.expected_power_watts.toLocaleString()} W expected.`;
      tone = "danger";
    }
  } else if (evidence?.kind === "diagnostic") {
    const result = evidence.data;
    const lastAttempt = result.attempts[result.attempts.length - 1];
    const peak = Math.max(...result.attempts.flatMap((attempt) => attempt.power_samples_watts), lastAttempt?.observed_watts ?? 0);
    if (result.final_status === "RECOVERED" || result.final_status === "VERIFIED") {
      title = result.final_status === "RECOVERED" ? "Recovered" : "Electrical response verified";
      detail = `${watts(lastAttempt?.observed_watts ?? 0)} verified after ${result.retries_used} ${result.retries_used === 1 ? "retry" : "retries"}.`;
      tone = "success";
    } else if (result.final_status === "SAFETY_STOP") {
      title = "Safety stop";
      detail = `${watts(peak)} triggered simulated cutoff; zero retries.`;
      tone = "safety";
    } else {
      title = "Needs attention";
      detail = `${watts(lastAttempt?.observed_watts ?? 0)} observed; stopped after ${result.retries_used} safe ${result.retries_used === 1 ? "retry" : "retries"}.`;
      tone = "danger";
    }
  } else if (evidence?.kind === "usage") {
    const top = evidence.data.contributors[0];
    title = "Main contributor identified";
    detail = top ? `${top.device}: +${top.runtime_change_hours} h and ${top.energy_impact_kwh} kWh ${top.energy_impact_type.toLowerCase()}.` : "No monitored-device contributor was identified.";
  } else if (evidence?.kind === "tariff") {
    title = "Projected to cross";
    detail = `${Number(evidence.data.projected_month_end_kwh).toFixed(1)} kWh projected this cycle.`;
    tone = "warning";
  } else if (evidence?.kind === "energy") {
    title = "Comparison complete";
    detail = `${evidence.data.current_kwh} kWh this cycle versus ${evidence.data.previous_equivalent_kwh} kWh previously.`;
  } else if (evidence?.kind === "target") {
    title = "Action plan generated";
    detail = `${evidence.data.remaining_kwh_budget} kWh remains against the ${evidence.data.target_kwh} kWh target.`;
  } else if (!busy && activeDevice) {
    const names: Record<string, string> = { light: "Living Room Light", fan: "Ceiling Fan", tv: "TV", ac: "Air Conditioner", dishwasher: "Dishwasher" };
    title = `${names[activeDevice] ?? activeDevice} ${deviceStates[activeDevice] ?? "updated"}`;
    detail = "Device-reported state updated.";
    tone = "neutral";
  }

  const toolName = latestTrace?.tool_name ?? null;
  const duration = latestTrace?.duration_ms != null ? `${latestTrace.duration_ms.toFixed(1)} ms` : null;

  return <div className={`voltwise-activity ${busy ? "busy" : "completed"} tone-${tone}`} aria-label="VoltWise MCP live activity">
    <div className="activity-mcp-badge" title={`Trace: ${latestTrace?.trace_id || "pending"}`}>
      <span className={`live-dot ${busy ? "pulsing" : "active"}`} />
      <span className="badge-tag">MCP</span>
    </div>
    <div className="activity-summary" aria-live="polite">
      <span>Current outcome</span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
    <div className="activity-technical-hint">
      {!busy && toolName && <code>{toolName}</code>}
      {!busy && duration && <span>{duration}</span>}
      <small>Details in Technical evidence</small>
    </div>
  </div>;
}
