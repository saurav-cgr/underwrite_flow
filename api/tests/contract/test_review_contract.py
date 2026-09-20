"""Frozen JSON shapes for the human review start and decision contracts.

The underwriter screen reads nested evidence, summary, and failure objects, so
each nested key set is pinned here as well as the top-level response.
"""

import json
from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.records import (
    clear_recommendation_summary,
    motor_status,
    remove_case,
    remove_upload,
    set_motor_status,
)
from fixtures.support import (
    ADMINISTRATOR,
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
from fixtures.synthetic_pdf import (
    IDENTITY_ONLY_LINES,
    MOTOR_EVIDENCE_LINES,
    REGISTRATION_CERTIFICATE_LINES,
    text_pdf,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

REVIEW_START_KEYS = {
    "case_id",
    "journey",
    "status",
    "recommendation",
    "summary",
    "submitted_facts",
    "evidence",
    "conflicts",
    "missing_information",
    "reconciliation",
    "extraction_failures",
    "specialist_options",
}

RECONCILIATION_KEYS = {
    "check_code",
    "kind",
    "status",
    "comparisons",
    "discrepancies",
    "evidence",
    "missing_inputs",
    "rule_version",
}

COMPARISON_KEYS = {
    "field_key",
    "left",
    "right",
    "matched",
    "evidence",
    "explanation_code",
    "confidence_source",
}


SUMMARY_KEYS = {
    "evidence",
    "conflicts",
    "missing_information",
    "reconciliation_results",
    "reconciliation_status",
    "risk_signals",
    "open_questions",
}

DOCUMENT_EVIDENCE_KEYS = {
    "document_id",
    "document_code",
    "document_title",
    "filename",
    "content_type",
    "page_count",
    "source_type",
}

FIELD_EVIDENCE_KEYS = {
    "document_id",
    "field_name",
    "field_label",
    "field_type",
    "value",
    "source_locator",
    "extraction_method",
    "confidence",
    "conflict_status",
    "source_type",
}

SUBMITTED_FACT_KEYS = {
    "field_name",
    "field_label",
    "field_type",
    "value",
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


# Pin the v5 new-business review view with prior claims fully excluded.
def test_v5_new_business_review_excludes_prior_claims() -> None:
    prior = motor_status()
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            activated = client.post(
                "/api/v1/products/motor-private-car/activate",
                json={"version": "v5"},
                headers=login(client, ADMINISTRATOR),
            )
            assert activated.status_code == 200, activated.text
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = client.post(
                "/api/v1/cases",
                json={
                    "product_code": "motor-private-car",
                    "idempotency_key": str(uuid4()),
                    "journey": "new_business",
                    "payload": {"vehicle_age": 4, "vehicle_use": "personal"},
                    "document_codes": [],
                },
                headers=applicant,
            )
            assert created.status_code == 200, created.text
            case_id = str(created.json()["id"])
            upload_documents(
                client,
                applicant,
                case_id,
                [
                    ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
                    ("vehicle_record", text_pdf(MOTOR_EVIDENCE_LINES)),
                    (
                        "registration_certificate",
                        text_pdf(REGISTRATION_CERTIFICATE_LINES),
                    ),
                ],
            )
            submit_motor_case(client, applicant, case_id)

            body = start_review(client, underwriter, case_id)

            assert set(body) == REVIEW_START_KEYS, body
            assert body["journey"] == "new_business"
            assert {
                fact["field_name"] for fact in body["submitted_facts"]
            } == {"vehicle_age", "vehicle_use"}
            codes = {check["check_code"] for check in body["reconciliation"]}
            assert codes == {
                "motor_chassis_match",
                "motor_engine_match",
                "motor_registration_match",
            }
            assert body["missing_information"] == []
            assert body["specialist_options"] == ["motor inspection"]
            assert "prior_claims" not in json.dumps(body)
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


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
            assert body["submitted_facts"] == [
                {
                    "field_name": "vehicle_age",
                    "field_label": "Vehicle age",
                    "field_type": "integer",
                    "value": 2,
                },
                {
                    "field_name": "vehicle_use",
                    "field_label": "Vehicle use",
                    "field_type": "enum",
                    "value": "personal",
                },
                {
                    "field_name": "prior_claims",
                    "field_label": "Prior claims",
                    "field_type": "integer",
                    "value": 0,
                },
            ]
            assert all(
                set(fact) == SUBMITTED_FACT_KEYS
                for fact in body["submitted_facts"]
            )

            # Configured checks are served in code order with provenance.
            checks = body["reconciliation"]
            assert [check["check_code"] for check in checks] == [
                "motor_ncb_match",
                "motor_renewal_lapse",
            ]
            for check in checks:
                assert set(check) == RECONCILIATION_KEYS, check
                assert check["status"] in {
                    "CLEARED",
                    "FLAGGED_DISCREPANCY",
                    "MISSING_EVIDENCE",
                }
                for comparison in check["comparisons"]:
                    assert set(comparison) == COMPARISON_KEYS, comparison
                    assert comparison["confidence_source"] == (
                        "deterministic"
                    )
                    for reference in comparison["evidence"]:
                        assert reference["source_locator"].startswith(
                            "page:"
                        )

            assert body["evidence"], "a submitted case carries evidence"
            kinds = {item["source_type"] for item in body["evidence"]}
            assert kinds == {
                "submitted_document",
                "extracted_field",
            }, kinds
            for item in body["evidence"]:
                if item["source_type"] == "submitted_document":
                    assert set(item) == DOCUMENT_EVIDENCE_KEYS, item
                    assert item["document_title"].startswith("Synthetic ")
                    assert str(case_id) not in item.values()
                else:
                    assert set(item) == FIELD_EVIDENCE_KEYS, item
                    assert item["field_label"]
                    # Evidence fields a configured check reads have no
                    # declared application type, so they report as unknown.
                    assert item["field_type"] in {
                        "integer",
                        "enum",
                        "date",
                        "unknown",
                    }
                    assert item["extraction_method"] == "fake"
                    assert item["conflict_status"] == "clear"

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
