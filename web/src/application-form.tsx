import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createCase, updateApplication } from "./api";
import {
  Button,
  ErrorSummary,
  Journey,
  PageHeading,
} from "./components";
import { Icon } from "./icons";
import {
  allDocumentCodes,
  validateFields,
  visibleFields,
} from "./ui-state";
import type {
  CaseRecord,
  JourneyType,
  ProductCatalogItem,
  ProductField,
  Screen,
} from "./types";

type FieldChange = (
  key: string,
  type: string,
  rawValue: string,
  checked: boolean,
) => void;

// Render one typed product field with its hint, error and aria wiring.
function ProductFieldInput({
  field,
  error,
  onChange,
  value,
}: {
  field: ProductField;
  error?: string;
  onChange: FieldChange;
  value: unknown;
}) {
  const hintId = `${field.key}-hint`;
  const errorId = `${field.key}-error`;
  const describedBy = error ? `${hintId} ${errorId}` : hintId;
  const numeric = field.type === "integer" || field.type === "number";
  const controlProps = {
    "aria-describedby": describedBy,
    "aria-invalid": error ? true : undefined,
    "aria-required": field.required || undefined,
    id: field.key,
  };
  return (
    <div className="field">
      <label className="field-name" htmlFor={field.key}>
        {field.label}
        {field.required ? (
          <span aria-hidden="true" className="required-note"> *</span>
        ) : null}
      </label>
      <small id={hintId}>{field.help_text}</small>
      {field.type === "boolean" ? (
        <input
          {...controlProps}
          checked={Boolean(value)}
          onChange={(event) =>
            onChange(field.key, field.type, "", event.target.checked)
          }
          type="checkbox"
        />
      ) : field.type === "enum" ? (
        <select
          {...controlProps}
          onChange={(event) =>
            onChange(field.key, field.type, event.target.value, false)
          }
          value={String(value ?? "")}
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
          {...controlProps}
          max={field.validation.maximum}
          min={field.validation.minimum}
          onChange={(event) =>
            onChange(field.key, field.type, event.target.value, false)
          }
          type={numeric ? "number" : field.type}
          value={String(value ?? "")}
        />
      )}
      {error ? (
        <em className="field-error" id={errorId}>
          {error}
        </em>
      ) : null}
    </div>
  );
}

// Render the active product's typed application form with linked errors.
// A supplied `caseRecord` means this is a renewal's staged form step, so
// the draft case created before prior-policy upload is updated in place
// instead of creating a second case.
export function ApplicationForm({
  product,
  journey,
  token,
  caseRecord,
  initialValues,
  onCreated,
  onNavigate,
}: {
  product: ProductCatalogItem;
  journey: JourneyType;
  token: string;
  caseRecord?: CaseRecord | null;
  initialValues?: Record<string, unknown>;
  onCreated: (caseRecord: CaseRecord, product: ProductCatalogItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [values, setValues] = useState<Record<string, unknown>>(
    initialValues ?? {},
  );
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
      const documentCodes = allDocumentCodes(product.documents);
      const saved = caseRecord
        ? await updateApplication(token, caseRecord.id, {
            payload: values,
            document_codes: documentCodes,
          })
        : await createCase(token, {
            product_code: product.product_code,
            idempotency_key: crypto.randomUUID(),
            journey,
            payload: values,
            document_codes: documentCodes,
          });
      onCreated(saved, product);
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
          <Button
            onClick={() => onNavigate(caseRecord ? "documents" : "products")}
            variant="quiet"
          >
            {caseRecord ? "Back to documents" : "Change product"}
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
          <div className="form-card">
            <div className="card-section">
              <div>
                <h2>Application facts</h2>
                <span>Stored as submitted facts</span>
              </div>
              <span>{fields.length} visible fields</span>
            </div>
            <div className="form-grid">
              {fields.map((field) => (
                <ProductFieldInput
                  error={errors[field.key] || undefined}
                  field={field}
                  key={field.key}
                  onChange={handleChange}
                  value={values[field.key]}
                />
              ))}
            </div>
            <div className="form-actions">
              <Button
                onClick={() =>
                  onNavigate(caseRecord ? "documents" : "products")
                }
                variant="quiet"
              >
                Cancel
              </Button>
              <Button type="submit">Continue to documents</Button>
            </div>
          </div>
        </div>
        <aside className="help-panel">
          <Icon name="shield" />
          <h2>Fictional data only</h2>
          <p>
            This demonstration accepts synthetic applicant and document
            details. Do not enter real personal or insurance information.
          </p>
          <hr />
          <p>
            Fields and document requirements come from configuration
            version {product.version}.
          </p>
        </aside>
      </form>
    </>
  );
}
