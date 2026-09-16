"""Frozen JSON shapes for the human review start and decision contracts.

The underwriter screen reads nested evidence, summary, and failure objects, so
each nested key set is pinned here as well as the top-level response.
"""

from fastapi.testclient import TestClient

from fixtures.records import (
    clear_recommendation_summary,
    motor_status,
    remove_case,
    remove_upload,
    set_motor_status,
)
from fixtures.support import (
    APPLICANT,
    RECOMMENDATION_KEYS,
    UNDERWRITER,
    conflicting_motor_uploads,
    create_motor_case,
    login,
    start_review,
    submit_motor_case,
    upload_documents,
    upload_motor_documents,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

REVIEW_START_KEYS = {
    "case_id",
    "status",
    "recommendation",
    "summary",
    "evidence",
    "conflicts",
    "missing_information",
    "extraction_failures",
    "specialist_options",
}

SUMMARY_KEYS = {
    "evidence",
    "conflicts",
    "missing_information",
    "risk_signals",
    "open_questions",
}

DOCUMENT_EVIDENCE_KEYS = {
    "document_id",
    "filename",
    "source_locator",
    "source_type",
}

FIELD_EVIDENCE_KEYS = {
    "document_id",
    "field_name",
    "value",
    "source_locator",
    "source_type",
}

CONFLICT_KEYS = {
    "field_name",
    "value",
    "document_id",
    "source_locator",
    "conflict_status",
}

FAILURE_KEYS = {"rule_code", "details"}

FAILURE_DETAIL_KEYS = {"document_id", "filename", "error_code"}

REVIEW_KEYS = {"case_id", "action", "selected_route", "status"}


# Pin the review view served for a complete, consistent case.
def test_review_start_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)

            body = start_review(client, underwriter, case_id)
            assert set(body) == REVIEW_START_KEYS, body
            assert body["status"] == "awaiting_human_review"

            recommendation = body["recommendation"]
            assert set(recommendation) == RECOMMENDATION_KEYS, recommendation
            assert set(body["summary"]) == SUMMARY_KEYS, body["summary"]

            assert body["evidence"], "a submitted case carries evidence"
            kinds = {item["source_type"] for item in body["evidence"]}
            assert kinds == {
                "submitted_document",
                "extracted_field",
            }, kinds
            for item in body["evidence"]:
                if item["source_type"] == "submitted_document":
                    assert set(item) == DOCUMENT_EVIDENCE_KEYS, item
                else:
                    assert set(item) == FIELD_EVIDENCE_KEYS, item

            assert body["conflicts"] == []
            assert body["missing_information"] == []
            assert body["extraction_failures"] == []
            options = body["specialist_options"]
            assert options and all(isinstance(o, str) for o in options)
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the failure signal served when one document branch cannot extract.
def test_failed_branch_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            remove_upload(case_id, "identity_record")

            submitted = submit_motor_case(client, applicant, case_id)
            recommendation = submitted["recommendation"]
            assert recommendation["route"] == "specialist"
            assert recommendation["factors"] == ["processing_failure"]

            body = start_review(client, underwriter, case_id)
            failures = body["extraction_failures"]
            assert len(failures) == 1, failures
            for failure in failures:
                assert set(failure) == FAILURE_KEYS, failure
                assert set(failure["details"]) == FAILURE_DETAIL_KEYS, failure
                assert failure["rule_code"].startswith("document:")
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the recommendation keys served when the persisted summary is empty.
def test_review_start_keeps_factors_when_summary_is_missing() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)

            # A recommendation row can outlive the summary that produced it.
            clear_recommendation_summary(case_id)

            body = start_review(client, underwriter, case_id)
            recommendation = body["recommendation"]
            assert set(recommendation) == RECOMMENDATION_KEYS, recommendation
            assert recommendation["route"] == "expedited"
            assert recommendation["factors"] == []
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the conflict keys served when two documents disagree.
def test_conflict_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_documents(
                client, applicant, case_id, conflicting_motor_uploads()
            )

            submitted = submit_motor_case(client, applicant, case_id)
            assert submitted["recommendation"]["route"] == "specialist"

            body = start_review(client, underwriter, case_id)
            conflicts = body["conflicts"]
            assert conflicts, "a disagreeing pair is recorded"
            for conflict in conflicts:
                assert set(conflict) == CONFLICT_KEYS, conflict
                assert conflict["conflict_status"] != "clear"
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the human decision result keys.
def test_review_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)
            submit_motor_case(client, applicant, case_id)
            start_review(client, underwriter, case_id)

            decided = client.post(
                f"/api/v1/reviews/{case_id}",
                json={"action": "confirm", "evidence_acknowledged": True},
                headers=underwriter,
            )
            assert decided.status_code == 200, decided.text
            body = decided.json()
            assert set(body) == REVIEW_KEYS, body
            assert body["action"] == "confirm"
            assert body["status"] == "confirmed"
            assert body["selected_route"] == "expedited"
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)
