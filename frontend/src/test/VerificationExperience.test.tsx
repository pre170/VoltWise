import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { VerificationExperience } from "../components/VerificationExperience";
import { verification } from "./fixtures";

describe("progressive heater verification experience", () => {
  it("reveals real evidence in order and keeps the final verdict hidden until conclusion", () => {
    const onDiagnose = vi.fn();
    const view = render(<VerificationExperience stage="command" data={null} runId={null} onDiagnose={onDiagnose} />);
    expect(screen.getByText("Turning on the living room heater…")).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification conclusion")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Expected 1500 watts/)).not.toBeInTheDocument();

    view.rerender(<VerificationExperience stage="evidence" data={verification} runId="trace-progressive" onDiagnose={onDiagnose} />);
    expect(screen.getByLabelText("Expected 1500 watts, observed 7 watts")).toBeInTheDocument();
    expect(screen.getByText("Expected electrical response not detected.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Electrical evidence diagnosis")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Verification conclusion")).not.toBeInTheDocument();

    view.rerender(<VerificationExperience stage="diagnosis" data={verification} runId="trace-progressive" onDiagnose={onDiagnose} />);
    const diagnosis = screen.getByLabelText("Electrical evidence diagnosis");
    expect(within(diagnosis).getByText("Available")).toBeInTheDocument();
    expect(within(diagnosis).getByText("Not verified")).toBeInTheDocument();
    expect(screen.queryByLabelText("Verification conclusion")).not.toBeInTheDocument();

    view.rerender(<VerificationExperience stage="final" data={verification} runId="trace-progressive" onDiagnose={onDiagnose} />);
    expect(screen.getByLabelText("Verification conclusion")).toHaveTextContent("Electrical response not verified");
    expect(screen.getByLabelText("Technician help")).toBeInTheDocument();
    expect(onDiagnose).not.toHaveBeenCalled();
  });

  it("builds a shareable technician handoff from the actual run evidence", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(<VerificationExperience stage="final" data={verification} runId="trace-real-123" onDiagnose={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Get diagnostic summary" });
    await userEvent.click(trigger);
    const handoff = screen.getByRole("dialog", { name: "Technician handoff summary" });
    expect(handoff).toHaveTextContent("Living room heater");
    expect(handoff).toHaveTextContent("1,500 W");
    expect(handoff).toHaveTextContent("7 W");
    expect(handoff).toHaveTextContent("Available");
    expect(handoff).toHaveTextContent("Expected electrical response not detected");
    expect(handoff).toHaveTextContent("trace-real-123");
    expect(handoff).toHaveTextContent("No");
    await userEvent.click(within(handoff).getByRole("button", { name: "Copy diagnostic summary" }));
    expect(writeText).toHaveBeenCalledOnce();
    expect(writeText.mock.calls[0][0]).toContain("Run identifier: trace-real-123");
    expect(await screen.findByText("Diagnostic summary copied.")).toBeInTheDocument();
  });

  it("closes the diagnostic summary with Escape and restores focus", async () => {
    render(<VerificationExperience stage="final" data={verification} runId="trace-keyboard" onDiagnose={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Get diagnostic summary" });
    await userEvent.click(trigger);
    expect(screen.getByRole("button", { name: "Close diagnostic summary" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Technician handoff summary" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes a stale diagnostic summary when a new run replaces its evidence", async () => {
    const view = render(<VerificationExperience stage="final" data={verification} runId="trace-old" onDiagnose={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Get diagnostic summary" }));
    expect(screen.getByRole("dialog", { name: "Technician handoff summary" })).toBeInTheDocument();
    view.rerender(<VerificationExperience stage="final" data={verification} runId="trace-new" onDiagnose={vi.fn()} />);
    expect(screen.queryByRole("dialog", { name: "Technician handoff summary" })).not.toBeInTheDocument();
  });

  it("dismisses technician help without changing the verification result", async () => {
    render(<VerificationExperience stage="final" data={verification} runId="trace-dismiss" onDiagnose={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByLabelText("Technician help")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Verification conclusion")).toHaveTextContent("Electrical response not verified");
  });

  it("does not offer technician help for a verified result", () => {
    const success = { ...verification, verification: "VERIFIED", observed_power_watts: 1500, diagnostic_classification: "OK" };
    render(<VerificationExperience stage="final" data={success} runId="trace-success" onDiagnose={vi.fn()} />);
    expect(screen.getByLabelText("Verification conclusion")).toHaveTextContent("Electrical response verified");
    expect(screen.queryByLabelText("Technician help")).not.toBeInTheDocument();
  });
});
