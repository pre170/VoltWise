import { afterEach, describe, expect, it, vi } from "vitest";
import { scheduleVerificationPresentation, VERIFICATION_TIMELINE_MS } from "../services/verificationPresentation";

afterEach(() => vi.useRealTimers());

describe("verification presentation scheduler", () => {
  it("uses the measured command, evidence, diagnosis, and conclusion sequence", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-20T10:00:00Z"));
    const stages: string[] = ["command"];
    scheduleVerificationPresentation(Date.now(), (stage) => stages.push(stage));

    vi.advanceTimersByTime(VERIFICATION_TIMELINE_MS.evidence - 1);
    expect(stages).toEqual(["command"]);
    vi.advanceTimersByTime(1);
    expect(stages).toEqual(["command", "evidence"]);
    vi.advanceTimersByTime(VERIFICATION_TIMELINE_MS.diagnosis - VERIFICATION_TIMELINE_MS.evidence);
    expect(stages).toEqual(["command", "evidence", "diagnosis"]);
    vi.advanceTimersByTime(VERIFICATION_TIMELINE_MS.final - VERIFICATION_TIMELINE_MS.diagnosis);
    expect(stages).toEqual(["command", "evidence", "diagnosis", "final"]);
  });

  it("cancels every stale stage when reset or a new command replaces the run", () => {
    vi.useFakeTimers();
    const stages: string[] = [];
    const cancel = scheduleVerificationPresentation(Date.now(), (stage) => stages.push(stage));
    vi.advanceTimersByTime(VERIFICATION_TIMELINE_MS.evidence);
    expect(stages).toEqual(["evidence"]);
    cancel();
    vi.advanceTimersByTime(VERIFICATION_TIMELINE_MS.final);
    expect(stages).toEqual(["evidence"]);
  });
});
