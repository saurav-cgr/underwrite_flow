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

  useEffect(() => {
    listQueue(token, filter)
      .then(setItems)
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The queue could not be loaded.",
        ),
      );
  }, [filter, token]);

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
              <button
                className="queue-row"
                key={item.case_id}
                onClick={() => onSelect(item)}
                type="button"
              >
                <span className="mono">{item.case_id.slice(0, 8)}</span>
                <span>{item.product_code}</span>
                <span>
                  {item.route ?? "Pending"}
                  {item.specialist ? (
                    <Badge tone="specialist">Specialist</Badge>
                  ) : null}
                </span>
                <span>
                  <Badge tone={item.status}>
                    {item.status.replaceAll("_", " ")}
                  </Badge>
                </span>
                <span aria-hidden="true">→</span>
              </button>
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
        setSelectedRoute(response.recommendation.route);
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
              <input
                disabled={working || !canReview}
                onChange={(event) => setSpecialistLabel(event.target.value)}
                placeholder="Required for specialist review."
                type="text"
                value={specialistLabel}
              />
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
