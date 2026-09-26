"""Unit coverage for the reusable evaluation corpus preflight.

Both the end-to-end evaluator and the data loader must reject the corpus
before any case runs, so the rules live once in the evaluation package.
"""

import copy
from typing import Any

import pytest

from underwriteflow.evaluation.dataset import (
    DatasetPreflightError,
    load_configuration_manifest,
    load_dataset,
    preflight_dataset,
)


# Provide the authoritative corpus once per module.
@pytest.fixture(scope="module")
def records() -> list[dict[str, Any]]:
    return load_dataset()


# Provide the published product configuration manifest once per module.
@pytest.fixture(scope="module")
def configurations() -> dict[tuple[str, str], Any]:
    return load_configuration_manifest()


# Return a deep copy so a mutation cannot leak into another test.
def _mutated(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy(records)


# Given the shipped corpus, when preflighted, then it is accepted.
def test_authoritative_corpus_passes_preflight(records, configurations) -> None:
    preflight_dataset(records, configurations)


# Given the shipped corpus, when counted, then it holds 90 unique cases.
def test_corpus_holds_ninety_unique_cases(records) -> None:
    assert len(records) == 90
    assert len({record["case_id"] for record in records}) == 90


# Given a short corpus, when preflighted, then the count is rejected.
def test_short_corpus_is_rejected(records, configurations) -> None:
    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(_mutated(records)[:89], configurations)

    assert failure.value.code == "case_count"


# Given a duplicated case ID, when preflighted, then uniqueness is enforced.
def test_duplicate_case_id_is_rejected(records, configurations) -> None:
    mutated = _mutated(records)
    mutated[1]["case_id"] = mutated[0]["case_id"]

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "case_count"


# Given an unsafe case ID shape, when preflighted, then it is rejected
# before any downstream use, whatever else the record contains.
@pytest.mark.parametrize(
    "case_id",
    [
        "Bearer synthetic-secret-token-x",
        "case id with spaces",
        "case/../traversal",
        "x" * 500,
        "",
        None,
        12345,
    ],
)
def test_unsafe_case_id_is_rejected(records, configurations, case_id) -> None:
    mutated = _mutated(records)
    mutated[0]["case_id"] = case_id

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "unsafe_case_id"


# Given a wrong synthetic label, when preflighted, then it is rejected.
@pytest.mark.parametrize(
    "label",
    ["", "synthetic - for demonstration only", "REAL APPLICANT DATA", None],
)
def test_non_synthetic_label_is_rejected(
    records, configurations, label
) -> None:
    mutated = _mutated(records)
    if label is None:
        del mutated[0]["fixture_label"]
    else:
        mutated[0]["fixture_label"] = label

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "fixture_label"


# Given the shipped corpus, when split, then only known splits are present.
def test_only_supported_splits_are_present(records) -> None:
    splits = {record["split"] for record in records}

    assert splits == {"development", "holdout"}


# Given an unknown split, when preflighted, then it is rejected.
def test_unsupported_split_is_rejected(records, configurations) -> None:
    mutated = _mutated(records)
    mutated[0]["split"] = "production"

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "unsupported_split"


# Given a changed journey mix, when preflighted, then balance is enforced.
def test_journey_distribution_is_enforced(records, configurations) -> None:
    mutated = _mutated(records)
    for record in mutated:
        if record["journey_type"] == "renewal":
            record["journey_type"] = "new_business"
            break

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "journey_distribution"


# Given a changed route mix, when preflighted, then balance is enforced.
def test_route_balance_is_enforced(records, configurations) -> None:
    mutated = _mutated(records)
    mutated[0]["expected"]["route"] = "specialist"

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "route_balance"


# Given an unknown configuration version, when preflighted, then it fails.
def test_unknown_configuration_version_is_rejected(
    records, configurations
) -> None:
    mutated = _mutated(records)
    mutated[0]["configuration_version"] = "v999"

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code == "unknown_version"
    assert failure.value.case_id == mutated[0]["case_id"]


# Given a journey its version forbids, when preflighted, then it fails.
def test_unsupported_journey_is_rejected(records, configurations) -> None:
    mutated = _mutated(records)
    target = next(
        record
        for record in mutated
        if record["product_code"].startswith("life")
    )
    target["journey_type"] = "renewal"

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.code in {
        "journey_distribution",
        "unsupported_journey",
    }


# Given a failure, when reported, then only safe fields are exposed.
def test_preflight_error_reports_only_safe_fields(
    records, configurations
) -> None:
    mutated = _mutated(records)
    mutated[0]["configuration_version"] = "v999"

    with pytest.raises(DatasetPreflightError) as failure:
        preflight_dataset(mutated, configurations)

    assert failure.value.detail == {
        "case_id": mutated[0]["case_id"],
        "stage": "preflight",
        "code": "unknown_version",
    }
