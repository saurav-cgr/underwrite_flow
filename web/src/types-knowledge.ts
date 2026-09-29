// Typed administrator contracts for versioned guideline knowledge.
export interface KnowledgeVersion {
  id: string;
  scope: string;
  product_code: string | null;
  version: string;
  status: string;
  content_type: string;
  passage_count: number;
  validation?: { valid: boolean; issues: Record<string, unknown>[] };
  activated_at: string | null;
}

export interface KnowledgePassage {
  passage_key: string;
  title: string;
  topic: string;
  bands: Record<string, number | null>;
  label: string;
  body: string;
  thresholds: Record<string, unknown>[];
  topic_tags: string[];
  suggested_tags: string[];
  limits: Record<string, unknown>[];
}

export interface KnowledgePreview {
  version: KnowledgeVersion;
  validation: { valid: boolean; issues: Record<string, unknown>[] };
  passages: KnowledgePassage[];
}

export interface KnowledgeImportResult extends KnowledgeVersion {
  validation: { valid: boolean; issues: Record<string, unknown>[] };
}

export interface GuidanceCitation {
  version: string;
  passage_key: string;
}

export interface MissingGuidanceItem {
  item: string;
  reason: string;
  citations: GuidanceCitation[];
}

export interface RouteExplanation {
  status: "generated" | "template" | "unavailable";
  text: string;
  missing_items: MissingGuidanceItem[];
  citations: GuidanceCitation[];
  label: string;
}

export interface SpecialistBriefData {
  evidence: {
    field_name: string;
    value: unknown;
    document: string | null;
    source_locator: string;
  }[];
  rules: string[];
  passages: {
    title: string;
    body: string;
    citation: GuidanceCitation;
  }[];
  label: string;
}

export interface GuidanceResponse {
  pinned: {
    guideline_version: string | null;
    regulation_version: string | null;
  };
  route_explanation: RouteExplanation;
  specialist_brief: SpecialistBriefData | null;
  suggested_citations: GuidanceCitation[];
}

export interface CaseQuestion {
  id: string;
  question: string;
  answer: string;
  covered: boolean;
  citations: GuidanceCitation[];
  asked_by: string;
  created_at: string;
}
