import { useEffect, useRef, useState } from "react";

import { ApiError, fetchReviewDocument } from "./api";
import { Button } from "./components";
import { Icon } from "./icons";

type PreviewStatus = "loading" | "ready" | "error";

// Render one authenticated case document inline with retry and close states.
export function DocumentPreview({
  caseId,
  contentType,
  documentId,
  onClose,
  page,
  title,
  token,
}: {
  caseId: string;
  contentType: string;
  documentId: string;
  onClose: () => void;
  page: number | null;
  title: string;
  token: string;
}) {
  const [status, setStatus] = useState<PreviewStatus>("loading");
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [attempt, setAttempt] = useState(0);
  const paneRef = useRef<HTMLElement>(null);

  // Move focus into the pane and hand it back when the preview closes.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    paneRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  // Fetch the document once per selection and revoke any prior object URL.
  useEffect(() => {
    let active = true;
    let url: string | null = null;
    setStatus("loading");
    setMessage("");
    setObjectUrl(null);
    fetchReviewDocument(token, caseId, documentId)
      .then((document) => {
        if (!active) return;
        url = URL.createObjectURL(document.blob);
        setObjectUrl(url);
        setStatus("ready");
      })
      .catch((error) => {
        if (!active) return;
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The document could not be loaded.",
        );
        setStatus("error");
      });
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [token, caseId, documentId, attempt]);

  // Close on Escape without stealing focus from the page behind.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  function openInNewTab() {
    if (!source) return;
    window.open(source, "_blank", "noopener,noreferrer");
  }

  const isPdf = contentType === "application/pdf";
  const isImage =
    contentType === "image/jpeg" || contentType === "image/png";
  const source = objectUrl
    ? objectUrl + (isPdf && page !== null ? `#page=${page}` : "")
    : undefined;
  const alt = page !== null ? `${title} · Page ${page}` : title;

  return (
    <section
      aria-label={`Document preview: ${title}`}
      className="preview-pane"
      ref={paneRef}
      tabIndex={-1}
    >
      <header className="preview-head">
        <h3>{title}</h3>
        <div className="preview-actions">
          <Button
            disabled={status !== "ready"}
            onClick={openInNewTab}
            variant="quiet"
          >
            <Icon name="external" />
            Open in new tab
          </Button>
          <Button onClick={onClose} variant="quiet">
            <Icon name="close" />
            Close
          </Button>
        </div>
      </header>
      <div className="preview-body">
        {status === "loading" ? (
          <p className="preview-state" role="status">
            Loading document…
          </p>
        ) : null}
        {status === "error" ? (
          <div className="preview-state" role="alert">
            <p>{message || "The document could not be loaded."}</p>
            <Button onClick={() => setAttempt((value) => value + 1)}>
              Retry
            </Button>
          </div>
        ) : null}
        {status === "ready" && isPdf && source ? (
          <iframe
            className="preview-frame"
            sandbox=""
            src={source}
            title={title}
          />
        ) : null}
        {status === "ready" && isImage && source ? (
          <img alt={alt} className="preview-image" src={source} />
        ) : null}
        {status === "ready" && !isPdf && !isImage ? (
          <div className="preview-state">
            <p>This file type is not shown inline. Open it in a new tab.</p>
            <Button onClick={openInNewTab}>Open in new tab</Button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
