import { useEffect, useState } from "react";

import {
  ApiError,
  deleteReference,
  listReferences,
  uploadReference,
} from "./api";
import { Badge, Button, EmptyState, Panel } from "./components";
import { ConfirmDialog } from "./confirm";
import type { ProductVersionHistoryItem, ReferenceDocument } from "./types";

// Describe one reference document's size, length, and content hash.
function referenceFacts(reference: ReferenceDocument): {
  size: string;
  pages: string;
  hash: string;
} {
  const kilobytes = Math.max(1, Math.round(reference.byte_size / 1024));
  return {
    size: `${kilobytes} KB · ${reference.content_type}`,
    pages:
      reference.page_count === null
        ? "Length unknown"
        : reference.page_count === 1
          ? "1 page"
          : `${reference.page_count} pages`,
    hash: `hash ${reference.content_hash.slice(0, 8)}`,
  };
}

// Manage the administrator reference documents of one product version.
export function ReferenceDocuments({
  token,
  productCode,
  versions,
}: {
  token: string;
  productCode: string | null;
  versions: ProductVersionHistoryItem[];
}) {
  const [version, setVersion] = useState("");
  const [references, setReferences] = useState<ReferenceDocument[]>([]);
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [working, setWorking] = useState("");
  const [pending, setPending] = useState<ReferenceDocument | null>(null);

  // Follow the newest available version whenever the product changes.
  useEffect(() => {
    setVersion((current) =>
      versions.some((item) => item.version === current)
        ? current
        : versions[0]?.version ?? "",
    );
  }, [versions]);

  // Load the reference documents stored for the selected version.
  useEffect(() => {
    if (!productCode || !version) {
      setReferences([]);
      return;
    }
    listReferences(token, productCode, version)
      .then(setReferences)
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "Reference documents could not be loaded.",
        ),
      );
  }, [productCode, token, version]);

  // Store one selected file against the chosen product version.
  async function handleUpload(file: File | undefined) {
    if (!file || !productCode || !version) return;
    setWorking("upload");
    setMessage("");
    setNotice("");
    try {
      const stored = await uploadReference(token, productCode, version, file);
      setReferences((current) => [...current, stored]);
      setNotice(`${stored.filename} was added to ${stored.version}.`);
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The reference document could not be uploaded.",
      );
    } finally {
      setWorking("");
    }
  }

  // Ask before removing a reference document from this version.
  function requestDelete(reference: ReferenceDocument) {
    if (!productCode) return;
    setPending(reference);
  }

  // Remove the confirmed reference document and report the outcome.
  async function confirmDelete() {
    const reference = pending;
    if (!productCode || reference === null) return;
    setPending(null);
    setWorking(reference.id);
    setMessage("");
    setNotice("");
    try {
      await deleteReference(token, productCode, reference.id);
      setReferences((current) =>
        current.filter((item) => item.id !== reference.id),
      );
      setNotice("Reference document removed.");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The reference document could not be removed.",
      );
    } finally {
      setWorking("");
    }
  }

  if (!productCode) {
    return (
      <Panel title="Reference documents">
        <EmptyState
          title="Choose a product"
          detail="Select a configuration to manage its reference documents."
        />
      </Panel>
    );
  }

  return (
    <Panel title="Reference documents">
      <p className="muted">
        Background documents an administrator attaches to one version. They
        guide extraction and never override submitted evidence.
      </p>
      <label className="field" htmlFor="reference-version">
        <span>Version</span>
        <small>References are stored against the version you choose.</small>
        <select
          id="reference-version"
          onChange={(event) => setVersion(event.target.value)}
          value={version}
        >
          {versions.map((item) => (
            <option key={item.version} value={item.version}>
              {item.version} ({item.status})
            </option>
          ))}
        </select>
      </label>
      {versions.length === 0 ? (
        <p className="muted" role="status">
          No version is available for this product.
        </p>
      ) : (
        <label className="upload-button">
          <input
            accept="application/pdf,image/jpeg,image/png"
            aria-label="Choose reference document"
            disabled={working === "upload"}
            onChange={(event) =>
              handleUpload(event.target.files?.[0])
            }
            type="file"
          />
          {working === "upload" ? "Uploading…" : "Choose reference file"}
        </label>
      )}
      {references.length === 0 ? (
        <p className="muted">
          No reference document is stored for this version.
        </p>
      ) : (
        <div aria-label="Reference documents" className="mini-list" role="list">
          {references.map((reference) => {
            const facts = referenceFacts(reference);
            const isSelectedVersion = reference.version === version;
            return (
              <div
                className="mini-row"
                key={reference.id}
                role="listitem"
              >
                <span>{reference.filename}</span>
                <small>{facts.size}</small>
                <small>{facts.pages}</small>
                <small>{facts.hash}</small>
                <Badge tone={isSelectedVersion ? "active" : "draft"}>
                  {reference.version}
                </Badge>
                <Button
                  disabled={working === reference.id}
                  onClick={() => requestDelete(reference)}
                  variant="danger"
                >
                  {working === reference.id ? "Removing…" : "Remove"}
                </Button>
              </div>
            );
          })}
        </div>
      )}
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      {notice ? (
        <p className="form-notice" role="status">
          {notice}
        </p>
      ) : null}
      {pending ? (
        <ConfirmDialog
          confirmLabel="Remove reference"
          detail={
            `${pending.filename} will no longer guide extraction for this `
            + "version."
          }
          onCancel={() => setPending(null)}
          onConfirm={() => void confirmDelete()}
          title="Remove this reference document?"
        />
      ) : null}
    </Panel>
  );
}
