// Applicant-field editor for the guided builder.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderField,
} from "./product-builder-state";
import type { JourneyType } from "./types";
import { AppliesToEditor } from "./product-builder-shared";

interface SectionProps {
  configuration: BuilderConfiguration;
  onChange: (next: BuilderConfiguration) => void;
}

const FIELD_TYPES: BuilderField["type"][] = [
  "text",
  "integer",
  "number",
  "date",
  "boolean",
  "enum",
];

// Add or remove the applicant-facing fields collected during intake.
export function ApplicantFieldsSection({
  configuration,
  onChange,
}: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [type, setType] = useState<BuilderField["type"]>("text");
  const [required, setRequired] = useState(false);
  const [helpText, setHelpText] = useState("");
  const [options, setOptions] = useState("");
  const [minimum, setMinimum] = useState("");
  const [maximum, setMaximum] = useState("");
  const [appliesTo, setAppliesTo] = useState<JourneyType[]>(
    configuration.supported_journeys,
  );
  const [visibleWhenField, setVisibleWhenField] = useState("");
  const [visibleWhenValue, setVisibleWhenValue] = useState("");

  // Reset the inline add-field form to its empty defaults.
  function resetDraft() {
    setKey("");
    setLabel("");
    setType("text");
    setRequired(false);
    setHelpText("");
    setOptions("");
    setMinimum("");
    setMaximum("");
    setAppliesTo(configuration.supported_journeys);
    setVisibleWhenField("");
    setVisibleWhenValue("");
    setAdding(false);
  }

  // Append the drafted field to the configuration and close the form.
  function saveField() {
    if (!key.trim() || !label.trim() || appliesTo.length === 0) return;
    const validation: Record<string, number> = {};
    if (minimum.trim()) validation.minimum = Number(minimum);
    if (maximum.trim()) validation.maximum = Number(maximum);
    const field: BuilderField = {
      key: key.trim(),
      label: label.trim(),
      type,
      required,
      help_text: helpText.trim(),
      validation,
      options: type === "enum"
        ? options.split(",").map((item) => item.trim()).filter(Boolean)
        : [],
      applies_to: appliesTo,
      visible_when: visibleWhenField.trim()
        ? {
            field: visibleWhenField.trim(),
            operator: "equals",
            value: visibleWhenValue.trim(),
          }
        : undefined,
    };
    onChange({ ...configuration, fields: [...configuration.fields, field] });
    resetDraft();
  }

  // Remove one applicant field by its stable key.
  function removeField(fieldKey: string) {
    onChange({
      ...configuration,
      fields: configuration.fields.filter((field) => field.key !== fieldKey),
    });
  }

  return (
    <section aria-labelledby="section-applicant-fields">
      <h2 id="section-applicant-fields">Applicant fields</h2>
      {configuration.fields.length === 0 ? (
        <p className="muted">No applicant fields yet.</p>
      ) : (
        <ul aria-label="Applicant fields" className="mini-list">
          {configuration.fields.map((field) => (
            <li key={field.key}>
              <span>
                {field.label} ({field.key})
              </span>
              <Button
                onClick={() => removeField(field.key)}
                variant="quiet"
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="inline-form">
          <label className="field">
            Field key
            <input
              onChange={(event) => setKey(event.target.value)}
              value={key}
            />
          </label>
          <label className="field">
            Field label
            <input
              onChange={(event) => setLabel(event.target.value)}
              value={label}
            />
          </label>
          <label className="field">
            Field type
            <select
              onChange={(event) =>
                setType(event.target.value as BuilderField["type"])
              }
              value={type}
            >
              {FIELD_TYPES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <label className="field-inline">
            <input
              checked={required}
              onChange={(event) => setRequired(event.target.checked)}
              type="checkbox"
            />
            Required
          </label>
          <label className="field">
            Help text
            <input
              onChange={(event) => setHelpText(event.target.value)}
              value={helpText}
            />
          </label>
          {type === "enum" ? (
            <label className="field">
              Options (comma separated)
              <input
                onChange={(event) => setOptions(event.target.value)}
                value={options}
              />
            </label>
          ) : null}
          {type === "integer" || type === "number" ? (
            <>
              <label className="field">
                Minimum
                <input
                  onChange={(event) => setMinimum(event.target.value)}
                  type="number"
                  value={minimum}
                />
              </label>
              <label className="field">
                Maximum
                <input
                  onChange={(event) => setMaximum(event.target.value)}
                  type="number"
                  value={maximum}
                />
              </label>
            </>
          ) : null}
          <AppliesToEditor
            appliesTo={appliesTo}
            onChange={setAppliesTo}
            supported={configuration.supported_journeys}
          />
          <label className="field">
            Only show when field
            <input
              onChange={(event) => setVisibleWhenField(event.target.value)}
              value={visibleWhenField}
            />
          </label>
          <label className="field">
            equals value
            <input
              onChange={(event) => setVisibleWhenValue(event.target.value)}
              value={visibleWhenValue}
            />
          </label>
          <Button onClick={saveField}>Save field</Button>
        </div>
      ) : (
        <Button onClick={() => setAdding(true)} variant="secondary">
          Add field
        </Button>
      )}
    </section>
  );
}
