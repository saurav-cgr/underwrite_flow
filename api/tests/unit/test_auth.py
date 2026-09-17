"""Refresh-credential, rotation, scope, and ownership unit tests.

Strict access-token contract tests live beside this module in
`test_auth_tokens.py`. Behaviour that needs the live database, such as
disabled users and stale authorization claims, is covered by
`tests/integration/test_dynamic_authorization.py`.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from fixtures.auth import build_service, refresh_record

from underwriteflow.auth.dependencies import (
    Permission,
    authorize_case_access,
    require_permission,
)
from underwriteflow.auth.schemas import UserRole
from underwriteflow.auth.seed import seed_demo_users
from underwriteflow.auth.service import (
    RefreshOutcome,
    authorization_version,
    plan_refresh_rotation,
    replacement_chain,
)
from underwriteflow.persistence.models import User


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


# Verify Argon2 credentials accept the right password and refuse others.
def test_password_hashing_round_trip() -> None:
    service = build_service()
    password_hash = service.hash_password("synthetic-password")

    assert service.verify_password(password_hash, "synthetic-password")
    assert not service.verify_password(password_hash, "wrong-password")


# Verify applicant access is restricted to the applicant's own case.
def test_case_access_uses_role_and_ownership() -> None:
    owner = uuid4()
    other = uuid4()
    applicant = {"sub": str(owner), "role": "Applicant"}
    underwriter = {"sub": str(uuid4()), "role": "Underwriter"}

    assert authorize_case_access(applicant, owner)
    assert not authorize_case_access(applicant, other)
    assert authorize_case_access(underwriter, other)


# Verify permission checks read the scopes resolved for the current session.
def test_require_permission_uses_resolved_scopes() -> None:
    applicant = {
        "sub": str(uuid4()),
        "role": "Applicant",
        "permissions": ["cases:read", "cases:write"],
    }
    underwriter = {
        "sub": str(uuid4()),
        "role": "Underwriter",
        "permissions": ["cases:override", "cases:read", "reviews:write"],
    }

    assert require_permission(Permission.CASE_READ)(applicant) == applicant
    assert require_permission(Permission.REVIEW_WRITE)(underwriter) == (
        underwriter
    )
    with pytest.raises(HTTPException) as denied:
        require_permission(Permission.CASES_OVERRIDE)(applicant)
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as refused:
        require_permission(Permission.PRODUCT_CONFIG_WRITE)(underwriter)
    assert refused.value.status_code == 403


# Verify refresh credentials are random and stored only as a keyed digest.
def test_refresh_credentials_are_random_and_keyed() -> None:
    service = build_service()
    first = service.issue_refresh_credential()
    second = service.issue_refresh_credential()

    assert first != second
    assert len(first) >= 32
    assert service.refresh_digest(first) == service.refresh_digest(first)
    assert service.refresh_digest(first) != first
    assert service.refresh_digest(first) != service.refresh_digest(second)


# Verify the refresh digest is keyed by the configured pepper.
def test_refresh_digest_depends_on_the_pepper() -> None:
    credential = build_service().issue_refresh_credential()

    assert build_service(pepper="pepper-one").refresh_digest(
        credential
    ) != build_service(pepper="pepper-two").refresh_digest(credential)


# Verify the authorization version tracks the role and its sorted scopes.
def test_authorization_version_tracks_role_and_scopes() -> None:
    base = authorization_version("underwriter", ["cases:read"])

    assert base == authorization_version("underwriter", ["cases:read"])
    assert base != authorization_version("applicant", ["cases:read"])
    assert base != authorization_version(
        "underwriter", ["cases:read", "cases:override"]
    )


# Verify a live credential rotates against its own session row.
def test_refresh_rotation_rotates_a_live_session() -> None:
    record = refresh_record()

    plan = plan_refresh_rotation(record, datetime.now(timezone.utc))

    assert plan.outcome is RefreshOutcome.ROTATE
    assert plan.session_id == record.id
    assert plan.user_id == record.user_id


# Verify an expired credential is refused instead of rotated.
def test_refresh_rotation_reports_expiry() -> None:
    plan = plan_refresh_rotation(
        refresh_record(expires_in=timedelta(minutes=-1)),
        datetime.now(timezone.utc),
    )

    assert plan.outcome is RefreshOutcome.EXPIRED


# Verify an unknown credential is never treated as a valid session.
def test_refresh_rotation_reports_unknown_credential() -> None:
    plan = plan_refresh_rotation(None, datetime.now(timezone.utc))

    assert plan.outcome is RefreshOutcome.UNKNOWN
    assert plan.session_id is None


# Verify replaying a revoked credential is detected as replay.
def test_refresh_rotation_detects_replay() -> None:
    revoked = refresh_record(revoked_at=datetime.now(timezone.utc))

    plan = plan_refresh_rotation(revoked, datetime.now(timezone.utc))

    assert plan.outcome is RefreshOutcome.REPLAY
    assert plan.session_id == revoked.id


# Verify a replay targets every later session in the replacement chain.
def test_replacement_chain_lists_every_successor() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()
    successors = {first: second, second: third, third: None}

    assert replacement_chain(first, successors) == (second, third)
    assert replacement_chain(third, successors) == ()


# Verify a replay never walks a replacement chain that loops back on itself.
def test_replacement_chain_stops_on_a_cycle() -> None:
    first, second = uuid4(), uuid4()

    assert replacement_chain(first, {first: second, second: first}) == (
        second,
    )


# Verify the seed helper creates exactly the three supported roles.
@pytest.mark.asyncio
async def test_seed_creates_three_demo_roles() -> None:
    session = SeedSession()
    auth = build_service()
    passwords = {
        UserRole.APPLICANT: "synthetic-applicant-password",
        UserRole.UNDERWRITER: "synthetic-underwriter-password",
        UserRole.ADMINISTRATOR: "synthetic-administrator-password",
    }

    seeded = await seed_demo_users(session, passwords, auth)

    assert len(seeded) == 3
    assert {user.role for user in seeded} == {role.value for role in UserRole}
    assert all(
        auth.verify_password(user.password_hash, passwords[UserRole(user.role)])
        for user in seeded
    )
