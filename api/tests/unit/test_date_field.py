"""Date field validation tests."""

from datetime import date, timedelta

import pytest

from underwriteflow.cases.validation import (
    CaseValidationError,
    validate_field_value,
)
from underwriteflow.products.schemas import ProductField


# Build a required date field that rejects future values.
def date_field() -> ProductField:
    return ProductField(
        key="date_of_birth",
        label="Date of birth",
        type="date",
        required=True,
        help_text="Enter a fictional date of birth.",
        validation={"not_future": True},
    )


# Given a future or malformed date, when validated, then reject its value.
@pytest.mark.parametrize(
    "value",
    [(date.today() + timedelta(days=1)).isoformat(), "not-a-date"],
)
def test_date_field_rejects_future_or_non_iso_values(value: object) -> None:
    with pytest.raises(
        CaseValidationError, match="invalid field value: date_of_birth"
    ):
        validate_field_value(date_field(), value)


# Given today's ISO date, when validated, then accept the value.
def test_date_field_accepts_today() -> None:
    validate_field_value(date_field(), date.today().isoformat())
