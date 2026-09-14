import type {
  ProductDocument,
  ProductField,
  Role,
  Screen,
} from "./types";

// Choose the first useful screen for an authenticated role.
export function homeScreenForRole(role: Role): Screen {
  if (role === "Applicant") return "dashboard";
  if (role === "Underwriter") return "queue";
  return "admin";
}

// Return only fields that are currently visible for the application values.
export function visibleFields(
  fields: ProductField[],
  values: Record<string, unknown>,
): ProductField[] {
  return fields.filter((field) => {
    const condition = field.visible_when;
    return !condition || values[condition.field] === condition.equals;
  });
}

// Validate visible required fields and return field-linked messages.
export function validateFields(
  fields: ProductField[],
  values: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of visibleFields(fields, values)) {
    if (
      field.required &&
      (values[field.key] === undefined || values[field.key] === "")
    ) {
      errors[field.key] = "This field is required.";
    }
  }
  return errors;
}

// Return configured document codes accepted by the intake contract.
export function allDocumentCodes(documents: ProductDocument[]): string[] {
  return documents
    .filter((document) => document.requirement !== "not_applicable")
    .map((document) => document.code);
}
