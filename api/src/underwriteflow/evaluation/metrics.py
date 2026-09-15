"""Deterministic metrics for the synthetic evaluation reference set.

Every metric is calculated from the pipeline's produced output. `expected` is
the reference label; `prediction` is what the extraction, reconciliation,
product, and routing pipeline actually produced.

Route agreement is scored only over cases the pipeline could route. The
reference labels describe the final triage route, while `needs_information` is
a queue state the pipeline reports before it has enough evidence to route. A
case flagged `needs_information` is measured by missing-information precision
instead, so flagging everything cannot inflate the route score.
"""

from collections import Counter
from typing import Any

NEEDS_INFORMATION = "needs_information"


# Return a safe ratio for empty or unavailable metric denominators.
def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


# Read the expected labels and the produced prediction for one record.
def labels(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return record["expected"], record["prediction"]


# Calculate route, detection, provenance, and workflow metrics.
def evaluate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("evaluation requires at least one record")
    pairs = [labels(record) for record in records]
    routable = [
        (expected, predicted)
        for expected, predicted in pairs
        if predicted["route"] != NEEDS_INFORMATION
    ]
    route_matches = sum(
        expected["route"] == predicted["route"]
        for expected, predicted in routable
    )
    specialist_total = sum(
        expected["route"] == "specialist" for expected, _ in routable
    )
    specialist_hits = sum(
        expected["route"] == predicted["route"] == "specialist"
        for expected, predicted in routable
    )
    conflict_total = sum(expected["conflict"] for expected, _ in pairs)
    conflict_hits = sum(
        expected["conflict"] and predicted["conflict"]
        for expected, predicted in pairs
    )
    conflict_flagged = sum(predicted["conflict"] for _, predicted in pairs)
    missing_total = sum(expected["missing"] for expected, _ in pairs)
    missing_hits = sum(
        expected["missing"] and predicted["missing"]
        for expected, predicted in pairs
    )
    missing_flagged = sum(predicted["missing"] for _, predicted in pairs)
    evidence_hits = sum(
        set(expected["evidence"]) == set(predicted["evidence"])
        for expected, predicted in pairs
    )
    unsupported_claims = sum(
        predicted["unsupported_claims"] for _, predicted in pairs
    )
    produced_claims = sum(predicted["claim_count"] for _, predicted in pairs)
    return {
        "case_count": len(records),
        "development_count": sum(
            record.get("split") == "development" for record in records
        ),
        "holdout_count": sum(
            record.get("split") == "holdout" for record in records
        ),
        "route_counts": dict(
            Counter(expected["route"] for expected, _ in pairs)
        ),
        "routable_count": len(routable),
        "needs_information_count": len(pairs) - len(routable),
        "route_agreement": ratio(route_matches, len(routable)),
        "specialist_recall": ratio(specialist_hits, specialist_total),
        "conflict_detection": ratio(conflict_hits, conflict_total),
        "conflict_precision": ratio(conflict_hits, conflict_flagged),
        "missing_data_detection": ratio(missing_hits, missing_total),
        "missing_precision": ratio(missing_hits, missing_flagged),
        "evidence_accuracy": ratio(evidence_hits, len(records)),
        "unsupported_claim_rate": ratio(unsupported_claims, produced_claims),
        "workflow_reliability": ratio(
            sum(record.get("workflow_succeeded", False) for record in records),
            len(records),
        ),
    }
