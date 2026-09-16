// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  completeCase: vi.fn(),
  startReview: vi.fn(),
  submitReview: vi.fn(),
}));

import { completeCase, startReview, submitReview } from "./api";
import { CaseReview } from "./case-review";
import "./test-setup";
import type { QueueItem, ReviewStart } from "./types";

const ITEM: QueueItem = {
  case_id: "case-id-0000-0000-0000-000000000000",
  product_code: "motor-private-car",
  status: "underwriter_review",
  route: "specialist",
  selected_route: null,
  specialist_label: null,
  specialist: true,
  awaiting_handoff: false,
};

const PACK: ReviewStart = {
  case_id: "case-id-0000-0000-0000-000000000000",
  status: "awaiting_human_review",
  recommendation: { route: "specialist", factors: ["specialist_signal"] },
  summary: {
    risk_signals: [
      {
        code: "vehicle_age_specialist",
        severity: "high",
        explanation: "Configured rule triggered: vehicle_age_specialist",
      },
    ],
  },
  evidence: [
    {
      source_type: "submitted_document",
      document_id: "document-1",
      document_code: "vehicle_record",
      document_title: "Synthetic vehicle record",
      filename: "synthetic.pdf",
      content_type: "application/pdf",
      page_count: 1,
    },
  ],
  submitted_facts: [],
  conflicts: [],
  missing_information: [],
  extraction_failures: [],
  specialist_options: ["motor inspection"],
};

// Start every review check from a loaded evidence pack.
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(startReview).mockResolvedValue(PACK);
});

// Render the review screen for the synthetic queued case.
function renderReview(item: QueueItem = ITEM) {
  render(
    <CaseReview item={item} onNavigate={vi.fn()} token="session" />,
  );
}

// Verify the evidence is shown before the underwriter can attest to it.
describe("review evidence pack", () => {
  it("shows the submitted evidence above the acknowledgement", async () => {
    renderReview();

    const heading = await screen.findByRole("heading", {
      name: "Case evidence",
    });
    const acknowledgement = screen.getByText(
      "I reviewed the submitted evidence.",
    );

    expect(screen.getByText("Synthetic vehicle record")).toBeTruthy();
    expect(
      heading.compareDocumentPosition(acknowledgement)
        & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("explains the route from its recorded factors", async () => {
    renderReview();

    expect(await screen.findByText("Why this route")).toBeTruthy();
    expect(screen.getAllByText("specialist_signal").length).toBeGreaterThan(0);
  });

  it("blocks a decision until the evidence is acknowledged", async () => {
    renderReview();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", {
        name: "Confirm recommendation",
      }),
    );

    expect(screen.getByRole("alert").textContent).toContain(
      "Acknowledge the evidence",
    );
    expect(submitReview).not.toHaveBeenCalled();
  });
});

// Verify manual recommendations become explicit specialist decisions.
describe("manual recommendation", () => {
  const fallback = "Manual configuration review";
  const manualPack: ReviewStart = {
    ...PACK,
    recommendation: { route: "manual", factors: ["unsupported_product"] },
    specialist_options: [fallback],
  };

  it("shows and submits the fallback specialist destination", async () => {
    vi.mocked(startReview).mockResolvedValue(manualPack);
    vi.mocked(submitReview).mockResolvedValue({
      case_id: ITEM.case_id,
      action: "confirm",
      selected_route: "specialist",
      status: "overridden",
    });
    renderReview({ ...ITEM, route: "manual" });
    const user = userEvent.setup();

    const option = await screen.findByRole("option", { name: fallback });
    const specialist = screen.getByRole("radio", {
      name: /Specialist review/i,
    }) as HTMLInputElement;
    expect(option).toBeTruthy();
    expect(specialist.checked).toBe(true);

    await user.click(
      screen.getByRole("checkbox", {
        name: /reviewed the submitted evidence/i,
      }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirm recommendation" }),
    );

    expect(submitReview).toHaveBeenCalledWith(
      "session",
      ITEM.case_id,
      {
        action: "confirm",
        selected_route: undefined,
        specialist_label: fallback,
        reason: undefined,
        evidence_acknowledged: true,
      },
    );
  });

  it.each(["Standard", "Expedited"])(
    "still requires a reason for a %s override",
    async (route) => {
      vi.mocked(startReview).mockResolvedValue(manualPack);
      renderReview({ ...ITEM, route: "manual" });
      const user = userEvent.setup();

      await screen.findByRole("option", { name: fallback });
      await user.click(
        screen.getByRole("radio", { name: new RegExp(`${route} review`, "i") }),
      );
      await user.click(
        screen.getByRole("checkbox", {
          name: /reviewed the submitted evidence/i,
        }),
      );
      await user.click(
        screen.getByRole("button", { name: "Override route" }),
      );

      expect(screen.getByRole("alert").textContent).toContain(
        "Add a short reason",
      );
      expect(submitReview).not.toHaveBeenCalled();
    },
  );
});

// Verify a recorded decision is described once, without a repeated route.
describe("decision summary", () => {
  it("does not repeat the word when the route matches the status", async () => {
    vi.mocked(submitReview).mockResolvedValue({
      case_id: ITEM.case_id,
      action: "request_information",
      selected_route: null,
      status: "needs_information",
    });
    renderReview();
    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("checkbox", {
        name: /reviewed the submitted evidence/i,
      }),
    );
    await user.type(
      screen.getByRole("textbox", { name: /reason/i }),
      "Send the missing record.",
    );
    await user.click(
      screen.getByRole("button", { name: "Request information" }),
    );

    const recorded = await screen.findByRole("status");

    expect(recorded.textContent?.replace(/\s+/g, " ").trim()).toBe(
      "Decision recorded. needs information",
    );
    expect(screen.queryByRole("alert")).toBeNull();
    expect(startReview).toHaveBeenCalledTimes(1);
  });

  it(
    "keeps a failed handoff visible and retryable without a stale alert",
    async () => {
      vi.mocked(submitReview).mockResolvedValue({
        case_id: ITEM.case_id,
        action: "confirm",
        selected_route: "specialist",
        status: "confirmed",
      });
      vi.mocked(completeCase).mockRejectedValueOnce(new Error("offline"));
      renderReview();
      const user = userEvent.setup();

      await user.click(
        await screen.findByRole("checkbox", {
          name: /reviewed the submitted evidence/i,
        }),
      );
      await user.click(
        screen.getByRole("button", { name: "Confirm recommendation" }),
      );

      expect(
        await screen.findByText(/queue handoff did not complete/i),
      ).toBeTruthy();
      expect(
        screen.getByRole("button", { name: "Retry handoff" }),
      ).toBeTruthy();
      expect(screen.queryByRole("alert")).toBeNull();
      expect(startReview).toHaveBeenCalledTimes(1);
    },
  );
});
