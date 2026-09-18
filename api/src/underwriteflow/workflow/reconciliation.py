"""Pure reconciliation checks over normalized synthetic evidence.

Reconciliation reads serializable inputs and returns typed results only. It
performs no database access, provider call, file access, logging, audit write,
or routing, so identical inputs always produce identical output.
"""

from decimal import Decimal
from typing import Any

from underwriteflow.workflow.reconciliation_values import (
    normalized_identifier,
    normalized_number,
    output_value,
    parsed_date,
    source_evidence,
    value_comparison,
)

STATUS_CLEARED = "CLEARED"
STATUS_FLAGGED = "FLAGGED_DISCREPANCY"
STATUS_MISSING = "MISSING_EVIDENCE"

# Most cautious first: the overall state the case evidence ends in.
STATUS_PRECEDENCE = (STATUS_MISSING, STATUS_FLAGGED, STATUS_CLEARED)

CHECK_KINDS = frozenset({"ncb_match", "asset_match", "policy_lapse"})

# Source key for a value the applicant claimed rather than evidence supplied.
APPLICATION_SOURCE = "application"

# Fictional demonstration window: a renewal within this many calendar days of
# the previous expiry counts as continuous cover. It is a demonstration
# constant, never genuine Indian underwriting guidance.
MAX_LAPSE_DAYS = 30

# Report whether one supplied value can be compared at all.
def is_present(value: Any) -> bool:
    return value is not None and value != ""


# Resolve every configured input to the value one source supplied.
def resolve_inputs(
    check: dict[str, Any],
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    resolved: dict[str, dict[str, Any]] = {}
    missing_inputs: list[str] = []
    for source, field_name in sorted(check.get("inputs", {}).items()):
        if source == APPLICATION_SOURCE:
            value = application.get(field_name)
            resolved[source] = {
                "field_name": field_name,
                "value": value,
                "items": [],
            }
            if not is_present(value):
                missing_inputs.append(source)
            continue
        matches = sorted(
            (
                item
                for item in evidence
                if item.get("document_code") == source
                and item.get("field_name") == field_name
            ),
            key=lambda item: (
                str(item.get("document_id")),
                str(item.get("source_locator")),
            ),
        )
        value = matches[0].get("value") if matches else None
        resolved[source] = {
            "field_name": field_name,
            "value": value,
            "items": matches,
        }
        if not matches or not is_present(value):
            missing_inputs.append(source)
    return resolved, missing_inputs


# List every evidence reference once, ordered by document then locator.
def unique_evidence(
    resolved: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    references = {
        (str(item.get("document_id")), str(item.get("source_locator")))
        for entry in resolved.values()
        for item in entry.get("items", [])
    }
    return [
        {"document_id": document_id, "source_locator": locator}
        for document_id, locator in sorted(references)
    ]


# Compare the claimed no-claim bonus with the previous policy evidence.
def ncb_comparisons(
    resolved: dict[str, dict[str, Any]],
    application: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claimed = resolved[APPLICATION_SOURCE]
    if normalized_number(claimed["value"]) is None:
        return [], []
    if parameters:
        claims = normalized_number(
            application.get(str(parameters["claim_count_field"]))
        )
        prior = next(
            item
            for source, item in resolved.items()
            if source != APPLICATION_SOURCE
        )
        prior_value = normalized_number(prior["value"])
        if claims is None or claims < 0 or claims != claims.to_integral():
            return [], []
        tiers = [Decimal(str(tier)) for tier in parameters["tiers"]]
        if prior_value not in tiers:
            return [], []
        threshold = Decimal(str(parameters["claims_reset_threshold"]))
        expected = (
            Decimal(str(parameters["claims_reset_tier"]))
            if claims >= threshold
            else tiers[min(tiers.index(prior_value) + 1, len(tiers) - 1)]
        )
        matched = normalized_number(claimed["value"]) == expected
        expected_value = output_value(expected)
        claimed_value = output_value(normalized_number(claimed["value"]))
        comparison = {
            "field_key": claimed["field_name"],
            "left": expected_value,
            "right": claimed_value,
            "matched": matched,
            "evidence": source_evidence(prior),
            "explanation_code": (
                "ncb_progression_matches"
                if matched
                else "ncb_progression_mismatch"
            ),
        }
        discrepancy = None if matched else {
            "code": "ncb_progression_mismatch",
            "field_key": claimed["field_name"],
            "expected": expected_value,
            "actual": claimed_value,
        }
        return [comparison], [discrepancy] if discrepancy else []
    comparisons: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    for source, item in resolved.items():
        if source == APPLICATION_SOURCE:
            continue
        if normalized_number(item["value"]) is None:
            return [], []
        comparison, discrepancy = value_comparison(
            claimed,
            item,
            normalized_number,
            "ncb_matches",
            "ncb_mismatch",
        )
        comparisons.append(comparison)
        if discrepancy is not None:
            discrepancies.append(discrepancy)
    return comparisons, discrepancies


# Compare identifiers across the resolved document sources.
def identifier_comparisons(
    kind: str,
    resolved: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reference = resolved.get(APPLICATION_SOURCE) or next(
        iter(resolved.values())
    )
    if normalized_identifier(reference["value"]) is None:
        return [], []
    comparisons: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []
    # `asset_match` and friends collapse to a short stable code prefix.
    prefix = kind.removesuffix("_match")
    for source, item in resolved.items():
        if item is reference:
            continue
        if normalized_identifier(item["value"]) is None:
            return [], []
        comparison, discrepancy = value_comparison(
            reference,
            item,
            normalized_identifier,
            f"{prefix}_identifiers_match",
            f"{prefix}_mismatch",
        )
        comparisons.append(comparison)
        if discrepancy is not None:
            discrepancies.append(discrepancy)
    return comparisons, discrepancies


# Measure the whole-day gap between a previous expiry and a renewal start.
def lapse_comparison(
    claimed: dict[str, Any],
    expiry: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    start = parsed_date(claimed["value"])
    previous = parsed_date(expiry["value"])
    if start is None or previous is None:
        return [], []
    gap_days = (start - previous).days
    maximum = int((parameters or {}).get("maximum_gap_days", MAX_LAPSE_DAYS))
    boundary = (parameters or {}).get("boundary", "inclusive")
    within_maximum = gap_days <= maximum
    if boundary == "exclusive":
        within_maximum = gap_days < maximum
    matched = 0 <= gap_days and within_maximum
    comparison = {
        "field_key": expiry["field_name"],
        "left": output_value(start),
        "right": output_value(previous),
        "matched": matched,
        "evidence": source_evidence(expiry),
        "explanation_code": (
            "policy_gap_within_window" if matched else "policy_lapse_gap"
        ),
    }
    if matched:
        return [comparison], []
    return [comparison], [
        {
            "code": "policy_lapse_gap",
            "field_key": expiry["field_name"],
            "expected": maximum,
            "actual": gap_days,
        }
    ]


# Run one configured check over the resolved sources.
def run_check(
    check: dict[str, Any],
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
    rule_version: str,
) -> dict[str, Any]:
    kind = str(check.get("kind"))
    if kind not in CHECK_KINDS:
        raise ValueError(f"unsupported reconciliation kind: {kind}")
    code = str(check.get("code"))
    resolved, missing_inputs = resolve_inputs(check, application, evidence)
    parameters = check.get("parameters") or {}
    if kind == "ncb_match" and parameters:
        claim_field = str(parameters.get("claim_count_field"))
        if not is_present(application.get(claim_field)):
            missing_inputs.append(f"application.{claim_field}")
    if missing_inputs:
        return {
            "check_code": code,
            "kind": kind,
            "status": STATUS_MISSING,
            "comparisons": [],
            "discrepancies": [],
            "evidence": [],
            "missing_inputs": missing_inputs,
            "rule_version": rule_version,
        }
    # A lapse check reads the configured document source, whatever it is
    # named, rather than assuming one fixed document code.
    document_sources = [
        source for source in resolved if source != APPLICATION_SOURCE
    ]
    if kind == "policy_lapse" and document_sources:
        comparisons, discrepancies = lapse_comparison(
            resolved[APPLICATION_SOURCE],
            resolved[document_sources[0]],
            parameters,
        )
    elif kind == "ncb_match" and APPLICATION_SOURCE in resolved:
        comparisons, discrepancies = ncb_comparisons(
            resolved, application, parameters
        )
    elif kind == "asset_match":
        comparisons, discrepancies = identifier_comparisons(kind, resolved)
    else:
        comparisons, discrepancies = [], []
    if not comparisons:
        status = STATUS_MISSING
        # Report the unusable inputs so a caller can tell an unanswered claim
        # from a claim the configured documents cannot verify.
        missing_inputs = sorted(resolved)
    elif discrepancies:
        status = STATUS_FLAGGED
    else:
        status = STATUS_CLEARED
    return {
        "check_code": code,
        "kind": kind,
        "status": status,
        "comparisons": sorted(
            comparisons, key=lambda item: item["field_key"]
        ),
        "discrepancies": sorted(
            discrepancies, key=lambda item: item["code"]
        ),
        "evidence": unique_evidence(resolved),
        "missing_inputs": [],
        "rule_version": rule_version,
    }


# Report whether one check applies: an unanswered optional claim does not.
#
# A claim the applicant never made needs no verification, so it neither
# decides the overall status nor queues the case for missing evidence.
def check_applies(result: dict[str, Any]) -> bool:
    missing_inputs = result.get("missing_inputs") or []
    return set(missing_inputs) != {APPLICATION_SOURCE}


# Reconcile every configured check and report the overall evidence state.
def reconcile(
    checks: list[dict[str, Any]],
    application: dict[str, Any],
    evidence: list[dict[str, Any]],
    rule_version: str,
) -> dict[str, Any]:
    results = [
        run_check(check, application, evidence, rule_version)
        for check in sorted(checks, key=lambda item: str(item.get("code")))
    ]
    statuses = {
        result["status"] for result in results if check_applies(result)
    }
    overall = next(
        (
            status
            for status in STATUS_PRECEDENCE
            if status in statuses
        ),
        STATUS_CLEARED,
    )
    return {"results": results, "overall_status": overall}
