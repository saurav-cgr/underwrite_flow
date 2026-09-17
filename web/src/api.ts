import type {
  CaseConfiguration,
  CaseRecord,
  CaseSubmissionResult,
  Credentials,
  CurrentUser,
  DocumentRecord,
} from "./types";
import { request } from "./api-core";

export * from "./api-core";
export * from "./api-products";
export * from "./api-staff";

// Create a session for a synthetic demo account.
export async function createSession(
  email: string,
  password: string,
): Promise<Credentials> {
  return request("/auth/login", undefined, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

// Rotate the in-memory refresh credential for a new credential pair.
export async function refreshSession(
  refreshToken: string,
): Promise<Credentials> {
  return request("/auth/refresh", undefined, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

// Resolve the persisted identity and current scopes behind an access token.
export async function readSession(token: string): Promise<CurrentUser> {
  return request("/auth/me", token);
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

// Load the exact configuration version one case is pinned to.
export async function readCaseConfiguration(
  token: string,
  caseId: string,
): Promise<CaseConfiguration> {
  return request(`/cases/${caseId}/configuration`, token);
}

// Submit an owned case for evidence processing and human review.
export async function submitCase(
  token: string,
  caseId: string,
): Promise<CaseSubmissionResult> {
  return request(`/cases/${caseId}/submit`, token, { method: "POST" });
}

// Restart processing for a case the underwriter returned for information.
export async function resubmitCase(
  token: string,
  caseId: string,
): Promise<CaseSubmissionResult> {
  return request(`/cases/${caseId}/resubmit`, token, { method: "POST" });
}
