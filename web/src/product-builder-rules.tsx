// Routing-rule and specialist-label editors.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderCondition,
  BuilderRoute,
  BuilderRoutingRule,
} from "./product-builder-state";
import { AppliesToEditor } from "./product-builder-shared";
import type { JourneyType } from "./types";

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

const OPERATORS: BuilderCondition["operator"][] = ["equals", "greater_than"];

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
  const [operator, setOperator] =
    useState<BuilderCondition["operator"]>("greater_than");
  const [value, setValue] = useState("");
  const [route, setRoute] = useState<BuilderRoute>("standard");
  const [specialistLabel, setSpecialistLabel] = useState("");
  const [appliesTo, setAppliesTo] = useState<JourneyType[]>(
    configuration.supported_journeys,
  );

  // Reset the inline add-rule form to its empty defaults.
  function resetDraft() {
    setCode("");
    setConditionField("");
    setOperator("greater_than");
    setValue("");
    setRoute("standard");
    setSpecialistLabel("");
    setAppliesTo(configuration.supported_journeys);
    setAdding(false);
  }

  // Append the drafted routing rule and close the form.
  function saveRule() {
    if (!code.trim() || appliesTo.length === 0) return;
    if (route === "specialist" && !specialistLabel.trim()) return;
    const rule: BuilderRoutingRule = {
      code: code.trim(),
      condition: {
        field: conditionField.trim() || configuration.fields[0]?.key || "",
        operator,
        value: parseComparisonValue(value),
      },
      route,
      specialist_label:
        route === "specialist" ? specialistLabel.trim() : undefined,
      applies_to: appliesTo,
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
            Operator
            <select
              onChange={(event) =>
                setOperator(event.target.value as BuilderCondition["operator"])
              }
              value={operator}
            >
              {OPERATORS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
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
          {route === "specialist" ? (
            <label className="field">
              Specialist label
              <select
                onChange={(event) => setSpecialistLabel(event.target.value)}
                value={specialistLabel}
              >
                <option value="">Select a specialist label</option>
                {configuration.specialist_labels.map((label) => (
                  <option key={label} value={label}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <AppliesToEditor
            appliesTo={appliesTo}
            onChange={setAppliesTo}
            supported={configuration.supported_journeys}
          />
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
