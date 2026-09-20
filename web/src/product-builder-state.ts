// Pure state helpers for the guided product-configuration builder.
import type {
  DocumentStage,
  JourneyType,
  ReconciliationKind,
} from "./types";

export type ProductFamily = "motor" | "life" | "health";

export interface BuilderCondition {
  field: string;
  operator: "equals" | "greater_than";
  value: string | number | boolean;
}

export interface BuilderField {
  key: string;
  label: string;
  type: "text" | "integer" | "number" | "date" | "boolean" | "enum";
  required: boolean;
  help_text: string;
  validation: Record<string, number>;
  options: string[];
  applies_to: JourneyType[];
  visible_when?: BuilderCondition;
}

export interface BuilderDocument {
  code: string;
  title: string;
  requirement: "required" | "optional" | "conditional" | "not_applicable";
  accepted_types: string[];
  stage: DocumentStage;
  applies_to: JourneyType[];
  condition?: BuilderCondition;
  required_for?: JourneyType[];
}

export type BuilderRoute =
  | "manual"
  | "needs_information"
  | "specialist"
  | "standard"
  | "expedited";

export interface BuilderRoutingRule {
  code: string;
  condition: BuilderCondition;
  route: BuilderRoute;
  specialist_label?: string;
  applies_to: JourneyType[];
}

export interface BuilderReconciliation {
  code: string;
  kind: ReconciliationKind;
  inputs: Record<string, string>;
  parameters?: Record<string, unknown>;
  applies_to: JourneyType[];
}

export interface BuilderConfiguration {
  product_code: string;
  title: string;
  family: ProductFamily;
  scope: string;
  description: string;
  version: string;
  status: "draft" | "active" | "retired";
  fields: BuilderField[];
  documents: BuilderDocument[];
  routing_rules: BuilderRoutingRule[];
  reconciliations: BuilderReconciliation[];
  specialist_labels: string[];
  supported_journeys: JourneyType[];
}

// The normalized configuration previewed from uploaded expert YAML, plus
// summary counts. The full shape matches BuilderConfiguration so a preview
// can hydrate the guided builder for further editing before import.
export interface BuilderConfigurationPreview extends BuilderConfiguration {
  field_count: number;
  document_count: number;
  routing_rule_count: number;
  reconciliation_count: number;
}

// Build an empty configuration pinned to the chosen family.
export function blankConfiguration(
  family: ProductFamily,
): BuilderConfiguration {
  return {
    product_code: "",
    title: "",
    family,
    scope: "",
    description: "",
    version: "",
    status: "draft",
    fields: [],
    documents: [],
    routing_rules: [],
    reconciliations: [],
    specialist_labels: [],
    supported_journeys: ["new_business", "renewal"],
  };
}

// Deep copy one configuration for a new draft version, locking its identity.
export function cloneForNewVersion(
  source: BuilderConfiguration,
  version: string,
): BuilderConfiguration {
  const cloned = JSON.parse(JSON.stringify(source)) as BuilderConfiguration;
  cloned.version = version;
  cloned.status = "draft";
  return cloned;
}

const REQUIRED_SECTIONS = [
  "fields",
  "documents",
  "routing_rules",
  "specialist_labels",
] as const;

// Report which required sections still need at least one entry.
export function builderCompletion(configuration: BuilderConfiguration): {
  complete: boolean;
  missingSections: string[];
} {
  const missingSections = REQUIRED_SECTIONS.filter(
    (section) => configuration[section].length === 0,
  );
  return { complete: missingSections.length === 0, missingSections };
}

export type ConfigurationDiffKind = "added" | "removed" | "changed";

export interface ConfigurationDiffEntry {
  section: string;
  kind: ConfigurationDiffKind;
  key: string;
}

// Diff one keyed list section by stable identifier, ignoring order.
function diffKeyedSection<T>(
  section: string,
  before: T[],
  after: T[],
  keyOf: (item: T) => string,
): ConfigurationDiffEntry[] {
  const beforeMap = new Map(before.map((item) => [keyOf(item), item]));
  const afterMap = new Map(after.map((item) => [keyOf(item), item]));
  const entries: ConfigurationDiffEntry[] = [];
  for (const [key, item] of afterMap) {
    const previous = beforeMap.get(key);
    if (previous === undefined) {
      entries.push({ section, kind: "added", key });
    } else if (JSON.stringify(previous) !== JSON.stringify(item)) {
      entries.push({ section, kind: "changed", key });
    }
  }
  for (const key of beforeMap.keys()) {
    if (!afterMap.has(key)) entries.push({ section, kind: "removed", key });
  }
  return entries;
}

// Diff the flat specialist-label list by its own text as the identifier.
function diffLabels(
  before: string[],
  after: string[],
): ConfigurationDiffEntry[] {
  const beforeSet = new Set(before);
  const afterSet = new Set(after);
  const entries: ConfigurationDiffEntry[] = [];
  for (const label of afterSet) {
    if (!beforeSet.has(label)) {
      entries.push({ section: "specialist_labels", kind: "added", key: label });
    }
  }
  for (const label of beforeSet) {
    if (!afterSet.has(label)) {
      entries.push({
        section: "specialist_labels",
        kind: "removed",
        key: label,
      });
    }
  }
  return entries;
}

// Compare two configurations by stable identifier, ignoring section order.
export function semanticDiff(
  before: BuilderConfiguration,
  after: BuilderConfiguration,
): ConfigurationDiffEntry[] {
  return [
    ...diffKeyedSection("fields", before.fields, after.fields, (f) => f.key),
    ...diffKeyedSection(
      "documents",
      before.documents,
      after.documents,
      (d) => d.code,
    ),
    ...diffKeyedSection(
      "routing_rules",
      before.routing_rules,
      after.routing_rules,
      (r) => r.code,
    ),
    ...diffKeyedSection(
      "reconciliations",
      before.reconciliations,
      after.reconciliations,
      (r) => r.code,
    ),
    ...diffLabels(before.specialist_labels, after.specialist_labels),
  ];
}
