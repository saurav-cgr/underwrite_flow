// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SpecialistBrief } from "./specialist-brief";
import "./test-setup";

const BRIEF = {
  evidence: [
    {
      field_name: "occupation_type",
      value: "hazardous",
      document: "identity_record.pdf",
      source_locator: "page:1",
    },
  ],
  rules: ["hazardous_occupation_specialist"],
  passages: [
    {
      title: "Hazardous occupation",
      body: "Synthetic hazardous occupation guidance.",
      citation: {
        version: "g1",
        passage_key: "life-occupation-hazardous",
      },
    },
  ],
  label: "SYNTHETIC - FOR DEMONSTRATION ONLY",
};

// Verify specialist evidence, rules, passages, and sources render as text.
describe("specialist brief", () => {
  it("renders every deterministic section", () => {
    render(<SpecialistBrief brief={BRIEF} />);

    expect(screen.getByText("Specialist brief")).toBeTruthy();
    expect(screen.getByText(/occupation_type/)).toBeTruthy();
    expect(screen.getByText(/identity_record\.pdf, page:1/)).toBeTruthy();
    expect(screen.getByText("hazardous_occupation_specialist")).toBeTruthy();
    expect(screen.getByText("Hazardous occupation")).toBeTruthy();
    expect(screen.getByText(/life-occupation-hazardous/)).toBeTruthy();
  });
});
