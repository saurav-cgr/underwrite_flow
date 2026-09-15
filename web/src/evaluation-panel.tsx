import { useState } from "react";

import { ApiError, runEvaluation } from "./api";
import { Button, EmptyState, Panel } from "./components";
import type { EvaluationSplit, EvaluationSummary } from "./types";

const SPLITS: { value: string; label: string }[] = [
  { value: "", label: "All 90 synthetic cases" },
  { value: "development", label: "Development split (60 cases)" },
  { value: "holdout", label: "Holdout split (30 cases)" },
];

interface Metric {
  key: keyof EvaluationSummary;
  label: string;
  rate: boolean;
}

const METRICS: Metric[] = [
  { key: "case_count", label: "Cases evaluated", rate: false },
  { key: "route_agreement", label: "Route agreement", rate: true },
  { key: "specialist_recall", label: "Specialist recall", rate: true },
  { key: "conflict_detection", label: "Conflict recall", rate: true },
  { key: "conflict_precision", label: "Conflict precision", rate: true },
  { key: "missing_data_detection", label: "Missing recall", rate: true },
  { key: "missing_precision", label: "Missing precision", rate: true },
  { key: "evidence_accuracy", label: "Evidence accuracy", rate: true },
  {
    key: "unsupported_claim_rate",
    label: "Unsupported claim rate",
    rate: true,
  },
  { key: "workflow_reliability", label: "Workflow reliability", rate: true },
  { key: "routable_count", label: "Routed on merit", rate: false },
  {
    key: "needs_information_count",
    label: "Held for information",
    rate: false,
  },
];

// Read a validated split from the selector value.
function splitFromValue(value: string): EvaluationSplit | "" {
  return value === "development" || value === "holdout" ? value : "";
}

// Format one produced metric for display.
function formatMetric(metric: Metric, summary: EvaluationSummary): string {
  const value = summary[metric.key];
  if (typeof value !== "number") return "—";
  return metric.rate ? `${Math.round(value * 100)}%` : String(value);
}

// Run the synthetic reference set and report every produced metric.
export function EvaluationPanel({ token }: { token: string }) {
  const [split, setSplit] = useState<EvaluationSplit | "">("");
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [message, setMessage] = useState("");
  const [working, setWorking] = useState(false);

  // Run the reference set and keep the aggregate metrics it produced.
  async function handleRun() {
    setWorking(true);
    setMessage("");
    try {
      setSummary(await runEvaluation(token, split || undefined));
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The evaluation could not be run.",
      );
    } finally {
      setWorking(false);
    }
  }

  return (
    <Panel title="Reference evaluation">
      <div className="eval-controls">
        <label className="field" htmlFor="evaluation-split">
          <span>Case split</span>
          <select
            disabled={working}
            id="evaluation-split"
            onChange={(event) => setSplit(splitFromValue(event.target.value))}
            value={split}
          >
            {SPLITS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <Button disabled={working} onClick={handleRun}>
          {working ? "Running…" : "Run evaluation"}
        </Button>
      </div>
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      {summary ? (
        <>
          <div className="metric-strip wide">
            {METRICS.map((metric) => (
              <div key={metric.key}>
                <strong>{formatMetric(metric, summary)}</strong>
                <span>{metric.label}</span>
              </div>
            ))}
          </div>
          <p className="chart-note">
            Every metric is calculated from what the pipeline produced, not
            from the reference labels. Route agreement covers only the{" "}
            {summary.routable_count} cases the pipeline had enough evidence to
            route; the other {summary.needs_information_count} are measured by
            missing-information precision. Split: {summary.split}.
          </p>
        </>
      ) : (
        <EmptyState
          title="No evaluation run yet"
          detail={
            "Run the synthetic reference set to see route, detection, and "
            + "provenance metrics for the current pipeline."
          }
        />
      )}
    </Panel>
  );
}
