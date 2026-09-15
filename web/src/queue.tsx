import { useEffect, useState } from "react";

import { ApiError, completeCase, listQueue } from "./api";
import {
  Badge,
  Button,
  EmptyState,
  PageHeading,
  Panel,
} from "./components";
import { familyMark, Icon } from "./icons";
import type { QueueItem, Screen } from "./types";

const FILTERS: { value: string; label: string }[] = [
  { value: "underwriter_review", label: "Underwriter review" },
  { value: "needs_information", label: "Needs information" },
  { value: "awaiting_handoff", label: "Awaiting handoff" },
  { value: "completed", label: "Completed" },
];

// Show the human-selected route and specialist label once a decision exists.
function routeLabel(item: QueueItem): string {
  if (!item.selected_route) {
    return item.route ?? "Pending";
  }
  return item.specialist_label
    ? `${item.selected_route} · ${item.specialist_label}`
    : item.selected_route;
}

// Load and filter the underwriter queue with safe server-side rows.
export function UnderwriterQueue({
  token,
  onSelect,
  onNavigate,
}: {
  token: string;
  onSelect: (item: QueueItem) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [filter, setFilter] = useState("underwriter_review");
  const [message, setMessage] = useState("");
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    const awaitingHandoff = filter === "awaiting_handoff";
    listQueue(token, awaitingHandoff ? undefined : filter, awaitingHandoff)
      .then(setItems)
      .catch((error) =>
        setMessage(
          error instanceof ApiError
            ? error.message
            : "The queue could not be loaded.",
        ),
      );
  }, [filter, token]);

  // Retry the handoff for a finalised route that was never completed.
  async function handleRetry(item: QueueItem) {
    setRetryingId(item.case_id);
    setMessage("");
    try {
      await completeCase(token, item.case_id);
      setItems((current) =>
        current.filter((row) => row.case_id !== item.case_id),
      );
      setMessage("Handoff completed.");
    } catch (error) {
      setMessage(
        error instanceof ApiError
          ? error.message
          : "The handoff could not be completed.",
      );
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="Underwriter workspace"
        title="Review queue"
        description={
          "Prioritize cases with visible evidence state, deterministic "
          + "signals, and a human decision boundary."
        }
      />
      <div aria-label="Queue filter" className="filter-group" role="group">
        {FILTERS.map((option) => (
          <button
            aria-pressed={filter === option.value}
            className={
              filter === option.value ? "filter filter-active" : "filter"
            }
            key={option.value}
            onClick={() => setFilter(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </div>
      <Panel>
        {message ? (
          <p className="form-error" role="alert">
            {message}
          </p>
        ) : items.length === 0 ? (
          <EmptyState
            title="Queue is clear"
            detail="No cases match this view."
          />
        ) : (
          <div className="data-table-wrap">
            <table className="data-table">
              <caption className="sr-only">
                Cases awaiting underwriter attention
              </caption>
              <thead>
                <tr>
                  <th scope="col">Case</th>
                  <th scope="col">Product</th>
                  <th scope="col">Route</th>
                  <th scope="col">Status</th>
                  <th scope="col">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  // Rows expose only the product code, so the family is its
                  // prefix; unknown families fall back to a generic mark.
                  const mark = familyMark(item.product_code.split("-")[0]);
                  return (
                    <tr key={item.case_id}>
                      <td className="mono">{item.case_id.slice(0, 8)}</td>
                      <td>
                        <span className="product-label">
                          <Icon name={mark.icon} />
                          {item.product_code}
                        </span>
                      </td>
                      <td>
                        <span className="route-cell">
                          <span>{routeLabel(item)}</span>
                          {item.specialist ? (
                            <Badge tone="specialist">Specialist</Badge>
                          ) : null}
                        </span>
                      </td>
                      <td>
                        <Badge tone={item.status}>
                          {item.status.replaceAll("_", " ")}
                        </Badge>
                      </td>
                      <td>
                        <span className="row-actions">
                          <Button
                            variant="quiet"
                            onClick={() => onSelect(item)}
                          >
                            Open
                          </Button>
                          {item.awaiting_handoff ? (
                            <Button
                              disabled={retryingId === item.case_id}
                              onClick={() => handleRetry(item)}
                              variant="secondary"
                            >
                              {retryingId === item.case_id
                                ? "Retrying…"
                                : "Retry handoff"}
                            </Button>
                          ) : null}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
