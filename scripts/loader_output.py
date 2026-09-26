"""Result-shaping helpers for the evaluation loader.

Split out of `load_evaluation_data.py` to keep that file under the project
line-count limit. These helpers own only how one run's dataset identity and
result are named and safely rendered; case, document, and workflow mapping
stay in the main script.
"""

import hashlib
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.environ.get("UNDERWRITEFLOW_SRC", "/app/src"))

from underwriteflow.evaluation.dataset import SAFE_CASE_ID  # noqa: E402

KEY_PREFIX = "evaluation"

ERROR_FORBIDDEN = "evaluation_load_forbidden"
ERROR_COLLISION = "evaluation_record_collision"
ERROR_PRECONDITION = "evaluation_load_precondition_failed"
ERROR_PREFLIGHT = "evaluation_load_preflight_failed"
ERROR_UNEXPECTED = "evaluation_load_failed"


# Build the reserved idempotency key for one source record.
def record_key(dataset_sha256_value: str, source_case_id: str) -> str:
    return f"{KEY_PREFIX}:{dataset_sha256_value}:{source_case_id}"


# Order records so every run walks the corpus in the same sequence.
def ordered_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda record: record["case_id"])


# Identify an injected record subset by its canonical serialized bytes.
def records_sha256(records: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        ordered_records(records), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


# Build the safe completion object one successful load prints.
def success_result(
    environment: str,
    dataset_sha256: str,
    expected_count: int,
    created_count: int,
    resumed_count: int,
    verified_count: int,
) -> dict[str, Any]:
    return {
        "environment": environment,
        "dataset_sha256": dataset_sha256,
        "expected_count": expected_count,
        "created_count": created_count,
        "resumed_count": resumed_count,
        "verified_count": verified_count,
        "complete": verified_count == expected_count,
    }


# Return one corpus-derived field only when it is a plain, bounded string.
# A malformed record can put anything in a labeled field, so nothing it
# supplies reaches standard output without this shape check first.
def safe_field(value: Any, limit: int = 200) -> str | None:
    if not isinstance(value, str) or not value or len(value) > limit:
        return None
    return value


# Return a source case ID only when it is a safe, bounded identifier: a
# length check alone lets a short secret-shaped string through, so this
# reuses the same identifier format the corpus preflight itself enforces.
def safe_case_id(value: Any) -> str | None:
    if not isinstance(value, str) or not SAFE_CASE_ID.match(value):
        return None
    return value


# Build the safe failure object a refused or incomplete load prints. Every
# caller shares this one sanitization: a source case ID or stage can come
# from a corpus record no preflight has yet rejected, so it is bounded here
# once rather than trusted at each call site, including record collisions.
def failure_result(
    environment: str,
    error_code: str,
    dataset_sha256: str | None = None,
    source_case_id: str | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "environment": environment,
        "complete": False,
        "error_code": error_code,
    }
    for key, value in (
        ("dataset_sha256", safe_field(dataset_sha256)),
        ("source_case_id", safe_case_id(source_case_id)),
        ("stage", safe_field(stage)),
    ):
        if value is not None:
            result[key] = value
    return result
