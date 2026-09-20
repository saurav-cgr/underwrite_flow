// Guided, accessible wizard shell for nontechnical product authoring.
import { useState } from "react";

import { ApplicantFieldsSection, DocumentsSection } from
  "./product-builder-evidence";
import { ReconciliationSection } from "./product-builder-reconciliation";
import {
  RoutingRulesSection,
  SpecialistLabelsSection,
} from "./product-builder-rules";
import { ReviewSection } from "./product-builder-review";
import {
  blankConfiguration,
  cloneForNewVersion,
} from "./product-builder-state";
import type {
  BuilderConfiguration,
  ProductFamily,
} from "./product-builder-state";
import type { JourneyType } from "./types";

export type BuilderSource = "blank" | "clone" | "upload";

const SECTIONS = [
  "Identity",
  "Journeys",
  "Applicant fields",
  "Documents",
  "Routing rules",
  "Reconciliation",
  "Specialist labels",
  "Review",
] as const;
type SectionName = (typeof SECTIONS)[number];

interface SectionProps {
  configuration: BuilderConfiguration;
  onChange: (next: BuilderConfiguration) => void;
}

// Edit the five plain-text identity fields shared by every draft.
function IdentitySection({
  activeConfiguration,
  configuration,
  onChange,
  source,
}: SectionProps & {
  activeConfiguration?: BuilderConfiguration;
  source: BuilderSource;
}) {
  // Update one plain-text identity field on the draft configuration.
  function set(key: "product_code" | "title" | "scope"
    | "description" | "version", value: string) {
    onChange({ ...configuration, [key]: value });
  }
  return (
    <section aria-labelledby="section-identity">
      <h2 id="section-identity">Identity</h2>
      <p className="muted">
        {source === "clone" && activeConfiguration
          ? `Cloned from ${activeConfiguration.product_code} `
            + `${activeConfiguration.version}. Family: `
            + `${configuration.family}.`
          : source === "upload"
            ? `Loaded from uploaded YAML. Family: ${configuration.family}.`
            : `New ${configuration.family} product.`}
      </p>
      <label className="field">
        Product code
        <input
          onChange={(event) => set("product_code", event.target.value)}
          value={configuration.product_code}
        />
      </label>
      <label className="field">
        Title
        <input
          onChange={(event) => set("title", event.target.value)}
          value={configuration.title}
        />
      </label>
      <label className="field">
        Scope
        <input
          onChange={(event) => set("scope", event.target.value)}
          value={configuration.scope}
        />
      </label>
      <label className="field">
        Description
        <input
          onChange={(event) => set("description", event.target.value)}
          value={configuration.description}
        />
      </label>
      <label className="field">
        Version
        <input
          onChange={(event) => set("version", event.target.value)}
          value={configuration.version}
        />
      </label>
    </section>
  );
}

// Choose which application journeys this configuration supports.
function JourneysSection({ configuration, onChange }: SectionProps) {
  // Toggle one supported journey on or off the draft configuration.
  function toggle(journey: JourneyType) {
    const supported = configuration.supported_journeys.includes(journey)
      ? configuration.supported_journeys.filter((item) => item !== journey)
      : [...configuration.supported_journeys, journey];
    onChange({ ...configuration, supported_journeys: supported });
  }
  return (
    <section aria-labelledby="section-journeys">
      <h2 id="section-journeys">Journeys</h2>
      <label className="field-inline">
        <input
          checked={configuration.supported_journeys.includes(
            "new_business",
          )}
          onChange={() => toggle("new_business")}
          type="checkbox"
        />
        New business
      </label>
      <label className="field-inline">
        <input
          checked={configuration.supported_journeys.includes("renewal")}
          onChange={() => toggle("renewal")}
          type="checkbox"
        />
        Renewal
      </label>
    </section>
  );
}

export interface ProductBuilderProps {
  activeConfiguration?: BuilderConfiguration;
  family: ProductFamily;
  onImported: (productCode: string) => void;
  onStatus: (next: { message?: string; notice?: string }) => void;
  source: BuilderSource;
  token: string;
}

// Build one blank or cloned starting configuration for this wizard.
function initialConfiguration(
  family: ProductFamily,
  source: BuilderSource,
  activeConfiguration?: BuilderConfiguration,
): BuilderConfiguration {
  if (source === "clone" && activeConfiguration) {
    return cloneForNewVersion(activeConfiguration, activeConfiguration.version);
  }
  if (source === "upload" && activeConfiguration) {
    return { ...activeConfiguration, status: "draft" };
  }
  return blankConfiguration(family);
}

// Guide an administrator through one draft configuration end to end.
export function ProductBuilder({
  activeConfiguration,
  family,
  onImported,
  onStatus,
  source,
  token,
}: ProductBuilderProps) {
  const [section, setSection] = useState<SectionName>("Identity");
  const [configuration, setConfiguration] = useState<BuilderConfiguration>(
    () => initialConfiguration(family, source, activeConfiguration),
  );

  return (
    <div className="builder">
      <nav aria-label="Builder sections" className="builder-nav">
        {SECTIONS.map((name) => (
          <button
            aria-current={section === name ? "step" : undefined}
            key={name}
            onClick={() => setSection(name)}
            type="button"
          >
            {name}
          </button>
        ))}
      </nav>
      <div className="builder-content">
        {section === "Identity" ? (
          <IdentitySection
            activeConfiguration={activeConfiguration}
            configuration={configuration}
            onChange={setConfiguration}
            source={source}
          />
        ) : null}
        {section === "Journeys" ? (
          <JourneysSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Applicant fields" ? (
          <ApplicantFieldsSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Documents" ? (
          <DocumentsSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Routing rules" ? (
          <RoutingRulesSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Reconciliation" ? (
          <ReconciliationSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Specialist labels" ? (
          <SpecialistLabelsSection
            configuration={configuration}
            onChange={setConfiguration}
          />
        ) : null}
        {section === "Review" ? (
          <ReviewSection
            activeConfiguration={activeConfiguration}
            configuration={configuration}
            onImported={onImported}
            onStatus={onStatus}
            source={source}
            token={token}
          />
        ) : null}
      </div>
    </div>
  );
}
