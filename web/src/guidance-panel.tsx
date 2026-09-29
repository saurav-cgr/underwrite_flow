import { useEffect, useState } from "react";

import { ApiError } from "./api-core";
import { fetchGuidance } from "./api-knowledge";
import { Panel } from "./components";
import type { GuidanceResponse } from "./types-knowledge";

// Render one stored, cited explanation without polling or regeneration.
export function GuidancePanel({
  token,
  caseId,
}: {
  token: string;
  caseId: string;
}) {
  const [guidance, setGuidance] = useState<GuidanceResponse | null>(null);
  const [message, setMessage] = useState("");

  // Fetch durable guidance exactly once for the current case and session.
  useEffect(() => {
    let active = true;
    fetchGuidance(token, caseId)
      .then((response) => {
        if (active) setGuidance(response);
      })
      .catch((error) => {
        if (!active) return;
        setMessage(
          error instanceof ApiError
            ? error.message
            : "Explanation unavailable.",
        );
      });
    return () => {
      active = false;
    };
  }, [caseId, token]);

  if (message) {
    return (
      <Panel title="Route explanation">
        <p aria-label="Explanation unavailable." role="status">
          Explanation unavailable. {message}
        </p>
      </Panel>
    );
  }
  if (!guidance) {
    return (
      <Panel title="Route explanation">
        <p role="status">Loading stored explanation…</p>
      </Panel>
    );
  }
  const explanation = guidance.route_explanation;
  return (
    <Panel title="Route explanation">
      {explanation.status === "template" ? (
        <p className="advisory">Template fallback</p>
      ) : null}
      <p>{explanation.text}</p>
      <p className="muted">{explanation.label}</p>
      {explanation.missing_items.length > 0 ? (
        <ul>
          {explanation.missing_items.map((item) => (
            <li key={item.item}>
              <strong>{item.item}</strong>: {item.reason}
            </li>
          ))}
        </ul>
      ) : null}
      {explanation.citations.length > 0 ? (
        <ul aria-label="Guidance citations">
          {explanation.citations.map((citation) => (
            <li key={`${citation.version}:${citation.passage_key}`}>
              {citation.version}: {citation.passage_key}
            </li>
          ))}
        </ul>
      ) : null}
      {explanation.status === "unavailable" ? (
        <p aria-label="Explanation unavailable." role="status">
          Explanation unavailable.
        </p>
      ) : null}
    </Panel>
  );
}
