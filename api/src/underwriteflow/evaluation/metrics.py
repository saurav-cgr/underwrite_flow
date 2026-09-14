"""Deterministic metrics for the synthetic evaluation reference set."""

from collections import Counter
from typing import Any


# Return a safe ratio for empty or unavailable metric denominators.
def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


# Read expected and predicted labels from one evaluation record.
def labels(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if "expected" in record and "prediction" in record:
        return record["expected"], record["prediction"]
    return (
        {
            "route": record["expected_route"],
            "evidence": record["expected_evidence"],
            "conflict": record["expected_conflict"],
            "missing": record["expected_missing"],
            "unsupported_claims": record["expected_unsupported_claims"],
        },
        {
            "route": record["predicted_route"],
            "evidence": record["predicted_evidence"],
            "conflict": record["predicted_conflict"],
            "missing": record["predicted_missing"],
            "unsupported_claims": record["predicted_unsupported_claims"],
        },
    )


# Calculate route, evidence, detection, claim, and workflow metrics.
def evaluate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("evaluation requires at least one record")
    pairs = [labels(record) for record in records]
    expected_routes = [expected["route"] for expected, _ in pairs]
    route_matches = sum(
        expected["route"] == predicted["route"]
        for expected, predicted in pairs
    )
    specialist_total = sum(route == "specialist" for route in expected_routes)
    specialist_hits = sum(
        expected["route"] == predicted["route"] == "specialist"
        for expected, predicted in pairs
    )
    evidence_hits = sum(
        set(expected["evidence"]) == set(predicted["evidence"])
        for expected, predicted in pairs
    )
    conflict_total = sum(expected["conflict"] for expected, _ in pairs)
    conflict_hits = sum(
        expected["conflict"] and predicted["conflict"]
        for expected, predicted in pairs
    )
    missing_total = sum(expected["missing"] for expected, _ in pairs)
    missing_hits = sum(
        expected["missing"] and predicted["missing"]
        for expected, predicted in pairs
    )
    unsupported_cases = sum(
        predicted["unsupported_claims"] > 0 for _, predicted in pairs
    )
    return {
        "case_count": len(records),
        "development_count": sum(
            record.get("split") == "development" for record in records
        ),
        "holdout_count": sum(
            record.get("split") == "holdout" for record in records
        ),
        "route_counts": dict(Counter(expected_routes)),
        "route_agreement": ratio(route_matches, len(records)),
        "specialist_recall": ratio(specialist_hits, specialist_total),
        "evidence_accuracy": ratio(evidence_hits, len(records)),
        "conflict_detection": ratio(conflict_hits, conflict_total),
        "missing_data_detection": ratio(missing_hits, missing_total),
        "unsupported_claim_rate": ratio(unsupported_cases, len(records)),
        "workflow_reliability": ratio(
            sum(record.get("workflow_succeeded", False) for record in records),
            len(records),
        ),
    }
