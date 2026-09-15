import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  listAudit,
  listQueue,
} from "./api";
import type { AuditEvent, QueueItem, Screen } from "./types";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
} from "./components";
import { EvaluationPanel } from "./evaluation-panel";
import { Icon } from "./icons";

// Give administrators an inspectable queue and audit lookup workspace.
export function AdminWorkspace({
  token,
  onNavigate,
}: {
  token: string;
  onNavigate: (screen: Screen) => void;
}) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [caseId, setCaseId] = useState("");
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [message, setMessage] = useState("");

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

  // Fetch immutable events for an administrator-entered case identifier.
  async function handleAuditSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!caseId.trim()) return;
    setMessage("");
    try {
      setEvents(await listAudit(token, caseId.trim()));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "Audit history could not be loaded.",
      );
    }
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
            <ol className="audit-list">
              {events.map((event) => (
                <li key={event.id}>
                  <span aria-hidden="true" className="audit-icon">
                    <Icon name="log" />
                  </span>
                  <div>
                    <strong>{event.event_type.replaceAll("_", " ")}</strong>
                    <span className="audit-time">
                      {new Date(event.occurred_at).toLocaleString()}
                    </span>
                    <code>{JSON.stringify(event.details)}</code>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>
    </>
  );
}
