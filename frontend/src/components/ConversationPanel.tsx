import { type ReactNode, useState } from "react";

export type Message = { id: number; role: "assistant" | "user"; text: string };

const LANDING_ACTIONS = [
  { command: "How are we doing this month?", label: "How are we doing this month?" },
  { command: "Why is our usage higher?", label: "Why is our usage higher?" },
  { command: "How's my tariff looking?", label: "How's my tariff looking?" },
];

const SUGGESTED_ACTIONS = [
  "Turn on the light",
  "Turn on the fan",
  "Turn on the TV",
  "Turn on the AC",
  "Turn on the heater",
  "Why is our usage higher?",
  "How's my tariff looking?",
];

type Props = {
  messages: Message[];
  busy: boolean;
  progress: string;
  connected: boolean;
  hasContext: boolean;
  prioritizeDiagnosis: boolean;
  home: ReactNode;
  context: ReactNode;
  technical: ReactNode;
  activity?: ReactNode;
  onSend: (text: string) => void;
  onRetry: () => void;
};

export function ConversationPanel({
  messages,
  busy,
  progress,
  connected,
  hasContext,
  prioritizeDiagnosis,
  home,
  context,
  technical,
  activity,
  onSend,
  onRetry,
}: Props) {
  const [value, setValue] = useState("");
  const landing = messages.length === 1 && !hasContext;
  const lastUser = [...messages].reverse().find((message) => message.role === "user");
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");

  const submit = () => {
    const text = value.trim();
    if (!text || busy || !connected) return;
    setValue("");
    onSend(text);
  };

  return (
    <section className={`conversation-panel ${landing ? "landing" : "active"}`} aria-label="Conversation">
      {landing ? (
        <>
          <p className="sr-only">
            Independent electrical evidence verifies the physical outcome, then guides safe diagnosis and recovery when reported state and reality don't match.
          </p>
          <div className="landing-experience">
            {home}
            <aside className="ready-panel" aria-label="Ready to verify heater">
              <div className="ready-copy">
                <p>Ready to verify</p>
                <h2>Reported ON is only the starting point.</h2>
                <span>VoltWise compares the device report with its simulated electrical response before confirming operation.</span>
              </div>
              <ol className="ready-workflow" aria-label="VoltWise verification workflow">
                <li><b>1</b><span>Observe</span></li>
                <li><b>2</b><span>Reason</span></li>
                <li><b>3</b><span>Act safely</span></li>
                <li><b>4</b><span>Verify</span></li>
              </ol>
              <button className="ready-action" aria-label="Turn on the heater" disabled={busy || !connected} onClick={() => onSend("Turn on the heater")}>
                <span><strong>Turn on &amp; verify heater</strong><small>Compare reported state with electrical response</small></span>
                <b aria-hidden="true">→</b>
              </button>
            </aside>
          </div>
          {activity}
          <div className="suggested-actions landing-actions" aria-label="Suggested prompts">
            {LANDING_ACTIONS.map((action) => (
              <button
                key={action.command}
                aria-label={action.command}
                disabled={busy || !connected}
                onClick={() => onSend(action.command)}
              >
                <span><strong>{action.label}</strong></span>
                <b aria-hidden="true">→</b>
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          {/* Active status alerts / service messages */}
          {lastAssistant || busy || lastUser ? (
            <div className="current-interaction" aria-live="polite">
              {lastUser && (
                <div className="spoken-line">
                  <span>You asked</span>
                  <p>{lastUser.text}</p>
                </div>
              )}
              {lastAssistant && (
                <div className="service-message">
                  <span aria-hidden="true">i</span>
                  <p>{lastAssistant.text}</p>
                </div>
              )}
              {busy && (
                <div className="thinking">
                  <i/>
                  <p>{progress || "Working…"}</p>
                </div>
              )}
            </div>
          ) : null}

          {/* Central Experience: Digital Home + Context Card */}
          <div className={`experience-grid ${hasContext ? "with-context" : ""}`}>
            {home}
            {context}
          </div>
          {activity}
        </>
      )}

      {!connected && (
        <div className="offline-card" role="status">
          <div>
            <strong>VoltWise is offline</strong>
            <span>Start the local services, then retry.</span>
          </div>
          <button onClick={onRetry}>Retry connection</button>
        </div>
      )}

      {/* Suggestion chips in active mode */}
      {!landing && !busy && !(prioritizeDiagnosis && hasContext) && (
        <div className={`suggested-actions contextual-actions ${prioritizeDiagnosis ? "priority" : ""}`} aria-label="Suggested prompts">
          {prioritizeDiagnosis ? (
            <button className="diagnose-action" disabled={!connected} onClick={() => onSend("Diagnose the heater")}>
              <span>Diagnose heater</span>
              <b aria-hidden="true">→</b>
            </button>
          ) : (
            SUGGESTED_ACTIONS.map((action) => (
              <button key={action} disabled={!connected} onClick={() => onSend(action)}>
                {action}
              </button>
            ))
          )}
        </div>
      )}

      {/* Ambient Alexa command surface */}
      <form className="composer" onSubmit={(event) => { event.preventDefault(); submit(); }}>
        <label htmlFor="voltwise-message">Alexa+ experience simulation</label>
        <div className="composer-shell">
          <span className="alexa-indicator" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" x2="12" y1="19" y2="22"/>
            </svg>
          </span>
          <span className="alexa-prefix" aria-hidden="true">Alexa ›</span>
          <input
            id="voltwise-message"
            aria-label="Message VoltWise"
            value={value}
            disabled={busy || !connected}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Turn on the heater…"
          />
          <button type="submit" disabled={!value.trim() || busy || !connected}>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            <span>Send</span>
          </button>
        </div>
      </form>

      {/* Collapsed by default technical evidence */}
      {technical}
    </section>
  );
}
