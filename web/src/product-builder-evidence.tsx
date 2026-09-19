// Applicant-field and staged-document editors for the guided builder.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderDocument,
  BuilderField,
} from "./product-builder-state";
import type { DocumentStage } from "./types";

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

  // Reset the inline add-field form to its empty defaults.
  function resetDraft() {
    setKey("");
    setLabel("");
    setType("text");
    setRequired(false);
    setHelpText("");
    setAdding(false);
  }

  // Append the drafted field to the configuration and close the form.
  function saveField() {
    if (!key.trim() || !label.trim()) return;
    const field: BuilderField = {
      key: key.trim(),
      label: label.trim(),
      type,
      required,
      help_text: helpText.trim(),
      validation: {},
      options: [],
      applies_to: configuration.supported_journeys,
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

  // Reset the inline add-document form to its empty defaults.
  function resetDraft() {
    setCode("");
    setTitle("");
    setStage("supporting");
    setAdding(false);
  }

  // Append the drafted document requirement and close the form.
  function saveDocument() {
    if (!code.trim() || !title.trim()) return;
    const document: BuilderDocument = {
      code: code.trim(),
      title: title.trim(),
      requirement: "required",
      accepted_types: ["application/pdf"],
      stage,
      applies_to: configuration.supported_journeys,
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
