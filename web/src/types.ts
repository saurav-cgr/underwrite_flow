export type Role = "Applicant" | "Underwriter" | "Administrator";

export type Screen =
  | "dashboard"
  | "products"
  | "application"
  | "documents"
  | "tracking"
  | "queue"
  | "review"
  | "admin";

export interface Session {
  token: string;
  role: Role;
  sub: string;
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

export interface ProductDocument {
  code: string;
  title: string;
  requirement: "required" | "optional" | "conditional" | "not_applicable";
  accepted_types: string[];
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
}

export interface CaseRecord {
  id: string;
  product_code: string;
  product_version: string;
  rulebook_version: string;
  status: string;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  content_type: string;
  byte_size: number;
  content_hash: string;
  page_count: number | null;
}

export interface QueueItem {
  case_id: string;
  product_code: string;
  status: string;
  route: string | null;
  specialist: boolean;
}

export interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  event_type: string;
  details: Record<string, unknown>;
  occurred_at: string;
}

export interface Recommendation {
  route: string;
  reasons?: string[];
  summary?: Record<string, unknown>;
}

export interface ReviewStart {
  case_id: string;
  status: "awaiting_human_review";
  recommendation: Recommendation;
}

export interface ReviewResult {
  case_id: string;
  action: "confirm" | "override" | "request_information";
  selected_route: string | null;
  status: "confirmed" | "overridden" | "needs_information" | "manual_review";
}

export interface CompletionResult {
  handoff_id: string;
  case_id: string;
  route: "specialist" | "standard" | "expedited";
  status: "completed";
}
