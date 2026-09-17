// Underwriter queue, review, completion, audit, and evaluation calls.
import type {
  AuditEvent,
  CompletionResult,
  EvaluationSplit,
  EvaluationSummary,
  PermissionSummary,
  QueueItem,
  ReviewResult,
  ReviewStart,
  RoleRecord,
  UserRecord,
} from "./types";
import { request, requestBlob } from "./api-core";

// Load operations queue rows with safe optional filters.
export async function listQueue(
  token: string,
  status?: string,
  awaitingHandoff?: boolean,
  reconciliationStatus?: string,
): Promise<QueueItem[]> {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (awaitingHandoff) {
    params.set("awaiting_handoff", "true");
  }
  if (reconciliationStatus) {
    params.set("reconciliation_status", reconciliationStatus);
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

// Load one case document for the authenticated underwriter inline preview.
export async function fetchReviewDocument(
  token: string,
  caseId: string,
  documentId: string,
): Promise<{ blob: Blob; contentType: string; filename: string }> {
  return requestBlob(`/reviews/${caseId}/documents/${documentId}`, token);
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

// Load administrable users with their current role assignments.
export async function listUsers(token: string): Promise<UserRecord[]> {
  return request("/admin/users", token);
}

// Create one synthetic user with a single role assignment.
export async function createUser(
  token: string,
  payload: {
    email: string;
    display_name: string;
    password: string;
    role_id: string;
  },
): Promise<UserRecord> {
  return request("/admin/users", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Change one user's display name, active state, or role.
export async function updateUser(
  token: string,
  userId: string,
  payload: {
    display_name?: string;
    is_active?: boolean;
    role_id?: string;
  },
): Promise<UserRecord> {
  return request(`/admin/users/${userId}`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Load every configured role with its sorted permission scopes.
export async function listRoles(token: string): Promise<RoleRecord[]> {
  return request("/admin/roles", token);
}

// Create one configurable role from the fixed permission catalogue.
export async function createRole(
  token: string,
  payload: {
    code: string;
    title: string;
    description?: string;
    permissions: string[];
  },
): Promise<RoleRecord> {
  return request("/admin/roles", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Replace one role's metadata, active state, or complete scope list.
export async function updateRole(
  token: string,
  roleId: string,
  payload: {
    title?: string;
    description?: string;
    is_active?: boolean;
    permissions?: string[];
  },
): Promise<RoleRecord> {
  return request(`/admin/roles/${roleId}`, token, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// Load the fixed permission catalogue available to compose roles from.
export async function listPermissions(
  token: string,
): Promise<PermissionSummary[]> {
  return request("/admin/permissions", token);
}
