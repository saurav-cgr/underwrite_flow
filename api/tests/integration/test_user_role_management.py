"""Live administrator journeys over users, roles, and their audit trail.

Each test drives the public API against the migrated database and then removes
every user it created, because the demo-account migration asserts the exact
set of seeded identities.
"""

import json
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.records import (
    DATABASE_URL,
    remove_role_by_code,
    remove_user_with_audit,
)
from fixtures.support import ADMINISTRATOR, login

from underwriteflow.app import create_app

USERS = "/api/v1/admin/users"
ROLES = "/api/v1/admin/roles"


# Read one admin payload's role identifier by its stable code.
def role_id_for(client: TestClient, headers: dict, code: str) -> str:
    roles = client.get(ROLES, headers=headers).json()
    return next(role["id"] for role in roles if role["code"] == code)


# Read the audit events one actor authored, newest last.
def events_for_actor(actor_id: str) -> list[tuple[str, dict]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT event_type, details FROM audit_events "
                "WHERE actor_user_id = %s ORDER BY occurred_at, id",
                (actor_id,),
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]


# Read the administration events that targeted one user.
def events_for_target(actor_id: str, target_id: str) -> list[tuple[str, dict]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT event_type, details FROM audit_events "
                "WHERE actor_user_id = %s "
                "AND details->>'target_user_id' = %s "
                "ORDER BY occurred_at, id",
                (actor_id, target_id),
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]


# Read the most recent denials recorded for unauthenticated callers.
def unattributed_denials() -> list[tuple[str, dict]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT event_type, details FROM audit_events "
                "WHERE actor_user_id IS NULL AND event_type = %s "
                "ORDER BY occurred_at DESC LIMIT 5",
                ("login_denied",),
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]


# Verify a created user can sign in and sees the assigned role and scopes.
def test_created_user_signs_in_with_the_assigned_role() -> None:
    email = f"reviewer-{uuid4().hex[:8]}@example.test"
    created_id = ""
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            response = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Synthetic Reviewer",
                    "password": "synthetic-initial-password",
                    "role_id": role_id_for(client, headers, "underwriter"),
                },
                headers=headers,
            )
            assert response.status_code == 201, response.text
            created_id = response.json()["id"]
            signed_in = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            assert signed_in.status_code == 200, signed_in.text
            me = client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": (
                        f"Bearer {signed_in.json()['access_token']}"
                    )
                },
            )

        assert me.status_code == 200, me.text
        assert me.json()["role"]["code"] == "underwriter"
        assert me.json()["email"] == email
        assert me.json()["permissions"] == sorted(me.json()["permissions"])
    finally:
        if created_id:
            remove_user_with_audit(UUID(created_id))


# Verify a role change invalidates the old token but a fresh login reflects it.
def test_replacing_a_role_requires_a_new_token() -> None:
    email = f"reviewer-{uuid4().hex[:8]}@example.test"
    created_id = ""
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            created = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Synthetic Reviewer",
                    "password": "synthetic-initial-password",
                    "role_id": role_id_for(client, headers, "applicant"),
                },
                headers=headers,
            )
            created_id = created.json()["id"]
            signed_in = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            stale = {
                "Authorization": f"Bearer {signed_in.json()['access_token']}"
            }
            replaced = client.patch(
                f"{USERS}/{created_id}",
                json={"role_id": role_id_for(client, headers, "underwriter")},
                headers=headers,
            )
            rejected = client.get("/api/v1/auth/me", headers=stale)
            fresh = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            current = client.get(
                "/api/v1/auth/me",
                headers={
                    "Authorization": f"Bearer {fresh.json()['access_token']}"
                },
            )

        assert replaced.status_code == 200, replaced.text
        # The token still carries the previous role snapshot.
        assert rejected.status_code == 401
        assert current.json()["role"]["code"] == "underwriter"
    finally:
        if created_id:
            remove_user_with_audit(UUID(created_id))


# Verify deactivation blocks sign-in and revokes live refresh sessions.
def test_deactivation_blocks_sign_in_and_revokes_refresh() -> None:
    email = f"reviewer-{uuid4().hex[:8]}@example.test"
    created_id = ""
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            created = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Synthetic Reviewer",
                    "password": "synthetic-initial-password",
                    "role_id": role_id_for(client, headers, "applicant"),
                },
                headers=headers,
            )
            created_id = created.json()["id"]
            signed_in = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            refresh_token = signed_in.json()["refresh_token"]
            deactivated = client.patch(
                f"{USERS}/{created_id}",
                json={"is_active": False},
                headers=headers,
            )
            refused = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            rotated = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert deactivated.status_code == 200, deactivated.text
        assert deactivated.json()["is_active"] is False
        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "inactive_user"
        # The live refresh session was revoked with the account.
        assert rotated.status_code == 401
    finally:
        if created_id:
            remove_user_with_audit(UUID(created_id))


# Verify a second administrator can be deactivated while one remains.
def test_a_second_administrator_may_be_deactivated() -> None:
    email = f"admin-two-{uuid4().hex[:8]}@example.test"
    created_id = ""
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            created = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Second Synthetic Administrator",
                    "password": "synthetic-initial-password",
                    "role_id": role_id_for(client, headers, "administrator"),
                },
                headers=headers,
            )
            created_id = created.json()["id"]
            deactivated = client.patch(
                f"{USERS}/{created_id}",
                json={"is_active": False},
                headers=headers,
            )

        assert created.status_code == 201, created.text
        assert deactivated.status_code == 200, deactivated.text
        assert deactivated.json()["is_active"] is False
    finally:
        if created_id:
            remove_user_with_audit(UUID(created_id))


# Verify a custom role's scopes decide what its holder may reach.
def test_custom_role_scopes_decide_route_access() -> None:
    code = f"synthetic_reader_{uuid4().hex[:8]}"
    email = f"reader-{uuid4().hex[:8]}@example.test"
    created_id = ""
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            role = client.post(
                ROLES,
                json={
                    "code": code,
                    "title": "Synthetic Reader",
                    "permissions": ["cases:read"],
                },
                headers=headers,
            )
            assert role.status_code == 201, role.text
            created = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Synthetic Reader",
                    "password": "synthetic-initial-password",
                    "role_id": role.json()["id"],
                },
                headers=headers,
            )
            created_id = created.json()["id"]
            signed_in = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "synthetic-initial-password"},
            )
            actor = {
                "Authorization": f"Bearer {signed_in.json()['access_token']}"
            }
            allowed = client.get("/api/v1/cases", headers=actor)
            # The custom role holds no review scope and is not the underwriter.
            denied = client.post(
                f"/api/v1/reviews/{uuid4()}", json={"action": "confirm"},
                headers=actor,
            )
            queue_denied = client.get("/api/v1/queues", headers=actor)

        assert allowed.status_code == 200, allowed.text
        assert denied.status_code == 403
        assert queue_denied.status_code == 403
    finally:
        remove_role_by_code(code)
        if created_id:
            remove_user_with_audit(UUID(created_id))


# Verify the journey appends sanitized events and never records a credential.
def test_admin_journey_appends_sanitized_audit_events() -> None:
    email = f"reviewer-{uuid4().hex[:8]}@example.test"
    created_id = ""
    credential = "synthetic-initial-password"
    try:
        with TestClient(create_app()) as client:
            headers = login(client, ADMINISTRATOR)
            admin_id = client.get(
                "/api/v1/auth/me", headers=headers
            ).json()["id"]
            created = client.post(
                USERS,
                json={
                    "email": email,
                    "display_name": "Synthetic Reviewer",
                    "password": credential,
                    "role_id": role_id_for(client, headers, "applicant"),
                },
                headers=headers,
            )
            created_id = created.json()["id"]
            signed_in = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": credential},
            )
            refresh_token = signed_in.json()["refresh_token"]
            client.patch(
                f"{USERS}/{created_id}",
                json={"display_name": "Renamed Reviewer"},
                headers=headers,
            )
            client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "wrong-password"},
            )
            events = events_for_actor(created_id)
            targeted = events_for_target(admin_id, created_id)
            denials = unattributed_denials()

        kinds = [event_type for event_type, _ in events]
        assert "login_succeeded" in kinds
        # The administrator authors the administration events, so they are
        # read back by the user they targeted.
        targeted_kinds = [event_type for event_type, _ in targeted]
        assert "user_created" in targeted_kinds
        assert "user_updated" in targeted_kinds
        # A failed password attempt is recorded against no actor, because the
        # caller was never authenticated.
        assert denials
        assert all(
            details.get("reason") == "invalid_credentials"
            for _, details in denials
        )
        serialized = json.dumps([details for _, details in events + targeted])
        # No credential, digest, or password value may reach the audit trail.
        assert refresh_token not in serialized
        assert credential not in serialized
        for _, details in events:
            assert not any(
                key in {"token", "password", "authorization"}
                for key in details
            )
    finally:
        if created_id:
            remove_user_with_audit(UUID(created_id))
