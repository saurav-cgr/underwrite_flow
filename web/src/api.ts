import type {
  AuditEvent,
  CaseRecord,
  CompletionResult,
  DocumentRecord,
  EvaluationSummary,
  ProductCatalogItem,
  QueueItem,
  ReviewResult,
  ReviewStart,
  Role,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  status: number;

  // Preserve safe status information for inline UI error states.
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Call one typed API endpoint and normalize safe error text.
async function request<T>(
  path: string,
  token: string | undefined,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: string;
    };
    throw new ApiError(
      response.status,
      body.detail ?? "The request could not be completed.",
    );
  }
  return (await response.json()) as T;
}

// Create a short-lived session for a synthetic demo account.
export async function createSession(
  email: string,
  password: string,
): Promise<{ token: string; expires_in: number }> {
  return request("/auth/session", undefined, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

// Resolve the persisted role behind a signed session.
export async function readSession(
  token: string,
): Promise<{ sub: string; role: Role }> {
  return request("/auth/me", token);
}

// Load active product fields from the backend-owned catalog.
export async function listCatalog(
  token: string,
): Promise<ProductCatalogItem[]> {
  return request("/products/catalog", token);
}

// Create an applicant case with all configured document codes.
export async function createCase(
  token: string,
  payload: {
    product_code: string;
    idempotency_key: string;
    payload: Record<string, unknown>;
    document_codes: string[];
  },
): Promise<CaseRecord> {
  return request("/cases", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Upload one synthetic document and return safe stored metadata.
export async function uploadDocument(
  token: string,
  caseId: string,
  file: File,
): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("document", file);
  return request(`/cases/${caseId}/documents`, token, {
    method: "POST",
    body: form,
  });
}

// Load one case visible to the current role.
export async function readCase(
  token: string,
  caseId: string,
): Promise<CaseRecord> {
  return request(`/cases/${caseId}`, token);
}

// Load safe document metadata for one visible case.
export async function listDocuments(
  token: string,
  caseId: string,
): Promise<DocumentRecord[]> {
  return request(`/cases/${caseId}/documents`, token);
}

// Load operations queue rows with safe optional filters.
export async function listQueue(
  token: string,
  status?: string,
): Promise<QueueItem[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/queues${query}`, token);
}

// Start a review checkpoint for one queued case.
export async function startReview(
  token: string,
  caseId: string,
): Promise<ReviewStart> {
  return request(`/reviews/${caseId}/start`, token, { method: "POST" });
}

// Persist one underwriter command at the human review checkpoint.
export async function submitReview(
  token: string,
  caseId: string,
  command: {
    action: "confirm" | "override" | "request_information";
    selected_route?: string;
    reason?: string;
  },
): Promise<ReviewResult> {
  return request(`/reviews/${caseId}`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(command),
  });
}

// Complete a confirmed route exactly once.
export async function completeCase(
  token: string,
  caseId: string,
): Promise<CompletionResult> {
  return request(`/completion/${caseId}`, token, { method: "POST" });
}

// Load immutable audit events for administrator inspection.
export async function listAudit(
  token: string,
  caseId: string,
): Promise<AuditEvent[]> {
  return request(`/audit/cases/${caseId}`, token);
}

// Load safe aggregate evaluation metrics for the administrator workspace.
export async function getEvaluationSummary(
  token: string,
): Promise<EvaluationSummary> {
  return request("/evaluation/summary", token);
}
