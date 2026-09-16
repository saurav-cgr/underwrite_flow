// Pure helpers that turn one review evidence pack into reviewer-facing cards.

import type {
  DocumentEvidence,
  EvidenceItem,
  ExtractedFieldEvidence,
  SubmittedFact,
} from "./types";

export type FactStatus =
  | "Consistent"
  | "Conflict"
  | "Not found in documents"
  | "Document only";

export interface ExtractedEntry {
  documentId: string | null;
  documentTitle: string;
  value: string;
  source: string;
  locator: string | null;
  confidence: number | null;
  status: string;
  extractionMethod: string;
}

export interface FactCard {
  fieldName: string;
  fieldLabel: string;
  fieldType: string;
  submittedValue: string | null;
  entries: ExtractedEntry[];
  status: FactStatus;
}

export interface DocumentCard {
  documentId: string;
  documentCode: string | null;
  title: string;
  filename: string;
  contentType: string;
  pageCount: number | null;
}

export interface RiskSignalRow {
  code: string;
  severity: string;
  explanation: string;
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

// Render a stored media type as a short reviewer-facing label.
export function contentTypeLabel(contentType: string): string {
  if (contentType === "application/pdf") return "PDF";
  if (contentType === "image/jpeg" || contentType === "image/jpg") {
    return "JPEG";
  }
  if (contentType === "image/png") return "PNG";
  const subtype = contentType.split("/")[1];
  return subtype ? subtype.toUpperCase() : "File";
}

// Render a stored page count as a readable suffix, or empty when unknown.
export function pageCountLabel(pageCount: number | null): string {
  if (pageCount === null || pageCount === undefined) return "";
  return `${pageCount} page${pageCount === 1 ? "" : "s"}`;
}

// Render a stored locator as reviewer-facing prose where the format is known.
export function sourceLabel(locator: string | null): string {
  if (!locator) return "—";
  const page = /^page:(\d+)$/i.exec(locator);
  if (page) return `Page ${page[1]}`;
  const line = /^line:(\d+)$/i.exec(locator);
  if (line) return `Line ${line[1]}`;
  return locator;
}

// Read the PDF page a page-style locator points at, when one exists.
export function pdfPageOf(locator: string | null): number | null {
  if (!locator) return null;
  const page = /^page:(\d+)$/i.exec(locator);
  return page ? Number(page[1]) : null;
}

// Return the uploaded documents as readable cards, disambiguating titles.
export function documentCards(evidence: EvidenceItem[]): DocumentCard[] {
  const cards = evidence
    .filter((item): item is DocumentEvidence =>
      item.source_type === "submitted_document")
    .map((item) => ({
      documentId: item.document_id,
      documentCode: item.document_code,
      title: item.document_title,
      filename: item.filename,
      contentType: item.content_type,
      pageCount: item.page_count,
    }));
  return dedupeTitles(cards);
}

// Resolve each submitted document id to its reviewer-facing title.
export function documentTitles(evidence: EvidenceItem[]): Map<string, string> {
  return new Map(
    documentCards(evidence).map((card) => [card.documentId, card.title]),
  );
}

// Group submitted facts and extracted values into one card per case field.
export function groupFacts(
  submitted: SubmittedFact[],
  evidence: EvidenceItem[],
): FactCard[] {
  const titles = documentTitles(evidence);
  const extracted = evidence.filter(
    (item): item is ExtractedFieldEvidence =>
      item.source_type === "extracted_field",
  );
  const byField = new Map<string, ExtractedFieldEvidence[]>();
  for (const item of extracted) {
    const list = byField.get(item.field_name) ?? [];
    list.push(item);
    byField.set(item.field_name, list);
  }

  const cards: FactCard[] = [];
  const seen = new Set<string>();
  for (const fact of submitted) {
    seen.add(fact.field_name);
    const entries = buildEntries(byField.get(fact.field_name) ?? [], titles);
    cards.push({
      fieldName: fact.field_name,
      fieldLabel: fact.field_label,
      fieldType: fact.field_type,
      submittedValue: displayValue(fact.value),
      entries,
      status: factStatus(entries),
    });
  }
  for (const [name, items] of byField) {
    if (seen.has(name)) continue;
    cards.push({
      fieldName: name,
      fieldLabel: items[0]?.field_label ?? name,
      fieldType: items[0]?.field_type ?? "unknown",
      submittedValue: null,
      entries: buildEntries(items, titles),
      status: "Document only",
    });
  }
  return cards;
}

// Derive one card status from backend conflict metadata and presence alone.
function factStatus(entries: ExtractedEntry[]): FactStatus {
  if (entries.length === 0) return "Not found in documents";
  if (entries.some((entry) => entry.status === "conflict")) return "Conflict";
  return "Consistent";
}

// Build the readable extracted rows that back one field.
function buildEntries(
  items: ExtractedFieldEvidence[],
  titles: Map<string, string>,
): ExtractedEntry[] {
  return items.map((item) => ({
    documentId: item.document_id,
    documentTitle:
      item.document_id
        ? titles.get(item.document_id) ?? "unknown document"
        : "unknown document",
    value: displayValue(item.value),
    source: sourceLabel(item.source_locator),
    locator: item.source_locator,
    confidence: item.confidence,
    status: item.conflict_status,
    extractionMethod: item.extraction_method,
  }));
}

// Disambiguate duplicate document titles with a readable ordinal suffix.
function dedupeTitles(cards: DocumentCard[]): DocumentCard[] {
  const counts = new Map<string, number>();
  for (const card of cards) {
    counts.set(card.title, (counts.get(card.title) ?? 0) + 1);
  }
  const seen = new Map<string, number>();
  return cards.map((card) => {
    if ((counts.get(card.title) ?? 0) === 1) return card;
    const index = (seen.get(card.title) ?? 0) + 1;
    seen.set(card.title, index);
    return { ...card, title: `${card.title} (${index})` };
  });
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
