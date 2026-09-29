import { Button } from "./components";
import { Icon } from "./icons";
import type { ReviewStart } from "./types";

const ROUTES = [
  {
    value: "expedited",
    label: "Expedited review",
    detail: "Evidence is complete with no open conflicts.",
  },
  {
    value: "standard",
    label: "Standard review",
    detail: "Routine checks before a decision is made.",
  },
  {
    value: "specialist",
    label: "Specialist review",
    detail: "Routes to a named specialist queue.",
  },
];

// Render route selection and underwriter action controls.
export function ReviewActions({
  start,
  selectedRoute,
  specialistLabel,
  reason,
  locked,
  decided,
  needsInformation,
  overriding,
  onRouteChange,
  onSpecialistLabelChange,
  onReasonChange,
  onDecision,
  onOverrideChange,
}: {
  start: ReviewStart | null;
  selectedRoute: string;
  specialistLabel: string;
  reason: string;
  locked: boolean;
  decided: boolean;
  needsInformation: boolean;
  overriding: boolean;
  onRouteChange: (route: string) => void;
  onSpecialistLabelChange: (label: string) => void;
  onReasonChange: (reason: string) => void;
  onDecision: (action: "confirm" | "override" | "request_information") => void;
  onOverrideChange: (value: boolean) => void;
}) {
  const showRouteOptions = !needsInformation || overriding;
  return (
    <aside className="decision-panel">
      <h2>Your decision</h2>
      <p className="muted">
        {needsInformation && !overriding
          ? "Request the missing information, or override to a final route."
          : "Pick the route this case should follow, then confirm or "
            + "override."}
      </p>
      {showRouteOptions ? (
        <fieldset className="route-options">
          <legend className="sr-only">Final triage route</legend>
          {ROUTES.map((option) => (
            <label
              className={selectedRoute === option.value ? "selected" : ""}
              key={option.value}
            >
              <input
                checked={selectedRoute === option.value}
                disabled={locked}
                name="route"
                onChange={() => onRouteChange(option.value)}
                type="radio"
                value={option.value}
              />
              <span>
                <b>{option.label}</b>
                <small>{option.detail}</small>
              </span>
            </label>
          ))}
        </fieldset>
      ) : null}
      {showRouteOptions && selectedRoute === "specialist" ? (
        <label className="field">
          <span>Specialist label</span>
          <select
            disabled={locked}
            onChange={(event) => onSpecialistLabelChange(event.target.value)}
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
          disabled={locked}
          onChange={(event) => onReasonChange(event.target.value)}
          placeholder="Required for an override or information request."
          value={reason}
        />
      </label>
      <div className="decision-actions">
        {needsInformation && !overriding ? (
          <>
            <Button
              disabled={locked || decided}
              onClick={() => onDecision("request_information")}
            >
              Request information
            </Button>
            <Button
              disabled={locked || decided}
              onClick={() => onOverrideChange(true)}
              variant="secondary"
            >
              Override route
            </Button>
          </>
        ) : (
          <>
            <Button
              disabled={locked || decided}
              onClick={() =>
                onDecision(needsInformation ? "override" : "confirm")
              }
            >
              {needsInformation ? "Confirm override" : "Confirm recommendation"}
            </Button>
            <Button
              disabled={locked || decided}
              onClick={() =>
                needsInformation
                  ? onOverrideChange(false)
                  : onDecision("override")
              }
              variant="secondary"
            >
              {needsInformation ? "Cancel override" : "Override route"}
            </Button>
            {!needsInformation ? (
              <Button
                disabled={locked || decided}
                onClick={() => onDecision("request_information")}
                variant="quiet"
              >
                Request information
              </Button>
            ) : null}
          </>
        )}
      </div>
      <p className="audit-hint">
        <Icon name="log" />
        Every decision is written to the immutable audit trail.
      </p>
    </aside>
  );
}
