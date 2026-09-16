"""Frozen JSON shapes for case intake, configuration, and submission.

These tests fail whenever a served key is renamed, removed, or added, which is
what the typed web client and the applicant screens depend on.
"""

from fastapi.testclient import TestClient

from fixtures.records import motor_status, remove_case, set_motor_status
from fixtures.support import (
    APPLICANT,
    DOCUMENT_CODES,
    RECOMMENDATION_KEYS,
    create_motor_case,
    login,
    submit_motor_case,
    upload_motor_documents,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

CASE_KEYS = {
    "id",
    "product_code",
    "product_version",
    "rulebook_version",
    "status",
}

CONFIGURATION_KEYS = {
    "case_id",
    "product_code",
    "product_version",
    "rulebook_version",
    "fields",
    "documents",
}

FIELD_KEYS = {
    "key",
    "label",
    "type",
    "required",
    "help_text",
    "validation",
    "options",
    "visible_when",
}

REQUIREMENT_KEYS = {
    "code",
    "title",
    "requirement",
    "required",
    "accepted_types",
    "condition",
}

DOCUMENT_KEYS = {
    "id",
    "document_code",
    "filename",
    "content_type",
    "byte_size",
    "content_hash",
    "page_count",
}

SUBMIT_KEYS = {"id", "status", "recommendation"}


# Pin the case identity keys served by create, read, and list.
def test_case_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])

            assert set(created) == CASE_KEYS, created
            assert created["product_code"] == "motor-private-car"
            assert created["status"] == "new"

            fetched = client.get(f"/api/v1/cases/{case_id}", headers=applicant)
            assert fetched.status_code == 200, fetched.text
            assert set(fetched.json()) == CASE_KEYS, fetched.json()

            listed = client.get("/api/v1/cases", headers=applicant)
            assert listed.status_code == 200, listed.text
            for item in listed.json():
                assert set(item) == CASE_KEYS, item
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the pinned-configuration shape the applicant documents screen reads.
def test_case_configuration_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])

            response = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert set(body) == CONFIGURATION_KEYS, body

            assert body["fields"], "the motor product publishes fields"
            for field in body["fields"]:
                assert set(field) == FIELD_KEYS, field

            assert body["documents"], "the motor product publishes documents"
            for requirement in body["documents"]:
                assert set(requirement) == REQUIREMENT_KEYS, requirement
                assert isinstance(requirement["required"], bool)
                assert isinstance(requirement["accepted_types"], list)

            codes = {item["code"] for item in body["documents"]}
            assert set(DOCUMENT_CODES) <= codes, codes
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the uploaded-document metadata keys the documents screen renders.
def test_document_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])

            uploads = upload_motor_documents(client, applicant, case_id)
            assert len(uploads) == len(DOCUMENT_CODES)
            for uploaded in uploads:
                assert set(uploaded) == DOCUMENT_KEYS, uploaded
            assert {item["document_code"] for item in uploads} == set(
                DOCUMENT_CODES
            )

            listed = client.get(
                f"/api/v1/cases/{case_id}/documents", headers=applicant
            )
            assert listed.status_code == 200, listed.text
            for item in listed.json():
                assert set(item) == DOCUMENT_KEYS, item
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)


# Pin the submission result and its pending recommendation keys.
def test_submit_response_keys_are_stable() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            upload_motor_documents(client, applicant, case_id)

            submitted = submit_motor_case(client, applicant, case_id)
            assert set(submitted) == SUBMIT_KEYS, submitted
            assert submitted["status"] == "underwriter_review"

            recommendation = submitted["recommendation"]
            assert set(recommendation) == RECOMMENDATION_KEYS, recommendation
            assert recommendation["route"] == "expedited"
            assert recommendation["factors"] == [
                "complete_consistent_submission"
            ]
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)
