"""Extract retrieval filter facts from a submitted case payload."""

from datetime import date, datetime
from typing import Any


# Read scalar values from either direct or normalized field payloads.
def _value(payload: dict[str, Any], key: str) -> Any:
    value = payload.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


# Convert supported submission date shapes to a calendar date.
def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


# Return age and sum-assured facts without inventing absent values.
def case_facts(
    payload: dict[str, Any], submitted_on: date | datetime | str
) -> dict[str, int | float | None]:
    submitted = _as_date(submitted_on)
    birth_text = _value(payload, "date_of_birth")
    age = None
    if birth_text:
        birth_date = _as_date(birth_text)
        age = submitted.year - birth_date.year
        if (submitted.month, submitted.day) < (
            birth_date.month,
            birth_date.day,
        ):
            age -= 1
    cover = _value(payload, "requested_cover")
    if cover is None:
        cover = _value(payload, "sum_assured")
    return {"age": age, "sum_assured": cover}
