// Cross-document reconciliation-check editor for the guided builder.
import { useState } from "react";

import { Button } from "./components";
import type {
  BuilderConfiguration,
  BuilderReconciliation,
} from "./product-builder-state";
import { AppliesToEditor } from "./product-builder-shared";
import type { JourneyType, ReconciliationKind } from "./types";

interface SectionProps {
  configuration: BuilderConfiguration;
  onChange: (next: BuilderConfiguration) => void;
}

const RECONCILIATION_KINDS: ReconciliationKind[] = [
  "ncb_match",
  "asset_match",
  "policy_lapse",
];

// asset_match compares two documents directly; the other kinds compare the
// applicant's claimed value against one document, so only they take
// parameters and pin their first source to the fixed "application" key.
function usesApplicationSource(kind: ReconciliationKind): boolean {
  return kind !== "asset_match";
}

// Add or remove cross-document reconciliation checks for this product.
export function ReconciliationSection({
  configuration,
  onChange,
}: SectionProps) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [kind, setKind] = useState<ReconciliationKind>("ncb_match");
  const [applicationField, setApplicationField] = useState("");
  const [sourceADocument, setSourceADocument] = useState("");
  const [sourceAField, setSourceAField] = useState("");
  const [sourceBDocument, setSourceBDocument] = useState("");
  const [sourceBField, setSourceBField] = useState("");
  const [tiers, setTiers] = useState("");
  const [claimCountField, setClaimCountField] = useState("");
  const [claimsResetThreshold, setClaimsResetThreshold] = useState("");
  const [claimsResetTier, setClaimsResetTier] = useState("");
  const [maximumGapDays, setMaximumGapDays] = useState("");
  const [boundary, setBoundary] =
    useState<"inclusive" | "exclusive">("inclusive");
  const [appliesTo, setAppliesTo] = useState<JourneyType[]>(
    configuration.supported_journeys,
  );

  // Reset the inline add-check form to its empty defaults.
  function resetDraft() {
    setCode("");
    setKind("ncb_match");
    setApplicationField("");
    setSourceADocument("");
    setSourceAField("");
    setSourceBDocument("");
    setSourceBField("");
    setTiers("");
    setClaimCountField("");
    setClaimsResetThreshold("");
    setClaimsResetTier("");
    setMaximumGapDays("");
    setBoundary("inclusive");
    setAppliesTo(configuration.supported_journeys);
    setAdding(false);
  }

  // Build the two-source inputs map for the drafted check's kind.
  function draftInputs(): Record<string, string> {
    if (usesApplicationSource(kind)) {
      if (!applicationField.trim() || !sourceADocument.trim()) return {};
      return {
        application: applicationField.trim(),
        [sourceADocument.trim()]: sourceAField.trim(),
      };
    }
    if (!sourceADocument.trim() || !sourceBDocument.trim()) return {};
    return {
      [sourceADocument.trim()]: sourceAField.trim(),
      [sourceBDocument.trim()]: sourceBField.trim(),
    };
  }

  // Build the kind-specific pinned parameters for the drafted check.
  function draftParameters(): Record<string, unknown> | undefined {
    if (kind === "ncb_match") {
      const parsedTiers = tiers
        .split(",")
        .map((item) => Number(item.trim()))
        .filter((item) => !Number.isNaN(item));
      if (
        parsedTiers.length < 2
        || !claimCountField.trim()
        || !claimsResetThreshold.trim()
        || !claimsResetTier.trim()
      ) {
        return undefined;
      }
      return {
        tiers: parsedTiers,
        claim_count_field: claimCountField.trim(),
        claims_reset_threshold: Number(claimsResetThreshold),
        claims_reset_tier: Number(claimsResetTier),
      };
    }
    if (kind === "policy_lapse") {
      if (!maximumGapDays.trim()) return undefined;
      return {
        maximum_gap_days: Number(maximumGapDays),
        boundary,
      };
    }
    return undefined;
  }

  // Append the drafted reconciliation check and close the form.
  function saveCheck() {
    if (!code.trim() || appliesTo.length === 0) return;
    const inputs = draftInputs();
    if (Object.keys(inputs).length === 0) return;
    const check: BuilderReconciliation = {
      code: code.trim(),
      kind,
      inputs,
      parameters: draftParameters(),
      applies_to: appliesTo,
    };
    onChange({
      ...configuration,
      reconciliations: [...configuration.reconciliations, check],
    });
    resetDraft();
  }

  // Remove one reconciliation check by its stable code.
  function removeCheck(checkCode: string) {
    onChange({
      ...configuration,
      reconciliations: configuration.reconciliations.filter(
        (check) => check.code !== checkCode,
      ),
    });
  }

  return (
    <section aria-labelledby="section-reconciliation">
      <h2 id="section-reconciliation">Reconciliation</h2>
      {configuration.reconciliations.length === 0 ? (
        <p className="muted">No reconciliation checks yet.</p>
      ) : (
        <ul aria-label="Reconciliation checks" className="mini-list">
          {configuration.reconciliations.map((check) => (
            <li key={check.code}>
              <span>
                {check.code} ({check.kind})
              </span>
              <Button onClick={() => removeCheck(check.code)} variant="quiet">
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      {adding ? (
        <div className="inline-form">
          <label className="field">
            Reconciliation code
            <input
              onChange={(event) => setCode(event.target.value)}
              value={code}
            />
          </label>
          <label className="field">
            Kind
            <select
              onChange={(event) =>
                setKind(event.target.value as ReconciliationKind)
              }
              value={kind}
            >
              {RECONCILIATION_KINDS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          {usesApplicationSource(kind) ? (
            <label className="field">
              Application field
              <input
                onChange={(event) => setApplicationField(event.target.value)}
                value={applicationField}
              />
            </label>
          ) : null}
          <label className="field">
            {usesApplicationSource(kind) ? "Document code" : "Document 1 code"}
            <input
              onChange={(event) => setSourceADocument(event.target.value)}
              value={sourceADocument}
            />
          </label>
          <label className="field">
            {usesApplicationSource(kind)
              ? "Document field"
              : "Document 1 field"}
            <input
              onChange={(event) => setSourceAField(event.target.value)}
              value={sourceAField}
            />
          </label>
          {!usesApplicationSource(kind) ? (
            <>
              <label className="field">
                Document 2 code
                <input
                  onChange={(event) => setSourceBDocument(event.target.value)}
                  value={sourceBDocument}
                />
              </label>
              <label className="field">
                Document 2 field
                <input
                  onChange={(event) => setSourceBField(event.target.value)}
                  value={sourceBField}
                />
              </label>
            </>
          ) : null}
          {kind === "ncb_match" ? (
            <>
              <label className="field">
                Tiers (comma separated)
                <input
                  onChange={(event) => setTiers(event.target.value)}
                  value={tiers}
                />
              </label>
              <label className="field">
                Claim count field
                <input
                  onChange={(event) =>
                    setClaimCountField(event.target.value)
                  }
                  value={claimCountField}
                />
              </label>
              <label className="field">
                Claims reset threshold
                <input
                  onChange={(event) =>
                    setClaimsResetThreshold(event.target.value)
                  }
                  type="number"
                  value={claimsResetThreshold}
                />
              </label>
              <label className="field">
                Claims reset tier
                <input
                  onChange={(event) =>
                    setClaimsResetTier(event.target.value)
                  }
                  type="number"
                  value={claimsResetTier}
                />
              </label>
            </>
          ) : null}
          {kind === "policy_lapse" ? (
            <>
              <label className="field">
                Maximum gap days
                <input
                  onChange={(event) => setMaximumGapDays(event.target.value)}
                  type="number"
                  value={maximumGapDays}
                />
              </label>
              <label className="field">
                Boundary
                <select
                  onChange={(event) =>
                    setBoundary(
                      event.target.value as "inclusive" | "exclusive",
                    )
                  }
                  value={boundary}
                >
                  <option value="inclusive">inclusive</option>
                  <option value="exclusive">exclusive</option>
                </select>
              </label>
            </>
          ) : null}
          <AppliesToEditor
            appliesTo={appliesTo}
            onChange={setAppliesTo}
            supported={configuration.supported_journeys}
          />
          <Button onClick={saveCheck}>Save reconciliation</Button>
        </div>
      ) : (
        <Button onClick={() => setAdding(true)} variant="secondary">
          Add reconciliation
        </Button>
      )}
    </section>
  );
}
