const good = new Set(["VERIFIED", "RECOVERED", "ACHIEVABLE", "ACHIEVABLE_WITH_REDUCTION", "ON", "OK"]);
const bad = new Set(["FAILED", "UNRESOLVED", "SAFETY_STOP", "ABNORMAL_HIGH_DRAW", "NO_ELECTRICAL_RESPONSE"]);

export function StatusBadge({ status }: { status: string }) {
  const tone = good.has(status) ? "good" : bad.has(status) ? "bad" : "warn";
  return <span className={`status-badge ${tone}`} aria-label={`Status: ${status}`}>{status.replaceAll("_", " ")}</span>;
}
