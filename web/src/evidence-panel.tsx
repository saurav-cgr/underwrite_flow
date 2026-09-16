import { Panel } from "./components";
import {
  evidenceDocuments,
  evidenceFields,
  failureReason,
  riskSignals,
} from "./evidence";
import type { ReviewStart } from "./types";

// Render the evidence an underwriter must review before recording a decision.
export function EvidencePanel({ pack }: { pack: ReviewStart }) {
  const documents = evidenceDocuments(pack.evidence);
  const fields = evidenceFields(pack.evidence);
  const signals = riskSignals(pack.summary);
  const names = new Map(
    documents.map((document) => [document.documentId, document.filename]),
  );

  return (
    <>
      <Panel title="Submitted evidence">
        <p className="muted">
          Every extracted value keeps the document and page it came from.
        </p>
        {documents.length === 0 ? (
          <p className="muted">No evidence was supplied.</p>
        ) : (
          <ul className="evidence-list">
            {documents.map((document) => (
              <li key={document.source}>
                <b>{document.filename}</b>
                <small>{document.source}</small>
              </li>
            ))}
          </ul>
        )}
        {fields.length > 0 ? (
          <ul className="evidence-list">
            {/* Two documents can report the same field at the same line, so
                the position is the only stable key for these rows. */}
            {fields.map((field, index) => (
              <li key={`field-${index}`}>
                <b>{field.field}</b>
                <span>{field.value}</span>
                <small>
                  {names.get(field.documentId) ?? "unknown document"}
                  {" · "}
                  {field.source}
                </small>
              </li>
            ))}
          </ul>
        ) : null}
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
        {pack.conflicts.length === 0 ? (
          <p className="muted">No conflict was detected.</p>
        ) : (
          <ul className="evidence-list">
            {pack.conflicts.map((conflict, index) => (
              <li key={`conflict-${index}`}>
                <b>{String(conflict.field_name ?? "unnamed field")}</b>
                <span>{String(conflict.conflict_status ?? "conflict")}</span>
              </li>
            ))}
          </ul>
        )}
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
