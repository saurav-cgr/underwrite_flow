// Routing-rule, reconciliation, and specialist-label editors.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderReconciliation,
  BuilderRoute,
  BuilderRoutingRule,
} from "./product-builder-state";
import type { ReconciliationKind } from "./types";

interface SectionProps {
  configuration: BuilderConfiguration;
  onChange: (next: BuilderConfiguration) => void;
}

const ROUTES: BuilderRoute[] = [
  "expedited",
  "standard",
  "specialist",
  "needs_information",
  "manual",
];

// Parse a routing-rule comparison value as a number when it looks numeric.
function parseComparisonValue(raw: string): string | number {
  if (raw.trim() === "") return raw;
  const numeric = Number(raw);
  return Number.isNaN(numeric) ? raw : numeric;
}

// Add or remove the deterministic routing rules for this product.
export function RoutingRulesSection({ configuration, onChange }: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [conditionField, setConditionField] = useState("");
  const [value, setValue] = useState("");
  const [route, setRoute] = useState<BuilderRoute>("standard");

  // Reset the inline add-rule form to its empty defaults.
  function resetDraft() {
    setCode("");
    setConditionField("");
    setValue("");
    setRoute("standard");
    setAdding(false);
  }

  // Append the drafted routing rule and close the form.
  function saveRule() {
    if (!code.trim()) return;
    const rule: BuilderRoutingRule = {
      code: code.trim(),
      condition: {
        field: conditionField.trim() || configuration.fields[0]?.key || "",
        operator: "greater_than",
        value: parseComparisonValue(value),
      },
      route,
      applies_to: configuration.supported_journeys,
    };
    onChange({
      ...configuration,
      routing_rules: [...configuration.routing_rules, rule],
    });
    resetDraft();
  }

  // Remove one routing rule by its stable code.
  function removeRule(ruleCode: string) {
    onChange({
      ...configuration,
      routing_rules: configuration.routing_rules.filter(
        (rule) => rule.code !== ruleCode,
      ),
    });
  }

  return (
    <section aria-labelledby="section-routing-rules">
      <h2 id="section-routing-rules">Routing rules</h2>
      {configuration.routing_rules.length === 0 ? (
        <p className="muted">No routing rules yet.</p>
      ) : (
        <ul aria-label="Routing rules" className="mini-list">
          {configuration.routing_rules.map((rule) => (
            <li key={rule.code}>
              <span>
                {rule.code} → {rule.route}
              </span>
              <Button onClick={() => removeRule(rule.code)} variant="quiet">
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="inline-form">
          <label className="field">
            Rule code
            <input
              onChange={(event) => setCode(event.target.value)}
              value={code}
            />
          </label>
          <label className="field">
            Comparison field
            <input
              onChange={(event) => setConditionField(event.target.value)}
              value={conditionField}
            />
          </label>
          <label className="field">
            Comparison value
            <input
              onChange={(event) => setValue(event.target.value)}
              value={value}
            />
          </label>
          <label className="field">
            Route
            <select
              onChange={(event) =>
                setRoute(event.target.value as BuilderRoute)
              }
              value={route}
            >
              {ROUTES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={saveRule}>Save routing rule</Button>
        </div>
      ) : (
        <Button onClick={() => setAdding(true)} variant="secondary">
          Add routing rule
        </Button>
      )}
    </section>
  );
}

const RECONCILIATION_KINDS: ReconciliationKind[] = [
  "ncb_match",
  "asset_match",
  "policy_lapse",
];

// Add or remove cross-document reconciliation checks for this product.
export function ReconciliationSection({
  configuration,
  onChange,
}: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [kind, setKind] = useState<ReconciliationKind>("ncb_match");
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");

  // Reset the inline add-check form to its empty defaults.
  function resetDraft() {
    setCode("");
    setKind("ncb_match");
    setSource("");
    setTarget("");
    setAdding(false);
  }

  // Append the drafted reconciliation check and close the form.
  function saveCheck() {
    if (!code.trim()) return;
    const check: BuilderReconciliation = {
      code: code.trim(),
      kind,
      inputs: source.trim() && target.trim()
        ? { [source.trim()]: target.trim() }
        : {},
      applies_to: configuration.supported_journeys,
    };
    onChange({
      ...configuration,
      reconciliations: [...configuration.reconciliations, check],
    });
    resetDraft();
  }

  // Remove one reconciliation check by its stable code.
  function removeCheck(checkCode: string) {
    onChange({
      ...configuration,
      reconciliations: configuration.reconciliations.filter(
        (check) => check.code !== checkCode,
      ),
    });
  }

  return (
    <section aria-labelledby="section-reconciliation">
      <h2 id="section-reconciliation">Reconciliation</h2>
      {configuration.reconciliations.length === 0 ? (
        <p className="muted">No reconciliation checks yet.</p>
      ) : (
        <ul aria-label="Reconciliation checks" className="mini-list">
          {configuration.reconciliations.map((check) => (
            <li key={check.code}>
              <span>
                {check.code} ({check.kind})
              </span>
              <Button onClick={() => removeCheck(check.code)} variant="quiet">
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="inline-form">
          <label className="field">
            Reconciliation code
            <input
              onChange={(event) => setCode(event.target.value)}
              value={code}
            />
          </label>
          <label className="field">
            Kind
            <select
              onChange={(event) =>
                setKind(event.target.value as ReconciliationKind)
              }
              value={kind}
            >
              {RECONCILIATION_KINDS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Source field
            <input
              onChange={(event) => setSource(event.target.value)}
              value={source}
            />
          </label>
          <label className="field">
            Compared field
            <input
              onChange={(event) => setTarget(event.target.value)}
              value={target}
            />
          </label>
          <Button onClick={saveCheck}>Save reconciliation</Button>
        </div>
      ) : (
        <Button onClick={() => setAdding(true)} variant="secondary">
          Add reconciliation
        </Button>
      )}
    </section>
  );
}

// Add or remove the specialist labels routing rules may hand off to.
export function SpecialistLabelsSection({
  configuration,
  onChange,
}: SectionProps) {
  const [label, setLabel] = useState("");

  // Append the drafted label to the configuration's unique label set.
  function addLabel() {
    const trimmed = label.trim();
    if (!trimmed || configuration.specialist_labels.includes(trimmed)) return;
    onChange({
      ...configuration,
      specialist_labels: [...configuration.specialist_labels, trimmed],
    });
    setLabel("");
  }

  // Remove one specialist label from the configuration.
  function removeLabel(target: string) {
    onChange({
      ...configuration,
      specialist_labels: configuration.specialist_labels.filter(
        (item) => item !== target,
      ),
    });
  }

  return (
    <section aria-labelledby="section-specialist-labels">
      <h2 id="section-specialist-labels">Specialist labels</h2>
      {configuration.specialist_labels.length === 0 ? (
        <p className="muted">No specialist labels yet.</p>
      ) : (
        <ul aria-label="Specialist labels" className="mini-list">
          {configuration.specialist_labels.map((item) => (
            <li key={item}>
              <span>{item}</span>
              <Button onClick={() => removeLabel(item)} variant="quiet">
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      <label className="field">
        Specialist label
        <input
          onChange={(event) => setLabel(event.target.value)}
          value={label}
        />
      </label>
      <Button onClick={addLabel}>Add label</Button>
    </section>
  );
}
