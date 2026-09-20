// Applicant-field and staged-document editors for the guided builder.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderDocument,
  BuilderField,
} from "./product-builder-state";
import type { DocumentStage, JourneyType } from "./types";
import { AppliesToEditor } from "./product-builder-shared";

const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png"];

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

const DOCUMENT_STAGES: DocumentStage[] = ["supporting", "prior_policy"];

// Add or remove the staged document requirements for this product.
export function DocumentsSection({ configuration, onChange }: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [stage, setStage] = useState<DocumentStage>("supporting");
  const [acceptedTypes, setAcceptedTypes] = useState<string[]>([
    "application/pdf",
  ]);
  const [appliesTo, setAppliesTo] = useState<JourneyType[]>(
    configuration.supported_journeys,
  );

  // Reset the inline add-document form to its empty defaults.
  function resetDraft() {
    setCode("");
    setTitle("");
    setStage("supporting");
    setAcceptedTypes(["application/pdf"]);
    setAppliesTo(configuration.supported_journeys);
    setAdding(false);
  }

  // Toggle one accepted content type in the drafted document's type set.
  function toggleType(type: string) {
    setAcceptedTypes(
      acceptedTypes.includes(type)
        ? acceptedTypes.filter((item) => item !== type)
        : [...acceptedTypes, type],
    );
  }

  // Append the drafted document requirement and close the form.
  function saveDocument() {
    if (
      !code.trim()
      || !title.trim()
      || acceptedTypes.length === 0
      || appliesTo.length === 0
    ) {
      return;
    }
    const document: BuilderDocument = {
      code: code.trim(),
      title: title.trim(),
      requirement: "required",
      accepted_types: acceptedTypes,
      stage,
      applies_to: appliesTo,
    };
    onChange({
      ...configuration,
      documents: [...configuration.documents, document],
    });
    resetDraft();
  }

  // Remove one document requirement by its stable code.
  function removeDocument(documentCode: string) {
    onChange({
      ...configuration,
      documents: configuration.documents.filter(
        (document) => document.code !== documentCode,
      ),
    });
  }

  return (
    <section aria-labelledby="section-documents">
      <h2 id="section-documents">Documents</h2>
      {configuration.documents.length === 0 ? (
        <p className="muted">No document requirements yet.</p>
      ) : (
        <ul aria-label="Documents" className="mini-list">
          {configuration.documents.map((document) => (
            <li key={document.code}>
              <span>
                {document.title} ({document.code})
              </span>
              <Button
                onClick={() => removeDocument(document.code)}
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
            Document code
            <input
              onChange={(event) => setCode(event.target.value)}
              value={code}
            />
          </label>
          <label className="field">
            Document title
            <input
              onChange={(event) => setTitle(event.target.value)}
              value={title}
            />
          </label>
          <label className="field">
            Stage
            <select
              onChange={(event) =>
                setStage(event.target.value as DocumentStage)
              }
              value={stage}
            >
              {DOCUMENT_STAGES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="field">
            <legend>Accepted types</legend>
            {ACCEPTED_TYPES.map((type) => (
              <label className="field-inline" key={type}>
                <input
                  checked={acceptedTypes.includes(type)}
                  onChange={() => toggleType(type)}
                  type="checkbox"
                />
                {type}
              </label>
            ))}
          </fieldset>
          <AppliesToEditor
            appliesTo={appliesTo}
            onChange={setAppliesTo}
            supported={configuration.supported_journeys}
          />
          <Button onClick={saveDocument}>Save document</Button>
        </div>
      ) : (
        <Button onClick={() => setAdding(true)} variant="secondary">
          Add document
        </Button>
      )}
    </section>
  );
}
