import { useEffect, useState } from "react";

import { fetchPassageGuidance } from "./api-knowledge";
import type { PinnedPassage } from "./types-knowledge";

// Render the public clauses related to one pinned guideline passage.
export function RegulationSide({
  token,
  caseId,
  passageKey,
}: {
  token: string;
  caseId: string;
  passageKey: string;
}) {
  const [related, setRelated] = useState<PinnedPassage[]>([]);

  // Load related clauses once per pinned passage, hiding any failure.
  useEffect(() => {
    let active = true;
    setRelated([]);
    fetchPassageGuidance(token, caseId, passageKey)
      .then((response) => {
        if (!active) return;
        setRelated(response.related_regulation);
      })
      .catch(() => {
        if (!active) return;
        setRelated([]);
      });
    return () => {
      active = false;
    };
  }, [caseId, passageKey, token]);

  if (related.length === 0) return null;
  return (
    <section aria-label="Related regulation">
      <h4>Related regulation</h4>
      <ul>
        {related.map((clause) => (
          <li key={clause.passage_key}>
            <strong>{clause.title}</strong>
            <p>{clause.body}</p>
            <small>{clause.label}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
