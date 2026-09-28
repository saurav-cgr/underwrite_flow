"""Unit tests for deterministic corpus-to-product alignment."""

from pathlib import Path

import pytest

from underwriteflow.knowledge.alignment import check_alignment
from underwriteflow.knowledge.corpus import load_corpus
from underwriteflow.products.service import load_configuration


ROOT = Path("/app") if Path("/app").exists() else Path(__file__).parents[3]
CONFIGURATION = load_configuration(
    (ROOT / "product-config/life-individual-term-v3.yaml").read_text()
)


# Load one corpus with a single threshold for focused alignment assertions.
def corpus_text(
    rule_code: str = "high_cover_standard",
    value: int = 10_000_000,
    body: str = "Requested cover above 10000000 needs review.",
) -> str:
    return f"""
product_code: life-individual-term
version: g1
aligned_product_version: v3
label: SYNTHETIC - FOR DEMONSTRATION ONLY
topics: [cover-amount]
sections:
  - id: life-cover-high-sum-assured
    title: High requested cover
    topic: cover-amount
    thresholds:
      - rule_code: {rule_code}
        field: requested_cover
        operator: greater_than
        value: {value}
    body: {body}
"""


# Verify an aligned routing threshold produces no issues.
def test_matching_threshold_passes() -> None:
    result = check_alignment(
        load_corpus(corpus_text()),
        CONFIGURATION,
    )

    assert result == {"valid": True, "issues": []}


# Verify changed threshold values identify both sides of the mismatch.
def test_changed_value_reports_threshold_mismatch() -> None:
    result = check_alignment(
        load_corpus(
            corpus_text(
                value=5_000_000,
                body="High cover needs standard review.",
            )
        ),
        CONFIGURATION,
    )

    assert result["valid"] is False
    assert result["issues"] == [
        {
            "code": "threshold_mismatch",
            "section_id": "life-cover-high-sum-assured",
            "stated": 5_000_000,
            "rule_value": 10_000_000,
            "rule_code": "high_cover_standard",
        }
    ]


# Verify unknown rule references fail without changing product rules.
def test_unknown_rule_reports_code() -> None:
    result = check_alignment(
        load_corpus(corpus_text(rule_code="missing_rule")),
        CONFIGURATION,
    )

    assert result["valid"] is False
    assert result["issues"][0]["code"] == "unknown_rule"
    assert result["issues"][0]["rule_code"] == "missing_rule"


# Verify conditional document requirements align through document prefixes.
def test_document_condition_matches() -> None:
    result = check_alignment(
        load_corpus(
            corpus_text(
                rule_code="document:income_record",
                body="Income record is needed above 10000000.",
            )
        ),
        CONFIGURATION,
    )

    assert result == {"valid": True, "issues": []}


# Verify reconciliation parameters align through reconciliation prefixes.
def test_reconciliation_parameter_matches() -> None:
    result = check_alignment(
        load_corpus(
            """
product_code: life-individual-term
version: g1
aligned_product_version: v3
label: SYNTHETIC - FOR DEMONSTRATION ONLY
topics: [lapse-gap]
sections:
  - id: life-lapse-gap
    title: Lapse gap
    topic: lapse-gap
    thresholds:
      - rule_code: reconciliation:life_renewal_lapse
        field: maximum_gap_days
        operator: equals
        value: 30
    body: A lapse gap up to 30 days remains within this check.
"""
        ),
        CONFIGURATION,
    )

    assert result == {"valid": True, "issues": []}


# Verify prose numbers must be declared thresholds or section band bounds.
def test_undeclared_body_number_is_reported() -> None:
    result = check_alignment(
        load_corpus(
            corpus_text(body="Requested cover above 999 needs review.")
        ),
        CONFIGURATION,
    )

    assert result["valid"] is False
    assert result["issues"] == [
        {
            "code": "undeclared_number",
            "section_id": "life-cover-high-sum-assured",
            "number": 999,
        }
    ]
