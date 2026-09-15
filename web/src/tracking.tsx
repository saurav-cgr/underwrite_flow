import { useEffect, useState } from "react";

import { ApiError, readCase } from "./api";
import { Badge, Button, Journey, PageHeading, Panel } from "./components";
import { Icon } from "./icons";
import { applicantNextStep } from "./ui-state";
import type { CaseRecord, Screen } from "./types";

// Show case status, versions, and the human-governance boundary.
export function TrackingScreen({
  caseRecord,
  token,
  onNavigate,
}: {
  caseRecord: CaseRecord | null;
  token: string;
  onNavigate: (screen: Screen) => void;
}) {
  const [current, setCurrent] = useState(caseRecord);
  const [message, setMessage] = useState("");

  // Refresh the case status without retaining raw application evidence.
  useEffect(() => {
    if (!caseRecord) return;
    readCase(token, caseRecord.id)
      .then((refreshed) => {
        setCurrent(refreshed);
        setMessage("");
      })
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The case status could not be refreshed.",
        ),
      );
  }, [caseRecord, token]);

  if (!current) {
    return (
      <Panel>
        <div className="empty-state">
          <h2>No case to track</h2>
          <p>Start a fictional application to see its progress here.</p>
          <Button onClick={() => onNavigate("products")}>
            Start an application
          </Button>
        </div>
      </Panel>
    );
  }

  const done =
    current.status === "completed"
      ? 3
      : current.status === "underwriter_review"
        ? 2
        : current.status === "new"
          ? 1
          : 2;
  const nextStep = applicantNextStep(current.status);
  return (
    <>
      <PageHeading
        eyebrow="Case tracking"
        title={nextStep.title}
        description={
          `Case ${current.id.slice(0, 8)} · configuration `
          + current.product_version
        }
        action={
          <Badge tone={current.status}>
            {current.status.replaceAll("_", " ")}
          </Badge>
        }
      />
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      <Panel title="Next step">
        <p>{nextStep.detail}</p>
        {nextStep.screen !== "tracking" ? (
          <Button onClick={() => onNavigate(nextStep.screen)}>
            {nextStep.action}
          </Button>
        ) : null}
      </Panel>
      <Journey current={done} />
      <Panel title="Pinned record">
        <div className="facts-grid">
          <div>
            <small>Product</small>
            <b>{current.product_code}</b>
          </div>
          <div>
            <small>Rulebook</small>
            <b>{current.rulebook_version}</b>
          </div>
          <div>
            <small>Case ID</small>
            <b>{current.id.slice(0, 18)}…</b>
          </div>
        </div>
      </Panel>
      <Panel title="Human confirmation">
        <div className="human-note">
          <Icon name="shield" />
          <div>
            <b>An underwriter must confirm the route.</b>
            <p>
              UnderwriteFlow recommends a triage route only. It never
              approves, declines, binds, prices, issues, renews or cancels
              coverage.
            </p>
          </div>
        </div>
      </Panel>
    </>
  );
}
