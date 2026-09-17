"""Frozen JSON shapes for login, refresh, and access administration.

The web client reads these payloads directly, so every key set and error code
is pinned here. Each test removes the users and roles it creates, because the
demo-account migration asserts the exact set of seeded identities.
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from fixtures.records import remove_role_by_code, remove_user
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login

from underwriteflow.app import create_app

CREDENTIAL_KEYS = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "refresh_expires_in",
}

ME_KEYS = {"id", "email", "display_name", "role", "permissions"}
ROLE_SUMMARY_KEYS = {"id", "code"}
USER_KEYS = {
    "id",
    "email",
    "display_name",
    "is_active",
    "role",
    "created_at",
}
ROLE_KEYS = {
    "id",
    "code",
    "title",
    "description",
    "is_active",
    "is_system",
    "permissions",
}
PERMISSION_KEYS = {"code", "title", "description"}


# Post one login request and return the raw response.
def post_login(client: TestClient, account: tuple[str, str]):
    return client.post(
        "/api/v1/auth/login",
        json={"email": account[0], "password": account[1]},
    )


# Verify login returns exactly the contracted credential payload.
def test_login_returns_the_credential_contract() -> None:
    with TestClient(create_app()) as client:
        response = post_login(client, UNDERWRITER)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == CREDENTIAL_KEYS
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["expires_in"] > 0
    assert body["refresh_expires_in"] > body["expires_in"]


# Verify unknown and wrong passwords fail with one sanitized error code.
def test_login_rejects_bad_credentials() -> None:
    with TestClient(create_app()) as client:
        unknown = post_login(
            client, ("nobody@synthetic.test", "synthetic-password")
        )
        wrong = post_login(client, (UNDERWRITER[0], "wrong-password"))

    for response in (unknown, wrong):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"


# Verify the session route still serves the legacy token the client reads.
def test_session_route_stays_a_compatible_alias() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/session",
            json={"email": APPLICANT[0], "password": APPLICANT[1]},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"token", "token_type", "expires_in"}
    assert body["token"] and body["expires_in"] > 0


# Verify refresh rotates the credential and keeps the contracted shape.
def test_refresh_rotates_the_credential() -> None:
    with TestClient(create_app()) as client:
        issued = post_login(client, UNDERWRITER).json()
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": issued["refresh_token"]},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == CREDENTIAL_KEYS
    assert body["refresh_token"] != issued["refresh_token"]
    assert body["access_token"] != issued["access_token"]


# Verify an unknown refresh credential is refused with its own code.
def test_refresh_rejects_unknown_credential() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": f"synthetic-unknown-{uuid4()}"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh"
    assert response.json()["error"]["request_id"]


# Verify replaying a rotated credential is detected and refused.
def test_refresh_replay_is_detected() -> None:
    with TestClient(create_app()) as client:
        issued = post_login(client, UNDERWRITER).json()
        first = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": issued["refresh_token"]},
        )
        replay = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": issued["refresh_token"]},
        )

    assert first.status_code == 200, first.text
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "refresh_reuse_detected"


# Verify the current-user payload is the contracted nested identity.
def test_me_returns_the_contracted_identity() -> None:
    with TestClient(create_app()) as client:
        headers = login(client, UNDERWRITER)
        response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == ME_KEYS
    assert set(body["role"]) == ROLE_SUMMARY_KEYS
    assert body["role"]["code"] == "underwriter"
    assert body["email"] == UNDERWRITER[0]
    assert isinstance(body["permissions"], list)
    assert body["permissions"] == sorted(body["permissions"])


# Verify the permission catalogue is the fixed seeded scope list.
def test_permissions_returns_the_fixed_catalogue() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/admin/permissions",
            headers=login(client, ADMINISTRATOR),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body
    for entry in body:
        assert set(entry) == PERMISSION_KEYS
    codes = {entry["code"] for entry in body}
    assert {"cases:read", "users:manage", "schemas:edit"} <= codes


# Verify roles expose metadata plus sorted scopes to administrators only.
def test_roles_returns_roles_with_sorted_scopes() -> None:
    with TestClient(create_app()) as client:
        allowed = client.get(
            "/api/v1/admin/roles", headers=login(client, ADMINISTRATOR)
        )
        denied = client.get(
            "/api/v1/admin/roles", headers=login(client, UNDERWRITER)
        )

    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert {role["code"] for role in body} >= {
        "applicant",
        "underwriter",
        "administrator",
    }
    for role in body:
        assert set(role) == ROLE_KEYS
        assert role["permissions"] == sorted(role["permissions"])
    assert denied.status_code == 403


# Verify the user list is administrable and hides password material.
def test_users_returns_sanitized_records() -> None:
    with TestClient(create_app()) as client:
        headers = login(client, ADMINISTRATOR)
        allowed = client.get("/api/v1/admin/users", headers=headers)
        denied = client.get(
            "/api/v1/admin/users", headers=login(client, APPLICANT)
        )

    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert body
    for record in body:
        assert set(record) == USER_KEYS
    assert denied.status_code == 403


# Verify creating a user returns 201 without any password material.
def test_create_user_hides_password_material() -> None:
    email = f"reviewer-{uuid4()}@example.test"
    created: dict = {}
    with TestClient(create_app()) as client:
        headers = login(client, ADMINISTRATOR)
        roles = {
            role["code"]: role["id"]
            for role in client.get(
                "/api/v1/admin/roles", headers=headers
            ).json()
        }
        response = client.post(
            "/api/v1/admin/users",
            json={
                "email": email,
                "display_name": "Synthetic Reviewer",
                "password": "synthetic-initial-password",
                "role_id": roles["underwriter"],
            },
            headers=headers,
        )
        created = response.json() if response.status_code < 300 else {}
        if created:
            remove_user(UUID(created["id"]))

    assert response.status_code == 201, response.text
    assert set(created) == USER_KEYS
    assert created["role"]["code"] == "underwriter"
    assert "password" not in response.text


# Verify unknown permission codes are refused when a role is created.
def test_create_role_rejects_unknown_permission_codes() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/admin/roles",
            json={
                "code": f"synthetic_invalid_{uuid4().hex[:8]}",
                "title": "Synthetic Invalid",
                "permissions": ["cases:read", "synthetic:unknown"],
            },
            headers=login(client, ADMINISTRATOR),
        )

    assert response.status_code == 422


# Verify a created role is returned with its sorted scopes.
def test_create_role_returns_the_contracted_shape() -> None:
    code = f"synthetic_claims_{uuid4().hex[:8]}"
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/admin/roles",
            json={
                "code": code,
                "title": "Synthetic Claims Reviewer",
                "description": "Synthetic demonstration role",
                "permissions": ["reviews:read", "cases:read"],
            },
            headers=login(client, ADMINISTRATOR),
        )
        body = response.json() if response.status_code < 300 else {}
        remove_role_by_code(code)

    assert response.status_code == 201, response.text
    assert set(body) == ROLE_KEYS
    assert body["permissions"] == ["cases:read", "reviews:read"]
    assert body["is_system"] is False


# Verify the last active administrator cannot be deactivated.
def test_last_administrator_cannot_be_deactivated() -> None:
    with TestClient(create_app()) as client:
        headers = login(client, ADMINISTRATOR)
        users = client.get("/api/v1/admin/users", headers=headers).json()
        administrator = next(
            user
            for user in users
            if user["role"]["code"] == "administrator"
        )
        response = client.patch(
            f"/api/v1/admin/users/{administrator['id']}",
            json={"is_active": False},
            headers=headers,
        )

    assert response.status_code == 409


# Verify every administration route refuses an anonymous caller.
def test_admin_routes_require_authentication() -> None:
    with TestClient(create_app()) as client:
        responses = [
            client.get("/api/v1/admin/users"),
            client.get("/api/v1/admin/roles"),
            client.get("/api/v1/admin/permissions"),
            client.post("/api/v1/admin/users", json={}),
            client.patch(f"/api/v1/admin/users/{uuid4()}", json={}),
        ]

    for response in responses:
        assert response.status_code == 401
