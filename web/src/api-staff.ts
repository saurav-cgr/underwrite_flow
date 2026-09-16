// Underwriter queue, review, completion, audit, and evaluation calls.
import type {
  AuditEvent,
  CompletionResult,
  EvaluationSplit,
  EvaluationSummary,
  QueueItem,
  ReviewResult,
  ReviewStart,
} from "./types";
import { request } from "./api-core";

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
