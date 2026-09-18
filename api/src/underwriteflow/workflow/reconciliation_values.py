"""Value normalization and comparison helpers for reconciliation."""

import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

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


# Describe the evidence references one resolved source contributed.
def source_evidence(source: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "document_id": str(item.get("document_id")),
            "source_locator": str(item.get("source_locator")),
        }
        for item in source.get("items", [])
    ]


# Convert one normalized value to a stable JSON-safe representation.
def output_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return format(value.normalize(), "f")
    if isinstance(value, date):
        return value.isoformat()
    return value


# Build one value comparison for two resolved sources.
def value_comparison(
    left: dict[str, Any],
    right: dict[str, Any],
    normalize: Callable[[Any], Any],
    match_code: str,
    mismatch_code: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    left_value = output_value(normalize(left["value"]))
    right_value = output_value(normalize(right["value"]))
    matched = left_value == right_value
    comparison = {
        "field_key": right["field_name"],
        "left": left_value,
        "right": right_value,
        "matched": matched,
        "evidence": source_evidence(right),
        "explanation_code": match_code if matched else mismatch_code,
    }
    if matched:
        return comparison, None
    return comparison, {
        "code": mismatch_code,
        "field_key": right["field_name"],
        "expected": left_value,
        "actual": right_value,
    }
