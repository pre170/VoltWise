import type { VerificationPresentationStage } from "../components/VerificationExperience";

export const VERIFICATION_TIMELINE_MS = {
  evidence: 3200,
  diagnosis: 6400,
  final: 9600,
} as const;

export function scheduleVerificationPresentation(
  startedAt: number,
  reveal: (stage: VerificationPresentationStage) => void,
) {
  const elapsed = Date.now() - startedAt;
  const timers = (Object.entries(VERIFICATION_TIMELINE_MS) as Array<["evidence" | "diagnosis" | "final", number]>).map(([stage, atMilliseconds]) =>
    window.setTimeout(() => reveal(stage), Math.max(0, atMilliseconds - elapsed)),
  );
  return () => timers.forEach((timer) => window.clearTimeout(timer));
}
