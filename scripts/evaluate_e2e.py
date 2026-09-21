"""Standalone public-HTTP evaluation runner for the isolated Compose stack.

Run only inside `compose.evaluation.yaml` (see
`specs/002-journey-authoring-evaluation/contracts/evaluation.md`), which
mounts `api/src`, `evaluation/`, and `product-config/` read-only so this
script can reuse the same dataset/config loaders the offline evaluator
uses, and talks to `evaluation-api` over its own internal network.
"""

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
    DatasetPreflightError,
    dataset_sha256,
    load_configuration_manifest,
    load_dataset,
    preflight_dataset,
)

from evaluate_failures import EvaluationFailure, sanitized_failure  # noqa: E402
from evaluate_review import (  # noqa: E402
    representative_cases,
    review_and_complete,
    specialist_label_for,
    verify_queue_and_audit,
)
from synthetic_pdf import document_types, document_upload  # noqa: E402

DEFAULT_BASE_URL = "http://evaluation-api:8000/api/v1"
RESULT_PATH = Path("/app/evaluation/results/e2e.json")

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


# Write JSON atomically, so a reader never observes a partial file.
def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.chmod(0o644)
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


# Reject the dataset before any case executes, reusing the shared corpus
# rules and reporting them in this runner's sanitized failure shape.
def preflight(
    records: list[dict[str, Any]],
    configurations: dict[tuple[str, str], Any],
) -> None:
    try:
        preflight_dataset(records, configurations)
    except DatasetPreflightError as rejection:
        raise EvaluationFailure(
            rejection.case_id, rejection.stage, rejection.code
        ) from rejection


# Activate one exact version for one product and record its content hash.
# Only one version can be active per product at a time, so this is called
# per group instead of once for the whole dataset up front.
def activate_version(
    client: httpx.Client,
    admin: dict[str, str],
    product_code: str,
    version: str,
) -> dict[str, str]:
    response = client.post(
        f"/products/{product_code}/activate",
        json={"version": version},
        headers=admin,
    )
    if response.status_code != 200:
        raise EvaluationFailure(product_code, "activate", "http_error")
    history = client.get(f"/products/{product_code}/history", headers=admin)
    history.raise_for_status()
    entry = next(item for item in history.json() if item["version"] == version)
    return {"version": entry["version"], "content_hash": entry["content_hash"]}


# Create, evidence, and submit one synthetic case; return its UUID and the
# route the public submit response reported for it.
def submit_case(
    client: httpx.Client,
    applicant: dict[str, str],
    record: dict[str, Any],
    accepted_types: dict[str, list[str]] | None = None,
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
            files={"document": document_upload(document, accepted_types)},
            headers=applicant,
        )
        if uploaded.status_code != 200:
            raise EvaluationFailure(record["case_id"], "upload", "http_error")
    submitted = client.post(f"/cases/{case_uuid}/submit", headers=applicant)
    if submitted.status_code != 200:
        raise EvaluationFailure(record["case_id"], "submit", "http_error")
    route = submitted.json()["recommendation"]["route"]
    # needs_information is a queue state, not a final route: the offline
    # evaluator excludes it from route comparison and checks missing-data
    # detection instead, so this mirrors that instead of asserting equality.
    if route == "needs_information":
        if not record["expected"]["missing"]:
            raise EvaluationFailure(
                record["case_id"], "submit", "unexpected_needs_information"
            )
        return case_uuid, route
    if route != record["expected"]["route"]:
        raise EvaluationFailure(record["case_id"], "submit", "unexpected_route")
    return case_uuid, route


# Run one synthetic case and report its route without raising on mismatch.
def run_case(
    client: httpx.Client,
    applicant: dict[str, str],
    record: dict[str, Any],
    accepted_types: dict[str, list[str]] | None = None,
) -> dict[str, str]:
    _, route = submit_case(client, applicant, record, accepted_types)
    return {"case_id": record["case_id"], "route": route}


# Run every reference case end to end and return the result artifact.
def run_evaluation(base_url: str) -> dict[str, Any]:
    records = load_dataset()
    configurations = load_configuration_manifest()
    preflight(records, configurations)

    corpus_sha256 = dataset_sha256()

    failures: list[dict[str, str]] = []
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        admin = login(client, "administrator")
        applicant = login(client, "applicant")
        underwriter = login(client, "underwriter")

        # Group by (product, version) so each product activates one version
        # at a time, submitting that group before switching versions.
        ordered = sorted(
            records,
            key=lambda r: (r["product_code"], r["configuration_version"]),
        )
        product_configurations: dict[str, dict[str, str]] = {}
        active_version: dict[str, str] = {}
        case_uuids: dict[str, str] = {}
        actual_routes: dict[str, str] = {}
        for record in ordered:
            product_code = record["product_code"]
            version = record["configuration_version"]
            if active_version.get(product_code) != version:
                product_configurations[product_code] = activate_version(
                    client, admin, product_code, version
                )
                active_version[product_code] = version
            configuration = configurations[(product_code, version)]
            try:
                case_uuid, route = submit_case(
                    client, applicant, record, document_types(configuration)
                )
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
            specialist_label = specialist_label_for(record, configurations)
            try:
                review_and_complete(
                    client, underwriter, case_id, case_uuid, specialist_label
                )
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
        "dataset_sha256": corpus_sha256,
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


# Build the empty-metrics failing result artifact for one sanitized failure.
def failure_result(detail: dict[str, str]) -> dict[str, Any]:
    return {
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
        "failures": [detail],
    }


# Run the isolated evaluation, write its result, and exit with its status.
def main() -> int:
    base_url = os.environ.get("EVALUATION_API_BASE_URL", DEFAULT_BASE_URL)
    started = time.monotonic()
    try:
        result = run_evaluation(base_url)
    except EvaluationFailure as failure:
        result = failure_result(failure.detail)
    except Exception as error:  # noqa: BLE001 - sanitized into the result
        print(f"unexpected failure: {type(error).__name__}", file=sys.stderr)
        result = failure_result(
            sanitized_failure("dataset", "runtime", type(error).__name__)
        )
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    atomic_write_json(RESULT_PATH, result)
    print(json.dumps({"passed": result["passed"]}))
    return exit_code_for(result)


if __name__ == "__main__":
    sys.exit(main())
