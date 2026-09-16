"""Authenticated access to synthetic review document content."""

from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.records import (
    motor_status,
    remove_case,
    remove_upload,
    set_motor_status,
)
from fixtures.support import (
    APPLICANT,
    UNDERWRITER,
    create_motor_case,
    login,
    submit_motor_case,
    upload_motor_documents,
)
from underwriteflow.app import create_app
from underwriteflow.config import Settings

ADMINISTRATOR = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)


# Verify only an underwriter can read content for a document in its case.
def test_review_document_content_is_role_and_case_scoped() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_ids: list[str] = []
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            administrator = login(client, ADMINISTRATOR)
            first = create_motor_case(client, applicant)
            second = create_motor_case(client, applicant)
            first_id = str(first["id"])
            second_id = str(second["id"])
            case_ids.extend([first_id, second_id])
            first_documents = upload_motor_documents(
                client, applicant, first_id
            )
            second_documents = upload_motor_documents(
                client, applicant, second_id
            )
            submit_motor_case(client, applicant, first_id)
            document_id = str(first_documents[0]["id"])
            other_document_id = str(second_documents[0]["id"])
            path = f"/api/v1/reviews/{first_id}/documents/{document_id}"

            allowed = client.get(path, headers=underwriter)
            anonymous = client.get(path)
            applicant_denied = client.get(path, headers=applicant)
            administrator_denied = client.get(path, headers=administrator)
            cross_case = client.get(
                f"/api/v1/reviews/{first_id}/documents/"
                f"{other_document_id}",
                headers=underwriter,
            )
            missing = client.get(
                f"/api/v1/reviews/{first_id}/documents/{uuid4()}",
                headers=underwriter,
            )

        assert allowed.status_code == 200
        assert allowed.headers["content-type"] == "application/pdf"
        assert allowed.headers["cache-control"] == "no-store"
        assert allowed.headers["x-content-type-options"] == "nosniff"
        assert allowed.headers["content-disposition"].startswith("inline")
        assert allowed.content.startswith(b"%PDF-")
        assert anonymous.status_code == 401
        assert applicant_denied.status_code == 403
        assert administrator_denied.status_code == 403
        assert cross_case.status_code == 404
        assert missing.status_code == 404
    finally:
        for case_id in case_ids:
            remove_case(case_id)
        set_motor_status(prior)


# Verify a missing stored file returns a sanitized not-found response.
def test_review_document_missing_file_is_not_found() -> None:
    prior = motor_status()
    set_motor_status("active")
    case_id = ""
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            created = create_motor_case(client, applicant)
            case_id = str(created["id"])
            documents = upload_motor_documents(client, applicant, case_id)
            document_id = str(documents[0]["id"])
            remove_upload(case_id, "identity_record")

            response = client.get(
                f"/api/v1/reviews/{case_id}/documents/{document_id}",
                headers=underwriter,
            )

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Resource not found"
        assert "uploads" not in response.text
    finally:
        if case_id:
            remove_case(case_id)
        set_motor_status(prior)
