import type { SpecialistBriefData } from "./types-knowledge";

// Render the deterministic specialist brief with sources and citations.
export function SpecialistBrief({ brief }: { brief: SpecialistBriefData }) {
  return (
    <section aria-labelledby="specialist-brief-heading">
      <h3 id="specialist-brief-heading">Specialist brief</h3>
      <p className="muted">{brief.label}</p>
      <h4>Evidence</h4>
      <ul aria-label="Brief evidence">
        {brief.evidence.map((item) => (
          <li key={`${item.field_name}:${item.source_locator}`}>
            {item.field_name}: {String(item.value ?? "")} (source{" "}
            {item.document ?? "unknown document"}, {item.source_locator})
          </li>
        ))}
      </ul>
      <h4>Triggered rules</h4>
      <ul aria-label="Triggered rules">
        {brief.rules.map((rule) => (
          <li key={rule}>{rule}</li>
        ))}
      </ul>
      <h4>Guideline passages</h4>
      {brief.passages.length > 0 ? (
        <ul aria-label="Brief passages">
          {brief.passages.map((passage) => (
            <li key={passage.citation.passage_key}>
              <strong>{passage.title}</strong>
              <p>{passage.body}</p>
              <small>
                {passage.citation.version}: {passage.citation.passage_key}
              </small>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">No guideline passage matches these rules.</p>
      )}
    </section>
  );
}
