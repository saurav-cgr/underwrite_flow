import type {
  AuditEvent,
  CaseRecord,
  CompletionResult,
  DocumentRecord,
  EvaluationSplit,
  EvaluationSummary,
  ProductCatalogItem,
  ProductConfigurationChange,
  ProductConfigurationItem,
  ProductConfigurationPreview,
  ProductVersionHistoryItem,
  QueueItem,
  ReviewResult,
  ReviewStart,
  Role,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;
  retryable: boolean;
  requestId: string | undefined;

  // Preserve safe status information for inline UI error states.
  constructor(
    status: number,
    message: string,
    code = "http_error",
    retryable = false,
    requestId?: string,
  ) {
    super(message);
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.requestId = requestId;
  }
}

// Read the sanitized {error: {…}} envelope, tolerating other error bodies.
export function parseErrorBody(status: number, body: unknown): ApiError {
  const envelope = (body ?? {}) as {
    error?: {
      code?: string;
      message?: string;
      request_id?: string;
      retryable?: boolean;
    };
    detail?: unknown;
    message?: unknown;
  };
  const inner = envelope.error;
  const fallback = typeof envelope.detail === "string"
    ? envelope.detail
    : typeof envelope.message === "string"
      ? envelope.message
      : undefined;
  const message = typeof inner?.message === "string"
    ? inner.message
    : fallback ?? "The request could not be completed.";
  return new ApiError(
    status,
    message,
    inner?.code ?? "http_error",
    inner?.retryable ?? false,
    inner?.request_id,
  );
}

let unauthorizedHandler: (() => void) | null = null;

// Register the single recovery path used when a session stops being valid.
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
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
    // An expired token is recoverable: let the shell offer a fresh sign-in.
    if (response.status === 401 && token) unauthorizedHandler?.();
    const body = await response.json().catch(() => undefined);
    throw parseErrorBody(response.status, body);
  }
  if (response.status === 204) return undefined as T;
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

// Load all product configurations visible to an administrator.
export async function listProductConfigurations(
  token: string,
): Promise<ProductConfigurationItem[]> {
  return request("/products", token);
}

// Load immutable version history for one selected product configuration.
export async function listProductVersionHistory(
  token: string,
  productCode: string,
): Promise<ProductVersionHistoryItem[]> {
  return request(`/products/${encodeURIComponent(productCode)}/history`, token);
}

// Validate product YAML without persisting a configuration version.
export async function validateProductConfiguration(
  token: string,
  yamlText: string,
): Promise<Pick<ProductConfigurationChange, "product_code" | "version">> {
  return request("/products/validate", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Preview normalized configuration counts without changing persisted products.
export async function previewProductConfiguration(
  token: string,
  yamlText: string,
): Promise<ProductConfigurationPreview> {
  return request("/products/preview", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Import validated YAML as a draft configuration version.
export async function importProductConfiguration(
  token: string,
  yamlText: string,
): Promise<ProductConfigurationChange> {
  return request("/products/import", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yaml_text: yamlText }),
  });
}

// Activate one imported product version after administrator confirmation.
export async function activateProductConfiguration(
  token: string,
  productCode: string,
  version: string,
): Promise<ProductConfigurationChange> {
  return request(
    `/products/${encodeURIComponent(productCode)}/activate`,
    token,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    },
  );
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
  documentCode: string,
  file: File,
): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("document", file);
  form.append("document_code", documentCode);
  return request(`/cases/${caseId}/documents`, token, {
    method: "POST",
    body: form,
  });
}

// Remove one pre-review document selected by the applicant.
export async function removeDocument(
  token: string,
  caseId: string,
  documentId: string,
): Promise<void> {
  await request(`/cases/${caseId}/documents/${documentId}`, token, {
    method: "DELETE",
  });
}

// Load every case owned by the authenticated identity.
export async function listCases(token: string): Promise<CaseRecord[]> {
  return request("/cases", token);
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
  awaitingHandoff?: boolean,
): Promise<QueueItem[]> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (awaitingHandoff) {
    params.set("awaiting_handoff", "true");
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
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
    specialist_label?: string;
    reason?: string;
    evidence_acknowledged: boolean;
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

// Run the synthetic reference set and return its aggregate metrics.
export async function runEvaluation(
  token: string,
  split?: EvaluationSplit,
): Promise<EvaluationSummary> {
  return request("/evaluation/run", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ split: split ?? null }),
  });
}
