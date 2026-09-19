"""Pure reconciliation checks over synthetic normalized evidence.

Every case here is fictional and exists only to prove the deterministic
comparison rules: no database, provider, file, or routing behaviour is
involved.
"""

import pytest

from underwriteflow.workflow.reconciliation import reconcile


# Build one synthetic evidence item with a trusted document locator.
def evidence(
    field_name: str,
    value: object,
    document_code: str,
    source_locator: str = "page:1",
    document_id: str = "doc-1",
) -> dict[str, object]:
    return {
        "field_name": field_name,
        "value": value,
        "document_id": document_id,
        "document_code": document_code,
        "source_locator": source_locator,
        "confidence": 0.99,
    }


# Build one configured check as the pinned configuration would supply it.
def check(
    code: str,
    kind: str,
    inputs: dict[str, str],
    parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    configured: dict[str, object] = {
        "code": code,
        "kind": kind,
        "inputs": inputs,
    }
    if parameters is not None:
        configured["parameters"] = parameters
    return configured


# Reconcile one synthetic case with the pinned rulebook version.
def run(
    checks: list[dict[str, object]],
    application: dict[str, object],
    items: list[dict[str, object]],
) -> dict[str, object]:
    return reconcile(
        checks=checks,
        application=application,
        evidence=items,
        rule_version="v1",
    )


NCB_CHECK = check(
    "motor_ncb_match",
    "ncb_match",
    {"application": "claimed_ncb_percent", "previous_policy": "ncb_percent"},
)

# Verify a claimed NCB that equals the policy evidence is cleared.
def test_ncb_match_is_cleared_when_values_agree() -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": 20},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    assert result["overall_status"] == "CLEARED"
    outcome = result["results"][0]
    assert outcome["check_code"] == "motor_ncb_match"
    assert outcome["status"] == "CLEARED"
    assert outcome["comparisons"][0]["matched"] is True
    assert outcome["comparisons"][0]["explanation_code"] == "ncb_matches"
    assert outcome["rule_version"] == "v1"


# Verify a claimed NCB that disagrees with the policy is flagged.
def test_ncb_match_is_flagged_when_values_differ() -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": 35},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    outcome = result["results"][0]
    assert result["overall_status"] == "FLAGGED_DISCREPANCY"
    assert outcome["status"] == "FLAGGED_DISCREPANCY"
    assert outcome["discrepancies"] == [
        {
            "code": "ncb_mismatch",
            "field_key": "ncb_percent",
            "expected": 35,
            "actual": 20,
        }
    ]


# Verify a percentage sign in the claim does not create a false mismatch.
def test_ncb_match_normalizes_percentage_text() -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": "20%"},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    assert result["overall_status"] == "CLEARED"


# Verify a claim without any policy evidence is missing, never flagged.
def test_ncb_match_without_policy_evidence_is_missing() -> None:
    result = run([NCB_CHECK], {"claimed_ncb_percent": 20}, [])

    outcome = result["results"][0]
    assert outcome["status"] == "MISSING_EVIDENCE"
    assert outcome["comparisons"] == []
    assert outcome["discrepancies"] == []


# Verify a claim the applicant never answered is missing evidence.
def test_ncb_match_without_claim_is_missing() -> None:
    result = run(
        [NCB_CHECK],
        {},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


ASSET_CHECK = check(
    "motor_asset_match",
    "asset_match",
    {
        "previous_policy": "registration_number",
        "vehicle_record": "registration_number",
    },
)


# Verify identifiers that differ only in formatting are treated as a match.
def test_asset_match_normalizes_identifiers() -> None:
    result = run(
        [ASSET_CHECK],
        {},
        [
            evidence(
                "registration_number", "mh 12-ab-1234", "previous_policy"
            ),
            evidence(
                "registration_number",
                "MH12AB1234",
                "vehicle_record",
                document_id="doc-2",
            ),
        ],
    )

    assert result["overall_status"] == "CLEARED"
    assert result["results"][0]["comparisons"][0]["matched"] is True


# Verify genuinely different identifiers are flagged.
def test_asset_match_flags_different_identifiers() -> None:
    result = run(
        [ASSET_CHECK],
        {},
        [
            evidence("registration_number", "MH12AB1234", "previous_policy"),
            evidence(
                "registration_number",
                "MH12AB9999",
                "vehicle_record",
                document_id="doc-2",
            ),
        ],
    )

    assert result["results"][0]["status"] == "FLAGGED_DISCREPANCY"
    assert result["results"][0]["discrepancies"][0]["code"] == (
        "asset_mismatch"
    )


# Verify one identifier missing from a document marks the check missing.
def test_asset_match_without_one_identifier_is_missing() -> None:
    result = run(
        [ASSET_CHECK],
        {},
        [evidence("registration_number", "MH12AB1234", "previous_policy")],
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


LAPSE_CHECK = check(
    "motor_renewal_lapse",
    "policy_lapse",
    {
        "application": "policy_start_date",
        "previous_policy": "policy_expiry_date",
    },
)


# Verify a renewal inside the allowed window is cleared, leap day included.
def test_policy_lapse_counts_real_calendar_days() -> None:
    result = run(
        [LAPSE_CHECK],
        {"policy_start_date": "2024-03-01"},
        [evidence("policy_expiry_date", "2024-02-28", "previous_policy")],
    )

    comparison = result["results"][0]["comparisons"][0]
    assert comparison["left"] == "2024-03-01"
    assert comparison["right"] == "2024-02-28"
    assert comparison["explanation_code"] == "policy_gap_within_window"
    assert result["overall_status"] == "CLEARED"


# Verify a gap beyond the configured window is flagged with its day count.
def test_policy_lapse_beyond_window_is_flagged() -> None:
    result = run(
        [LAPSE_CHECK],
        {"policy_start_date": "2026-06-01"},
        [evidence("policy_expiry_date", "2024-02-28", "previous_policy")],
    )

    outcome = result["results"][0]
    assert outcome["status"] == "FLAGGED_DISCREPANCY"
    assert outcome["discrepancies"][0]["code"] == "policy_lapse_gap"
    assert outcome["discrepancies"][0]["actual"] == 824


# Verify a lapse check reads whichever document source it configures.
def test_policy_lapse_uses_the_configured_document_source() -> None:
    configured = check(
        "motor_renewal_lapse",
        "policy_lapse",
        {
            "application": "policy_start_date",
            "vehicle_record": "policy_expiry",
        },
    )

    result = run(
        [configured],
        {"policy_start_date": "2026-01-15"},
        [evidence("policy_expiry", "2026-01-05", "vehicle_record")],
    )

    assert result["results"][0]["status"] == "CLEARED"


# Verify an unparseable date is missing evidence, never a guessed lapse.
def test_policy_lapse_with_invalid_date_is_missing() -> None:
    result = run(
        [LAPSE_CHECK],
        {"policy_start_date": "not a date"},
        [evidence("policy_expiry_date", "2024-02-28", "previous_policy")],
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify a date carried by a document source is also validated.
def test_policy_lapse_with_document_date_text_is_missing() -> None:
    result = run(
        [LAPSE_CHECK],
        {"policy_start_date": "2024-03-01"},
        [evidence("policy_expiry_date", "31-02-2024", "previous_policy")],
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify the most cautious status wins across several checks.
def test_overall_status_prefers_missing_then_flagged() -> None:
    result = run(
        [ASSET_CHECK, NCB_CHECK],
        {"claimed_ncb_percent": 35},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    assert result["overall_status"] == "MISSING_EVIDENCE"


# Verify checks, comparisons, and evidence come back in a stable order.
def test_results_are_deterministically_ordered() -> None:
    result = run(
        [ASSET_CHECK, NCB_CHECK],
        {"claimed_ncb_percent": 20},
        [
            evidence(
                "registration_number",
                "MH12AB1234",
                "vehicle_record",
                document_id="doc-b",
                source_locator="page:2",
            ),
            evidence("ncb_percent", 20, "previous_policy", document_id="doc-a"),
            evidence(
                "registration_number",
                "MH12AB1234",
                "previous_policy",
                document_id="doc-a",
                source_locator="page:3",
            ),
        ],
    )

    assert [item["check_code"] for item in result["results"]] == [
        "motor_asset_match",
        "motor_ncb_match",
    ]
    asset = result["results"][0]
    assert [item["field_key"] for item in asset["comparisons"]] == [
        "registration_number"
    ]
    assert asset["evidence"] == [
        {"document_id": "doc-a", "source_locator": "page:3"},
        {"document_id": "doc-b", "source_locator": "page:2"},
    ]


# Verify an unanswered optional claim does not decide the overall status.
def test_unanswered_claim_does_not_decide_overall_status() -> None:
    result = run(
        [NCB_CHECK, LAPSE_CHECK],
        {"claimed_ncb_percent": 20},
        [
            evidence("ncb_percent", 20, "previous_policy"),
            evidence(
                "policy_expiry_date", "2024-02-28", "previous_policy"
            ),
        ],
    )

    lapse = next(
        item
        for item in result["results"]
        if item["check_code"] == "motor_renewal_lapse"
    )
    assert lapse["status"] == "MISSING_EVIDENCE"
    assert lapse["missing_inputs"] == ["application"]
    assert result["overall_status"] == "CLEARED"


# Verify absent document evidence still decides the overall status.
def test_absent_document_evidence_decides_overall_status() -> None:
    result = run([NCB_CHECK], {"claimed_ncb_percent": 20}, [])

    assert result["results"][0]["missing_inputs"] == ["previous_policy"]
    assert result["overall_status"] == "MISSING_EVIDENCE"


# Verify identical inputs always produce identical serialized output.
def test_reconciliation_is_repeatable() -> None:
    items = [evidence("ncb_percent", 20, "previous_policy")]
    first = run([NCB_CHECK], {"claimed_ncb_percent": 20}, items)
    second = run([NCB_CHECK], {"claimed_ncb_percent": 20}, list(items))

    assert first == second


# Verify a value a check cannot compare is treated as missing evidence.
def test_unusable_value_type_is_missing_evidence() -> None:
    result = run(
        [NCB_CHECK],
        {"claimed_ncb_percent": {"unexpected": "object"}},
        [evidence("ncb_percent", 20, "previous_policy")],
    )

    assert result["results"][0]["status"] == "MISSING_EVIDENCE"


# Verify an unknown check kind is refused as invalid configuration.
def test_unknown_check_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        run(
            [check("motor_unknown", "arbitrary_python", {"application": "a"})],
            {},
            [],
        )
