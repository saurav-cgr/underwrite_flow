// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { ReviewActions } from "./review-actions";
import "./test-setup";

const SUGGESTIONS = [
  { version: "g1", passage_key: "life-occupation-hazardous" },
];

// Render review controls with live reason state for suggestion checks.
function Harness({ suggestions = SUGGESTIONS, overriding = false }) {
  const [reason, setReason] = useState("");
  return (
    <ReviewActions
      decided={false}
      locked={false}
      needsInformation={false}
      onDecision={vi.fn()}
      onOverrideChange={vi.fn()}
      onReasonChange={setReason}
      onRouteChange={vi.fn()}
      onSpecialistLabelChange={vi.fn()}
      overriding={overriding}
      reason={reason}
      selectedRoute="specialist"
      specialistLabel="life review"
      start={null}
      suggestedCitations={suggestions}
    />
  );
}

// Verify suggestions appear only while the override dialog is open.
describe("review citation suggestion visibility", () => {
  it("hides stored suggestions outside the override dialog", () => {
    render(<Harness overriding={false} />);

    expect(
      screen.queryByRole("group", { name: "Suggested citations" }),
    ).toBeNull();
  });

  it("shows stored suggestions inside the override dialog", () => {
    render(<Harness overriding />);

    expect(
      screen.getByRole("group", { name: "Suggested citations" }),
    ).toBeTruthy();
  });
});

// Verify accepting a suggestion appends its citation to the override reason.
describe("review citation suggestions", () => {
  it("adds an accepted citation to the reason", async () => {
    render(<Harness overriding />);
    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Use citation g1: life-occupation-hazardous",
      }),
    );

    const reason = screen.getByRole("textbox", { name: /reason/i });
    expect((reason as HTMLTextAreaElement).value).toBe(
      "[g1:life-occupation-hazardous]",
    );
  });

  it("allows the underwriter to ignore every suggestion", async () => {
    render(<Harness overriding />);
    const user = userEvent.setup();
    const reason = screen.getByRole("textbox", { name: /reason/i });

    await user.type(reason, "Use independent underwriter judgment.");

    expect((reason as HTMLTextAreaElement).value).toBe(
      "Use independent underwriter judgment.",
    );
  });
});
