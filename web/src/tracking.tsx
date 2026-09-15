import { useEffect, useState } from "react";

import { readCase } from "./api";
import { Badge, Button, Journey, PageHeading, Panel } from "./components";
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

  // Refresh the case status without retaining raw application evidence.
  useEffect(() => {
    if (caseRecord) {
      readCase(token, caseRecord.id)
        .then(setCurrent)
        .catch(() => undefined);
    }
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
  return (
    <>
      <PageHeading
        eyebrow="Case tracking"
        title="Your submission has a clear next step."
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
      <Journey current={done} />
      <Panel title="Pinned record">
        <div className="detail-grid">
          <div>
            <span className="metric-label">Product</span>
            <strong>{current.product_code}</strong>
          </div>
          <div>
            <span className="metric-label">Rulebook</span>
            <strong>{current.rulebook_version}</strong>
          </div>
          <div>
            <span className="metric-label">Case ID</span>
            <strong>{current.id.slice(0, 18)}…</strong>
          </div>
        </div>
      </Panel>
      <div className="notice-card">
        <span className="notice-mark" aria-hidden="true">
          i
        </span>
        <div>
          <strong>Human confirmation is required.</strong>
          <p>
            UnderwriteFlow recommends a triage route only. An authenticated
            underwriter must confirm the route before completion.
          </p>
        </div>
      </div>
    </>
  );
}
