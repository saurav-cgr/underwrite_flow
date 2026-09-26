import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  listAudit,
  listQueue,
} from "./api";
import type { AuditEvent, ProviderCall, QueueItem, Screen } from "./types";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
} from "./components";
import { AccessAdministration } from "./access-admin";
import { EvaluationPanel } from "./evaluation-panel";
import { Icon } from "./icons";
import { auditFacts, auditLabel } from "./ui-state";

// Read the bounded provider calls one event recorded, if any.
function providerCalls(event: AuditEvent): ProviderCall[] {
  const value = event.details.provider_calls;
  return Array.isArray(value) ? (value as ProviderCall[]) : [];
}

// Summarize one provider call without exposing any document content.
function providerCallSummary(call: ProviderCall): string {
  const parts = [call.provider ?? "unknown provider"];
  if (call.model) parts.push(`model ${call.model}`);
  const attempts = call.attempts ?? 0;
  parts.push(attempts === 1 ? "1 attempt" : `${attempts} attempts`);
  if (call.usage_unavailable) {
    parts.push("usage unavailable");
  } else {
    parts.push(`${call.prompt_tokens ?? 0} prompt tokens`);
    parts.push(`${call.completion_tokens ?? 0} completion tokens`);
  }
  if (call.error_code) parts.push(`failed: ${call.error_code}`);
  return parts.join(" · ");
}

// Name the event a later event replaced, when the timeline still holds it.
function supersededLabel(event: AuditEvent, events: AuditEvent[]): string {
  const replaced = events.find(
    (candidate) => candidate.id === event.supersedes_event_id,
  );
  return replaced ? auditLabel(replaced.event_type) : "an earlier event";
}

// Render one immutable audit event as an anchored chronology entry.
function AuditEventItem({
  event,
  events,
}: {
  event: AuditEvent;
  events: AuditEvent[];
}) {
  const calls = providerCalls(event);
  return (
    <li id={`event-${event.id}`}>
      <span aria-hidden="true" className="audit-icon">
        <Icon name="log" />
      </span>
      <div>
        <strong>{auditLabel(event.event_type)}</strong>
        <span className="audit-time">
          {new Date(event.occurred_at).toLocaleString()}
        </span>
        {event.supersedes_event_id ? (
          <a
            className="audit-supersedes"
            href={`#event-${event.supersedes_event_id}`}
          >
            {`Supersedes: ${supersededLabel(event, events)}`}
          </a>
        ) : null}
        <dl className="audit-facts">
          {auditFacts(event.details).map((fact) => (
            <div key={fact.label}>
              <dt>{fact.label}</dt>
              <dd>{fact.value}</dd>
            </div>
          ))}
        </dl>
        {calls.length > 0 ? (
          <dl className="provider-calls">
            {calls.map((call) => (
              <div key={`${call.document_id}-${call.document_code}`}>
                <dt>{call.document_code ?? "document"}</dt>
                <dd>{providerCallSummary(call)}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        <details className="audit-raw">
          <summary>Raw event payload</summary>
          <code>{JSON.stringify(event.details, null, 2)}</code>
        </details>
      </div>
    </li>
  );
}

// Give administrators an inspectable queue and audit lookup workspace.
export function AdminWorkspace({
  token,
  onNavigate,
  initialCaseId = "",
}: {
  token: string;
  onNavigate: (screen: Screen) => void;
  initialCaseId?: string;
}) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [caseId, setCaseId] = useState(initialCaseId);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState("");

  // Load immutable audit history for one exact case identifier.
  const loadAuditHistory = useCallback(async (targetCaseId: string) => {
    setMessage("");
    try {
      setEvents(await listAudit(token, targetCaseId));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "Audit history could not be loaded.",
      );
    }
  }, [token]);

  useEffect(() => {
    listQueue(token)
      .then(setQueue)
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The queue could not be loaded.",
        ),
      );
  }, [token]);

  useEffect(() => {
    if (initialCaseId) void loadAuditHistory(initialCaseId);
  }, [initialCaseId, loadAuditHistory]);

  // Fetch immutable events for an administrator-entered case identifier.
  async function handleAuditSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!caseId.trim()) return;
    await loadAuditHistory(caseId.trim());
  }

  return (
    <>
      <PageHeading
        eyebrow="Administrator workspace"
        title="Audit workspace"
        description={
          "Inspect queue state and reconstruct a case from immutable "
          + "business events."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("queue")}>
            Open all queues
          </Button>
        }
      />
      <EvaluationPanel token={token} />
      <AccessAdministration token={token} />
      <div className="admin-grid">
        <Panel title="Queue pulse">
          <div className="metric-strip">
            <div>
              <strong>{queue.length}</strong>
              <span>Total visible</span>
            </div>
            <div>
              <strong>
                {queue.filter(
                  (item) => item.status === "underwriter_review",
                ).length}
              </strong>
              <span>Awaiting review</span>
            </div>
            <div>
              <strong>
                {queue.filter((item) => item.status === "completed").length}
              </strong>
              <span>Completed</span>
            </div>
          </div>
          <div className="mini-list">
            {queue.slice(0, 5).map((item) => (
              <div className="mini-row" key={item.case_id}>
                <span className="mono">{item.case_id.slice(0, 8)}</span>
                <span>{item.product_code}</span>
                <Badge tone={item.status}>
                  {item.status.replaceAll("_", " ")}
                </Badge>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Find audit history">
          <form className="audit-search" onSubmit={handleAuditSearch}>
            <label className="field" htmlFor="audit-case">
              <span>Case ID</span>
              <small>Paste a complete synthetic case UUID.</small>
              <input
                id="audit-case"
                onChange={(event) => setCaseId(event.target.value)}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                value={caseId}
              />
            </label>
            <Button type="submit">Load events</Button>
          </form>
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
          {events.length === 0 ? (
            <EmptyState
              title="No audit loaded"
              detail={
                "Search for a case to inspect its transitions, actions, and "
                + "completion record."
              }
            />
          ) : (
            <ol className="audit-list" aria-label="Audit chronology">
              {events.map((event) => (
                <AuditEventItem key={event.id} event={event} events={events} />
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </>
  );
}
