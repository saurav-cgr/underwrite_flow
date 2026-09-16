// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  runEvaluation: vi.fn(),
}));

import { ApiError, runEvaluation } from "./api";
import { EvaluationPanel } from "./evaluation-panel";
import "./test-setup";
import type { EvaluationSummary } from "./types";

const runEvaluationMock = vi.mocked(runEvaluation);

const SUMMARY: EvaluationSummary = {
  case_count: 90,
  development_count: 60,
  holdout_count: 30,
  route_counts: { expedited: 40, standard: 18, specialist: 32 },
  routable_count: 38,
  needs_information_count: 52,
  route_agreement: 0.875,
  specialist_recall: 0.9,
  evidence_accuracy: 0.95,
  conflict_detection: 1,
  conflict_precision: 0.8,
  missing_data_detection: 0.7,
  missing_precision: 0.6,
  unsupported_claim_rate: 0,
  workflow_reliability: 1,
  split: "all",
  trace_sent: false,
};

// Reset the mocked client before each panel check.
beforeEach(() => {
  vi.clearAllMocks();
});

// Verify the panel runs the reference set and reports what it produced.
describe("evaluation panel", () => {
  it("runs the full reference set and shows every metric", async () => {
    runEvaluationMock.mockResolvedValue(SUMMARY);
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    expect(runEvaluationMock).toHaveBeenCalledWith("session", undefined);
    expect(await screen.findByText("Cases evaluated")).toBeTruthy();
    expect(screen.getByText("Route agreement")).toBeTruthy();
    expect(screen.getByText("Unsupported claim rate")).toBeTruthy();
    expect(screen.getByText("90")).toBeTruthy();
    expect(screen.getByText("88%")).toBeTruthy();
  });

  it("narrows the run to the split the administrator chose", async () => {
    runEvaluationMock.mockResolvedValue(SUMMARY);
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.selectOptions(
      screen.getByLabelText(/case split/i),
      "holdout",
    );
    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    expect(runEvaluationMock).toHaveBeenCalledWith("session", "holdout");
  });

  it("states which cases route agreement covers", async () => {
    runEvaluationMock.mockResolvedValue(SUMMARY);
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    const note = await screen.findByText(/Route agreement covers only the/);
    expect(note.textContent).toContain("38 cases");
    expect(note.textContent).toContain("52");
    expect(note.textContent).toContain("all");
  });

  it("marks a metric the run did not produce", async () => {
    runEvaluationMock.mockResolvedValue({
      ...SUMMARY,
      workflow_reliability: null,
    } as unknown as EvaluationSummary);
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    expect(await screen.findByText("Workflow reliability")).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("holds the controls while the run is in flight", async () => {
    let settle: (value: EvaluationSummary) => void = () => undefined;
    runEvaluationMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          settle = resolve;
        }),
    );
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    const running = screen.getByRole("button", { name: "Running…" });
    expect((running as HTMLButtonElement).disabled).toBe(true);
    const split = screen.getByLabelText(/case split/i) as HTMLSelectElement;
    expect(split.disabled).toBe(true);

    settle(SUMMARY);
    await waitFor(() =>
      expect(
        (screen.getByRole("button", {
          name: "Run evaluation",
        }) as HTMLButtonElement).disabled,
      ).toBe(false),
    );
  });

  it("surfaces the message the API returned for a failed run", async () => {
    runEvaluationMock.mockRejectedValue(
      new ApiError(500, "Evaluation is unavailable"),
    );
    render(<EvaluationPanel token="session" />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Run evaluation" }));

    expect((await screen.findByRole("alert")).textContent).toBe(
      "Evaluation is unavailable",
    );
    expect(screen.getByText("No evaluation run yet")).toBeTruthy();
  });
});
