import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createCase } from "./api";
import {
  Button,
  ErrorSummary,
  Journey,
  PageHeading,
  Panel,
} from "./components";
import {
  allDocumentCodes,
  validateFields,
  visibleFields,
} from "./ui-state";
import type { CaseRecord, ProductCatalogItem, Screen } from "./types";

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
