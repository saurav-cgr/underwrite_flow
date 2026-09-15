import { useEffect, useState } from "react";

import {
  ApiError,
  listDocuments,
  removeDocument,
  uploadDocument,
} from "./api";
import { Button, Journey, PageHeading, Panel } from "./components";
import { requiredDocuments } from "./ui-state";
import type {
  CaseRecord,
  DocumentRecord,
  ProductCatalogItem,
  ProductDocument,
  Screen,
} from "./types";

// Render one product-configured document request and its upload control.
function DocumentUploadRow({
  document,
  uploading,
  onUpload,
}: {
  document: ProductDocument;
  uploading: boolean;
  onUpload: (documentCode: string, file: File | undefined) => void;
}) {
  return (
    <div className="document-row">
      <div>
        <strong>{document.title}</strong>
        <span>
          {document.requirement === "required"
            ? "Required"
            : "Optional or conditional"}
        </span>
      </div>
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

// Let applicants upload and replace pre-review supporting documents.
export function DocumentsScreen({
  product,
  caseRecord,
  token,
  onNavigate,
}: {
  product: ProductCatalogItem;
  caseRecord: CaseRecord;
  token: string;
  onNavigate: (screen: Screen) => void;
}) {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);
  const [removingDocumentId, setRemovingDocumentId] = useState<string | null>(
    null,
  );
  const required = requiredDocuments(product.documents);
  const otherDocuments = product.documents.filter(
    (document) => document.requirement !== "required"
      && document.requirement !== "not_applicable",
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

  // Remove one incorrectly uploaded document after native confirmation.
  async function handleRemove(document: DocumentRecord) {
    if (!window.confirm(`Remove ${document.filename}?`)) return;
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
        eyebrow="Supporting evidence"
        title="Add your documents."
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
      <div className="document-layout">
        <Panel title="Required documents">
          <div className="document-list">
            {required.map((document) => (
              <DocumentUploadRow
                document={document}
                key={document.code}
                onUpload={handleUpload}
                uploading={uploading}
              />
            ))}
          </div>
          {otherDocuments.length > 0 ? (
            <details>
              <summary>Other supporting documents</summary>
              <p className="muted">
                Optional and conditional documents may provide additional
                evidence.
              </p>
              <div className="document-list">
                {otherDocuments.map((document) => (
                  <DocumentUploadRow
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
        </Panel>
        <Panel title="Uploaded metadata">
          <div className="uploaded-list">
            {documents.length === 0 ? (
              <p className="muted">No files uploaded yet.</p>
            ) : (
              documents.map((document) => (
                <div className="uploaded-row" key={document.id}>
                  <span className="status-dot" aria-hidden="true" />
                  <span>{document.filename}</span>
                  <small>
                    {Math.round(document.byte_size / 1024)} KB ·{" "}
                    {document.content_type}
                  </small>
                  <Button
                    disabled={removingDocumentId === document.id}
                    onClick={() => handleRemove(document)}
                    variant="danger"
                  >
                    {removingDocumentId === document.id
                      ? "Removing…"
                      : "Remove"}
                  </Button>
                </div>
              ))
            )}
          </div>
          <div className="form-actions">
            <Button onClick={() => onNavigate("tracking")}>
              Continue to tracking
            </Button>
          </div>
        </Panel>
      </div>
    </>
  );
}
