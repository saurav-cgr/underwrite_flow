// Administrator API calls for versioned guideline knowledge.
import { request } from "./api-core";
import type {
  CaseQuestion,
  KnowledgeImportResult,
  KnowledgePreview,
  KnowledgeVersion,
  GuidanceResponse,
  PassageGuidance,
  RegulationImportResult,
  RegulationTags,
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

// List regulation versions, newest first.
export function listRegulationVersions(
  token: string,
): Promise<KnowledgeVersion[]> {
  return request("/knowledge/versions?scope=regulation", token);
}

// Import the manifest folder, storing one approved upload first if given.
export function importRegulation(
  token: string,
  file?: File,
): Promise<RegulationImportResult> {
  const body = new FormData();
  if (file) body.append("file", file);
  return request("/knowledge/regulation/import", token, {
    method: "POST",
    body,
  });
}

// Accept administrator topic tags on one regulation draft clause.
export function acceptRegulationTags(
  token: string,
  versionId: string,
  passageKey: string,
  topicTags: string[],
): Promise<RegulationTags> {
  return request(
    `/knowledge/versions/${versionId}/passages/` +
      `${encodeURIComponent(passageKey)}/tags`,
    token,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic_tags: topicTags }),
    },
  );
}

// Read one pinned passage beside its related regulation clauses.
export function fetchPassageGuidance(
  token: string,
  caseId: string,
  passageKey: string,
): Promise<PassageGuidance> {
  return request(
    `/reviews/${caseId}/guidance/passages/` +
      `${encodeURIComponent(passageKey)}`,
    token,
  );
}

// Read every underwriter's questions for one case, oldest first.
export function listQuestions(
  token: string,
  caseId: string,
): Promise<CaseQuestion[]> {
  return request(`/reviews/${caseId}/questions`, token);
}

// Ask one question answered only from the case's pinned guidance.
export function askQuestion(
  token: string,
  caseId: string,
  question: string,
): Promise<CaseQuestion> {
  return request(`/reviews/${caseId}/questions`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
}
