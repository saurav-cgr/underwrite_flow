"""Negative controls for the synthetic evaluation metrics.

The reference set is solvable by design, so the pipeline reproduces every label
and each metric reads a perfect score. A perfect score is only meaningful if a
worse pipeline would score worse. These controls corrupt one part of the
produced output at a time and assert that the matching metric falls while the
unrelated metrics hold.
"""

import asyncio
from copy import deepcopy
from typing import Any

from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.runner import evaluate_cases

_REFERENCE: list[list[dict[str, Any]]] = []


# Run the reference set through the pipeline once for every control.
def produced() -> list[dict[str, Any]]:
    if not _REFERENCE:
        _REFERENCE.append(asyncio.run(evaluate_cases()))
    return _REFERENCE[0]


# Return a fresh copy of the produced records for one control to corrupt.
def corrupted() -> list[dict[str, Any]]:
    return deepcopy(produced())


# Read one metric from the uncorrupted produced reference set.
def baseline(metric: str) -> float:
    return evaluate_records(produced())[metric]


# Verify the reference set starts perfect, so each control is a real reduction.
def test_reference_baseline_is_perfect() -> None:
    summary = evaluate_records(produced())

    assert summary["route_agreement"] == 1.0
    assert summary["conflict_detection"] == 1.0
    assert summary["conflict_precision"] == 1.0
    assert summary["missing_data_detection"] == 1.0
    assert summary["missing_precision"] == 1.0
    assert summary["evidence_accuracy"] == 1.0
    assert summary["unsupported_claim_rate"] == 0.0


# Verify one wrong route is enough to move route agreement.
def test_one_diverging_route_lowers_route_agreement() -> None:
    records = corrupted()
    target = next(
        record
        for record in records
        if record["prediction"]["route"] == "expedited"
    )
    target["prediction"]["route"] = "specialist"

    summary = evaluate_records(records)

    assert summary["route_agreement"] < baseline("route_agreement")
    assert summary["conflict_detection"] == baseline("conflict_detection")


# Verify a uniformly wrong route scale collapses both route metrics.
def test_wrong_route_scale_collapses_route_metrics() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["route"] = "expedited"

    summary = evaluate_records(records)

    assert summary["specialist_recall"] == 0.0
    assert summary["route_agreement"] < 0.5


# Verify suppressing conflict detection lowers conflict metrics only.
def test_suppressed_conflict_detection_lowers_conflict_metrics() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["conflict"] = False

    summary = evaluate_records(records)

    assert summary["conflict_detection"] == 0.0
    assert summary["conflict_precision"] == 0.0
    assert summary["route_agreement"] == baseline("route_agreement")
    assert summary["missing_data_detection"] == baseline(
        "missing_data_detection"
    )


# Verify suppressing missing detection lowers missing recall only.
def test_suppressed_missing_detection_lowers_missing_recall() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["missing"] = False

    summary = evaluate_records(records)

    assert summary["missing_data_detection"] == 0.0
    assert summary["route_agreement"] == baseline("route_agreement")
    assert summary["conflict_detection"] == baseline("conflict_detection")


# Verify flagging every case as missing costs precision, not recall. This is
# the guard that stops a pipeline gaming route agreement by refusing to route.
def test_over_flagging_missing_lowers_precision_only() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["missing"] = True

    summary = evaluate_records(records)

    assert summary["missing_data_detection"] == 1.0
    assert summary["missing_precision"] < 1.0
    assert summary["missing_precision"] < baseline("missing_precision")


# Verify dropping extracted evidence lowers evidence accuracy only.
def test_dropping_evidence_lowers_evidence_accuracy() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["evidence"] = []

    summary = evaluate_records(records)

    assert summary["evidence_accuracy"] == 0.0
    assert summary["route_agreement"] == baseline("route_agreement")


# Verify stripping provenance raises the unsupported claim rate.
def test_stripping_provenance_raises_unsupported_claim_rate() -> None:
    records = corrupted()
    for record in records:
        record["prediction"]["unsupported_claims"] = record["prediction"][
            "claim_count"
        ]

    summary = evaluate_records(records)

    assert summary["unsupported_claim_rate"] == 1.0
    assert summary["unsupported_claim_rate"] > baseline(
        "unsupported_claim_rate"
    )
    assert summary["route_agreement"] == baseline("route_agreement")


# Verify a failed workflow lowers reliability without touching routing.
def test_failed_workflow_lowers_reliability_only() -> None:
    records = corrupted()
    for record in records:
        record["workflow_succeeded"] = False

    summary = evaluate_records(records)

    assert summary["workflow_reliability"] == 0.0
    assert summary["route_agreement"] == baseline("route_agreement")
