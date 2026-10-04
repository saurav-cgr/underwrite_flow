"""Deterministic product-rule conformance checks."""

import pytest
from pydantic import ValidationError

from underwriteflow.knowledge.conformance import (
    build_change_impact,
    build_conformance,
)
from underwriteflow.knowledge.regulation_router import RegulationTagLimit
from underwriteflow.products.schemas import RoutingRule
from underwriteflow.products.service import load_configuration


# Build one small product configuration for conformance assertions.
def configuration(version: str, threshold: int = 10_000_000):
    return load_configuration(
        f"""
product_code: synthetic-life
title: Synthetic Life
family: life
scope: Fictional demonstration only
description: Synthetic product
version: {version}
fields:
  - key: requested_cover
    label: Requested cover
    type: number
    required: true
    help_text: Synthetic cover
documents:
  - code: income_record
    title: Synthetic income record
    requirement: conditional
    condition:
      field: requested_cover
      operator: greater_than
      value: {threshold}
    accepted_types: [application/pdf]
routing_rules:
  - code: high_cover_standard
    condition:
      field: requested_cover
      operator: greater_than
      value: {threshold}
    route: standard
specialist_labels: [life review]
"""
    )


# Verify accepted limits flag rules while suggested tags stay inert.
def test_conformance_flags_and_related_tags() -> None:
    result = build_conformance(
        configuration("v2"),
        "r1",
        [
            {
                "passage_key": "4.2",
                "label": "PUBLIC REGULATION - INFORMATIONAL",
                "topic_tags": ["cover-amount"],
                "suggested_tags": ["cover-amount"],
                "limits": [
                    {
                        "field": "requested_cover",
                        "operator": "greater_than",
                        "value": 0,
                    }
                ],
            },
            {
                "passage_key": "4.3",
                "label": "PUBLIC REGULATION - INFORMATIONAL",
                "topic_tags": [],
                "suggested_tags": ["cover-amount"],
                "limits": [],
            },
        ],
    )

    assert result["flags"][0]["rule_code"] == "high_cover_standard"
    assert result["flags"][0]["clause"]["passage_key"] == "4.2"
    assert result["related"] == [
        {"rule_code": "high_cover_standard", "passage_keys": ["4.2"]}
    ]


# Verify structural rule and document changes against the active version.
def test_change_impact_lists_rule_threshold_and_document_changes() -> None:
    before = configuration("v2", 5_000_000)
    after = configuration("v3", 10_000_000)

    impact = build_change_impact(after, before)

    assert impact["against_version"] == "v2"
    assert impact["changed_thresholds"] == [
        {
            "rule_code": "high_cover_standard",
            "from": 5_000_000,
            "to": 10_000_000,
        }
    ]
    assert impact["changed_documents"] == [
        {
            "document_code": "income_record",
            "from": 5_000_000,
            "to": 10_000_000,
        }
    ]


# Verify added and removed rule codes remain visible in the impact diff.
def test_change_impact_lists_added_and_removed_rules() -> None:
    before = configuration("v2")
    after = configuration("v3")
    after.routing_rules = [
        RoutingRule(
            code="new_rule",
            condition={
                "field": "requested_cover",
                "operator": "greater_than",
                "value": 1,
            },
            route="standard",
            applies_to=["new_business"],
        )
    ]

    impact = build_change_impact(after, before)

    assert impact["added_rules"] == ["new_rule"]
    assert impact["removed_rules"] == ["high_cover_standard"]


# Verify equals conditions use flagged-zone semantics for numeric and text.
def test_conformance_supports_equals_condition_shorthand() -> None:
    product = configuration("v2")
    product.routing_rules[0].condition = {
        "field": "requested_cover",
        "equals": 10_000_000,
    }
    passage = {
        "passage_key": "4.4",
        "label": "PUBLIC REGULATION - INFORMATIONAL",
        "topic_tags": [],
        "limits": [
            {
                "field": "requested_cover",
                "operator": "equals",
                "value": 10_000_000,
            }
        ],
    }

    assert len(build_conformance(product, "r1", [passage])["flags"]) == 1
    product.routing_rules[0].condition["equals"] = 5_000_000
    assert build_conformance(product, "r1", [passage])["flags"] == []

    product.routing_rules[0].condition = {
        "field": "requested_cover",
        "equals": "hazardous",
    }
    passage["limits"][0]["value"] = "hazardous"
    assert len(build_conformance(product, "r1", [passage])["flags"]) == 1
    passage["limits"][0]["value"] = "safe"
    assert build_conformance(product, "r1", [passage])["flags"] == []


# Keep non-finite conformance values informational instead of crashing.
def test_conformance_ignores_non_finite_values() -> None:
    product = configuration("v2")
    passage = {
        "passage_key": "4.5",
        "label": "PUBLIC REGULATION - INFORMATIONAL",
        "topic_tags": [],
        "limits": [
            {
                "field": "requested_cover",
                "operator": "greater_than",
                "value": 0,
            }
        ],
    }
    product.routing_rules[0].condition["value"] = float("nan")
    assert build_conformance(product, "r1", [passage])["flags"] == []

    passage["limits"][0]["value"] = float("inf")
    product.routing_rules[0].condition["value"] = 10_000_000
    assert build_conformance(product, "r1", [passage])["flags"] == []

    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            RegulationTagLimit.model_validate(
                {
                    "field": "requested_cover",
                    "operator": "greater_than",
                    "value": value,
                }
            )
