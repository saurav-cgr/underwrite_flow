import { useEffect, useState } from "react";

import { ApiError } from "./api-core";
import {
  activateKnowledge,
  importKnowledge,
  listKnowledgeVersions,
  previewKnowledge,
} from "./api-knowledge";
import { Badge, Button, EmptyState, PageHeading, Panel } from "./components";
import type {
  KnowledgeImportResult,
  KnowledgePreview,
  KnowledgeVersion,
} from "./types-knowledge";

const PREVIEW_PAGE_SIZE = 100;

// Render administrator import, preview, and activation controls.
export function KnowledgeAdmin({ token }: { token: string }) {
  const [versions, setVersions] = useState<KnowledgeVersion[]>([]);
  const [selected, setSelected] = useState<KnowledgeVersion | null>(null);
  const [preview, setPreview] = useState<KnowledgePreview | null>(null);
  const [yamlText, setYamlText] = useState("");
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState(false);
  const [previewOffset, setPreviewOffset] = useState(0);

  // Load current guideline versions for administrator review.
  useEffect(() => {
    listKnowledgeVersions(token)
      .then(setVersions)
      .catch((error) => setMessage(errorMessage(error)));
  }, [token]);

  // Convert API failures into one bounded message for the screen.
  function errorMessage(error: unknown): string {
    return error instanceof ApiError
      ? error.message
      : "Knowledge operation could not be completed.";
  }

  // Reload versions after an import or activation changes their state.
  async function refreshVersions(): Promise<KnowledgeVersion[]> {
    const next = await listKnowledgeVersions(token);
    setVersions(next);
    return next;
  }

  // Import YAML as a draft and show its validation report.
  async function handleImport() {
    if (!yamlText.trim()) return;
    setWorking(true);
    setMessage("");
    setNotice("");
    try {
      const result: KnowledgeImportResult = await importKnowledge(
        token,
        yamlText,
      );
      setSelected(result);
      setPreview(null);
      await refreshVersions();
      setNotice(`Imported ${result.version} as draft.`);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setWorking(false);
    }
  }

  // Load one preview page for the selected version.
  async function handlePreview(
    version: KnowledgeVersion,
    offset = 0,
  ) {
    setSelected(version);
    setMessage("");
    try {
      setPreviewOffset(offset);
      setPreview(
        await previewKnowledge(
          token,
          version.id,
          offset,
          PREVIEW_PAGE_SIZE,
        ),
      );
    } catch (error) {
      setMessage(errorMessage(error));
    }
  }

  // Activate the selected draft through the administrator API.
  async function handleActivate() {
    if (!selected) return;
    setWorking(true);
    setMessage("");
    try {
      const result = await activateKnowledge(token, selected.id);
      setSelected(result);
      await refreshVersions();
      setNotice(`${result.version} is active.`);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="Administrator workspace"
        title="Knowledge store"
        description={
          "Import, inspect, and activate synthetic guideline versions."
        }
      />
      {message ? <p className="form-error" role="alert">{message}</p> : null}
      {notice ? <p className="form-notice" role="status">{notice}</p> : null}
      <div className="admin-grid">
        <Panel title="Import guideline YAML">
          <label className="field" htmlFor="knowledge-yaml">
            <span>Guideline YAML</span>
            <textarea
              id="knowledge-yaml"
              onChange={(event) => setYamlText(event.target.value)}
              rows={8}
              value={yamlText}
            />
          </label>
          <Button disabled={working} onClick={() => void handleImport()}>
            Import draft
          </Button>
        </Panel>
        <Panel title="Version history">
          {versions.length === 0 ? (
            <EmptyState
              title="No guideline versions"
              detail="Import a synthetic guideline YAML to begin."
            />
          ) : (
            <ul aria-label="Knowledge versions" className="mini-list">
              {versions.map((version) => (
                <li key={version.id}>
                  <button
                    aria-pressed={selected?.id === version.id}
                    className="product-config-row"
                    onClick={() => void handlePreview(version)}
                    type="button"
                  >
                    <span>
                      <strong>{version.version}</strong>
                      <small>{version.product_code}</small>
                    </span>
                    <Badge tone={version.status}>{version.status}</Badge>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
      {preview ? (
        <Panel title={`Preview ${preview.version.version}`}>
          <p className="muted">
            {preview.validation.valid
              ? "Validation passed."
              : "Validation issues found."}
          </p>
          {!preview.validation.valid ? (
            <ul aria-label="Validation issues">
              {preview.validation.issues.map((issue, index) => (
                <li key={`${String(issue.code)}-${index}`}>
                  {String(issue.code ?? "validation issue")}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mini-list">
            {preview.passages.map((passage) => (
              <article key={passage.passage_key} className="mini-row">
                <div>
                  <strong>{passage.title}</strong>
                  <p>{passage.body}</p>
                  <small>{passage.label}</small>
                </div>
              </article>
            ))}
          </div>
          <div>
            <Button
              disabled={working || previewOffset === 0}
              onClick={() =>
                void handlePreview(
                  preview.version,
                  previewOffset - PREVIEW_PAGE_SIZE,
                )
              }
            >
              Previous passages
            </Button>
            <Button
              disabled={
                working ||
                previewOffset + preview.passages.length >=
                  preview.version.passage_count
              }
              onClick={() =>
                void handlePreview(
                  preview.version,
                  previewOffset + PREVIEW_PAGE_SIZE,
                )
              }
            >
              Next passages
            </Button>
          </div>
          <Button
            disabled={working || selected?.status !== "draft"}
            onClick={() => void handleActivate()}
          >
            Activate selected version
          </Button>
        </Panel>
      ) : null}
    </>
  );
}
