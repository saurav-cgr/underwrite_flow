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

export interface AuditFact {
  label: string;
  value: string;
}

// Shorten one long audit value so a hash or id stays recognisable at a glance.
function shortValue(text: string): string {
  return text.length > 24 ? `${text.slice(0, 8)}…` : text;
}

// Turn a snake_case audit key into a readable label.
export function auditLabel(key: string): string {
  const words = key.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

// Summarize audit details as bounded facts instead of one raw JSON string.
export function auditFacts(details: Record<string, unknown>): AuditFact[] {
  const facts: AuditFact[] = [];
  for (const [key, value] of Object.entries(details)) {
    if (value === null || value === undefined) continue;
    const label = auditLabel(key);
    if (Array.isArray(value)) {
      const scalars = value.filter(
        (item) => item === null || typeof item !== "object",
      );
      const allScalar = scalars.length === value.length;
      if (value.length === 0) {
        facts.push({ label, value: "none" });
      } else if (allScalar) {
        facts.push({ label, value: shortValue(scalars.join(", ")) });
      } else {
        facts.push({
          label,
          value: `${value.length} record${value.length === 1 ? "" : "s"}`,
        });
      }
      continue;
    }
    if (typeof value === "object") {
      facts.push({ label, value: "structured detail" });
      continue;
    }
    facts.push({ label, value: shortValue(String(value)) });
  }
  return facts;
}


// Report whether a case still needs applicant or underwriter attention.
export function isOpenCase(status: string): boolean {
  return status !== "completed";
}

export interface NextStep {
  title: string;
  detail: string;
  action: string;
  screen: Screen;
}

// Describe the applicant's next action for one case status, including a case
// whose processing never finished and is therefore still open for submission.
export function applicantNextStep(status: string): NextStep {
  if (status === "new") {
    return {
      title: "This case has not finished processing.",
      detail:
        "Its documents have not been submitted for review yet, so no "
        + "recommendation exists. Send the required documents to start.",
      action: "Continue documents",
      screen: "documents",
    };
  }
  if (status === "needs_information") {
    return {
      title: "More information is needed.",
      detail:
        "Review is paused until the requested evidence is supplied.",
      action: "Add information",
      screen: "documents",
    };
  }
  if (status === "underwriter_review" || status === "manual_review") {
    return {
      title: "An underwriter is reviewing this case.",
      detail:
        "No action is needed. The confirmed route appears here once an "
        + "underwriter records it.",
      action: "Refresh guidance",
      screen: "tracking",
    };
  }
  if (status === "completed") {
    return {
      title: "This case is complete.",
      detail:
        "The confirmed route was handed to its destination queue.",
      action: "View pinned record",
      screen: "tracking",
    };
  }
  return {
    title: "This case needs review.",
    detail: "Check the confirmed route and pinned configuration below.",
    action: "View pinned record",
    screen: "tracking",
  };
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

export type ReviewAction = "confirm" | "override" | "request_information";

export interface ReviewDecisionInput {
  action: ReviewAction;
  selectedRoute: string;
  recommendedRoute: string | undefined;
  specialistLabel: string;
  reason: string;
  acknowledged: boolean;
}

export interface ReviewDecisionBody {
  action: ReviewAction;
  selected_route?: string;
  specialist_label?: string;
  reason?: string;
  evidence_acknowledged: boolean;
}

// Resolve the route a decision settles on, mirroring the server rule that
// treats a manual recommendation as specialist review.
export function resolvedRoute(
  action: ReviewAction,
  selectedRoute: string,
  recommendedRoute: string | undefined,
): string | undefined {
  if (action === "request_information") return undefined;
  if (action === "override") return selectedRoute;
  return recommendedRoute;
}

// Build the decision body the API expects, labelling every specialist route.
export function reviewDecisionBody(
  input: ReviewDecisionInput,
): ReviewDecisionBody {
  const route = resolvedRoute(
    input.action,
    input.selectedRoute,
    input.recommendedRoute,
  );
  const needsLabel = route === "specialist" || route === "manual";
  const routeField =
    input.action === "override" ? input.selectedRoute : undefined;
  return {
    action: input.action,
    selected_route: routeField,
    specialist_label: needsLabel
      ? input.specialistLabel || undefined
      : undefined,
    reason: input.reason || undefined,
    evidence_acknowledged: input.acknowledged,
  };
}
