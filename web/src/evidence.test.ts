import { describe, expect, it } from "vitest";

import {
  contentTypeLabel,
  displayValue,
  documentCards,
  documentTitles,
  failureReason,
  groupFacts,
  pageCountLabel,
  pdfPageOf,
  riskSignals,
  sourceLabel,
} from "./evidence";
import type { EvidenceItem, SubmittedFact } from "./types";

const SUBMITTED: SubmittedFact[] = [
  {
    field_name: "vehicle_age",
    field_label: "Vehicle age",
    field_type: "integer",
    value: 2,
  },
  {
    field_name: "vehicle_use",
    field_label: "Vehicle use",
    field_type: "enum",
    value: "commute",
  },
  {
    field_name: "annual_distance",
    field_label: "Annual distance",
    field_type: "integer",
    value: 12000,
  },
];

const EVIDENCE: EvidenceItem[] = [
  {
    source_type: "submitted_document",
    document_id: "doc-1",
    document_code: "vehicle_record",
    document_title: "Synthetic vehicle record",
    filename: "synthetic.pdf",
    content_type: "application/pdf",
    page_count: 1,
  },
  {
    source_type: "extracted_field",
    document_id: "doc-1",
    field_name: "vehicle_age",
    field_label: "Vehicle age",
    field_type: "integer",
    value: 2,
    source_locator: "line:1",
    extraction_method: "fake",
    confidence: 0.98,
    conflict_status: "clear",
  },
  {
    source_type: "extracted_field",
    document_id: "doc-1",
    field_name: "vehicle_use",
    field_label: "Vehicle use",
    field_type: "enum",
    value: "commercial",
    source_locator: "page:2",
    extraction_method: "fake",
    confidence: 0.9,
    conflict_status: "conflict",
  },
  {
    source_type: "extracted_field",
    document_id: "doc-1",
    field_name: "chassis_number",
    field_label: "Chassis number",
    field_type: "text",
    value: "CH-0001",
    source_locator: "page:1",
    extraction_method: "fake",
    confidence: null,
    conflict_status: "clear",
  },
];

// Verify a media type and page count read as short reviewer-facing labels.
describe("media labels", () => {
  it("names common document types", () => {
    expect(contentTypeLabel("application/pdf")).toBe("PDF");
    expect(contentTypeLabel("image/jpeg")).toBe("JPEG");
    expect(contentTypeLabel("image/png")).toBe("PNG");
    expect(contentTypeLabel("text/plain")).toBe("PLAIN");
  });

  it("describes a page count or omits it when unknown", () => {
    expect(pageCountLabel(1)).toBe("1 page");
    expect(pageCountLabel(3)).toBe("3 pages");
    expect(pageCountLabel(null)).toBe("");
  });
});

// Verify provider locators become readable prose without inventing detail.
describe("source labels", () => {
  it("turns page and line locators into prose", () => {
    expect(sourceLabel("page:1")).toBe("Page 1");
    expect(sourceLabel("line:2")).toBe("Line 2");
    expect(sourceLabel(null)).toBe("—");
    expect(sourceLabel("table:3")).toBe("table:3");
  });

  it("reads a PDF page from a page locator only", () => {
    expect(pdfPageOf("page:3")).toBe(3);
    expect(pdfPageOf("line:1")).toBeNull();
    expect(pdfPageOf(null)).toBeNull();
  });
});

// Verify uploaded documents become readable, distinguishable cards.
describe("document cards", () => {
  it("keeps a unique configured title", () => {
    expect(documentCards(EVIDENCE)).toEqual([
      {
        documentId: "doc-1",
        documentCode: "vehicle_record",
        title: "Synthetic vehicle record",
        filename: "synthetic.pdf",
        contentType: "application/pdf",
        pageCount: 1,
      },
    ]);
  });

  it("disambiguates two documents that share a title", () => {
    const two: EvidenceItem[] = [
      {
        source_type: "submitted_document",
        document_id: "doc-1",
        document_code: "vehicle_record",
        document_title: "Synthetic vehicle record",
        filename: "a.pdf",
        content_type: "application/pdf",
        page_count: 1,
      },
      {
        source_type: "submitted_document",
        document_id: "doc-2",
        document_code: "vehicle_record",
        document_title: "Synthetic vehicle record",
        filename: "b.pdf",
        content_type: "application/pdf",
        page_count: 1,
      },
    ];

    expect(documentCards(two).map((card) => card.title)).toEqual([
      "Synthetic vehicle record (1)",
      "Synthetic vehicle record (2)",
    ]);
    expect(documentTitles(two).get("doc-2")).toBe(
      "Synthetic vehicle record (2)",
    );
  });
});

// Verify one card groups a submitted value with its extracted evidence.
describe("group facts", () => {
  it("groups a consistent fact with its value and provenance", () => {
    const [card] = groupFacts(SUBMITTED, EVIDENCE);

    expect(card).toMatchObject({
      fieldName: "vehicle_age",
      fieldLabel: "Vehicle age",
      fieldType: "integer",
      submittedValue: "2",
      status: "Consistent",
    });
    expect(card.entries).toHaveLength(1);
    expect(card.entries[0]).toMatchObject({
      documentTitle: "Synthetic vehicle record",
      value: "2",
      source: "Line 1",
      confidence: 0.98,
      extractionMethod: "fake",
    });
  });

  it("reports a backend-recorded conflict without comparing values", () => {
    const cards = groupFacts(SUBMITTED, EVIDENCE);
    const use = cards.find((card) => card.fieldName === "vehicle_use");

    expect(use?.status).toBe("Conflict");
    expect(use?.submittedValue).toBe("commute");
    expect(use?.entries[0].value).toBe("commercial");
  });

  it("never infers a conflict from differing values", () => {
    const evidence: EvidenceItem[] = [
      {
        source_type: "extracted_field",
        document_id: "doc-1",
        field_name: "vehicle_age",
        field_label: "Vehicle age",
        field_type: "integer",
        value: 3,
        source_locator: "line:1",
        extraction_method: "fake",
        confidence: null,
        conflict_status: "clear",
      },
    ];

    expect(groupFacts(SUBMITTED, evidence)[0].status).toBe("Consistent");
  });

  it("marks a submitted fact with no document value as not found", () => {
    const cards = groupFacts(SUBMITTED, EVIDENCE);
    const distance = cards.find(
      (card) => card.fieldName === "annual_distance",
    );

    expect(distance?.status).toBe("Not found in documents");
    expect(distance?.entries).toEqual([]);
  });

  it("marks an extracted value with no submitted fact as document only", () => {
    const cards = groupFacts(SUBMITTED, EVIDENCE);
    const chassis = cards.find((card) => card.fieldName === "chassis_number");

    expect(chassis?.status).toBe("Document only");
    expect(chassis?.submittedValue).toBeNull();
    expect(chassis?.fieldLabel).toBe("Chassis number");
  });

  it("orders submitted facts first and document-only facts after", () => {
    const names = groupFacts(SUBMITTED, EVIDENCE).map(
      (card) => card.fieldName,
    );

    expect(names).toEqual([
      "vehicle_age",
      "vehicle_use",
      "annual_distance",
      "chassis_number",
    ]);
  });

  it("keeps two extracted values for the same field apart", () => {
    const evidence: EvidenceItem[] = [
      {
        source_type: "extracted_field",
        document_id: "doc-1",
        field_name: "vehicle_age",
        field_label: "Vehicle age",
        field_type: "integer",
        value: "2",
        source_locator: "line:1",
        extraction_method: "fake",
        confidence: null,
        conflict_status: "clear",
      },
      {
        source_type: "extracted_field",
        document_id: "doc-1",
        field_name: "vehicle_age",
        field_label: "Vehicle age",
        field_type: "integer",
        value: "9",
        source_locator: "line:1",
        extraction_method: "fake",
        confidence: null,
        conflict_status: "clear",
      },
    ];

    const [card] = groupFacts(SUBMITTED, evidence);

    expect(card.entries).toHaveLength(2);
    expect(card.entries.map((entry) => entry.value)).toEqual(["2", "9"]);
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
