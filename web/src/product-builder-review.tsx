// Normalized preview, active-version diff, and import for the builder.
import { useEffect, useState } from "react";

import {
  ApiError,
  importProductConfiguration,
  previewProductConfiguration,
} from "./api";
import { Button, ErrorSummary } from "./components";
import { yamlHash } from "./ui-state";
import type { BuilderSource } from "./product-builder";
import {
  builderCompletion,
  semanticDiff,
} from "./product-builder-state";
import type { BuilderConfiguration } from "./product-builder-state";

interface ReviewSectionProps {
  activeConfiguration?: BuilderConfiguration;
  configuration: BuilderConfiguration;
  onImported: (productCode: string) => void;
  onStatus: (next: { message?: string; notice?: string }) => void;
  source: BuilderSource;
  token: string;
}

const REQUIRED_LABELS: Record<string, string> = {
  fields: "Add at least one applicant field.",
  documents: "Add at least one document requirement.",
  routing_rules: "Add at least one routing rule.",
  specialist_labels: "Add at least one specialist label.",
};

// Report missing identity fields, a broken clone lock, and missing required
// sections for a draft the administrator is about to preview or import.
function identityErrors(
  configuration: BuilderConfiguration,
  source: BuilderSource,
  activeConfiguration?: BuilderConfiguration,
): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!configuration.product_code.trim()) {
    errors.product_code = "Enter a product code.";
  }
  if (!configuration.title.trim()) errors.title = "Enter a title.";
  if (!configuration.scope.trim()) errors.scope = "Enter a scope.";
  if (!configuration.description.trim()) {
    errors.description = "Enter a description.";
  }
  if (!configuration.version.trim()) errors.version = "Enter a version.";
  if (source === "clone" && activeConfiguration) {
    if (configuration.product_code !== activeConfiguration.product_code) {
      errors.product_code = "A clone must keep the source product code.";
    }
    if (configuration.version.trim() === activeConfiguration.version) {
      errors.version = "Enter a version distinct from the cloned source.";
    }
  }
  for (const section of builderCompletion(configuration).missingSections) {
    errors[section] = REQUIRED_LABELS[section] ?? "Add at least one entry.";
  }
  return errors;
}

// Render one plain-language line describing an added, changed, or removed
// entry so the difference never relies on color alone.
function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

// Summarize the normalized draft, its diff against the active version, and
// the import action that persists it as an immutable draft.
export function ReviewSection({
  activeConfiguration,
  configuration,
  onImported,
  onStatus,
  source,
  token,
}: ReviewSectionProps) {
  const errors = source === "upload"
    ? {}
    : identityErrors(configuration, source, activeConfiguration);
  const configHash = yamlHash(JSON.stringify(configuration));
  const [candidate, setCandidate] = useState<BuilderConfiguration | null>(
    null,
  );
  const [candidateHash, setCandidateHash] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const hasErrors = Object.keys(errors).length > 0;

  // Refresh the normalized server-side preview whenever the draft changes.
  useEffect(() => {
    if (hasErrors) return;
    let cancelled = false;
    previewProductConfiguration(token, JSON.stringify(configuration))
      .then((result) => {
        if (cancelled) return;
        setCandidate(result as unknown as BuilderConfiguration);
        setCandidateHash(configHash);
      })
      .catch(() => {
        if (!cancelled) {
          onStatus({ message: "The configuration could not be previewed." });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configHash, hasErrors]);

  if (hasErrors) {
    return (
      <section aria-labelledby="section-review">
        <h2 id="section-review">Review</h2>
        <ErrorSummary errors={errors} />
      </section>
    );
  }

  const previewIsCurrent = candidate !== null && candidateHash === configHash;
  const diff = activeConfiguration && previewIsCurrent && candidate
    ? semanticDiff(activeConfiguration, candidate)
    : [];

  // Import the normalized draft as JSON through the existing YAML field.
  async function handleImport() {
    setWorking(true);
    onStatus({ message: "", notice: "" });
    try {
      const result = await importProductConfiguration(
        token,
        JSON.stringify(configuration),
      );
      onImported(result.product_code);
      onStatus({
        notice: `Draft ${result.version} imported for ${result.product_code}.`,
      });
    } catch (error) {
      onStatus({
        message: error instanceof ApiError
          ? error.message
          : "The product configuration could not be imported.",
      });
    } finally {
      setWorking(false);
    }
  }

  return (
    <section aria-labelledby="section-review">
      <h2 id="section-review">Review</h2>
      {!previewIsCurrent ? (
        <p className="muted" role="status">
          Normalizing the current configuration…
        </p>
      ) : null}
      {activeConfiguration ? (
        diff.length === 0 ? (
          <p className="muted">No changes from the active version.</p>
        ) : (
          <ul aria-label="Configuration changes" role="list">
            {diff.map((entry) => (
              <li key={`${entry.section}-${entry.kind}-${entry.key}`}>
                {capitalize(entry.kind)}: {entry.section}.{entry.key}
              </li>
            ))}
          </ul>
        )
      ) : null}
      <Button disabled={working || !previewIsCurrent} onClick={handleImport}>
        {working ? "Importing…" : "Import"}
      </Button>
    </section>
  );
}
