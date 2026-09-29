import { useEffect, useState } from "react";

import { ApiError, completeCase, startReview, submitReview } from "./api";
import { Button, PageHeading, Panel } from "./components";
import { EvidencePanel } from "./evidence-panel";
import { GuidancePanel } from "./guidance-panel";
import { Icon } from "./icons";
import { ReviewActions } from "./review-actions";
import type { GuidanceCitation } from "./types-knowledge";
import { decisionSummary, reviewDecisionBody } from "./ui-state";
import type {
  QueueItem,
  Recommendation,
  ReviewResult,
  ReviewStart,
  Screen,
} from "./types";

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
  const [overriding, setOverriding] = useState(false);
  const [specialistLabel, setSpecialistLabel] = useState("");
  const [reason, setReason] = useState("");
  const [suggestions, setSuggestions] = useState<GuidanceCitation[]>([]);
  const [message, setMessage] = useState("");
  const [handoffFailed, setHandoffFailed] = useState(false);
  const [working, setWorking] = useState(false);
  const queueReviewable = item.status === "underwriter_review";
  const canReview = queueReviewable && !result;
  const locked = working || !canReview;

  // Retry the queue handoff for a decision that was already recorded.
  async function retryHandoff() {
    setWorking(true);
    setMessage("");
    try {
      await completeCase(token, item.case_id);
      setHandoffFailed(false);
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The handoff could not be completed.",
      );
    } finally {
      setWorking(false);
    }
  }

  useEffect(() => {
    if (!queueReviewable) {
      setMessage("This case is no longer awaiting underwriter review.");
      return;
    }
    startReview(token, item.case_id)
      .then((response) => {
        setStart(response);
        const route = response.recommendation.route;
        setSelectedRoute(
          route === "needs_information"
            ? ""
            : route === "manual"
            ? "specialist"
            : route === "expedited" ||
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
  }, [queueReviewable, item.case_id, token]);

  // Confirm or override a recommendation and complete final routes.
  async function handleDecision(
    action: "confirm" | "override" | "request_information",
  ) {
    if (!canReview) return;
    if (!acknowledged) {
      setMessage("Acknowledge the evidence before submitting a decision.");
      return;
    }
    if (action === "override" && !selectedRoute) {
      setMessage("Select a final route for this override.");
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
    let review: ReviewResult;
    try {
      review = await submitReview(
        token,
        item.case_id,
        reviewDecisionBody({
          action,
          selectedRoute,
          recommendedRoute:
            start?.recommendation?.route ?? item.route ?? undefined,
          specialistLabel,
          reason,
          acknowledged,
        }),
      );
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The decision could not be saved.",
      );
      setWorking(false);
      return;
    }
    setResult(review);
    // The decision is durable now, so a handoff failure is reported apart
    // from it and left retryable rather than described as a lost decision.
    if (review.status === "confirmed" || review.status === "overridden") {
      try {
        await completeCase(token, item.case_id);
      } catch {
        // "Decision recorded" and "decision lost" must not both be shown.
        setHandoffFailed(true);
      }
    }
    setWorking(false);
  }

  const recommendation: Recommendation | undefined = start?.recommendation;
  const factors = recommendation?.factors ?? [];
  const route =
    recommendation?.route ?? item.route ?? "unavailable";
  const needsInformation = route === "needs_information";
  const decided = Boolean(result);
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
        <div
          className={handoffFailed ? "notice-card" : "success-card"}
          role="status"
        >
          <strong>Decision recorded.</strong>{" "}
          <span>{decisionSummary(result)}</span>
          {handoffFailed ? (
            <span>
              The queue handoff did not complete, so this case is not in
              the completed queue yet.
            </span>
          ) : null}
        </div>
      ) : null}
      {handoffFailed ? (
        <Button disabled={working} onClick={retryHandoff} variant="secondary">
          {working ? "Retrying…" : "Retry handoff"}
        </Button>
      ) : null}
      <div className="review-layout">
        <div className="review-main">
          <section className="recommendation-card">
            <div className="rec-kicker">
              <span>System recommendation</span>
              <span className="advisory">Advisory only</span>
            </div>
            <div className="rec-content">
              <div>
                <h2>{route}</h2>
                <p>
                  {factors.length > 0
                    ? "Deterministic rules and extracted evidence produced "
                      + "this route."
                    : canReview
                      ? "The workflow is assembling an evidence-backed "
                        + "summary."
                      : "This case is closed to further review decisions."}
                </p>
              </div>
              {item.specialist ? (
                <span className="specialist-tag">Specialist</span>
              ) : null}
            </div>
            {factors.length > 0 && !needsInformation ? (
              <div className="reason-box">
                <Icon name="alert" />
                <div>
                  <b>Why this route</b>
                  <ul>
                    {factors.map((entry) => (
                      <li key={entry}>
                        {entry === "specialist_signal"
                          ? "Evidence requires specialist review."
                          : entry.replaceAll("_", " ")}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
            <p className="disclaimer">
              <Icon name="shield" />
              Triage only. An underwriter confirms every final route.
            </p>
          </section>
          {start ? <EvidencePanel pack={start} token={token} /> : null}
          <GuidancePanel
            caseId={item.case_id}
            onSuggestions={setSuggestions}
            token={token}
          />
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
        <ReviewActions
          decided={decided}
          locked={locked}
          needsInformation={needsInformation}
          onDecision={handleDecision}
          onOverrideChange={setOverriding}
          onReasonChange={setReason}
          onRouteChange={setSelectedRoute}
          onSpecialistLabelChange={setSpecialistLabel}
          overriding={overriding}
          reason={reason}
          selectedRoute={selectedRoute}
          specialistLabel={specialistLabel}
          start={start}
          suggestedCitations={suggestions}
        />
      </div>
    </>
  );
}
