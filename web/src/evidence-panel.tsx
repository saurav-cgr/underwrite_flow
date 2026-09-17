import { useState } from "react";

import { Badge, Button, Panel } from "./components";
import { Icon } from "./icons";
import {
  contentTypeLabel,
  documentCards,
  failureReason,
  groupFacts,
  missingFields,
  pageCountLabel,
  pdfPageOf,
  riskSignals,
} from "./evidence";
import type {
  DocumentCard,
  ExtractedEntry,
  FactCard,
  FactStatus,
} from "./evidence";
import { DocumentPreview } from "./document-preview";
import type { ReconciliationCheck, ReviewStart } from "./types";

// Describe one configured check status in words rather than colour alone.
function checkStatusLabel(check: ReconciliationCheck): string {
  if (!check.status) {
    return "not evaluated";
  }
  return check.status.replaceAll("_", " ").toLowerCase();
}

// Render the comparisons of one configured check with their provenance.
function CheckComparisons({ check }: { check: ReconciliationCheck }) {
  if (check.comparisons.length === 0) {
    const missing = check.missing_inputs.join(", ");
    return (
      <small>
        {missing
          ? `No usable value for: ${missing}`
          : "No comparison was possible."}
      </small>
    );
  }
  return (
    <>
      {check.comparisons.map((comparison) => (
        <div className="check-comparison" key={comparison.field_key}>
          <span>
            <code>{comparison.field_key}</code>{" "}
            {comparison.matched ? "matches" : "differs"}:{" "}
            {String(comparison.left ?? "not supplied")} versus{" "}
            {String(comparison.right ?? "not extracted")}
          </span>
          <small>
            {comparison.explanation_code} · from {" "}
            {comparison.confidence_source}
            {comparison.evidence.length > 0
              ? " · " +
                comparison.evidence
                  .map(
                    (reference) =>
                      `${reference.document_id} ${reference.source_locator}`,
                  )
                  .join(", ")
              : ""}
          </small>
        </div>
      ))}
    </>
  );
}

// Render the evidence an underwriter must review before recording a decision.
export function EvidencePanel({
  pack,
  token,
}: {
  pack: ReviewStart;
  token: string;
}) {
  const facts = groupFacts(pack.submitted_facts, pack.evidence);
  const documents = documentCards(pack.evidence);
  const signals = riskSignals(pack.summary);
  const gaps = missingFields(pack.summary);
  const [preview, setPreview] = useState<{
    contentType: string;
    documentId: string;
    page: number | null;
    title: string;
  } | null>(null);

  function openDocument(document: DocumentCard) {
    setPreview({
      contentType: document.contentType,
      documentId: document.documentId,
      page: null,
      title: document.title,
    });
  }

  function openSource(documentId: string, locator: string | null) {
    const document = documents.find((item) => item.documentId === documentId);
    const entry = facts
      .flatMap((fact) => fact.entries)
      .find((item) => item.documentId === documentId);
    setPreview({
      contentType: document?.contentType ?? "",
      documentId,
      page: pdfPageOf(locator),
      title: entry?.documentTitle ?? document?.title ?? "Document",
    });
  }

  const hasAny = documents.length > 0 || facts.length > 0;
  return (
    <>
      <Panel title="Case evidence">
        <p className="muted">
          Each case fact is shown beside the value extracted from its
          documents.
        </p>
        {!hasAny ? <p className="muted">No evidence was supplied.</p> : null}
        <div
          className={
            preview ? "evidence-workspace" : "evidence-workspace single"
          }
        >
          <div className="evidence-facts">
            {documents.length > 0 ? (
              <section aria-label="Uploaded documents">
                <h3 className="section-kicker">Uploaded documents</h3>
                <ul className="doc-list">
                  {documents.map((document) => (
                    <li className="doc-card" key={document.documentId}>
                      <div className="doc-card-main">
                        <Icon name="file" />
                        <div>
                          <b>{document.title}</b>
                          <small>
                            {[
                              document.filename,
                              contentTypeLabel(document.contentType),
                              pageCountLabel(document.pageCount),
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </small>
                        </div>
                      </div>
                      <Button
                        onClick={() => openDocument(document)}
                        variant="quiet"
                      >
                        View document
                      </Button>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {facts.length > 0 ? (
              <section aria-label="Case facts">
                <h3 className="section-kicker">Case facts</h3>
                <ul className="fact-list">
                  {facts.map((fact) => (
                    <FactCardView
                      fact={fact}
                      key={fact.fieldName}
                      onViewSource={openSource}
                    />
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
          {preview ? (
            <DocumentPreview
              caseId={pack.case_id}
              contentType={preview.contentType}
              documentId={preview.documentId}
              onClose={() => setPreview(null)}
              page={preview.page}
              title={preview.title}
              token={token}
            />
          ) : null}
        </div>
      </Panel>
      <Panel title="Configured checks">
        {pack.reconciliation.length === 0 ? (
          <p className="muted">
            The pinned configuration defines no reconciliation check.
          </p>
        ) : (
          <ul className="check-list">
            {pack.reconciliation.map((check) => (
              <li className="check-item" key={check.check_code}>
                <header>
                  <b>{check.check_code}</b>
                  <Badge tone={check.status}>
                    {checkStatusLabel(check)}
                  </Badge>
                </header>
                <CheckComparisons check={check} />
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Recorded risk signals">
        {signals.length === 0 ? (
          <p className="muted">No configured risk signal was recorded.</p>
        ) : (
          <ul className="evidence-list">
            {signals.map((signal) => (
              <li key={signal.code}>
                <b>{signal.code}</b>
                <span>{signal.severity}</span>
                <small>{signal.explanation}</small>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Conflicts and gaps">
        <p className="muted">Missing documents</p>
        {pack.missing_information.length === 0 ? (
          <p className="muted">No requested document is outstanding.</p>
        ) : (
          <ul className="evidence-list">
            {pack.missing_information.map((code) => (
              <li key={code}>
                <b>{code}</b>
              </li>
            ))}
          </ul>
        )}
        <p className="muted">Missing fields</p>
        {gaps.length === 0 ? (
          <p className="muted">No requested field is missing.</p>
        ) : (
          <ul className="evidence-list">
            {gaps.map((field) => (
              <li key={field}>
                <b>{field}</b>
                <span>missing</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      <Panel title="Processing failures">
        {pack.extraction_failures.length === 0 ? (
          <p className="muted">No processing failure was recorded.</p>
        ) : (
          <ul className="evidence-list">
            {pack.extraction_failures.map((failure, index) => (
              <li key={`failure-${index}`}>
                <b>{String(failure.rule_code ?? "unnamed failure")}</b>
                <span>{failureReason(failure.details)}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}

// Render one grouped fact with its submitted value and extracted evidence.
function FactCardView({
  fact,
  onViewSource,
}: {
  fact: FactCard;
  onViewSource: (documentId: string, locator: string | null) => void;
}) {
  const sources = fact.entries.filter(
    (entry): entry is ExtractedEntry & { documentId: string } =>
      Boolean(entry.documentId),
  );
  return (
    <li className="fact-card">
      <h4>{fact.fieldLabel}</h4>
      <dl className="fact-rows">
        {fact.submittedValue !== null ? (
          <div className="fact-row">
            <dt>Submitted</dt>
            <dd className="fact-value">{fact.submittedValue}</dd>
          </div>
        ) : null}
        {fact.entries.map((entry, index) => (
          <div className="fact-row" key={`${fact.fieldName}-${index}`}>
            <dt>
              {fact.entries.length > 1 ? `Extracted ${index + 1}` : "Extracted"}
            </dt>
            <dd>
              <span className="fact-value">{entry.value}</span>
              <span className="fact-source">
                {[
                  entry.documentTitle,
                  entry.source !== "—" ? entry.source : "",
                  entry.confidence !== null
                    ? `${Math.round(entry.confidence * 100)}% confidence`
                    : "",
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </dd>
          </div>
        ))}
        <div className="fact-row">
          <dt>Status</dt>
          <dd>
            <Badge tone={statusTone(fact.status)}>{fact.status}</Badge>
          </dd>
        </div>
      </dl>
      {sources.length > 0 ? (
        <div className="fact-actions">
          {sources.map((entry, index) => (
            <Button
              key={`${entry.documentId}-${index}`}
              onClick={() => onViewSource(entry.documentId, entry.locator)}
              variant="quiet"
            >
              View source
            </Button>
          ))}
        </div>
      ) : null}
      <details className="technical-details">
        <summary>Technical details</summary>
        <dl className="technical-grid">
          <div>
            <dt>Field code</dt>
            <dd>{fact.fieldName}</dd>
          </div>
          <div>
            <dt>Field type</dt>
            <dd>{fact.fieldType}</dd>
          </div>
          {fact.entries.map((entry, index) => (
            <div key={index}>
              <dt>
                {fact.entries.length > 1 ? `Extracted ${index + 1}` : "Extracted"}
              </dt>
              <dd>
                {[
                  entry.documentId ?? "no document",
                  entry.locator ?? "",
                  entry.extractionMethod,
                  entry.confidence !== null
                    ? `confidence ${entry.confidence}`
                    : "",
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </li>
  );
}

// Map one reviewer-facing status to the badge tone it renders with.
function statusTone(status: FactStatus): string {
  if (status === "Consistent") return "consistent";
  if (status === "Conflict") return "conflict";
  if (status === "Not found in documents") return "not_found";
  return "document_only";
}
