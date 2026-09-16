// Pure helpers that turn one review evidence pack into reviewer-facing rows.

export interface DocumentRow {
  documentId: string;
  filename: string;
  source: string;
}

export interface FieldRow {
  documentId: string;
  field: string;
  value: string;
  source: string;
}

export interface RiskSignalRow {
  code: string;
  severity: string;
  explanation: string;
}

export interface ConflictRow {
  field: string;
  value: string;
  documentId: string;
  source: string;
  status: string;
}

// Render one evidence value as short readable text.
export function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "not provided";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "structured value";
}

// Read the machine reason recorded anywhere inside one failure payload.
export function failureReason(payload: unknown, depth = 0): string {
  if (depth > 3 || typeof payload !== "object" || payload === null) {
    return "recorded failure";
  }
  const record = payload as Record<string, unknown>;
  for (const key of ["reason", "error_code"]) {
    if (typeof record[key] === "string") return record[key] as string;
  }
  if ("details" in record) return failureReason(record.details, depth + 1);
  return "recorded failure";
}

// Read the stored locator of one evidence entry.
function locatorOf(item: Record<string, unknown>): string {
  return typeof item.source_locator === "string"
    ? item.source_locator
    : "no locator recorded";
}

// List the submitted documents named in the review evidence pack.
export function evidenceDocuments(
  evidence: Record<string, unknown>[],
): DocumentRow[] {
  return evidence
    .filter(
      (item) =>
        item.source_type === "submitted_document"
        && typeof item.filename === "string",
    )
    .map((item) => ({
      documentId: String(item.document_id ?? ""),
      filename: item.filename as string,
      source: locatorOf(item),
    }));
}
// Label each document once, disambiguating files that share a filename so two
// rows never read identically.
export function documentLabels(
  documents: DocumentRow[],
): Map<string, string> {
  const counts = new Map<string, number>();
  for (const document of documents) {
    counts.set(document.filename, (counts.get(document.filename) ?? 0) + 1);
  }
  return new Map(
    documents.map((document) => {
      const unique = counts.get(document.filename) === 1;
      const label =
        unique || !document.documentId
          ? document.filename
          : `${document.filename} #${document.documentId.slice(0, 8)}`;
      return [document.documentId, label];
    }),
  );
}
// List the extracted fields with their value and provenance.
export function evidenceFields(
  evidence: Record<string, unknown>[],
): FieldRow[] {
  return evidence
    .filter(
      (item) =>
        item.source_type === "extracted_field"
        && typeof item.field_name === "string",
    )
    .map((item) => ({
      documentId: String(item.document_id ?? ""),
      field: item.field_name as string,
      value: displayValue(item.value),
      source: locatorOf(item),
    }));
}

// List the recorded field conflicts with their value and provenance.
export function conflictRows(
  conflicts: Record<string, unknown>[],
): ConflictRow[] {
  return conflicts.map((conflict) => ({
    field:
      typeof conflict.field_name === "string"
        ? conflict.field_name
        : "unnamed field",
    value: displayValue(conflict.value),
    documentId: String(conflict.document_id ?? ""),
    source: locatorOf(conflict),
    status:
      typeof conflict.conflict_status === "string"
        ? conflict.conflict_status
        : "conflict",
  }));
}

// Read configured risk signals from the assembled case summary.
export function riskSignals(summary: unknown): RiskSignalRow[] {
  if (typeof summary !== "object" || summary === null) return [];
  const value = (summary as Record<string, unknown>).risk_signals;
  if (!Array.isArray(value)) return [];
  return value
    .filter(
      (item): item is Record<string, unknown> =>
        typeof item === "object" && item !== null,
    )
    .map((item) => ({
      code: typeof item.code === "string" ? item.code : "unnamed signal",
      severity: typeof item.severity === "string" ? item.severity : "high",
      explanation:
        typeof item.explanation === "string" ? item.explanation : "",
    }));
}

// List the requested fields the extracted evidence never supplied, which the
// top-level response reports separately as outstanding document codes.
export function missingFields(summary: unknown): string[] {
  if (typeof summary !== "object" || summary === null) return [];
  const value = (summary as Record<string, unknown>).missing_information;
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}
