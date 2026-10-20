import { useEffect, useRef } from "react";
import type { DemoState } from "../types/api";

type Props = { open: boolean; busy: boolean; state: DemoState | null; onClose: () => void; onReset: () => void; onScenario: (scenario: string) => void; onFault: (fault: string) => void; onPreset: (name: "NORMAL" | "FAILURE" | "RECOVERY" | "SAFETY" | "TARIFF") => void };
export function DemoControls(props: Props) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!props.open) return;
    restoreFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButton.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") props.onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      restoreFocus.current?.focus();
    };
  }, [props.open]);

  if (!props.open) return null;
  const presetLabels = { NORMAL: "Normal", FAILURE: "Heater failure", RECOVERY: "Recovery", SAFETY: "Safety stop", TARIFF: "Tariff edge" } as const;
  return <div className="drawer-scrim" role="presentation" onMouseDown={props.onClose}><aside className="demo-drawer" role="dialog" aria-modal="true" aria-label="Simulation controls" onMouseDown={(event) => event.stopPropagation()}>
    <div className="drawer-header"><div><h2>Simulation controls</h2><p>Prepare a repeatable judging scenario.</p></div><button ref={closeButton} aria-label="Close simulation controls" onClick={props.onClose}>×</button></div>
    <section><h3>Current state</h3><dl><div><dt>Energy</dt><dd>{props.state?.energy_scenario ?? "—"}</dd></div><div><dt>Heater</dt><dd>{props.state?.heater_fault ?? "—"}</dd></div></dl></section>
    <section><h3>One-click scenes</h3><div className="preset-grid">{(["NORMAL", "FAILURE", "RECOVERY", "SAFETY", "TARIFF"] as const).map((name) => <button key={name} disabled={props.busy} onClick={() => props.onPreset(name)}>{presetLabels[name]}</button>)}</div></section>
    <section><h3>Energy scenario</h3><div className="control-stack">{["NORMAL_CURRENT_CYCLE", "NEAR_THRESHOLD"].map((value) => <button key={value} disabled={props.busy} onClick={() => props.onScenario(value)}>{value.replaceAll("_", " ").toLowerCase()}</button>)}</div></section>
    <section><h3>Heater fault</h3><div className="control-stack">{["NONE", "NO_DRAW", "NO_DRAW_THEN_RECOVER", "HIGH_DRAW"].map((value) => <button key={value} disabled={props.busy} onClick={() => props.onFault(value)}>{value.replaceAll("_", " ").toLowerCase()}</button>)}</div></section>
    <button className="reset-button" disabled={props.busy} onClick={props.onReset}>Reset demo</button>
  </aside></div>;
}
