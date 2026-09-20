// Staged-document editor for the guided builder.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderCondition,
  BuilderDocument,
} from "./product-builder-state";
import type { DocumentStage, JourneyType } from "./types";
import {
  AppliesToEditor,
  RequiredForEditor,
  parseComparisonValue,
} from "./product-builder-shared";

const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png"];

interface SectionProps {
  configuration: BuilderConfiguration;
  onChange: (next: BuilderConfiguration) => void;
}

const DOCUMENT_STAGES: DocumentStage[] = ["supporting", "prior_policy"];

const REQUIREMENTS: BuilderDocument["requirement"][] = [
  "required",
  "optional",
  "conditional",
  "not_applicable",
];

const OPERATORS: BuilderCondition["operator"][] = ["equals", "greater_than"];

// Add or remove the staged document requirements for this product.
export function DocumentsSection({ configuration, onChange }: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [stage, setStage] = useState<DocumentStage>("supporting");
  const [requirement, setRequirement] =
    useState<BuilderDocument["requirement"]>("required");
  const [conditionField, setConditionField] = useState("");
  const [operator, setOperator] =
    useState<BuilderCondition["operator"]>("greater_than");
  const [value, setValue] = useState("");
  const [requiredFor, setRequiredFor] = useState<JourneyType[]>([]);
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
    setRequirement("required");
    setConditionField("");
    setOperator("greater_than");
    setValue("");
    setRequiredFor([]);
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
    if (requirement === "conditional" && !conditionField.trim()) return;
    const document: BuilderDocument = {
      code: code.trim(),
      title: title.trim(),
      requirement,
      accepted_types: acceptedTypes,
      stage,
      applies_to: appliesTo,
      condition: requirement === "conditional"
        ? {
            field: conditionField.trim(),
            operator,
            value: parseComparisonValue(value),
          }
        : undefined,
      required_for:
        requirement === "not_applicable" || requiredFor.length === 0
          ? undefined
          : requiredFor,
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
          <label className="field">
            Requirement
            <select
              onChange={(event) =>
                setRequirement(
                  event.target.value as BuilderDocument["requirement"],
                )
              }
              value={requirement}
            >
              {REQUIREMENTS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          {requirement === "conditional" ? (
            <>
              <label className="field">
                Condition field
                <select
                  onChange={(event) => setConditionField(event.target.value)}
                  value={conditionField}
                >
                  <option value="">Select a field</option>
                  {configuration.fields.map((field) => (
                    <option key={field.key} value={field.key}>
                      {field.key}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Condition operator
                <select
                  onChange={(event) =>
                    setOperator(
                      event.target.value as BuilderCondition["operator"],
                    )
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
                Condition value
                <input
                  onChange={(event) => setValue(event.target.value)}
                  value={value}
                />
              </label>
            </>
          ) : null}
          {requirement === "not_applicable" ? null : (
            <RequiredForEditor
              onChange={setRequiredFor}
              requiredFor={requiredFor}
              supported={appliesTo}
            />
          )}
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
