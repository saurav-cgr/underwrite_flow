"""Reconciliation definitions declared by one fictional product version.

These tests cover configuration shape and reference rules only. The pure
comparison code that consumes the definitions arrives with the evidence work.
"""

import json

import pytest
import yaml

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.service import (
    ProductConfigurationError,
    ProductService,
    load_configuration,
)


# Build one fictional configuration with the supplied reconciliation block.
def reconciliation_configuration(reconciliations: str) -> str:
    return f"""
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: claimed_ncb_percent
    label: Claimed NCB percent
    type: integer
    required: true
    help_text: Enter the fictional claimed NCB percentage.
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Enter the fictional vehicle age in years.
  - key: prior_claims
    label: Prior claims
    type: integer
    required: true
    help_text: Enter the fictional prior claim count.
documents:
  - code: previous_policy
    title: Synthetic previous policy
    requirement: required
    accepted_types: [application/pdf]
  - code: claims_history
    title: Synthetic claims history
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: vehicle_age_specialist
    condition: {{field: vehicle_age, operator: greater_than, value: 12}}
    route: specialist
    specialist_label: synthetic review
specialist_labels: [synthetic review]
reconciliations:
{reconciliations}
"""


VALID_RECONCILIATIONS = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
      previous_policy: ncb_percent
      claims_history: claim_count
"""

PARAMETERIZED_RECONCILIATIONS = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
      previous_policy: ncb_percent
    parameters:
      tiers: [0, 20, 25, 35, 45, 50]
      claim_count_field: prior_claims
      claims_reset_threshold: 1
      claims_reset_tier: 0
  - code: motor_renewal_lapse
    kind: policy_lapse
    inputs:
      application: claimed_ncb_percent
      previous_policy: policy_expiry_date
    parameters:
      maximum_gap_days: 30
      boundary: inclusive
"""


# Load one fictional configuration carrying the supplied reconciliation block.
def load_reconciliations(reconciliations: str) -> ProductConfiguration:
    return ProductConfiguration.model_validate(
        yaml.safe_load(reconciliation_configuration(reconciliations))
    )


# Verify a declared check keeps its code, kind, and input mapping.
def test_reconciliation_check_is_accepted() -> None:
    configuration = load_reconciliations(VALID_RECONCILIATIONS)

    assert [check.code for check in configuration.reconciliations] == [
        "motor_ncb_match"
    ]
    assert configuration.reconciliations[0].kind == "ncb_match"
    assert configuration.reconciliations[0].inputs["previous_policy"] == (
        "ncb_percent"
    )


# Verify NCB and renewal parameters survive validated configuration parsing.
def test_reconciliation_parameters_are_pinned() -> None:
    configuration = load_reconciliations(PARAMETERIZED_RECONCILIATIONS)

    ncb, renewal = configuration.reconciliations
    assert ncb.parameters.tiers == [0, 20, 25, 35, 45, 50]
    assert ncb.parameters.claim_count_field == "prior_claims"
    assert renewal.parameters.maximum_gap_days == 30
    assert renewal.parameters.boundary == "inclusive"
    preview = ProductService().preview(configuration)
    assert preview["reconciliations"][0]["parameters"]["tiers"] == [
        0,
        20,
        25,
        35,
        45,
        50,
    ]


# Verify invalid NCB progression cannot be activated.
def test_ncb_tiers_must_be_strictly_increasing() -> None:
    malformed = PARAMETERIZED_RECONCILIATIONS.replace(
        "[0, 20, 25, 35, 45, 50]", "[0, 25, 20]"
    )

    with pytest.raises(Exception) as refused:
        load_reconciliations(malformed)

    assert "strictly increasing" in str(refused.value)


# Verify parameterized NCB has one claim and one previous-policy source.
def test_parameterized_ncb_requires_one_document_source() -> None:
    malformed = PARAMETERIZED_RECONCILIATIONS.replace(
        "      previous_policy: ncb_percent\n",
        "      previous_policy: ncb_percent\n"
        "      claims_history: claim_count\n",
        1,
    )

    with pytest.raises(Exception) as refused:
        load_reconciliations(malformed)

    assert "one document source" in str(refused.value)


# Verify a configuration without checks stays valid for earlier versions.
def test_reconciliations_default_to_empty() -> None:
    configuration = load_reconciliations("  []")

    assert configuration.reconciliations == []


# Verify duplicate check codes are refused.
def test_duplicate_reconciliation_codes_are_refused() -> None:
    duplicated = VALID_RECONCILIATIONS + VALID_RECONCILIATIONS

    with pytest.raises(Exception) as refused:
        load_reconciliations(duplicated)

    assert "unique" in str(refused.value)


# Verify a source that is neither the claim nor a declared document is refused.
def test_unknown_input_source_is_refused() -> None:
    unknown = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
      inspection_photo: ncb_percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(unknown)

    assert "unknown input sources" in str(refused.value)


# Verify a check that reads no document evidence is refused.
def test_document_free_check_is_refused() -> None:
    evidence_free = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(evidence_free)

    assert "document source is required" in str(refused.value)


# Verify a check needs two sides before it can compare anything.
def test_single_source_check_is_refused() -> None:
    single = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      previous_policy: ncb_percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(single)

    assert "two comparison sources" in str(refused.value)


# Verify a document-to-document check such as asset matching is accepted.
def test_document_only_check_is_accepted() -> None:
    document_only = """
  - code: motor_asset_match
    kind: asset_match
    inputs:
      previous_policy: engine_number
      claims_history: engine_number
"""

    configuration = load_reconciliations(document_only)

    assert configuration.reconciliations[0].kind == "asset_match"
    assert "application" not in configuration.reconciliations[0].inputs


# Verify a claimed field that is not declared is refused.
def test_undeclared_application_field_is_refused() -> None:
    undeclared = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: invented_percent
      previous_policy: ncb_percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(undeclared)

    assert "not declared" in str(refused.value)


# Verify a malformed evidence field name is refused.
def test_malformed_field_name_is_refused() -> None:
    malformed = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
      previous_policy: NCB Percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(malformed)

    assert "malformed field name" in str(refused.value)


# Verify a malformed check code is refused.
def test_malformed_check_code_is_refused() -> None:
    malformed = """
  - code: Motor NCB
    kind: ncb_match
    inputs:
      application: claimed_ncb_percent
      previous_policy: ncb_percent
"""

    with pytest.raises(Exception) as refused:
        load_reconciliations(malformed)

    assert "malformed code" in str(refused.value)


# Verify only the three implemented kinds may be configured.
def test_unsupported_kind_is_refused() -> None:
    unsupported = """
  - code: motor_ncb_match
    kind: arbitrary_python
    inputs:
      application: claimed_ncb_percent
      previous_policy: ncb_percent
"""

    with pytest.raises(Exception):
        load_reconciliations(unsupported)


# Verify JSON configuration carries the same reconciliation definitions.
def test_json_configuration_carries_checks() -> None:
    text = reconciliation_configuration(VALID_RECONCILIATIONS)
    payload = yaml.safe_load(text)

    configuration = load_configuration(json.dumps(payload))

    assert configuration.product_code == "synthetic-motor"
    assert [check.code for check in configuration.reconciliations] == [
        "motor_ncb_match"
    ]


# Verify a badly formed configuration names the failing reference.
def test_validation_reason_names_the_failing_reference() -> None:
    undeclared = """
  - code: motor_ncb_match
    kind: ncb_match
    inputs:
      application: invented_percent
      previous_policy: ncb_percent
"""

    with pytest.raises(ProductConfigurationError) as refused:
        load_configuration(reconciliation_configuration(undeclared))

    assert "not declared" in str(refused.value)


# Verify the preview exposes each configured check for administrator review.
def test_preview_summarizes_configured_checks() -> None:
    configuration = load_reconciliations(VALID_RECONCILIATIONS)

    preview = ProductService().preview(configuration)

    assert preview["reconciliation_count"] == 1
    assert preview["reconciliations"] == [
        {
            "code": "motor_ncb_match",
            "kind": "ncb_match",
            "inputs": {
                "application": "claimed_ncb_percent",
                "previous_policy": "ncb_percent",
                "claims_history": "claim_count",
            },
            "applies_to": ["new_business"],
        }
    ]


# Verify a configuration without checks previews an empty list.
def test_preview_reports_no_checks() -> None:
    preview = ProductService().preview(load_reconciliations("  []"))

    assert preview["reconciliation_count"] == 0
    assert preview["reconciliations"] == []
