import { useState } from "react";

import { ApiError } from "./api-core";
import { acceptRegulationTags } from "./api-knowledge";
import { Button } from "./components";

// Render tag review for one regulation draft clause.
export function KnowledgeTags({
  token,
  versionId,
  passageKey,
  suggestedTags,
  topicTags,
  editable,
}: {
  token: string;
  versionId: string;
  passageKey: string;
  suggestedTags: string[];
  topicTags: string[];
  editable: boolean;
}) {
  const [accepted, setAccepted] = useState<string[]>(topicTags);
  const [message, setMessage] = useState("");

  // Accept one suggested tag on the selected draft clause.
  async function accept(tag: string) {
    if (accepted.includes(tag)) return;
    setMessage("");
    try {
      const result = await acceptRegulationTags(
        token,
        versionId,
        passageKey,
        [...accepted, tag],
      );
      setAccepted(result.topic_tags);
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "Tag acceptance could not be completed.",
      );
    }
  }

  if (!editable) return null;
  if (suggestedTags.length === 0 && accepted.length === 0) return null;
  return (
    <div className="tag-review">
      {accepted.length > 0 ? (
        <p className="muted">Accepted: {accepted.join(", ")}</p>
      ) : null}
      {suggestedTags.length > 0 ? (
        <p className="muted">Suggested tags</p>
      ) : null}
      <ul aria-label="Suggested regulation tags">
        {suggestedTags.map((tag) => (
          <li key={tag}>
            <Button
              disabled={accepted.includes(tag)}
              onClick={() => void accept(tag)}
            >
              {`Accept ${tag}`}
            </Button>
          </li>
        ))}
      </ul>
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
    </div>
  );
}
