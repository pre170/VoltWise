type Props = { connected: boolean; onOpenControls: () => void };

export function Header({ connected, onOpenControls }: Props) {
  return <header className="topbar">
    <div className="brand">
      <div className="brand-mark">V</div>
      <div className="brand-text">
        <div className="brand-title-row">
          <h1>VoltWise</h1>
          <p className="brand-subtitle">Digital Home · physical-outcome verification</p>
        </div>
        <div className="brand-tagline">
          <span>See what the home actually did.</span>
        </div>
      </div>
    </div>
    <div className="header-actions">
      <div className="simulation-badge">
        <span className={`connection ${connected ? "online" : "offline"}`}>
          <i />{connected ? "Connected" : "Offline"}
        </span>
        <small className="hackathon-disclosure" aria-label="Alexa+ experience simulated. Smart-home telemetry simulated. MCP integration real.">
          <span>Alexa+ <b>Simulated</b></span>
          <span>Telemetry <b>Simulated</b></span>
          <span>MCP <b>Real</b></span>
        </small>
      </div>
      <button className="control-button" onClick={onOpenControls} aria-label="Demo setup">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        <span>Demo setup</span>
        <b className="chevron" aria-hidden="true">▾</b>
      </button>
    </div>
  </header>;
}
