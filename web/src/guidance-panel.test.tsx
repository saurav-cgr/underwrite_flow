// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api-knowledge", () => ({
  fetchGuidance: vi.fn(),
  listQuestions: vi.fn().mockResolvedValue([]),
  askQuestion: vi.fn(),
  fetchPassageGuidance: vi.fn().mockResolvedValue({
    passage: {
      passage_key: "synthetic-section",
      title: "Synthetic section",
      body: "Synthetic passage body.",
      topic: "claim",
      label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
    },
    related_regulation: [],
  }),
}));

import { fetchGuidance } from "./api-knowledge";
import { GuidancePanel } from "./guidance-panel";
import "./test-setup";

const GUIDANCE = {
  pinned: { guideline_version: "g1", regulation_version: null },
  route_explanation: {
    status: "template" as const,
    text: "Standard review uses high cover guidance.",
    missing_items: [
      {
        item: "income_record",
        reason: "Cover exceeds synthetic threshold.",
        citations: [
          { version: "g1", passage_key: "life-cover-high-sum-assured" },
        ],
      },
    ],
    citations: [
      { version: "g1", passage_key: "life-cover-high-sum-assured" },
    ],
    label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
  },
  specialist_brief: null,
  suggested_citations: [],
};

// Start every panel test with a stable stored guidance response.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchGuidance).mockResolvedValue(GUIDANCE);
});

// Verify text, label, fallback badge, missing item, and citation rendering.
describe("guidance panel", () => {
  it("renders stored explanation details", async () => {
    render(<GuidancePanel token="session" caseId="case-id" />);

    expect(
      await screen.findByText("Standard review uses high cover guidance."),
    ).toBeTruthy();
    expect(screen.getByText("Template fallback")).toBeTruthy();
    expect(
      screen.getByText("SYNTHETIC - FOR DEMONSTRATION ONLY"),
    ).toBeTruthy();
    expect(screen.getByText(/income_record/)).toBeTruthy();
    expect(screen.getByText(/life-cover-high-sum-assured/)).toBeTruthy();
  });

  // Verify opening a case reads stored guidance once without polling.
  it("requests guidance exactly once", async () => {
    render(<GuidancePanel token="session" caseId="case-id" />);

    await screen.findByText("Standard review uses high cover guidance.");
    expect(fetchGuidance).toHaveBeenCalledTimes(1);
    expect(fetchGuidance).toHaveBeenCalledWith("session", "case-id");
  });

  // Verify unavailable guidance uses a visible non-color status cue.
  it("announces unavailable guidance", async () => {
    vi.mocked(fetchGuidance).mockResolvedValue({
      ...GUIDANCE,
      route_explanation: {
        ...GUIDANCE.route_explanation,
        status: "unavailable",
        text: "Explanation unavailable.",
        citations: [],
        missing_items: [],
      },
    });
    render(<GuidancePanel token="session" caseId="case-id" />);

    expect(
      await screen.findByRole("status", {
        name: "Explanation unavailable.",
      }),
    ).toBeTruthy();
  });

  // Verify Q&A stays available when the stored explanation fails to load.
  it("keeps questions available when guidance fails", async () => {
    vi.mocked(fetchGuidance).mockRejectedValue(new Error("offline"));
    render(<GuidancePanel token="session" caseId="case-id" />);

    expect(await screen.findByLabelText("Ask about this case")).toBeTruthy();
  });

  // Verify a case switch drops the previous case's brief and citations.
  it("clears stale guidance when the case changes", async () => {
    const onSuggestions = vi.fn();
    vi.mocked(fetchGuidance).mockResolvedValue({
      ...GUIDANCE,
      suggested_citations: [
        { version: "g1", passage_key: "life-occupation-hazardous" },
      ],
    });
    const { rerender } = render(
      <GuidancePanel
        token="session"
        caseId="case-one"
        onSuggestions={onSuggestions}
      />,
    );
    await screen.findByText("Standard review uses high cover guidance.");
    vi.mocked(fetchGuidance).mockRejectedValue(new Error("offline"));
    rerender(
      <GuidancePanel
        token="session"
        caseId="case-two"
        onSuggestions={onSuggestions}
      />,
    );

    expect(await screen.findByLabelText("Ask about this case")).toBeTruthy();
    expect(
      screen.queryByText("Standard review uses high cover guidance."),
    ).toBeNull();
    expect(onSuggestions).toHaveBeenLastCalledWith([]);
  });

  // Verify one failed case does not pin later cases to the error branch.
  it("reloads a later case after a failed fetch", async () => {
    vi.mocked(fetchGuidance).mockRejectedValue(new Error("offline"));
    const { rerender } = render(
      <GuidancePanel token="session" caseId="case-one" />,
    );
    expect(await screen.findByLabelText("Ask about this case")).toBeTruthy();
    vi.mocked(fetchGuidance).mockResolvedValue(GUIDANCE);
    rerender(<GuidancePanel token="session" caseId="case-two" />);

    expect(
      await screen.findByText("Standard review uses high cover guidance."),
    ).toBeTruthy();
  });
});
