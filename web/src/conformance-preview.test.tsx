// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConformancePreview } from "./conformance-preview";
import "./test-setup";


// Verify informational flags, labels, and structural changes are visible.
describe("conformance preview", () => {
  it("renders flags and change impact", () => {
    render(
      <ConformancePreview
        changeImpact={{
          against_version: "v1",
          added_rules: [],
          removed_rules: [],
          changed_thresholds: [
            { rule_code: "high_cover_standard", from: 5, to: 10 },
          ],
          changed_documents: [],
        }}
        conformance={{
          regulation_version: "r1",
          flags: [
            {
              rule_code: "high_cover_standard",
              field: "requested_cover",
              rule_value: 10,
              clause: {
                passage_key: "4.2",
                limit: { operator: "greater_than", value: 0 },
              },
              label: "PUBLIC REGULATION - INFORMATIONAL",
            },
          ],
          related: [
            { rule_code: "high_cover_standard", passage_keys: ["4.2"] },
          ],
        }}
      />,
    );

    expect(screen.getAllByText(/high_cover_standard/)).toHaveLength(3);
    expect(
      screen.getByText(/PUBLIC REGULATION - INFORMATIONAL/),
    ).toBeTruthy();
    expect(screen.getByText(/Changed threshold/)).toBeTruthy();
    expect(screen.getByText(/5 to 10/)).toBeTruthy();
    expect(screen.getByText(/against v1/)).toBeTruthy();
    expect(screen.getByText(/Related clauses/)).toBeTruthy();
  });

  // Verify no flag disables or removes product actions outside this panel.
  it("renders no-flag state", () => {
    render(
      <ConformancePreview
        changeImpact={{
          against_version: null,
          added_rules: [],
          removed_rules: [],
          changed_thresholds: [],
          changed_documents: [],
        }}
        conformance={{
          regulation_version: null,
          flags: [],
          related: [],
        }}
      />,
    );
    expect(screen.getByText("No conformance flags.")).toBeTruthy();
  });
});
