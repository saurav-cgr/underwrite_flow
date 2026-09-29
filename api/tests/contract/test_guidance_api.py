"""Underwriter-only stored guidance API contract tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.records import remove_case, seed_case
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings


# Verify a submitted case exposes stable guidance shape to underwriters.
def test_underwriter_guidance_shape_and_route_stability() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            applicant = login(client, APPLICANT)
            underwriter = login(client, UNDERWRITER)
            submitted = client.post(
                f"/api/v1/cases/{case_id}/submit", headers=applicant
            )
            assert submitted.status_code == 200, submitted.text
            before = client.post(
                f"/api/v1/reviews/{case_id}/start",
                headers=underwriter,
            )
            assert before.status_code == 200, before.text
            response = client.get(
                f"/api/v1/reviews/{case_id}/guidance",
                headers=underwriter,
            )
            after = client.post(
                f"/api/v1/reviews/{case_id}/start",
                headers=underwriter,
            )

            assert response.status_code == 200, response.text
            assert after.status_code == 200, after.text
            body = response.json()
            assert body["route_explanation"]["label"] == (
                "SYNTHETIC - FOR DEMONSTRATION ONLY"
            )
            assert body["route_explanation"]["status"] in {
                "template",
                "unavailable",
            }
            assert before.json()["recommendation"]["route"] == (
                after.json()["recommendation"]["route"]
            )
    finally:
        remove_case(case_id)


# Verify applicants and administrators cannot read underwriter guidance.
def test_guidance_rejects_applicant_and_administrator() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            path = f"/api/v1/reviews/{case_id}/guidance"
            applicant = client.get(path, headers=login(client, APPLICANT))
            administrator = client.get(
                path, headers=login(client, ADMINISTRATOR)
            )
            assert applicant.status_code == 403
            assert administrator.status_code == 403
    finally:
        remove_case(case_id)
