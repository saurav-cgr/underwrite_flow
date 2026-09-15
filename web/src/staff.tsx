import { useEffect, useState } from "react";

import {
  ApiError,
  completeCase,
  listQueue,
  startReview,
  submitReview,
} from "./api";
import type {
  QueueItem,
  Recommendation,
  ReviewResult,
  ReviewStart,
  Screen,
} from "./types";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
} from "./components";

// Show the human-selected route and specialist label once a decision exists.
function routeLabel(item: QueueItem): string {
  if (!item.selected_route) {
    return item.route ?? "Pending";
  }
  return item.specialist_label
    ? `${item.selected_route} · ${item.specialist_label}`
    : item.selected_route;
}


// Load and filter the underwriter queue with safe server-side rows.
export function UnderwriterQueue({
  token,
  onSelect,
  onNavigate,
}: {
  token: string;
  onSelect: (item: QueueItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [filter, setFilter] = useState("underwriter_review");
  const [message, setMessage] = useState("");
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    const awaitingHandoff = filter === "awaiting_handoff";
    listQueue(token, awaitingHandoff ? undefined : filter, awaitingHandoff)
      .then(setItems)
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The queue could not be loaded.",
        ),
      );
  }, [filter, token]);

  // Retry the handoff for a finalised route that was never completed.
  async function handleRetry(item: QueueItem) {
    setRetryingId(item.case_id);
    setMessage("");
    try {
      await completeCase(token, item.case_id);
      setItems((current) =>
        current.filter((row) => row.case_id !== item.case_id),
      );
      setMessage("Handoff completed.");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The handoff could not be completed.",
      );
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="Underwriter workspace"
        title="Review queue"
        description={
          "Prioritize cases with visible evidence state, deterministic "
          + "signals, and a human decision boundary."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("queue")}>
            Refresh queue
          </Button>
        }
      />
      <div className="filter-bar" role="group" aria-label="Queue filter">
        <button
          className={filter === "underwriter_review" ? "filter-active" : ""}
          onClick={() => setFilter("underwriter_review")}
          type="button"
        >
          Underwriter review
        </button>
        <button
          className={filter === "needs_information" ? "filter-active" : ""}
          onClick={() => setFilter("needs_information")}
          type="button"
        >
          Needs information
        </button>
        <button
          className={filter === "awaiting_handoff" ? "filter-active" : ""}
          onClick={() => setFilter("awaiting_handoff")}
          type="button"
        >
          Awaiting handoff
        </button>
        <button
          className={filter === "completed" ? "filter-active" : ""}
          onClick={() => setFilter("completed")}
          type="button"
        >
          Completed
        </button>
      </div>
      <Panel>
        {message ? (
          <p className="form-error" role="alert">
            {message}
          </p>
        ) : items.length === 0 ? (
          <EmptyState
            title="Queue is clear"
            detail="No cases match this view."
          />
        ) : (
          <div className="queue-table" role="table" aria-label="Case queue">
            <div className="queue-header" role="row">
              <span>Case</span>
              <span>Product</span>
              <span>Route</span>
              <span>Status</span>
              <span />
            </div>
            {items.map((item) => (
              <div className="queue-row" key={item.case_id} role="row">
                <span className="mono">{item.case_id.slice(0, 8)}</span>
                <span>{item.product_code}</span>
                <span>
                  {routeLabel(item)}
                  {item.specialist ? (
                    <Badge tone="specialist">Specialist</Badge>
                  ) : null}
                </span>
                <span>
                  <Badge tone={item.status}>
                    {item.status.replaceAll("_", " ")}
                  </Badge>
                </span>
                <span>
                  <Button variant="quiet" onClick={() => onSelect(item)}>
                    Open
                  </Button>
                  {item.awaiting_handoff ? (
                    <Button
                      variant="secondary"
                      disabled={retryingId === item.case_id}
                      onClick={() => handleRetry(item)}
                    >
                      {retryingId === item.case_id
                        ? "Retrying…"
                        : "Retry handoff"}
                    </Button>
                  ) : null}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}

// Render a route recommendation with evidence acknowledgement before action.
export function CaseReview({
  token,
  item,
  onNavigate,
}: {
  token: string;
  item: QueueItem;
  onNavigate: (screen: Screen) => void;
}) {
  const [start, setStart] = useState<ReviewStart | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [selectedRoute, setSelectedRoute] = useState(item.route ?? "standard");
  const [specialistLabel, setSpecialistLabel] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);
  const canReview = item.status === "underwriter_review";

  useEffect(() => {
    if (!canReview) {
      setMessage("This case is no longer awaiting underwriter review.");
      return;
    }
    startReview(token, item.case_id)
      .then((response) => {
        setStart(response);
        const route = response.recommendation.route;
        setSelectedRoute(
          route === "expedited" ||
            route === "standard" ||
            route === "specialist"
            ? route
            : "standard",
        );
        setSpecialistLabel(response.specialist_options[0] ?? "");
      })
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The review checkpoint could not be opened.",
        ),
      );
  }, [canReview, item.case_id, token]);

  // Confirm or override a recommendation and complete final routes.
  async function handleDecision(
    action: "confirm" | "override" | "request_information",
  ) {
    if (!canReview) return;
    if (!acknowledged) {
      setMessage("Acknowledge the evidence before submitting a decision.");
      return;
    }
    if (
      (action === "override" || action === "request_information") &&
      reason.trim().length < 3
    ) {
      setMessage("Add a short reason for this action.");
      return;
    }
    setWorking(true);
    setMessage("");
    try {
      const review = await submitReview(token, item.case_id, {
        action,
        selected_route: action === "confirm" ? undefined : selectedRoute,
        specialist_label:
          action !== "confirm" && selectedRoute === "specialist"
            ? specialistLabel
            : undefined,
        reason: reason || undefined,
        evidence_acknowledged: acknowledged,
      });
      setResult(review);
      if (review.status === "confirmed" || review.status === "overridden") {
        await completeCase(token, item.case_id);
      }
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The decision could not be saved.",
      );
    } finally {
      setWorking(false);
    }
  }

  const recommendation: Recommendation | undefined = start?.recommendation;
  const recommendationRoute =
    recommendation?.route ?? item.route ?? "Unavailable";
  const recommendationDetail = recommendation?.reasons?.join(" ") ?? (
    canReview
      ? "The workflow is assembling an evidence-backed summary."
      : "This completed case cannot receive another review decision."
  );
  return (
    <>
      <PageHeading
        eyebrow="Case review"
        title={`Case ${item.case_id.slice(0, 8)}`}
        description={
          "Review the recommendation and evidence state. This screen never "
          + "approves or declines coverage."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("queue")}>
            Back to queue
          </Button>
        }
      />
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      {result ? (
        <div className="success-card" role="status">
          <strong>Decision recorded.</strong>
          <span>
            {result.status.replaceAll("_", " ")} ·{" "}
            {result.selected_route ?? "needs information"}
          </span>
        </div>
      ) : null}
      <div className="review-layout">
        <div>
          <Panel title="Recommendation">
            <div className="recommendation">
              <span className="eyebrow">System recommendation</span>
              <strong>{recommendationRoute}</strong>
              <p>{recommendationDetail}</p>
            </div>
          </Panel>
          <Panel title="Evidence acknowledgement">
            <label className="check-row">
              <input
                checked={acknowledged}
                onChange={(event) => setAcknowledged(event.target.checked)}
                type="checkbox"
              />
              <span>
                <strong>I reviewed the submitted evidence.</strong>
                <small>
                  I understand this is a triage recommendation, not a
                  coverage decision.
                </small>
              </span>
            </label>
          </Panel>
        </div>
        <aside className="decision-panel">
          <p className="eyebrow">Human action</p>
          <label className="field">
            <span>Final triage route</span>
            <select
              disabled={working || !canReview}
              onChange={(event) => setSelectedRoute(event.target.value)}
              value={selectedRoute}
            >
              <option value="expedited">Expedited review</option>
              <option value="standard">Standard review</option>
              <option value="specialist">Specialist review</option>
            </select>
          </label>
          {selectedRoute === "specialist" ? (
            <label className="field">
              <span>Specialist label</span>
              <select
                disabled={working || !canReview}
                onChange={(event) => setSpecialistLabel(event.target.value)}
                value={specialistLabel}
              >
                {(start?.specialist_options ?? []).map((label) => (
                  <option key={label} value={label}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className="field">
            <span>Reason / reviewer note</span>
            <textarea
              disabled={working || !canReview}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Required for an override or information request."
              value={reason}
            />
          </label>
          <div className="decision-actions">
            <Button
              disabled={working || Boolean(result) || !canReview}
              onClick={() => handleDecision("confirm")}
            >
              Confirm recommendation
            </Button>
            <Button
              disabled={working || Boolean(result) || !canReview}
              onClick={() => handleDecision("override")}
              variant="secondary"
            >
              Override route
            </Button>
            <Button
              disabled={working || Boolean(result) || !canReview}
              onClick={() => handleDecision("request_information")}
              variant="quiet"
            >
              Request information
            </Button>
          </div>
        </aside>
      </div>
    </>
  );
}
