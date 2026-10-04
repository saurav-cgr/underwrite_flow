// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api-knowledge", () => ({
  activateKnowledge: vi.fn(),
  importKnowledge: vi.fn(),
  importRegulation: vi.fn(),
  listKnowledgeVersions: vi.fn(),
  listRegulationVersions: vi.fn(),
  previewKnowledge: vi.fn(),
  acceptRegulationTags: vi.fn(),
}));

import {
  activateKnowledge,
  importKnowledge,
  listKnowledgeVersions,
  listRegulationVersions,
  previewKnowledge,
} from "./api-knowledge";
import { KnowledgeAdmin } from "./knowledge-admin";
import "./test-setup";

const VERSION = {
  id: "version-1",
  scope: "guideline",
  product_code: "life-individual-term",
  version: "g1",
  status: "draft",
  content_type: "synthetic_guidance",
  passage_count: 1,
  validation: { valid: false, issues: [{ code: "threshold_mismatch" }] },
  activated_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listKnowledgeVersions).mockResolvedValue([VERSION]);
  vi.mocked(listRegulationVersions).mockResolvedValue([]);
  vi.mocked(previewKnowledge).mockResolvedValue({
    version: VERSION,
    validation: VERSION.validation!,
    passages: [
      {
        passage_key: "life-cover-high-sum-assured",
        title: "High requested cover",
        topic: "cover-amount",
        bands: {
          age_min: 18,
          age_max: 40,
          sum_assured_min: 1000000,
          sum_assured_max: 5000000,
        },
        label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
        body: "Synthetic passage body.",
        thresholds: [],
        topic_tags: [],
        suggested_tags: [],
        limits: [],
      },
    ],
  });
  vi.mocked(activateKnowledge).mockResolvedValue({
    ...VERSION,
    status: "active",
  });
});

// Verify administrators can inspect version labels and validation issues.
describe("knowledge administration", () => {
  it("previews passages and announces validation issues", async () => {
    const user = userEvent.setup();
    render(<KnowledgeAdmin token="session" />);

    await user.click(await screen.findByRole("button", { name: /g1/ }));
    expect(await screen.findByText("threshold_mismatch")).toBeTruthy();
    expect(
      screen.getByText("SYNTHETIC - FOR DEMONSTRATION ONLY"),
    ).toBeTruthy();
    expect(screen.getByText(/Identifier: life-cover-high-sum-assured/))
      .toBeTruthy();
    expect(screen.getByText(/Topic: cover-amount/)).toBeTruthy();
    expect(screen.getByText(/Age band: 18 to 40/)).toBeTruthy();
    expect(
      screen.getByText(/Sum-assured band: 1000000 to 5000000/),
    ).toBeTruthy();
  });

  it("loads later preview pages", async () => {
    vi.mocked(previewKnowledge).mockResolvedValue({
      version: { ...VERSION, passage_count: 101 },
      validation: VERSION.validation!,
      passages: [
        {
          passage_key: "life-cover-high-sum-assured",
          title: "High requested cover",
          topic: "cover-amount",
          bands: {},
          label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
          body: "Synthetic passage body.",
          thresholds: [],
          topic_tags: [],
          suggested_tags: [],
          limits: [],
        },
      ],
    });
    const user = userEvent.setup();
    render(<KnowledgeAdmin token="session" />);

    await user.click(await screen.findByRole("button", { name: /g1/ }));
    await user.click(screen.getByRole("button", { name: "Next passages" }));

    expect(vi.mocked(previewKnowledge)).toHaveBeenLastCalledWith(
      "session",
      "version-1",
      100,
      100,
    );
  });

  // Verify YAML import updates the screen with an accessible status message.
  it("imports YAML and announces the result", async () => {
    vi.mocked(importKnowledge).mockResolvedValue({
      ...VERSION,
      validation: { valid: true, issues: [] },
    });
    const user = userEvent.setup();
    render(<KnowledgeAdmin token="session" />);

    await user.type(
      screen.getByLabelText("Guideline YAML"),
      "product_code: life-individual-term",
    );
    await user.click(screen.getByRole("button", { name: "Import draft" }));

    expect(vi.mocked(importKnowledge)).toHaveBeenCalledWith(
      "session",
      "product_code: life-individual-term",
    );
    expect((await screen.findByRole("status")).textContent).toContain(
      "Imported g1 as draft.",
    );
  });

  it("activates selected draft with keyboard-operable button", async () => {
    const user = userEvent.setup();
    render(<KnowledgeAdmin token="session" />);

    await user.click(await screen.findByRole("button", { name: /g1/ }));
    const button = await screen.findByRole("button", {
      name: "Activate selected version",
    });
    button.focus();
    await user.keyboard("{Enter}");
    expect(vi.mocked(activateKnowledge)).toHaveBeenCalledWith(
      "session",
      "version-1",
    );
    expect((await screen.findByRole("status")).textContent).toContain(
      "g1 is active.",
    );
  });
});
