"""Standalone public-HTTP evaluation runner for the isolated Compose stack.

Run only inside `compose.evaluation.yaml` (see
`specs/002-journey-authoring-evaluation/contracts/evaluation.md`), which
mounts `api/src`, `evaluation/`, and `product-config/` read-only so this
script can reuse the same dataset/config loaders the offline evaluator
uses, and talks to `evaluation-api` over its own internal network.
"""

import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, os.environ.get("UNDERWRITEFLOW_SRC", "/app/src"))

from underwriteflow.evaluation.dataset import (  # noqa: E402
    default_dataset_path,
    load_configuration_manifest,
    load_dataset,
)

DEFAULT_BASE_URL = "http://evaluation-api:8000/api/v1"
RESULT_PATH = Path("/app/evaluation/results/e2e.json")
REVIEWABLE_ROUTES = {"expedited", "standard", "specialist"}

DEMO_ACCOUNTS = {
    "administrator": (
        "administrator@synthetic.test",
        "underwriteflow-demo-administrator",
    ),
    "applicant": ("applicant@synthetic.test", "underwriteflow-demo-applicant"),
    "underwriter": (
        "underwriter@synthetic.test",
        "underwriteflow-demo-underwriter",
    ),
}


class EvaluationFailure(Exception):
    """One case-level failure, carrying only its safe result-artifact shape."""

    # Record the sanitized failure a caller reports instead of raising raw.
    def __init__(self, case_id: str, stage: str, code: str) -> None:
        super().__init__(f"{case_id}:{stage}:{code}")
        self.detail = sanitized_failure(case_id, stage, code)


# Build the safe failure record the result artifact stores for one case.
def sanitized_failure(case_id: str, stage: str, code: str) -> dict[str, str]:
    return {"case_id": case_id, "stage": stage, "code": code}


# Write JSON atomically, so a reader never observes a partial file.
def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


# Map a result's pass flag to the process exit code CI checks.
def exit_code_for(result: dict[str, Any]) -> int:
    return 0 if result["passed"] else 1


# Log in one fictional demo role and return its bearer authorization header.
def login(client: httpx.Client, role: str) -> dict[str, str]:
    email, password = DEMO_ACCOUNTS[role]
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# Reject the dataset before any case executes, per the dataset contract.
def preflight(
    records: list[dict[str, Any]],
    configurations: dict[tuple[str, str], Any],
) -> None:
    case_ids = [record["case_id"] for record in records]
    if len(records) != 90 or len(set(case_ids)) != len(case_ids):
        raise EvaluationFailure("dataset", "preflight", "case_count")
    counts = Counter(
        (record["product_code"], record["journey_type"]) for record in records
    )
    plan = {
        ("motor-private-car", "new_business"): 15,
        ("motor-private-car", "renewal"): 15,
        ("health-individual-family-floater", "new_business"): 15,
        ("health-individual-family-floater", "renewal"): 15,
        ("life-individual-term", "new_business"): 30,
    }
    if counts != plan:
        raise EvaluationFailure("dataset", "preflight", "journey_distribution")
    routes = Counter(record["expected"]["route"] for record in records)
    if routes != {"expedited": 30, "standard": 30, "specialist": 30}:
        raise EvaluationFailure("dataset", "preflight", "route_balance")
    for record in records:
        key = (record["product_code"], record["configuration_version"])
        configuration = configurations.get(key)
        if configuration is None:
            raise EvaluationFailure(
                record["case_id"], "preflight", "unknown_version"
            )
        if record["journey_type"] not in configuration.supported_journeys:
            raise EvaluationFailure(
                record["case_id"], "preflight", "unsupported_journey"
            )


# Activate every exact version the dataset needs and record its content hash.
def activate_versions(
    client: httpx.Client,
    admin: dict[str, str],
    records: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    activated: dict[str, dict[str, str]] = {}
    seen: set[tuple[str, str]] = set()
    for record in records:
        key = (record["product_code"], record["configuration_version"])
        if key in seen:
            continue
        seen.add(key)
        product_code, version = key
        response = client.post(
            f"/products/{product_code}/activate",
            json={"version": version},
            headers=admin,
        )
        if response.status_code != 200:
            raise EvaluationFailure(product_code, "activate", "http_error")
        history = client.get(f"/products/{product_code}/history", headers=admin)
        history.raise_for_status()
        entry = next(
            item for item in history.json() if item["version"] == version
        )
        activated[product_code] = {
            "version": entry["version"],
            "content_hash": entry["content_hash"],
        }
    return activated


# Create, evidence, and submit one synthetic case; return its UUID and the
# route the public submit response reported for it.
def submit_case(
    client: httpx.Client, applicant: dict[str, str], record: dict[str, Any]
) -> tuple[str, str]:
    created = client.post(
        "/cases",
        json={
            "product_code": record["product_code"],
            "idempotency_key": record["case_id"],
            "journey": record["journey_type"],
            "payload": record["workflow_input"]["payload"],
            "document_codes": [
                document["document_id"] for document in record["documents"]
            ],
        },
        headers=applicant,
    )
    if created.status_code != 200:
        raise EvaluationFailure(record["case_id"], "create", "http_error")
    case_uuid = created.json()["id"]
    for document in record["documents"]:
        uploaded = client.post(
            f"/cases/{case_uuid}/documents",
            data={"document_code": document["document_id"]},
            files={
                "document": (
                    document["filename"],
                    "\n".join(document["lines"]).encode(),
                    "application/pdf",
                )
            },
            headers=applicant,
        )
        if uploaded.status_code != 200:
            raise EvaluationFailure(record["case_id"], "upload", "http_error")
    submitted = client.post(f"/cases/{case_uuid}/submit", headers=applicant)
    if submitted.status_code != 200:
        raise EvaluationFailure(record["case_id"], "submit", "http_error")
    route = submitted.json()["recommendation"]["route"]
    if route != record["expected"]["route"]:
        raise EvaluationFailure(record["case_id"], "submit", "unexpected_route")
    return case_uuid, route


# Run one synthetic case and report its route without raising on mismatch.
def run_case(
    client: httpx.Client, applicant: dict[str, str], record: dict[str, Any]
) -> dict[str, str]:
    _, route = submit_case(client, applicant, record)
    return {"case_id": record["case_id"], "route": route}


# Start review, confirm the recommendation, and complete a case twice.
def review_and_complete(
    client: httpx.Client,
    underwriter: dict[str, str],
    case_id: str,
    case_uuid: str,
) -> None:
    started = client.post(f"/reviews/{case_uuid}/start", headers=underwriter)
    if started.status_code != 200:
        raise EvaluationFailure(case_id, "review_start", "http_error")
    confirmed = client.post(
        f"/reviews/{case_uuid}",
        json={"action": "confirm", "evidence_acknowledged": True},
        headers=underwriter,
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
        if route not in REVIEWABLE_ROUTES:
            continue
        key = (record["product_code"], record["journey_type"], route)
        if key in seen:
            continue
        seen.add(key)
        representatives.append(record)
    return representatives


# Run every reference case end to end and return the result artifact.
def run_evaluation(base_url: str) -> dict[str, Any]:
    records = load_dataset()
    configurations = load_configuration_manifest()
    preflight(records, configurations)

    dataset_sha256 = hashlib.sha256(
        default_dataset_path().read_bytes()
    ).hexdigest()

    failures: list[dict[str, str]] = []
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        admin = login(client, "administrator")
        applicant = login(client, "applicant")
        underwriter = login(client, "underwriter")
        product_configurations = activate_versions(client, admin, records)

        case_uuids: dict[str, str] = {}
        actual_routes: dict[str, str] = {}
        for record in records:
            try:
                case_uuid, route = submit_case(client, applicant, record)
            except EvaluationFailure as failure:
                failures.append(failure.detail)
                continue
            case_uuids[record["case_id"]] = case_uuid
            actual_routes[record["case_id"]] = route

        reviewed_count = 0
        completed_count = 0
        for record in representative_cases(records):
            case_id = record["case_id"]
            case_uuid = case_uuids.get(case_id)
            if case_uuid is None:
                continue
            try:
                review_and_complete(client, underwriter, case_id, case_uuid)
                reviewed_count += 1
                completed_count += 1
                verify_queue_and_audit(client, admin, case_id, case_uuid)
            except EvaluationFailure as failure:
                failures.append(failure.detail)

    metrics = {
        "route_agreement": round(len(actual_routes) / len(records), 4)
        if records
        else 0.0,
    }
    failures.sort(
        key=lambda item: (item["case_id"], item["stage"], item["code"])
    )
    return {
        "schema_version": 1,
        "passed": not failures,
        "provider": "fake",
        "dataset_sha256": dataset_sha256,
        "configurations": product_configurations,
        "case_count": len(records),
        "journey_counts": dict(
            Counter(record["journey_type"] for record in records)
        ),
        "route_counts": dict(
            Counter(record["expected"]["route"] for record in records)
        ),
        "metrics": metrics,
        "reviewed_count": reviewed_count,
        "completed_count": completed_count,
        "failures": failures,
    }


# Run the isolated evaluation, write its result, and exit with its status.
def main() -> int:
    base_url = os.environ.get("EVALUATION_API_BASE_URL", DEFAULT_BASE_URL)
    started = time.monotonic()
    try:
        result = run_evaluation(base_url)
    except EvaluationFailure as failure:
        result = {
            "schema_version": 1,
            "passed": False,
            "provider": "fake",
            "dataset_sha256": "",
            "configurations": {},
            "case_count": 0,
            "journey_counts": {},
            "route_counts": {},
            "metrics": {},
            "reviewed_count": 0,
            "completed_count": 0,
            "failures": [failure.detail],
        }
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    atomic_write_json(RESULT_PATH, result)
    print(json.dumps({"passed": result["passed"]}))
    return exit_code_for(result)


if __name__ == "__main__":
    sys.exit(main())
