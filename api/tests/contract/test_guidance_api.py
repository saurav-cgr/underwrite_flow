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


# Verify underwriters can ask and list case questions with a stable shape.
def test_question_post_and_history_shape() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            underwriter = login(client, UNDERWRITER)
            path = f"/api/v1/reviews/{case_id}/questions"
            created = client.post(
                path,
                json={"question": "Is this covered?"},
                headers=underwriter,
            )
            listed = client.get(path, headers=underwriter)

            assert created.status_code == 201, created.text
            body = created.json()
            assert set(body) == {
                "id",
                "question",
                "answer",
                "covered",
                "citations",
                "asked_by",
                "created_at",
            }
            assert body["question"] == "Is this covered?"
            assert body["answer"] == "not covered by guidelines"
            assert body["covered"] is False
            assert body["citations"] == []
            assert listed.status_code == 200, listed.text
            assert listed.json() == [body]
    finally:
        remove_case(case_id)


# Verify question text outside 1 to 1,000 characters is rejected.
def test_question_length_bounds() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            underwriter = login(client, UNDERWRITER)
            path = f"/api/v1/reviews/{case_id}/questions"
            for question in ("", "q" * 1001):
                response = client.post(
                    path, json={"question": question}, headers=underwriter
                )
                assert response.status_code == 422
            longest = client.post(
                path, json={"question": "q" * 1000}, headers=underwriter
            )
            assert longest.status_code == 201, longest.text
    finally:
        remove_case(case_id)


# Verify applicants and administrators cannot ask or list questions.
def test_questions_reject_applicant_and_administrator() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            path = f"/api/v1/reviews/{case_id}/questions"
            for role in (APPLICANT, ADMINISTRATOR):
                headers = login(client, role)
                posted = client.post(
                    path, json={"question": "Covered?"}, headers=headers
                )
                listed = client.get(path, headers=headers)
                assert posted.status_code == 403
                assert listed.status_code == 403
    finally:
        remove_case(case_id)


# Verify unknown cases return 404 for both question endpoints.
def test_questions_unknown_case_returns_404() -> None:
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        underwriter = login(client, UNDERWRITER)
        path = f"/api/v1/reviews/{uuid4()}/questions"
        posted = client.post(
            path, json={"question": "Covered?"}, headers=underwriter
        )
        listed = client.get(path, headers=underwriter)
        assert posted.status_code == 404
        assert listed.status_code == 404


# Verify unusable provider settings still store the fallback, not a 500.
def test_question_unusable_providers_return_fallback() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        for settings in (
            Settings(generation_provider="gemini", embedding_provider="fake"),
            Settings(generation_provider="ollama"),
        ):
            with TestClient(create_app(settings)) as client:
                response = client.post(
                    f"/api/v1/reviews/{case_id}/questions",
                    json={"question": "Is this covered?"},
                    headers=login(client, UNDERWRITER),
                )
                assert response.status_code == 201, response.text
                assert response.json()["answer"] == (
                    "not covered by guidelines"
                )
                assert response.json()["covered"] is False
    finally:
        remove_case(case_id)
