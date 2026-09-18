"""Pinned fictional NCB and renewal parameter behavior."""

import json

import pytest

from underwriteflow.workflow.reconciliation import reconcile

NCB_CHECK = {
    "code": "motor_ncb_progression",
    "kind": "ncb_match",
    "inputs": {
        "application": "claimed_ncb_percent",
        "previous_policy": "ncb_percent",
    },
    "parameters": {
        "tiers": [0, 20, 25, 35, 45, 50],
        "claim_count_field": "prior_claims",
        "claims_reset_threshold": 1,
        "claims_reset_tier": 0,
    },
}


# Build one synthetic previous-policy evidence value.
def evidence(field_name: str, value: object) -> dict[str, object]:
    return {
        "field_name": field_name,
        "value": value,
        "document_id": "doc-1",
        "document_code": "previous_policy",
        "source_locator": "page:1",
    }


# Reconcile one synthetic case against the pinned parameter set.
def run(
    checks: list[dict[str, object]], application: dict[str, object]
) -> dict[str, object]:
    return reconcile(
        checks,
        application,
        [evidence("ncb_percent", 20)],
        "v2",
    )


# Verify a claim-free renewal advances exactly one configured NCB tier.
def test_ncb_progresses_through_the_pinned_tiers() -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": 25, "prior_claims": 0},
    )

    outcome = result["results"][0]
    assert outcome["status"] == "CLEARED"
    assert outcome["comparisons"][0]["left"] == 25
    assert outcome["comparisons"][0]["explanation_code"] == (
        "ncb_progression_matches"
    )


# Verify the configured claims threshold resets NCB to its configured tier.
def test_ncb_claims_apply_the_pinned_reset_tier() -> None:
    application = {"claimed_ncb_percent": 0, "prior_claims": 1}
    cleared = run([NCB_CHECK], application)
    application["claimed_ncb_percent"] = 20
    flagged = run([NCB_CHECK], application)

    assert cleared["results"][0]["status"] == "CLEARED"
    assert flagged["results"][0]["discrepancies"] == [
        {
            "code": "ncb_progression_mismatch",
            "field_key": "claimed_ncb_percent",
            "expected": 0,
            "actual": 20,
        }
    ]


# Verify the configured renewal boundary decides an exact maximum-day gap.
def test_policy_lapse_uses_the_pinned_boundary() -> None:
    inputs = {
        "application": "policy_start_date",
        "previous_policy": "policy_expiry_date",
    }
    checks = [
        {
            "code": f"{boundary}_renewal",
            "kind": "policy_lapse",
            "inputs": inputs,
            "parameters": {
                "maximum_gap_days": 30,
                "boundary": boundary,
            },
        }
        for boundary in ("inclusive", "exclusive")
    ]
    items = [evidence("policy_expiry_date", "2026-01-01")]

    results = [
        reconcile(
            [check],
            {"policy_start_date": "2026-01-31"},
            items,
            "v2",
        )["overall_status"]
        for check in checks
    ]
    assert results == ["CLEARED", "FLAGGED_DISCREPANCY"]


# Verify result values are canonical and explanations ignore input formatting.
def test_reconciliation_outputs_only_normalized_compared_values() -> None:
    checks = [
        {
            "code": "asset",
            "kind": "asset_match",
            "inputs": {
                "previous_policy": "registration_number",
                "vehicle_record": "registration_number",
            },
        },
        {
            "code": "ncb",
            "kind": "ncb_match",
            "inputs": {
                "application": "claimed_ncb_percent",
                "previous_policy": "ncb_percent",
            },
        },
        {
            "code": "renewal",
            "kind": "policy_lapse",
            "inputs": {
                "application": "policy_start_date",
                "previous_policy": "policy_expiry_date",
            },
        },
    ]
    items = [
        evidence("registration_number", "mh 12-ab-1234"),
        evidence("ncb_percent", "20.0%"),
        evidence("policy_expiry_date", " 2026-01-01 "),
        {
            **evidence("registration_number", "MH12AB1234"),
            "document_code": "vehicle_record",
            "document_id": "doc-2",
        },
    ]

    result = reconcile(
        checks,
        {
            "claimed_ncb_percent": " 20% ",
            "policy_start_date": " 2026-01-31 ",
        },
        items,
        "v3",
    )

    comparisons = {
        item["check_code"]: item["comparisons"][0]
        for item in result["results"]
    }
    assert comparisons["asset"]["left"] == "mh12ab1234"
    assert comparisons["asset"]["right"] == "mh12ab1234"
    assert comparisons["asset"]["explanation_code"] == (
        "asset_identifiers_match"
    )
    assert comparisons["ncb"]["left"] == 20
    assert comparisons["ncb"]["right"] == 20
    assert comparisons["renewal"]["left"] == "2026-01-31"
    assert comparisons["renewal"]["right"] == "2026-01-01"
    serialized = json.dumps(result, sort_keys=True)
    for raw in ("mh 12-ab-1234", "MH12AB1234", "20.0%", " 20% "):
        assert raw not in serialized


# Verify every unusable configured claim count becomes missing evidence.
@pytest.mark.parametrize("claim_count", ["invalid", -1, 0.5])
def test_ncb_rejects_unusable_claim_counts(claim_count: object) -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": 25, "prior_claims": claim_count},
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify a missing configured claim count names the missing application field.
def test_ncb_requires_the_configured_claim_count() -> None:
    result = run([NCB_CHECK], {"claimed_ncb_percent": 25})

    assert result["results"][0]["missing_inputs"] == [
        "application.prior_claims"
    ]


# Verify an unconfigured previous-policy tier cannot drive progression.
def test_ncb_rejects_an_unconfigured_prior_tier() -> None:
    result = reconcile(
        [NCB_CHECK],
        {"claimed_ncb_percent": 25, "prior_claims": 0},
        [evidence("ncb_percent", 30)],
        "v2",
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify an unusable legacy NCB evidence value becomes missing evidence.
def test_legacy_ncb_rejects_unusable_policy_value() -> None:
    check = {
        "code": "legacy_ncb",
        "kind": "ncb_match",
        "inputs": {
            "application": "claimed_ncb_percent",
            "previous_policy": "ncb_percent",
        },
    }
    result = reconcile(
        [check],
        {"claimed_ncb_percent": 20},
        [evidence("ncb_percent", "invalid")],
        "v1",
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify either unusable asset identifier makes the check missing evidence.
@pytest.mark.parametrize(
    ("left", "right"),
    [({}, "SYNTH-RC-1"), ("SYNTH-RC-1", {})],
)
def test_asset_match_rejects_unusable_identifiers(
    left: object, right: object
) -> None:
    check = {
        "code": "asset",
        "kind": "asset_match",
        "inputs": {
            "previous_policy": "registration_number",
            "vehicle_record": "registration_number",
        },
    }
    vehicle = {
        **evidence("registration_number", right),
        "document_code": "vehicle_record",
    }
    result = reconcile(
        [check],
        {},
        [evidence("registration_number", left), vehicle],
        "v1",
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify a document-only NCB check fails closed instead of guessing semantics.
def test_document_only_ncb_check_is_missing_evidence() -> None:
    check = {
        "code": "document_ncb",
        "kind": "ncb_match",
        "inputs": {
            "previous_policy": "ncb_percent",
            "vehicle_record": "ncb_percent",
        },
    }
    vehicle = {
        **evidence("ncb_percent", 20),
        "document_code": "vehicle_record",
    }

    result = reconcile(
        [check],
        {},
        [evidence("ncb_percent", 20), vehicle],
        "v1",
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"
