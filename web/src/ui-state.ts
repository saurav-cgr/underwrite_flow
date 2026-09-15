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

// Return a stable short hash for one YAML document's exact text.
export function yamlHash(text: string): string {
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 31 + text.charCodeAt(index)) | 0;
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}


// Report whether a case still needs applicant or underwriter attention.
export function isOpenCase(status: string): boolean {
  return status !== "completed";
}

// Return the two-letter avatar initials for a synthetic demo identity.
export function identityInitials(email: string): string {
  const local = email.split("@")[0] ?? "";
  const letters = local.replace(/[^a-z]/gi, "");
  return (letters.slice(0, 2) || "??").toUpperCase();
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

// Return only product-configured documents mandatory for an application.
export function requiredDocuments(
  documents: ProductDocument[],
): ProductDocument[] {
  return documents.filter((document) => document.requirement === "required");
}
