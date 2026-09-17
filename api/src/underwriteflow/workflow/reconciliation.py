"""Pure reconciliation checks over normalized synthetic evidence.

Reconciliation reads serializable inputs and returns typed results only. It
performs no database access, provider call, file access, logging, audit write,
or routing, so identical inputs always produce identical output.
"""

import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

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

# Characters ignored when identifier values are compared.
IDENTIFIER_SEPARATORS = frozenset({" ", "-", "_", ".", ",", "/"})


# Normalize one identifier for comparison, or report it as unusable.
def normalized_identifier(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    folded = unicodedata.normalize("NFKC", str(value)).casefold()
    cleaned = "".join(
        character
        for character in folded
        if character not in IDENTIFIER_SEPARATORS
    )
    return cleaned or None


# Normalize one numeric value, accepting a trailing percentage sign.
def normalized_number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if not isinstance(value, str):
        return None
    try:
        return Decimal(value.strip().removesuffix("%").strip())
    except (InvalidOperation, ValueError):
        return None


# Parse one ISO calendar date, rejecting any other format.
def parsed_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


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


# Describe the evidence references one resolved source contributed.
def source_evidence(source: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "document_id": str(item.get("document_id")),
            "source_locator": str(item.get("source_locator")),
        }
        for item in source.get("items", [])
    ]


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


# Build one value comparison for two resolved sources.
def value_comparison(
    left: dict[str, Any],
    right: dict[str, Any],
    normalize,
    match_code: str,
    mismatch_code: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    matched = normalize(left["value"]) == normalize(right["value"])
    comparison = {
        "field_key": right["field_name"],
        "left": left["value"],
        "right": right["value"],
        "matched": matched,
        "evidence": source_evidence(right),
        "explanation_code": match_code if matched else mismatch_code,
    }
    if matched:
        return comparison, None
    return comparison, {
        "code": mismatch_code,
        "field_key": right["field_name"],
        "expected": left["value"],
        "actual": right["value"],
    }


# Compare the claimed no-claim bonus with the previous policy evidence.
def ncb_comparisons(
    resolved: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claimed = resolved[APPLICATION_SOURCE]
    if normalized_number(claimed["value"]) is None:
        return [], []
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    start = parsed_date(claimed["value"])
    previous = parsed_date(expiry["value"])
    if start is None or previous is None:
        return [], []
    gap_days = (start - previous).days
    matched = 0 <= gap_days <= MAX_LAPSE_DAYS
    comparison = {
        "field_key": expiry["field_name"],
        "left": claimed["value"],
        "right": expiry["value"],
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
            "expected": MAX_LAPSE_DAYS,
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
            resolved[APPLICATION_SOURCE], resolved[document_sources[0]]
        )
    elif kind == "ncb_match" and APPLICATION_SOURCE in resolved:
        comparisons, discrepancies = ncb_comparisons(resolved)
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
    statuses = {result["status"] for result in results}
    overall = next(
        (
            status
            for status in STATUS_PRECEDENCE
            if status in statuses
        ),
        STATUS_CLEARED,
    )
    return {"results": results, "overall_status": overall}
