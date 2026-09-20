"""Human review, completion, and audit checks for the evaluation runner."""

from typing import Any

import httpx

from evaluate_failures import EvaluationFailure

REVIEWABLE_ROUTES = {"expedited", "standard", "specialist"}


# Start review, confirm the recommendation, and complete a case twice.
def review_and_complete(
    client: httpx.Client,
    underwriter: dict[str, str],
    case_id: str,
    case_uuid: str,
    specialist_label: str | None = None,
) -> None:
    started = client.post(f"/reviews/{case_uuid}/start", headers=underwriter)
    if started.status_code != 200:
        raise EvaluationFailure(case_id, "review_start", "http_error")
    command: dict[str, Any] = {
        "action": "confirm",
        "evidence_acknowledged": True,
    }
    if specialist_label is not None:
        command["specialist_label"] = specialist_label
    confirmed = client.post(
        f"/reviews/{case_uuid}", json=command, headers=underwriter
    )
    if confirmed.status_code != 200:
        raise EvaluationFailure(case_id, "review_confirm", "http_error")
    first = client.post(f"/completion/{case_uuid}", headers=underwriter)
    second = client.post(f"/completion/{case_uuid}", headers=underwriter)
    if first.status_code != 200 or second.status_code != 200:
        raise EvaluationFailure(case_id, "complete", "http_error")
    if first.json() != second.json():
        raise EvaluationFailure(case_id, "complete", "not_idempotent")


# Verify one completed case reaches the completed queue with a full trail.
def verify_queue_and_audit(
    client: httpx.Client,
    admin: dict[str, str],
    case_id: str,
    case_uuid: str,
) -> None:
    queue = client.get(
        "/queues", params={"status": "completed"}, headers=admin
    )
    if queue.status_code != 200:
        raise EvaluationFailure(case_id, "queue", "http_error")
    if not any(item["case_id"] == case_uuid for item in queue.json()):
        raise EvaluationFailure(case_id, "queue", "not_completed")
    audit = client.get(f"/audit/cases/{case_uuid}", headers=admin)
    if audit.status_code != 200:
        raise EvaluationFailure(case_id, "audit", "http_error")
    event_types = {event["event_type"] for event in audit.json()}
    required = {"underwriter_reviewed", "case_completed"}
    if not required.issubset(event_types):
        raise EvaluationFailure(case_id, "audit", "missing_event")


# Pick the first case per product, journey, and expected route to review.
def representative_cases(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    representatives: list[dict[str, Any]] = []
    for record in records:
        route = record["expected"]["route"]
        # A case expected to need information never reaches a final route,
        # so it is asserted at submit time, not forced through review.
        if route not in REVIEWABLE_ROUTES or record["expected"]["missing"]:
            continue
        key = (record["product_code"], record["journey_type"], route)
        if key in seen:
            continue
        seen.add(key)
        representatives.append(record)
    return representatives


# Look up the specialist label a case's product configuration requires.
def specialist_label_for(
    record: dict[str, Any],
    configurations: dict[tuple[str, str], Any],
) -> str | None:
    if record["expected"]["route"] != "specialist":
        return None
    key = (record["product_code"], record["configuration_version"])
    return configurations[key].specialist_labels[0]
