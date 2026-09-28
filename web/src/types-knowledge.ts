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
