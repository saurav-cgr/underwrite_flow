export type Role = "Applicant" | "Underwriter" | "Administrator";

export type JourneyType = "new_business" | "renewal";

// Stable lowercase role codes owned by the backend's database-backed RBAC.
const ROLE_LABELS: Record<string, Role> = {
  applicant: "Applicant",
  underwriter: "Underwriter",
  administrator: "Administrator",
};

// Resolve a role code to its screen label, or null when it is unsupported.
export function roleLabelFor(code: string): Role | null {
  return ROLE_LABELS[code] ?? null;
}

export interface Credentials {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
}

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string;
  role: { id: string; code: string };
  permissions: string[];
}

export type Screen =
  | "dashboard"
  | "journey"
  | "products"
  | "application"
  | "documents"
  | "tracking"
  | "queue"
  | "review"
  | "admin"
  | "product_config";

export interface PermissionSummary {
  code: string;
  title: string;
  description: string | null;
}

export interface UserRecord {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  role: { id: string; code: string } | null;
  created_at: string;
}

export interface RoleRecord {
  id: string;
  code: string;
  title: string;
  description: string | null;
  is_active: boolean;
  is_system: boolean;
  permissions: string[];
}

export interface Session {
  token: string;
  refreshToken: string;
  role: Role;
  sub: string;
  email: string;
  permissions: string[];
}

export interface ProductField {
  key: string;
  label: string;
  type: "text" | "integer" | "number" | "date" | "boolean" | "enum";
  required: boolean;
  help_text: string;
  validation: Record<string, number>;
  options: string[];
  visible_when?: { field: string; equals?: unknown };
}

export type DocumentStage = "prior_policy" | "supporting";

export interface ProductDocument {
  code: string;
  title: string;
  requirement: "required" | "optional" | "conditional" | "not_applicable";
  accepted_types: string[];
  stage: DocumentStage;
}

export interface ProductCatalogItem {
  product_code: string;
  title: string;
  family: string;
  scope: string;
  description: string;
  version: string;
  fields: ProductField[];
  documents: ProductDocument[];
  supported_journeys: JourneyType[];
}

export interface ProductConfigurationItem {
  product_code: string;
  title: string;
  family: string;
  status: string;
  active_version: string | null;
}

export interface ProductVersionHistoryItem {
  version: string;
  status: string;
  content_hash: string;
  activated_at: string | null;
}

export type ReconciliationKind =
  | "ncb_match"
  | "asset_match"
  | "policy_lapse";

export interface ReconciliationDefinition {
  code: string;
  kind: ReconciliationKind;
  inputs: Record<string, string>;
}

export interface ProductConfigurationPreview {
  product_code: string;
  version: string;
  status: string;
  field_count: number;
  document_count: number;
  routing_rule_count: number;
  reconciliation_count: number;
  reconciliations: ReconciliationDefinition[];
  specialist_labels: string[];
}

export interface ProductConfigurationChange {
  product_code: string;
  version: string;
  status: string;
}

export interface CaseRecord {
  id: string;
  product_code: string;
  product_version: string;
  rulebook_version: string;
  status: string;
  journey: JourneyType;
}

export interface DocumentRecord {
  id: string;
  document_code: string | null;
  filename: string;
  content_type: string;
  byte_size: number;
  content_hash: string;
  page_count: number | null;
}

export type ReconciliationStatus =
  | "CLEARED"
  | "FLAGGED_DISCREPANCY"
  | "MISSING_EVIDENCE"
  | "";

export interface ReconciliationReference {
  document_id: string;
  source_locator: string;
}

export interface ReconciliationComparison {
  field_key: string;
  left: unknown;
  right: unknown;
  matched: boolean;
  evidence: ReconciliationReference[];
  explanation_code: string;
  confidence_source: string;
}

export interface ReconciliationCheck {
  check_code: string;
  kind: ReconciliationKind;
  status: ReconciliationStatus;
  comparisons: ReconciliationComparison[];
  discrepancies: Record<string, unknown>[];
  evidence: ReconciliationReference[];
  missing_inputs: string[];
  rule_version: string;
}

export interface QueueItem {
  case_id: string;
  product_code: string;
  journey: JourneyType;
  status: string;
  route: string | null;
  selected_route: string | null;
  specialist_label: string | null;
  specialist: boolean;
  awaiting_handoff: boolean;
  reconciliation_status: ReconciliationStatus;
  discrepancy_count: number;
  missing_evidence_count: number;
}

export interface ProviderCall {
  document_id: string | null;
  document_code: string | null;
  provider: string | null;
  model: string | null;
  attempts: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  usage_unavailable: boolean;
  request_hash: string | null;
  result_hash: string | null;
  error_code: string | null;
}

export interface AuditEvent {
  id: string;
  case_id: string | null;
  actor_user_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  occurred_at: string;
  supersedes_event_id: string | null;
}

export type EvaluationSplit = "development" | "holdout";

export interface EvaluationSummary {
  case_count: number;
  development_count: number;
  holdout_count: number;
  route_counts: Record<string, number>;
  routable_count: number;
  needs_information_count: number;
  route_agreement: number;
  specialist_recall: number;
  evidence_accuracy: number;
  conflict_detection: number;
  conflict_precision: number;
  missing_data_detection: number;
  missing_precision: number;
  unsupported_claim_rate: number;
  workflow_reliability: number;
  split: string;
  trace_sent: boolean;
}

export interface Recommendation {
  route: string;
  factors?: string[];
  summary?: Record<string, unknown>;
}

export type EvidenceFieldType =
  | "text"
  | "integer"
  | "number"
  | "date"
  | "boolean"
  | "enum"
  | "unknown";

export interface SubmittedFact {
  field_name: string;
  field_label: string;
  field_type: EvidenceFieldType;
  value: unknown;
}

export interface DocumentEvidence {
  source_type: "submitted_document";
  document_id: string;
  document_code: string | null;
  document_title: string;
  filename: string;
  content_type: string;
  page_count: number | null;
}

export interface ExtractedFieldEvidence {
  source_type: "extracted_field";
  document_id: string | null;
  field_name: string;
  field_label: string;
  field_type: EvidenceFieldType;
  value: unknown;
  source_locator: string | null;
  extraction_method: string;
  confidence: number | null;
  conflict_status: "clear" | "conflict";
}

export type EvidenceItem = DocumentEvidence | ExtractedFieldEvidence;

export interface ConflictEvidence {
  field_name: string;
  value: unknown;
  document_id: string | null;
  source_locator: string | null;
  conflict_status: string;
}

export interface ReviewStart {
  case_id: string;
  journey: JourneyType;
  status: "awaiting_human_review";
  recommendation: Recommendation;
  summary: Record<string, unknown>;
  submitted_facts: SubmittedFact[];
  evidence: EvidenceItem[];
  conflicts: ConflictEvidence[];
  missing_information: string[];
  reconciliation: ReconciliationCheck[];
  extraction_failures: Record<string, unknown>[];
  specialist_options: string[];
}

export interface ReviewResult {
  case_id: string;
  journey: JourneyType;
  action: "confirm" | "override" | "request_information";
  selected_route: string | null;
  status: "confirmed" | "overridden" | "needs_information" | "manual_review";
}

export interface CompletionResult {
  handoff_id: string;
  case_id: string;
  journey: JourneyType;
  route: "specialist" | "standard" | "expedited";
  specialist_label: string | null;
  status: "completed";
}

export interface CaseSubmissionResult {
  id: string;
  status: string;
  recommendation: Recommendation;
}

export interface ResolvedDocument {
  code: string;
  title: string;
  requirement: "required" | "optional" | "conditional" | "not_applicable";
  required: boolean;
  accepted_types: string[];
  condition: Record<string, unknown> | null;
  stage: DocumentStage;
}

export interface CaseConfiguration {
  case_id: string;
  product_code: string;
  product_version: string;
  rulebook_version: string;
  journey: JourneyType;
  fields: ProductField[];
  documents: ResolvedDocument[];
}

export interface ReferenceDocument {
  id: string;
  version: string;
  filename: string;
  content_type: string;
  byte_size: number;
  content_hash: string;
  page_count: number | null;
}
