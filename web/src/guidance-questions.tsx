import { type FormEvent, useEffect, useState } from "react";

import { ApiError } from "./api-core";
import { askQuestion, listQuestions } from "./api-knowledge";
import { Badge, Button } from "./components";
import type { CaseQuestion } from "./types-knowledge";

// Let an underwriter ask cited questions and read the shared history.
export function GuidanceQuestions({
  token,
  caseId,
}: {
  token: string;
  caseId: string;
}) {
  const [questions, setQuestions] = useState<CaseQuestion[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  // Load the shared question history once per case and session.
  useEffect(() => {
    let active = true;
    listQuestions(token, caseId)
      .then((rows) => {
        if (active) setQuestions(rows);
      })
      .catch((error) => {
        if (active) setMessage(errorText(error));
      });
    return () => {
      active = false;
    };
  }, [caseId, token]);

  // Submit the typed question and append the stored answer.
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || busy) return;
    setBusy(true);
    setMessage("");
    try {
      const answered = await askQuestion(token, caseId, question);
      setQuestions((rows) => [...rows, answered]);
      setDraft("");
    } catch (error) {
      setMessage(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Case questions">
      <form onSubmit={(event) => void handleSubmit(event)}>
        <label className="field" htmlFor={`question-${caseId}`}>
          <span>Ask about this case</span>
          <input
            id={`question-${caseId}`}
            maxLength={1000}
            onChange={(event) => setDraft(event.target.value)}
            value={draft}
          />
        </label>
        <Button disabled={busy} type="submit">
          Ask
        </Button>
      </form>
      {busy ? (
        <p aria-label="Answering question" role="status">
          Answering question…
        </p>
      ) : null}
      {message ? (
        <p className="form-error" role="alert">
          {message}
        </p>
      ) : null}
      {questions.length > 0 ? (
        <ul aria-label="Question history">
          {questions.map((item) => (
            <li key={item.id}>
              <p>
                <strong>{item.question}</strong>{" "}
                <span className="muted">{item.asked_by}</span>
              </p>
              {item.covered ? null : (
                <Badge tone="needs_information">Not covered</Badge>
              )}
              <p>{item.answer}</p>
              {item.citations.length > 0 ? (
                <ul aria-label="Answer citations">
                  {item.citations.map((citation) => (
                    <li key={`${citation.version}:${citation.passage_key}`}>
                      {citation.version}: {citation.passage_key}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

// Convert request failures into a short visible message.
function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Question unavailable.";
}
