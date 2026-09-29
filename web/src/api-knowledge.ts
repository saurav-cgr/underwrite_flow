// Administrator API calls for versioned guideline knowledge.
import { request } from "./api-core";
import type {
  KnowledgeImportResult,
  KnowledgePreview,
  KnowledgeVersion,
  GuidanceResponse,
} from "./types-knowledge";

// List guideline versions, newest first.
export function listKnowledgeVersions(
  token: string,
): Promise<KnowledgeVersion[]> {
  return request("/knowledge/versions?scope=guideline", token);
}

// Import one YAML document as a draft guideline version.
export function importKnowledge(
  token: string,
  yamlText: string,
): Promise<KnowledgeImportResult> {
  return request("/knowledge/import", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scope: "guideline", yaml: yamlText }),
  });
}

// Preview one version's bounded passages.
export function previewKnowledge(
  token: string,
  versionId: string,
  offset = 0,
  limit = 100,
): Promise<KnowledgePreview> {
  const query = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return request(
    `/knowledge/versions/${versionId}/preview?${query.toString()}`,
    token,
  );
}

// Activate one administrator-selected draft.
export function activateKnowledge(
  token: string,
  versionId: string,
): Promise<KnowledgeVersion> {
  return request(`/knowledge/versions/${versionId}/activate`, token, {
    method: "POST",
  });
}

// Read the stored explanation once for one underwriter review screen.
export function fetchGuidance(
  token: string,
  caseId: string,
): Promise<GuidanceResponse> {
  return request(`/reviews/${caseId}/guidance`, token);
}
