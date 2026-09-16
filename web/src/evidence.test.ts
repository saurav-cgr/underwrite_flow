import { describe, expect, it } from "vitest";

import {
  displayValue,
  evidenceDocuments,
  evidenceFields,
  failureReason,
  riskSignals,
} from "./evidence";

const EVIDENCE = [
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
  {
    document_id: "document-1",
    field_name: "prior_claims",
    value: null,
    source_locator: "page:1",
    source_type: "extracted_field",
  },
];

// Verify documents and extracted fields are separated for the reviewer.
describe("evidence rows", () => {
  it("lists submitted documents with their stored locator", () => {
    expect(evidenceDocuments(EVIDENCE)).toEqual([
      {
        documentId: "document-1",
        filename: "synthetic.pdf",
        source: "case-1/synthetic.pdf",
      },
    ]);
  });

  it("lists extracted fields with value and provenance", () => {
    expect(evidenceFields(EVIDENCE)).toEqual([
      {
        documentId: "document-1",
        field: "vehicle_age",
        value: "2",
        source: "page:1",
      },
      {
        documentId: "document-1",
        field: "prior_claims",
        value: "not provided",
        source: "page:1",
      },
    ]);
  });

  it("ignores entries without a usable name", () => {
    expect(evidenceDocuments([{ source_type: "submitted_document" }])).toEqual(
      [],
    );
    expect(evidenceFields([{ source_type: "extracted_field" }])).toEqual([]);
  });
});

// Verify unknown evidence values never render as invented text.
describe("evidence values", () => {
  it("renders scalars and marks absent values", () => {
    expect(displayValue("personal")).toBe("personal");
    expect(displayValue(0)).toBe("0");
    expect(displayValue(false)).toBe("false");
    expect(displayValue(null)).toBe("not provided");
    expect(displayValue(undefined)).toBe("not provided");
    expect(displayValue({ nested: true })).toBe("structured value");
  });
});

// Verify the recorded failure reason is found in either stored shape.
describe("failure reasons", () => {
  it("reads a flat document failure", () => {
    expect(
      failureReason({
        document_id: "document-1",
        error_code: "provider_error",
      }),
    ).toBe("provider_error");
  });

  it("reads a nested processing failure reason", () => {
    expect(
      failureReason({
        rule_code: "unsupported_product",
        status: "error",
        details: { reason: "unreadable_product_configuration" },
      }),
    ).toBe("unreadable_product_configuration");
  });

  it("falls back when no reason is recorded", () => {
    expect(failureReason(null)).toBe("recorded failure");
    expect(failureReason({ rule_code: "synthetic" })).toBe(
      "recorded failure",
    );
  });
});

// Verify risk signals are read defensively from the assembled summary.
describe("summary risk signals", () => {
  it("reads configured signals", () => {
    expect(
      riskSignals({
        risk_signals: [
          {
            code: "vehicle_age_specialist",
            severity: "high",
            explanation: "Configured rule triggered: vehicle_age_specialist",
          },
        ],
      }),
    ).toEqual([
      {
        code: "vehicle_age_specialist",
        severity: "high",
        explanation: "Configured rule triggered: vehicle_age_specialist",
      },
    ]);
  });

  it("tolerates a missing or malformed summary", () => {
    expect(riskSignals({})).toEqual([]);
    expect(riskSignals({ risk_signals: "synthetic" })).toEqual([]);
    expect(riskSignals(null)).toEqual([]);
  });
});
