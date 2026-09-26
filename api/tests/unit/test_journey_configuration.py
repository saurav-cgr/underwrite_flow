"""Journey defaults, subsets, document stage, and pure-filter behavior."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from underwriteflow.products.schemas import (
    ProductConfiguration,
    filter_configuration_for_journey,
)

BASE_FIELDS = [
    {
        "key": "vehicle_age",
        "label": "Vehicle age",
        "type": "integer",
        "required": True,
        "help_text": "Enter a fictional vehicle age.",
    }
]
BASE_DOCUMENTS = [
    {
        "code": "synthetic_identity",
        "title": "Synthetic identity record",
        "requirement": "required",
        "accepted_types": ["application/pdf"],
    }
]
BASE_RULES = [
    {
        "code": "synthetic_specialist",
        "condition": {
            "field": "vehicle_age",
            "operator": "greater_than",
            "value": 12,
        },
        "route": "specialist",
        "specialist_label": "motor inspection",
    }
]


# Build one minimal valid configuration payload with optional overrides.
def base_payload(**overrides) -> dict:
    payload = {
        "product_code": "synthetic-motor",
        "title": "Synthetic Motor",
        "family": "motor",
        "scope": "Fictional demonstration only",
        "description": "Synthetic product configuration",
        "version": "v1",
        "fields": deepcopy(BASE_FIELDS),
        "documents": deepcopy(BASE_DOCUMENTS),
        "routing_rules": deepcopy(BASE_RULES),
        "specialist_labels": ["motor inspection"],
    }
    payload.update(overrides)
    return payload


# Given a configuration omitting every journey key, when it loads, then
# every item defaults to new-business-only support.
def test_omitted_journey_keys_default_to_new_business_only() -> None:
    configuration = ProductConfiguration.model_validate(base_payload())

    assert configuration.supported_journeys == ["new_business"]
    assert configuration.fields[0].applies_to == ["new_business"]
    assert configuration.documents[0].applies_to == ["new_business"]
    assert configuration.documents[0].required_for is None
    assert configuration.documents[0].stage == "supporting"
    assert configuration.routing_rules[0].applies_to == ["new_business"]


def test_duplicate_supported_journeys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductConfiguration.model_validate(
            base_payload(supported_journeys=["new_business", "new_business"])
        )


def test_empty_supported_journeys_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ProductConfiguration.model_validate(
            base_payload(supported_journeys=[])
        )


def test_item_journey_must_be_declared_by_product() -> None:
    fields = deepcopy(BASE_FIELDS)
    fields[0]["applies_to"] = ["renewal"]

    with pytest.raises(ValidationError, match="undeclared journeys"):
        ProductConfiguration.model_validate(base_payload(fields=fields))


def renewal_payload(**overrides) -> dict:
    fields = deepcopy(BASE_FIELDS)
    fields[0]["applies_to"] = ["new_business", "renewal"]
    documents = deepcopy(BASE_DOCUMENTS)
    documents[0]["applies_to"] = ["new_business", "renewal"]
    documents.append(
        {
            "code": "previous_policy",
            "title": "Previous policy",
            "requirement": "optional",
            "accepted_types": ["application/pdf"],
            "applies_to": ["renewal"],
            "required_for": ["renewal"],
            "stage": "prior_policy",
        }
    )
    rules = deepcopy(BASE_RULES)
    rules[0]["applies_to"] = ["new_business", "renewal"]
    payload = base_payload(
        supported_journeys=["new_business", "renewal"],
        fields=fields,
        documents=documents,
        routing_rules=rules,
    )
    payload.update(overrides)
    return payload


def test_renewal_configuration_with_prior_policy_document_is_valid() -> None:
    configuration = ProductConfiguration.model_validate(renewal_payload())

    assert configuration.supported_journeys == ["new_business", "renewal"]


def test_document_required_for_must_be_subset_of_applies_to() -> None:
    payload = renewal_payload()
    payload["documents"][1]["applies_to"] = ["renewal"]
    payload["documents"][1]["required_for"] = ["new_business"]

    with pytest.raises(ValidationError, match="required_for"):
        ProductConfiguration.model_validate(payload)


def test_prior_policy_document_must_apply_to_renewal() -> None:
    payload = renewal_payload()
    payload["documents"][1]["applies_to"] = ["new_business"]
    payload["documents"][1]["required_for"] = None

    with pytest.raises(ValidationError, match="prior_policy"):
        ProductConfiguration.model_validate(payload)


def test_renewal_product_requires_a_prior_policy_document() -> None:
    payload = renewal_payload()
    payload["documents"].pop()

    with pytest.raises(ValidationError, match="prior_policy document"):
        ProductConfiguration.model_validate(payload)


def test_not_applicable_document_cannot_declare_required_for() -> None:
    documents = deepcopy(BASE_DOCUMENTS)
    documents[0]["requirement"] = "not_applicable"
    documents[0]["required_for"] = ["new_business"]

    with pytest.raises(ValidationError, match="not_applicable"):
        ProductConfiguration.model_validate(base_payload(documents=documents))


def test_rule_condition_field_must_be_available_on_rule_journey() -> None:
    payload = renewal_payload()
    payload["fields"][0]["applies_to"] = ["new_business"]
    payload["routing_rules"][0]["applies_to"] = ["new_business", "renewal"]

    with pytest.raises(ValidationError, match="not available on journey"):
        ProductConfiguration.model_validate(payload)


def test_reconciliation_parameter_field_must_be_available() -> None:
    payload = renewal_payload()
    payload["fields"].append(
        {
            "key": "prior_claims",
            "label": "Prior claims",
            "type": "integer",
            "required": False,
            "help_text": "Enter the fictional prior claim count.",
            "applies_to": ["new_business"],
        }
    )
    payload["fields"].append(
        {
            "key": "claimed_ncb_percent",
            "label": "Claimed NCB percent",
            "type": "integer",
            "required": True,
            "help_text": "Enter the fictional claimed NCB percentage.",
            "applies_to": ["renewal"],
        }
    )
    payload["reconciliations"] = [
        {
            "code": "motor_ncb_match",
            "kind": "ncb_match",
            "inputs": {
                "application": "claimed_ncb_percent",
                "previous_policy": "vehicle_age",
            },
            "parameters": {
                "tiers": [0, 20],
                "claim_count_field": "prior_claims",
                "claims_reset_threshold": 1,
                "claims_reset_tier": 0,
            },
            "applies_to": ["renewal"],
        }
    ]

    with pytest.raises(ValidationError, match="not available on journey"):
        ProductConfiguration.model_validate(payload)


def test_reconciliation_application_input_journey_must_be_available() -> None:
    payload = renewal_payload()
    payload["fields"].append(
        {
            "key": "claimed_ncb_percent",
            "label": "Claimed NCB percent",
            "type": "integer",
            "required": False,
            "help_text": "Enter the fictional claimed NCB percentage.",
            "applies_to": ["new_business"],
        }
    )
    payload["reconciliations"] = [
        {
            "code": "motor_ncb_match",
            "kind": "asset_match",
            "inputs": {
                "application": "claimed_ncb_percent",
                "previous_policy": "vehicle_age",
            },
            "applies_to": ["renewal"],
        }
    ]

    with pytest.raises(ValidationError, match="not available on journey"):
        ProductConfiguration.model_validate(payload)


def test_reconciliation_document_source_journey_must_be_available() -> None:
    payload = renewal_payload()
    payload["documents"][1]["applies_to"] = ["new_business"]
    payload["documents"][1]["stage"] = "supporting"
    payload["documents"][1]["required_for"] = None
    payload["reconciliations"] = [
        {
            "code": "motor_ncb_match",
            "kind": "asset_match",
            "inputs": {
                "application": "vehicle_age",
                "previous_policy": "vehicle_age",
            },
            "applies_to": ["renewal"],
        }
    ]

    with pytest.raises(ValidationError, match="not available on journey"):
        ProductConfiguration.model_validate(payload)


def test_filter_configuration_for_journey_keeps_only_applicable_items() -> (
    None
):
    configuration = ProductConfiguration.model_validate(renewal_payload())

    new_business_only = filter_configuration_for_journey(
        configuration, "new_business"
    )
    renewal_only = filter_configuration_for_journey(configuration, "renewal")

    assert [d.code for d in new_business_only.documents] == [
        "synthetic_identity"
    ]
    assert [d.code for d in renewal_only.documents] == [
        "synthetic_identity",
        "previous_policy",
    ]
    # The input configuration is never mutated by filtering.
    assert len(configuration.documents) == 2


def test_filter_configuration_for_journey_rejects_unsupported_journey() -> (
    None
):
    configuration = ProductConfiguration.model_validate(base_payload())

    with pytest.raises(ValueError, match="unsupported journey"):
        filter_configuration_for_journey(configuration, "renewal")


def test_filter_configuration_for_journey_is_pure_and_repeatable() -> None:
    configuration = ProductConfiguration.model_validate(renewal_payload())

    first = filter_configuration_for_journey(configuration, "renewal")
    second = filter_configuration_for_journey(configuration, "renewal")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
