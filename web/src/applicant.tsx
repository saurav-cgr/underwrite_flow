import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  createCase,
} from "./api";
import {
  allDocumentCodes,
  validateFields,
  visibleFields,
} from "./ui-state";
import type {
  CaseRecord,
  ProductCatalogItem,
  Screen,
} from "./types";
import {
  Button,
  ErrorSummary,
  Journey,
  PageHeading,
  Panel,
} from "./components";

// Show the applicant landing view and the next safe action.
export function ApplicantDashboard({
  onNavigate,
  caseRecord,
}: {
  onNavigate: (screen: Screen) => void;
  caseRecord: CaseRecord | null;
}) {
  return (
    <>
      <PageHeading
        eyebrow="Applicant dashboard"
        title="Keep your submission moving."
        description={
          "A clear view of what UnderwriteFlow has received and what "
          + "needs your attention."
        }
        action={
          <Button onClick={() => onNavigate("products")}>
            Start an application
          </Button>
        }
      />
      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-label">Active cases</span>
          <strong>{caseRecord ? "01" : "00"}</strong>
          <span>
            {caseRecord ? "One case in progress" : "No submissions yet"}
          </span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Human review</span>
          <strong>
            {caseRecord?.status === "underwriter_review" ? "Ready" : "—"}
          </strong>
          <span>Every final route is confirmed by an underwriter.</span>
        </div>
        <div className="metric-card metric-accent">
          <span className="metric-label">Data boundary</span>
          <strong>Local</strong>
          <span>
            Fictional demonstration data stays inside this workspace.
          </span>
        </div>
      </div>
      <Panel title="Your next step">
        <div className="next-step">
          <div>
            <span className="step-number">{caseRecord ? "02" : "01"}</span>
            <div>
              <h2>
                {caseRecord ? "Add supporting documents" : "Choose a product"}
              </h2>
              <p>
                {caseRecord
                  ? "Upload the requested evidence so the review team can "
                    + "reconcile your submission."
                  : "Select a fictional product configuration to begin."}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            onClick={() => onNavigate(caseRecord ? "documents" : "products")}
          >
            {caseRecord ? "Open documents" : "Browse products"}
          </Button>
        </div>
      </Panel>
      <Panel title="How the review works">
        <div className="three-up">
          <div>
            <span className="eyebrow">01 / Submit</span>
            <p>Provide fictional application facts and supporting evidence.</p>
          </div>
          <div>
            <span className="eyebrow">02 / Organize</span>
            <p>
              Rules and extraction surface missing or conflicting information.
            </p>
          </div>
          <div>
            <span className="eyebrow">03 / Confirm</span>
            <p>An authenticated underwriter confirms the final triage route.</p>
          </div>
        </div>
      </Panel>
    </>
  );
}

// Show server-owned active product configurations for selection.
export function ProductSelection({
  catalog,
  error,
  onSelect,
  onNavigate,
}: {
  catalog: ProductCatalogItem[];
  error?: string;
  onSelect: (product: ProductCatalogItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  return (
    <>
      <PageHeading
        eyebrow="New application"
        title="Choose a product."
        description={
          "The fields and document requirements below come from the active "
          + "backend configuration."
        }
        action={
          <Button variant="quiet" onClick={() => onNavigate("dashboard")}>
            Back to overview
          </Button>
        }
      />
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {catalog.length === 0 ? (
        <Panel>
          <div className="empty-state">
            <h2>No active products</h2>
            <p>
              An administrator must activate a fictional product configuration
              before applications can be submitted.
            </p>
          </div>
        </Panel>
      ) : (
        <div className="product-grid">
          {catalog.map((product) => (
            <button
              className="product-card"
              key={product.product_code}
              onClick={() => onSelect(product)}
              type="button"
            >
              <span className="product-family">{product.family}</span>
              <h2>{product.title}</h2>
              <p>{product.description}</p>
              <span className="product-link">
                View application fields <span aria-hidden="true">→</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

// Render the active product's typed application form with linked errors.
export function ApplicationForm({
  product,
  token,
  onCreated,
  onNavigate,
}: {
  product: ProductCatalogItem;
  token: string;
  onCreated: (caseRecord: CaseRecord, product: ProductCatalogItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const fields = useMemo(
    () => visibleFields(product.fields, values),
    [product.fields, values],
  );

  // Submit the validated application to the API and preserve safe errors.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validateFields(product.fields, values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    try {
      const caseRecord = await createCase(token, {
        product_code: product.product_code,
        idempotency_key: crypto.randomUUID(),
        payload: values,
        document_codes: allDocumentCodes(product.documents),
      });
      onCreated(caseRecord, product);
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "We could not create this case.",
      );
    }
  }

  // Update one field while preserving typed boolean and numeric values.
  function handleChange(
    key: string,
    type: string,
    rawValue: string,
    checked: boolean,
  ) {
    const value =
      type === "boolean"
        ? checked
        : type === "integer" || type === "number"
          ? rawValue === ""
            ? ""
            : Number(rawValue)
          : rawValue;
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  }

  return (
    <>
      <PageHeading
        eyebrow={`${product.family} / ${product.version}`}
        title={product.title}
        description={product.scope}
        action={
          <Button variant="quiet" onClick={() => onNavigate("products")}>
            Change product
          </Button>
        }
      />
      <Journey current={0} />
      <form className="form-layout" onSubmit={handleSubmit}>
        <div>
          <ErrorSummary
            errors={Object.fromEntries(
              Object.entries(errors).filter(([, value]) => value),
            )}
          />
          {message ? (
            <p className="form-error" role="alert">
              {message}
            </p>
          ) : null}
          <Panel title="Application facts">
            <div className="field-grid">
              {fields.map((field) => (
                <label className="field" htmlFor={field.key} key={field.key}>
                  <span>
                    {field.label}
                    {field.required ? <b aria-label="required"> *</b> : null}
                  </span>
                  <small>{field.help_text}</small>
                  {field.type === "boolean" ? (
                    <input
                      checked={Boolean(values[field.key])}
                      id={field.key}
                      onChange={(event) =>
                        handleChange(
                          field.key,
                          field.type,
                          "",
                          event.target.checked,
                        )
                      }
                      type="checkbox"
                    />
                  ) : field.type === "enum" ? (
                    <select
                      aria-describedby={`${field.key}-hint`}
                      id={field.key}
                      onChange={(event) =>
                        handleChange(
                          field.key,
                          field.type,
                          event.target.value,
                          false,
                        )
                      }
                      value={String(values[field.key] ?? "")}
                    >
                      <option value="">Select one</option>
                      {field.options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      aria-describedby={`${field.key}-hint`}
                      id={field.key}
                      min={field.validation.minimum}
                      max={field.validation.maximum}
                      onChange={(event) =>
                        handleChange(
                          field.key,
                          field.type,
                          event.target.value,
                          false,
                        )
                      }
                      type={
                        field.type === "integer" || field.type === "number"
                          ? "number"
                          : field.type
                      }
                      value={String(values[field.key] ?? "")}
                    />
                  )}
                  {errors[field.key] ? (
                    <em className="field-error" id={`${field.key}-error`}>
                      {errors[field.key]}
                    </em>
                  ) : (
                    <span className="field-hint" id={`${field.key}-hint`}>
                      Stored as submitted fact.
                    </span>
                  )}
                </label>
              ))}
            </div>
          </Panel>
          <div className="form-actions">
            <Button variant="quiet" onClick={() => onNavigate("products")}>
              Cancel
            </Button>
            <Button type="submit">Continue to documents</Button>
          </div>
        </div>
        <aside className="side-note">
          <p className="eyebrow">Before you continue</p>
          <h2>Fictional data only</h2>
          <p>
            This demonstration accepts synthetic applicant and document
            details. Do not enter real personal or insurance information.
          </p>
        </aside>
      </form>
    </>
  );
}
