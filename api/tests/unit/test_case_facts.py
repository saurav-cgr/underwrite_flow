from datetime import date

from underwriteflow.knowledge.case_facts import case_facts


# Verify whole-year age uses birthday boundaries and maps requested cover.
def test_case_facts_uses_submission_date() -> None:
    facts = case_facts(
        {
            "date_of_birth": "1980-09-29",
            "requested_cover": 15000000,
        },
        date(2026, 9, 28),
    )

    assert facts == {"age": 45, "sum_assured": 15000000}
    assert case_facts(
        {"date_of_birth": "1980-09-29", "requested_cover": 15000000},
        date(2026, 9, 29),
    )["age"] == 46


# Verify missing case facts stay absent so retrieval skips those filters.
def test_case_facts_returns_none_for_absent_values() -> None:
    assert case_facts({}, date(2026, 9, 28)) == {
        "age": None,
        "sum_assured": None,
    }
