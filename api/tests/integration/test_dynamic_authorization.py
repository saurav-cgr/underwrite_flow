"""Live authorization checks against the migrated database.

Every protected request re-resolves the active user and its current role and
permission scopes. A token whose role or scope snapshot no longer matches the
database must be refused even though its signature is valid.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from fixtures.auth import app_service
from fixtures.records import (
    assign_role,
    role_scopes,
    synthetic_role,
    synthetic_user,
)

from underwriteflow.app import create_app

UNDERWRITER = ("underwriter@synthetic.test", "underwriteflow-demo-underwriter")


# Read one token's current identity and resolved authorization.
def read_me(client: TestClient, token: str):
    return client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )


# Verify login issues a token whose snapshot matches the stored authorization.
def test_login_and_current_user_agree_with_the_database() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": UNDERWRITER[0], "password": UNDERWRITER[1]},
        )
        assert response.status_code == 200, response.text
        me = read_me(client, response.json()["access_token"])

    assert me.status_code == 200, me.text
    body = me.json()
    assert body["email"] == UNDERWRITER[0]
    assert body["role"]["code"] == "underwriter"
    assert body["permissions"] == sorted(role_scopes("underwriter"))
    assert body["id"]


# Verify a token claiming a role the user never held is refused.
def test_stale_role_claim_is_rejected() -> None:
    service = app_service()
    with synthetic_user() as user_id:
        assign_role(user_id, "applicant")
        token = service.issue_access_token(
            user_id, "underwriter", role_scopes("underwriter")
        )
        with TestClient(create_app()) as client:
            response = read_me(client, token)

    assert response.status_code == 401


# Verify a token claiming scopes the role does not grant is refused.
def test_stale_scope_claim_is_rejected() -> None:
    service = app_service()
    with synthetic_user() as user_id:
        assign_role(user_id, "underwriter")
        token = service.issue_access_token(
            user_id,
            "underwriter",
            list(role_scopes("underwriter")) + ["users:manage"],
        )
        with TestClient(create_app()) as client:
            response = read_me(client, token)

    assert response.status_code == 401


# Verify a deactivated user is refused even with an otherwise valid token.
def test_disabled_user_is_rejected() -> None:
    service = app_service()
    with synthetic_user(is_active=False) as user_id:
        assign_role(user_id, "applicant")
        token = service.issue_access_token(
            user_id, "applicant", role_scopes("applicant")
        )
        with TestClient(create_app()) as client:
            response = read_me(client, token)

    assert response.status_code == 401


# Verify an expired access token is refused.
def test_expired_access_token_is_rejected() -> None:
    service = app_service()
    with synthetic_user() as user_id:
        assign_role(user_id, "applicant")
        token = service.issue_access_token(
            user_id,
            "applicant",
            role_scopes("applicant"),
            ttl_seconds=-1,
        )
        with TestClient(create_app()) as client:
            response = read_me(client, token)

    assert response.status_code == 401


# Verify a user with no role mapping is forbidden rather than anonymous.
def test_user_without_a_role_is_forbidden() -> None:
    service = app_service()
    with synthetic_user() as user_id:
        token = service.issue_access_token(
            user_id, "applicant", role_scopes("applicant")
        )
        with TestClient(create_app()) as client:
            response = read_me(client, token)

    assert response.status_code == 403


# Verify an inactive role grants no access at all.
def test_inactive_role_grants_no_access() -> None:
    service = app_service()
    code = f"synthetic_off_{uuid4().hex[:8]}"
    with synthetic_role(code, ["cases:read"], is_active=False):
        with synthetic_user() as user_id:
            assign_role(user_id, code)
            token = service.issue_access_token(user_id, code, ["cases:read"])
            with TestClient(create_app()) as client:
                response = read_me(client, token)

    assert response.status_code == 403


# Verify protected routes honour exactly the configured role scopes.
def test_scope_denial_follows_configured_role_scopes() -> None:
    service = app_service()
    code = f"synthetic_probe_{uuid4().hex[:8]}"
    with synthetic_role(code, ["cases:read"]):
        with synthetic_user() as user_id:
            assign_role(user_id, code)
            token = service.issue_access_token(user_id, code, ["cases:read"])
            headers = {"Authorization": f"Bearer {token}"}
            with TestClient(create_app()) as client:
                me = read_me(client, token)
                allowed = client.get("/api/v1/cases", headers=headers)
                denied = client.post(
                    f"/api/v1/reviews/{uuid4()}",
                    json={"action": "confirm"},
                    headers=headers,
                )

    assert me.status_code == 200, me.text
    assert me.json()["permissions"] == ["cases:read"]
    assert allowed.status_code == 200, allowed.text
    assert denied.status_code == 403


# Verify a missing or malformed credential never reaches authorization.
def test_missing_and_malformed_credentials_are_rejected() -> None:
    with TestClient(create_app()) as client:
        missing = client.get("/api/v1/auth/me")
        malformed = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not-a-token"},
        )
        wrong_scheme = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Basic {uuid4()}"},
        )

    assert missing.status_code == 401
    assert malformed.status_code == 401
    assert wrong_scheme.status_code == 401
