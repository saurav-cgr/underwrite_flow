// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {
    status = 500;
  },
  fetchReviewDocument: vi.fn(),
}));

import { fetchReviewDocument } from "./api";
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
  submitted_facts: [
    {
      field_name: "vehicle_age",
      field_label: "Vehicle age",
      field_type: "integer",
      value: 2,
    },
    {
      field_name: "annual_distance",
      field_label: "Annual distance",
      field_type: "integer",
      value: 12000,
    },
  ],
  evidence: [
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
      confidence: null,
      conflict_status: "clear",
    },
  ],
  conflicts: [],
  missing_information: ["inspection_photo"],
  reconciliation: [
    {
      check_code: "motor_ncb_match",
      kind: "ncb_match",
      status: "FLAGGED_DISCREPANCY",
      comparisons: [
        {
          field_key: "ncb_percent",
          left: 35,
          right: 20,
          matched: false,
          evidence: [
            { document_id: "doc-1", source_locator: "page:1" },
          ],
          explanation_code: "ncb_mismatch",
          confidence_source: "deterministic",
        },
      ],
      discrepancies: [
        {
          code: "ncb_mismatch",
          field_key: "ncb_percent",
          expected: 35,
          actual: 20,
        },
      ],
      evidence: [{ document_id: "doc-1", source_locator: "page:1" }],
      missing_inputs: [],
      rule_version: "v1",
    },
    {
      check_code: "motor_renewal_lapse",
      kind: "policy_lapse",
      status: "MISSING_EVIDENCE",
      comparisons: [],
      discrepancies: [],
      evidence: [],
      missing_inputs: ["application"],
      rule_version: "v1",
    },
  ],
  extraction_failures: [
    {
      rule_code: "document:doc-1",
      details: { error_code: "extraction_failed" },
    },
  ],
  specialist_options: ["motor inspection"],
};

// Verify each configured check is shown with words, values, and provenance.
describe("configured checks", () => {
  it("lists each check with its status in words", () => {
    render(<EvidencePanel pack={PACK} token="session" />);

    expect(screen.getByText("motor_ncb_match")).toBeTruthy();
    expect(screen.getByText("flagged discrepancy")).toBeTruthy();
    expect(screen.getByText("missing evidence")).toBeTruthy();
  });

  it("shows comparison values, provenance, and confidence source", () => {
    render(<EvidencePanel pack={PACK} token="session" />);

    expect(screen.getByText(/35 versus 20/)).toBeTruthy();
    expect(
      screen.getByText(/ncb_mismatch · from deterministic · doc-1 page:1/),
    ).toBeTruthy();
  });

  it("names the input a check could not read", () => {
    render(<EvidencePanel pack={PACK} token="session" />);

    expect(
      screen.getByText("No usable value for: application"),
    ).toBeTruthy();
  });
});

function stubObjectUrl() {
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: vi.fn(() => "blob:mock"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
}

function renderPanel(pack: ReviewStart = PACK) {
  return render(<EvidencePanel pack={pack} token="session" />);
}

beforeEach(() => {
  vi.clearAllMocks();
});

// Verify the panel shows every part of the pack the reviewer must weigh.
describe("evidence panel", () => {
  it("shows documents, facts, signals, gaps, and failures", () => {
    renderPanel();

    expect(screen.getByText("Synthetic vehicle record")).toBeTruthy();
    expect(screen.getByText("synthetic.pdf · PDF · 1 page")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Vehicle age" }),
    ).toBeTruthy();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Synthetic vehicle record · Line 1"),
    ).toBeTruthy();
    expect(screen.getByText("Consistent")).toBeTruthy();
    expect(screen.getByText("vehicle_age_specialist")).toBeTruthy();
    expect(screen.getByText("inspection_photo")).toBeTruthy();
    expect(screen.getByText("extraction_failed")).toBeTruthy();
    expect(
      screen.getAllByRole("button", { name: "View source" }).length,
    ).toBe(1);
    expect(
      screen.getAllByRole("button", { name: "View document" }).length,
    ).toBe(1);
  });

  it("states plainly when nothing is outstanding", () => {
    renderPanel({
      ...PACK,
      submitted_facts: [],
      evidence: [],
      extraction_failures: [],
      missing_information: [],
      summary: {},
    });

    expect(screen.getByText("No evidence was supplied.")).toBeTruthy();
    expect(
      screen.getByText("No configured risk signal was recorded."),
    ).toBeTruthy();
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

  it("shows conflict and missing statuses as explicit text", () => {
    renderPanel({
      ...PACK,
      submitted_facts: [
        ...PACK.submitted_facts,
        {
          field_name: "vehicle_use",
          field_label: "Vehicle use",
          field_type: "enum",
          value: "commute",
        },
      ],
      evidence: [
        ...PACK.evidence,
        {
          source_type: "extracted_field",
          document_id: "doc-1",
          field_name: "vehicle_use",
          field_label: "Vehicle use",
          field_type: "enum",
          value: "commercial",
          source_locator: "page:2",
          extraction_method: "fake",
          confidence: null,
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
      ],
    });

    expect(screen.getByText("Conflict")).toBeTruthy();
    expect(screen.getByText("Not found in documents")).toBeTruthy();
    expect(screen.getByText("Document only")).toBeTruthy();
  });

  it("shows extraction confidence when it is recorded", () => {
    renderPanel({
      ...PACK,
      evidence: PACK.evidence.map((item) =>
        item.source_type === "extracted_field"
          ? { ...item, confidence: 0.98 }
          : item,
      ),
    });

    expect(
      screen.getByText("Synthetic vehicle record · Line 1 · 98% confidence"),
    ).toBeTruthy();
  });

  it("tells two documents with the same name apart by title", () => {
    renderPanel({
      ...PACK,
      evidence: [
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
          source_type: "submitted_document",
          document_id: "doc-2",
          document_code: "vehicle_record",
          document_title: "Synthetic vehicle record",
          filename: "synthetic.pdf",
          content_type: "application/pdf",
          page_count: 1,
        },
      ],
    });

    expect(screen.getByText("Synthetic vehicle record (1)")).toBeTruthy();
    expect(screen.getByText("Synthetic vehicle record (2)")).toBeTruthy();
    expect(screen.queryByText(/#[0-9a-f]/i)).toBeNull();
  });

  it("never shows a storage path or raw field code as a heading", () => {
    renderPanel();

    expect(screen.queryByText(/case-1\/synthetic\.pdf/)).toBeNull();
    expect(screen.queryByText(/uploads/)).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "vehicle_age" }),
    ).toBeNull();
  });

  it("keeps raw codes inside the technical details disclosure", async () => {
    renderPanel();
    const user = userEvent.setup();

    await user.click(screen.getAllByText("Technical details")[0]);

    expect(screen.getAllByText("Field code").length).toBeGreaterThan(0);
    expect(screen.getAllByText("vehicle_age").length).toBeGreaterThan(0);
  });

  it("loads the source document with its PDF page", async () => {
    stubObjectUrl();
    vi.mocked(fetchReviewDocument).mockResolvedValue({
      blob: new Blob(["%PDF-1.4"], { type: "application/pdf" }),
      contentType: "application/pdf",
      filename: "synthetic.pdf",
    });
    renderPanel({
      ...PACK,
      evidence: PACK.evidence.map((item) =>
        item.source_type === "extracted_field"
          ? { ...item, source_locator: "page:2" }
          : item,
      ),
    });
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "View source" }));

    expect(fetchReviewDocument).toHaveBeenCalledWith(
      "session",
      "case-id",
      "doc-1",
    );
    const frame = await screen.findByTitle("Synthetic vehicle record");
    expect((frame as HTMLIFrameElement).src).toBe("blob:mock#page=2");
  });
});