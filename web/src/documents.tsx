import { useEffect, useState } from "react";

import {
  ApiError,
  listDocuments,
  removeDocument,
  resubmitCase,
  submitCase,
  uploadDocument,
} from "./api";
import { Button, Journey, PageHeading } from "./components";
import { ConfirmDialog } from "./confirm";
import { Icon } from "./icons";
import {
  intakeActionFor,
  requiredDocuments,
  satisfiedRequirementCount,
} from "./ui-state";
import type {
  CaseConfiguration,
  CaseRecord,
  DocumentRecord,
  DocumentStage,
  ResolvedDocument,
  Screen,
} from "./types";

// Render one resolved document request and its upload control.
function DocumentRequestRow({
  document,
  uploading,
  onUpload,
}: {
  document: ResolvedDocument;
  uploading: boolean;
  onUpload: (documentCode: string, file: File | undefined) => void;
}) {
  return (
    <div className="document-item">
      <span aria-hidden="true" className="file-tile">
        <Icon name="file" />
      </span>
      <span className="doc-copy">
        <b>{document.title}</b>
        <small>
          {document.required ? "Required" : "Optional or conditional"}
        </small>
      </span>
      <label className="upload-button">
        <input
          accept={document.accepted_types.join(",")}
          aria-label={`Upload ${document.title}`}
          disabled={uploading}
          onChange={(event) =>
            onUpload(document.code, event.target.files?.[0])
          }
          type="file"
        />
        {uploading ? "Uploading…" : "Choose file"}
      </label>
    </div>
  );
}

// Let applicants upload supporting documents and submit the case for review.
export function DocumentsScreen({
  configuration,
  caseRecord,
  token,
  onNavigate,
  onCaseChange,
  stageFilter,
  onContinue,
  continueLabel,
}: {
  configuration: CaseConfiguration;
  caseRecord: CaseRecord;
  token: string;
  onNavigate: (screen: Screen) => void;
  onCaseChange: (caseRecord: CaseRecord) => void;
  stageFilter?: DocumentStage;
  onContinue?: () => void;
  continueLabel?: string;
}) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [removingDocumentId, setRemovingDocumentId] = useState<string | null>(
    null,
  );
  const [pendingRemoval, setPendingRemoval] =
    useState<DocumentRecord | null>(null);
  const inStage = (document: ResolvedDocument) =>
    !stageFilter || document.stage === stageFilter;
  const required = requiredDocuments(configuration.documents).filter(inStage);
  const otherDocuments = configuration.documents.filter(
    (document) =>
      !document.required
      && document.requirement !== "not_applicable"
      && inStage(document),
  );
  const receivedCount = satisfiedRequirementCount(
    required,
    documents.map((document) => document.document_code),
  );
  const completion =
    required.length === 0
      ? 100
      : Math.round((receivedCount / required.length) * 100);
  const intake = onContinue ? null : intakeActionFor(caseRecord.status);
  const ready = required.every((document) =>
    documents.some((stored) => stored.document_code === document.code),
  );

  // Load current document metadata when the screen opens.
  useEffect(() => {
    listDocuments(token, caseRecord.id)
      .then(setDocuments)
      .catch(() => setMessage("Documents could not be loaded."));
  }, [caseRecord.id, token]);

  // Upload one selected file and refresh the safe metadata list.
  async function handleUpload(documentCode: string, file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const document = await uploadDocument(
        token,
        caseRecord.id,
        documentCode,
        file,
      );
      setDocuments((current) => [...current, document]);
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The document could not be uploaded.",
      );
    } finally {
      setUploading(false);
    }
  }

  // Submit or resubmit the case and report the recorded status upward.
  async function handleIntake(kind: "submit" | "resubmit") {
    setSubmitting(true);
    setMessage("");
    try {
      const result = kind === "submit"
        ? await submitCase(token, caseRecord.id)
        : await resubmitCase(token, caseRecord.id);
      onCaseChange({ ...caseRecord, status: result.status });
      onNavigate("tracking");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The case could not be submitted.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  // Ask before removing a document the applicant already uploaded.
  function requestRemoval(document: DocumentRecord) {
    setPendingRemoval(document);
  }

  // Remove the confirmed document and prompt for a replacement.
  async function confirmRemoval() {
    const document = pendingRemoval;
    if (document === null) return;
    setPendingRemoval(null);
    setRemovingDocumentId(document.id);
    setMessage("");
    try {
      await removeDocument(token, caseRecord.id, document.id);
      setDocuments((current) =>
        current.filter((currentDocument) => currentDocument.id !== document.id),
      );
      setMessage("Document removed. Choose the correct file to replace it.");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The document could not be removed.",
      );
    } finally {
      setRemovingDocumentId(null);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow={
          stageFilter === "prior_policy"
            ? "Prior policy"
            : "Supporting evidence"
        }
        title={
          stageFilter === "prior_policy"
            ? "Upload your existing policy."
            : "Add your documents."
        }
        description={
          "Upload synthetic files only. The review team sees metadata and "
          + "evidence links, not hidden browser state."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("tracking")}>
            View tracking
          </Button>
        }
      />
      <Journey current={1} />
      <div className="document-summary">
        <div>
          <b>Supporting evidence</b>
          <small>
            {receivedCount} of {required.length} requested documents received.
          </small>
        </div>
        <div
          aria-label="Document completion"
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={completion}
          className={
            completion === 100 ? "score-ring complete" : "score-ring"
          }
          role="progressbar"
        >
          {completion}%
        </div>
      </div>
      <div className="document-layout">
        <div className="card">
          <div className="card-section">
            <div>
              <h2>Required documents</h2>
              <span>{required.length} requested</span>
            </div>
          </div>
          <div className="document-list">
            {required.map((document) => (
              <DocumentRequestRow
                document={document}
                key={document.code}
                onUpload={handleUpload}
                uploading={uploading}
              />
            ))}
          </div>
          {otherDocuments.length > 0 ? (
            <details className="other-documents">
              <summary>Other supporting documents</summary>
              <p className="muted">
                Optional and conditional documents may provide additional
                evidence.
              </p>
              <div className="document-list">
                {otherDocuments.map((document) => (
                  <DocumentRequestRow
                    document={document}
                    key={document.code}
                    onUpload={handleUpload}
                    uploading={uploading}
                  />
                ))}
              </div>
            </details>
          ) : null}
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
        </div>
        <div className="card">
          <div className="card-section">
            <div>
              <h2>Uploaded metadata</h2>
              <span>{documents.length} files</span>
            </div>
          </div>
          {documents.length === 0 ? (
            <p className="muted">No files uploaded yet.</p>
          ) : (
            <div className="document-list">
              {documents.map((document) => (
                <div className="document-item" key={document.id}>
                  <span aria-hidden="true" className="file-tile ok">
                    <Icon name="check" />
                  </span>
                  <span className="doc-copy">
                    <b>{document.filename}</b>
                    <small>
                      {Math.round(document.byte_size / 1024)} KB ·{" "}
                      {document.content_type}
                    </small>
                  </span>
                  <Button
                    disabled={removingDocumentId === document.id}
                    onClick={() => requestRemoval(document)}
                    variant="danger"
                  >
                    {removingDocumentId === document.id
                      ? "Removing…"
                      : "Remove"}
                  </Button>
                </div>
              ))}
            </div>
          )}
          {(intake || onContinue) && !ready ? (
            <p className="muted">
              {onContinue
                ? "Upload every required document to continue."
                : "Upload every required document to submit this case."}
            </p>
          ) : null}
          <div className="form-actions">
            {onContinue ? (
              <Button disabled={!ready} onClick={onContinue}>
                {continueLabel ?? "Continue"}
              </Button>
            ) : intake ? (
              <Button
                disabled={submitting || !ready}
                onClick={() => handleIntake(intake.kind)}
              >
                {submitting ? "Submitting…" : intake.label}
              </Button>
            ) : null}
            <Button onClick={() => onNavigate("tracking")} variant="quiet">
              Continue to tracking
            </Button>
          </div>
        </div>
      </div>
      {pendingRemoval ? (
        <ConfirmDialog
          confirmLabel="Remove document"
          detail={
            `${pendingRemoval.filename} will no longer be evidence for this `
            + "case."
          }
          onCancel={() => setPendingRemoval(null)}
          onConfirm={() => void confirmRemoval()}
          title="Remove this document?"
        />
      ) : null}
    </>
  );
}
