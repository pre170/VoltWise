import type { ActivityEvent, Evidence, MCPTrace } from "../types/api";
import "./ActivityTimeline.css";

const friendly = (value: string) => value.replaceAll("_", " ").toLowerCase();
const transportName = (value: string) => value === "STREAMABLE_HTTP" ? "Streamable HTTP" : friendly(value);
const watts = (value: number) => `${value >= 1000 ? "≈" : ""}${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })} W`;
const classificationName = (value: string) => ({ NO_ELECTRICAL_RESPONSE: "No expected electrical response", ABNORMAL_HIGH_DRAW: "Abnormal high draw", OK: "Normal electrical response" }[value] ?? friendly(value));

function ResultSequence({ evidence, lastCommand }: { evidence: Evidence | null; lastCommand: string | null }) {
  if (evidence?.kind !== "verification" && evidence?.kind !== "diagnostic") return null;
  const items: Array<{ tone: "ok" | "active" | "verified" | "warning" | "safety"; text: string }> = [];
  if (lastCommand) items.push({ tone: "ok", text: `Alexa command: ${lastCommand}` });
  if (evidence.kind === "verification") {
    const data = evidence.data;
    items.push({ tone: "ok", text: `Device reported ${data.reported_state}` });
    items.push({ tone: "active", text: `Observed ${watts(data.observed_power_watts)} · expected ≈${data.expected_power_watts.toLocaleString("en-IN")} W` });
    items.push({ tone: data.verification === "VERIFIED" ? "verified" : "warning", text: data.verification === "VERIFIED" ? "Electrical response verified" : "Electrical response not verified" });
  } else {
    const data = evidence.data;
    const first = data.attempts[0];
    const last = data.attempts[data.attempts.length - 1] ?? first;
    if (first) items.push({ tone: data.final_status === "SAFETY_STOP" ? "safety" : "active", text: `${classificationName(first.diagnostic_classification)} · ${watts(first.observed_watts)}` });
    if (data.final_status === "SAFETY_STOP") {
      items.push({ tone: "safety", text: data.safety_action === "POWER_CUT_HIGH_DRAW" ? "Safety cutoff · power cut" : friendly(data.safety_action) });
      items.push({ tone: "safety", text: "Retry deliberately skipped · safety stop" });
    } else if (data.retries_used > 0) {
      items.push({ tone: "ok", text: `Safe retry executed · ${data.retries_used}` });
      if (last) items.push({ tone: last.verification === "VERIFIED" ? "verified" : "warning", text: `${last.verification === "VERIFIED" ? "Electrical response verified" : "Electrical response not verified"} · ${watts(last.observed_watts)}` });
    }
  }
  return <section className="result-sequence" aria-label="Recent result sequence"><strong>Recent sequence</strong><ol>{items.map((item, index) => <li className={item.tone} key={`${item.text}-${index}`}><i aria-hidden="true"/>{item.text}</li>)}</ol></section>;
}

type Props = { traces: MCPTrace[]; events: ActivityEvent[]; evidence: Evidence | null; lastCommand: string | null; classification: string | null; open: boolean; onToggle: () => void; };

export function ActivityTimeline({ traces, events, evidence, lastCommand, classification, open, onToggle }: Props) {
  const latest = traces[0];
  return <div className="evidence-footer">
    <ResultSequence evidence={evidence} lastCommand={lastCommand} />
    <section className={`activity-panel technical-evidence ${open ? "open" : ""}`}>
      <button className="activity-toggle" onClick={onToggle} aria-expanded={open} aria-label="View technical evidence">
        <span>Technical evidence{latest && <small>MCP · {transportName(latest.transport)} · {latest.protocol_version ?? "protocol unavailable"}</small>}</span><span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="trace-content">
        {!latest ? <p className="no-trace">No MCP calls yet.</p> : <>
          <div className="trace-route" aria-label="Latest MCP trace route">
            <div><i>Alexa+</i><span>Simulation</span></div><b aria-hidden="true">→</b>
            <div><i>{latest.tool_name}</i><span>MCP tool</span></div><b aria-hidden="true">→</b>
            <div><i>{transportName(latest.transport)}</i><span>{latest.protocol_version ?? "Protocol unavailable"}</span></div><b aria-hidden="true">→</b>
            <div><i>VoltWise</i><span>MCP server</span></div><b aria-hidden="true">→</b>
            <div className={latest.success ? "route-success" : "route-failed"}><i>Structured result</i><span><em>{latest.success ? "Success" : "Failed"}</em> · <time>{latest.duration_ms.toFixed(1)} ms</time></span></div>
          </div>
          <div className="technical-grid">
            <div className="technical-wide"><span>Arguments</span><code aria-label={`Arguments for ${latest.tool_name}`}>{JSON.stringify(latest.tool_arguments)}</code></div>
            {classification && latest.tool_name === "power_run_diagnostic" && <div><span>Classification</span><strong>{classification}</strong></div>}
            <div className="technical-wide"><span>Result summary</span><p>{latest.result_summary}</p></div>
            {latest.error && <div className="technical-wide"><span>Error</span><p className="trace-error">{latest.error}</p></div>}
          </div>
        </>}
        {traces.length > 1 && <details className="previous-traces"><summary>Earlier MCP calls · {traces.length - 1}</summary><ol>{traces.slice(1, 12).map((trace) => <li key={trace.trace_id}><strong>{trace.tool_name}</strong><span>{trace.success ? "Success" : "Failed"} · {trace.duration_ms.toFixed(1)} ms</span></li>)}</ol></details>}
        <details className="application-events"><summary>Application events · {events.length}</summary><ol className="timeline">{events.length === 0 ? <li>No application events yet.</li> : events.slice(0, 12).map((event) => <li key={event.event_id}><i/><div><strong>{friendly(event.action)}</strong><span>{friendly(event.outcome)} · {new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div></li>)}</ol></details>
      </div>}
    </section>
  </div>;
}
