from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from underwriteflow.app import create_app
from underwriteflow.auth.dependencies import (
    Permission,
    authorize_case_access,
    require_permission,
)
from underwriteflow.auth.router import get_session
from underwriteflow.auth.schemas import UserRole
from underwriteflow.auth.seed import seed_demo_users
from underwriteflow.auth.service import AuthService
from underwriteflow.config import Settings
from underwriteflow.database import get_session as database_session
from underwriteflow.persistence.models import User


class FakeSession:
    """Return one synthetic user for login tests."""

    # Keep the fake session tied to one persisted user.
    def __init__(self, user: User) -> None:
        self.user = user

    # Return the configured synthetic user for a select statement.
    async def scalar(self, statement: object) -> User | None:
        del statement
        return self.user if self.user.is_active else None


class SeedSession:
    """Collect synthetic users for seed-helper tests."""

    def __init__(self) -> None:
        self.users: list[User] = []

    # Report that each synthetic seed identity is absent.
    async def scalar(self, statement: object) -> None:
        del statement
        return None

    # Collect one synthetic user in the fake transaction.
    def add(self, user: User) -> None:
        self.users.append(user)

    # Complete the fake transaction without persistence.
    async def commit(self) -> None:
        return None


# Verify Argon2 credentials and signed sessions round-trip.
def test_password_and_session_round_trip() -> None:
    service = AuthService("synthetic-test-secret")
    password_hash = service.hash_password("synthetic-password")

    assert service.verify_password(password_hash, "synthetic-password")
    assert service.read_session(service.issue_session(uuid4(), "Underwriter"))["role"] == "Underwriter"


# Verify incorrect passwords never authenticate a synthetic user.
def test_wrong_password_is_rejected() -> None:
    service = AuthService("synthetic-test-secret")

    assert not service.verify_password(service.hash_password("right"), "wrong")


# Verify tampered sessions are rejected.
def test_tampered_session_is_rejected() -> None:
    service = AuthService("synthetic-test-secret")

    with pytest.raises(ValueError):
        service.read_session("invalid.token")


# Verify applicant access is restricted to the applicant's own case.
def test_case_access_uses_role_and_ownership() -> None:
    owner = uuid4()
    other = uuid4()
    applicant = {"sub": str(owner), "role": "Applicant"}
    underwriter = {"sub": str(uuid4()), "role": "Underwriter"}

    assert authorize_case_access(applicant, owner)
    assert not authorize_case_access(applicant, other)
    assert authorize_case_access(underwriter, other)


# Verify review, audit, and product configuration permissions are role-bound.
def test_role_permission_matrix() -> None:
    applicant = {"sub": str(uuid4()), "role": "Applicant"}
    underwriter = {"sub": str(uuid4()), "role": "Underwriter"}
    administrator = {"sub": str(uuid4()), "role": "Administrator"}

    with pytest.raises(HTTPException):
        require_permission(Permission.REVIEW_WRITE)(applicant)
    assert require_permission(Permission.REVIEW_WRITE)(underwriter) == underwriter
    assert require_permission(Permission.AUDIT_READ)(administrator) == administrator
    with pytest.raises(HTTPException) as denied:
        require_permission(Permission.PRODUCT_CONFIG_WRITE)(underwriter)
    assert denied.value.status_code == 403


# Verify login uses a persisted user and the configured session secret.
def test_login_issues_session_for_persisted_user() -> None:
    password_hash = AuthService("synthetic-test-secret").hash_password("synthetic-password")
    user = User(
        id=uuid4(),
        email="applicant@synthetic.test",
        display_name="Synthetic Applicant",
        role="Applicant",
        password_hash=password_hash,
        is_active=True,
    )
    app = create_app(Settings(session_secret="synthetic-test-secret"))

    # Supply an isolated in-memory session boundary to the auth router.
    async def override_session():
        yield FakeSession(user)

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/session",
        json={"email": user.email, "password": "synthetic-password"},
    )

    assert response.status_code == 200
    assert (
        AuthService("synthetic-test-secret")
        .read_session(response.json()["token"])["sub"]
        == str(user.id)
    )


# Verify the seed helper creates exactly the three supported roles.
@pytest.mark.asyncio
async def test_seed_creates_three_demo_roles() -> None:
    session = SeedSession()
    auth = AuthService("synthetic-test-secret")
    passwords = {
        UserRole.APPLICANT: "synthetic-applicant-password",
        UserRole.UNDERWRITER: "synthetic-underwriter-password",
        UserRole.ADMINISTRATOR: "synthetic-administrator-password",
    }

    seeded = await seed_demo_users(session, passwords, auth)

    assert len(seeded) == 3
    assert {user.role for user in seeded} == {role.value for role in UserRole}
    assert all(auth.verify_password(user.password_hash, passwords[UserRole(user.role)]) for user in seeded)


# Verify deactivation blocks a previously issued session immediately.
def test_deactivated_user_session_is_rejected() -> None:
    user = User(
        id=uuid4(),
        email="underwriter@synthetic.test",
        display_name="Synthetic Underwriter",
        role="Underwriter",
        password_hash="unused-in-session-test",
        is_active=False,
    )
    auth = AuthService("synthetic-test-secret")
    app = create_app(Settings(session_secret="synthetic-test-secret"))

    # Supply the current deactivated database record to session validation.
    async def override_session():
        yield FakeSession(user)

    app.dependency_overrides[database_session] = override_session
    client = TestClient(app)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth.issue_session(user.id, user.role)}"},
    )

    assert response.status_code == 401


# Verify a session reflects the user's current persisted role.
def test_session_uses_current_user_role() -> None:
    user = User(
        id=uuid4(),
        email="applicant@synthetic.test",
        display_name="Synthetic Applicant",
        role="Applicant",
        password_hash="unused-in-session-test",
        is_active=True,
    )
    auth = AuthService("synthetic-test-secret")
    app = create_app(Settings(session_secret="synthetic-test-secret"))

    # Supply the current role-mutated database record to session validation.
    async def override_session():
        yield FakeSession(user)

    app.dependency_overrides[database_session] = override_session
    client = TestClient(app)
    token = auth.issue_session(user.id, "Underwriter")

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"sub": str(user.id), "role": "Applicant"}
