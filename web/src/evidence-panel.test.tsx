// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EvidencePanel } from "./evidence-panel";
import "./test-setup";
import type { ReviewStart } from "./types";

const PACK: ReviewStart = {
  case_id: "case-id",
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
      document_id: "document-1",
      filename: "synthetic.pdf",
      source_locator: "case-1/synthetic.pdf",
      source_type: "submitted_document",
    },
    {
      document_id: "document-1",
      field_name: "vehicle_age",
      value: 2,
      source_locator: "page:1",
      source_type: "extracted_field",
    },
  ],
  conflicts: [
    {
      field_name: "vehicle_use",
      value: "commute",
      source_locator: "page:2",
      conflict_status: "conflict",
    },
  ],
  missing_information: ["inspection_photo"],
  extraction_failures: [
    {
      rule_code: "document:document-1",
      details: { error_code: "extraction_failed" },
    },
  ],
  specialist_options: ["motor inspection"],
};

// Verify the panel shows every part of the pack the reviewer must weigh.
describe("evidence panel", () => {
  it("shows documents, fields, signals, conflicts, gaps, and failures", () => {
    render(<EvidencePanel pack={PACK} />);

    expect(screen.getByText("synthetic.pdf")).toBeTruthy();
    expect(screen.getByText("case-1/synthetic.pdf")).toBeTruthy();
    expect(screen.getByText("vehicle_age")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("synthetic.pdf · page:1")).toBeTruthy();
    expect(screen.getByText("vehicle_age_specialist")).toBeTruthy();
    expect(screen.getByText("vehicle_use")).toBeTruthy();
    expect(screen.getByText("commute")).toBeTruthy();
    expect(screen.getByText("conflict")).toBeTruthy();
    expect(screen.getByText("inspection_photo")).toBeTruthy();
    expect(screen.getByText("document:document-1")).toBeTruthy();
    expect(screen.getByText("extraction_failed")).toBeTruthy();
  });

  it("states plainly when nothing is outstanding", () => {
    render(
      <EvidencePanel
        pack={{
          ...PACK,
          conflicts: [],
          evidence: [],
          extraction_failures: [],
          missing_information: [],
          summary: {},
        }}
      />,
    );

    expect(screen.getByText("No evidence was supplied.")).toBeTruthy();
    expect(screen.getByText("No conflict was detected.")).toBeTruthy();
    expect(
      screen.getByText("No requested document is outstanding."),
    ).toBeTruthy();
    expect(
      screen.getByText("No requested field is missing."),
    ).toBeTruthy();
    expect(
      screen.getByText("No processing failure was recorded."),
    ).toBeTruthy();
  });

  it("names the fields the evidence never supplied", () => {
    render(
      <EvidencePanel
        pack={{
          ...PACK,
          missing_information: [],
          summary: {
            missing_information: ["prior_claims", "annual_distance"],
          },
        }}
      />,
    );

    expect(screen.getByText("prior_claims")).toBeTruthy();
    expect(screen.getByText("annual_distance")).toBeTruthy();
    expect(screen.queryByText("No requested field is missing.")).toBeNull();
    expect(
      screen.getByText("No requested document is outstanding."),
    ).toBeTruthy();
  });

  it("renders two documents reporting the same field at the same line", () => {
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <EvidencePanel
        pack={{
          ...PACK,
          evidence: [
            {
              document_id: "document-1",
              field_name: "vehicle_age",
              value: "2",
              source_locator: "line:1",
              source_type: "extracted_field",
            },
            {
              document_id: "document-2",
              field_name: "vehicle_age",
              value: "9",
              source_locator: "line:1",
              source_type: "extracted_field",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("9")).toBeTruthy();
    expect(errors).not.toHaveBeenCalled();
    errors.mockRestore();
  });
});
