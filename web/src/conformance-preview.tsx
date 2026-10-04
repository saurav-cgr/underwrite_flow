import type {
  ChangeImpact,
  ConformancePreview as ConformanceResult,
} from "./product-builder-state";

interface ConformancePreviewProps {
  conformance?: ConformanceResult;
  changeImpact?: ChangeImpact;
}

// Render informational conformance flags and structural version changes.
export function ConformancePreview({
  conformance,
  changeImpact,
}: ConformancePreviewProps) {
  if (!conformance && !changeImpact) return null;
  return (
    <section aria-labelledby="conformance-heading">
      <h3 id="conformance-heading">Rule conformance</h3>
      {conformance?.regulation_version ? (
        <p className="panel-note">
          Regulation version: {conformance.regulation_version}
        </p>
      ) : null}
      {conformance?.flags.length ? (
        <ul aria-label="Conformance flags">
          {conformance.flags.map((flag) => (
            <li key={`${flag.rule_code}-${flag.clause.passage_key}`}>
              {flag.rule_code}: {flag.field} {String(
                flag.clause.limit.operator,
              )} {String(flag.clause.limit.value)} in{" "}
              {flag.clause.passage_key}. {flag.label}
            </li>
          ))}
        </ul>
      ) : (
        <p className="panel-note">No conformance flags.</p>
      )}
      {conformance?.related.length ? (
        <div>
          <h4>Related clauses</h4>
          <ul aria-label="Related clauses">
            {conformance.related.map((item) => (
              <li key={item.rule_code}>
                {item.rule_code}: {item.passage_keys.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {changeImpact ? <ImpactList impact={changeImpact} /> : null}
    </section>
  );
}

// Render change-impact entries as text and without color-only meaning.
function ImpactList({ impact }: { impact: ChangeImpact }) {
  const changes = [
    ...impact.added_rules.map((rule) => `Added rule: ${rule}`),
    ...impact.removed_rules.map((rule) => `Removed rule: ${rule}`),
    ...impact.changed_thresholds.map(
      (item) =>
        `Changed threshold: ${item.rule_code} (${String(item.from)} to ` +
        `${String(item.to)})`,
    ),
    ...impact.changed_documents.map(
      (item) =>
        `Changed document: ${item.document_code} (${String(item.from)} to ` +
        `${String(item.to)})`,
    ),
  ];
  return (
    <div aria-label="Change impact">
      <h4>
        Change impact{impact.against_version
          ? ` against ${impact.against_version}`
          : ""}
      </h4>
      {changes.length ? (
        <ul>
          {changes.map((change) => <li key={change}>{change}</li>)}
        </ul>
      ) : (
        <p className="panel-note">No rule or document changes.</p>
      )}
    </div>
  );
}
