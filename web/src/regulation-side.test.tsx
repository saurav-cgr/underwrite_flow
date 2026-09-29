// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api-knowledge", () => ({
  fetchPassageGuidance: vi.fn(),
}));

import { fetchPassageGuidance } from "./api-knowledge";
import { RegulationSide } from "./regulation-side";
import "./test-setup";

const PASSAGE = {
  passage_key: "life-claim-settlement",
  title: "Claim settlement",
  body: "Claims settle within thirty days.",
  topic: "claim",
  label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
};

const CLAUSE = {
  passage_key: "circular#2",
  title: "2. Claim settlement",
  body: "Insurers settle claims within thirty days.",
  topic: "regulation",
  label: "PUBLIC REGULATION - INFORMATIONAL",
};

beforeEach(() => {
  vi.clearAllMocks();
});

// Verify the side panel shows each related clause with its badge.
describe("regulation side panel", () => {
  it("lists related clauses with the informational badge", async () => {
    vi.mocked(fetchPassageGuidance).mockResolvedValue({
      passage: PASSAGE,
      related_regulation: [CLAUSE],
    });
    render(
      <RegulationSide
        caseId="case-1"
        passageKey="life-claim-settlement"
        token="session"
      />,
    );

    expect(await screen.findByText("2. Claim settlement")).toBeTruthy();
    expect(screen.getByText("PUBLIC REGULATION - INFORMATIONAL"))
      .toBeTruthy();
    expect(
      screen.getByText(/Insurers settle claims within thirty days/),
    ).toBeTruthy();
  });

  it("renders nothing when no clause is related", async () => {
    vi.mocked(fetchPassageGuidance).mockResolvedValue({
      passage: PASSAGE,
      related_regulation: [],
    });
    const { container } = render(
      <RegulationSide
        caseId="case-1"
        passageKey="life-claim-settlement"
        token="session"
      />,
    );

    await vi.waitFor(() => {
      expect(fetchPassageGuidance).toHaveBeenCalled();
    });
    expect(container.textContent).toBe("");
  });
});
