"""Strict access-token contract tests.

An access token must be a three-segment HS256 JWT carrying exactly the
contracted claims, and every deviation must be refused rather than repaired.
"""

from uuid import uuid4

import pytest

from underwriteflow.auth.service import authorization_version

from fixtures.auth import (
    CLAIM_KEYS,
    build_service,
    claim_payload,
    decode_segment,
    sign,
)


# Verify an issued access token carries every strict claim.
def test_access_token_carries_every_strict_claim() -> None:
    service = build_service()
    user_id = uuid4()

    token = service.issue_access_token(
        user_id,
        "underwriter",
        ["reviews:write", "cases:read", "cases:read"],
        ttl_seconds=900,
    )
    claims = service.read_access_token(token)

    assert len(token.split(".")) == 3
    assert decode_segment(token.split(".")[0]) == {"alg": "HS256", "typ": "JWT"}
    assert claims.sub == user_id
    assert claims.role == "underwriter"
    # Scopes are deduplicated and sorted before they are signed.
    assert list(claims.permissions) == ["cases:read", "reviews:write"]
    assert claims.typ == "access"
    assert claims.iss == "underwriteflow"
    assert claims.aud == "underwriteflow-web"
    assert claims.jti
    assert claims.exp > claims.iat
    assert claims.authz_version == authorization_version(
        "underwriter", ["cases:read", "reviews:write"]
    )


# Verify the signed payload exposes exactly the contracted claim names.
def test_access_token_payload_exposes_contracted_claims() -> None:
    service = build_service()

    token = service.issue_access_token(uuid4(), "applicant", ["cases:read"])

    assert set(decode_segment(token.split(".")[1])) == CLAIM_KEYS


# Verify each issued token carries its own unique identifier.
def test_access_tokens_are_individually_identified() -> None:
    service = build_service()
    user_id = uuid4()

    first = service.read_access_token(
        service.issue_access_token(user_id, "applicant", ["cases:read"])
    )
    second = service.read_access_token(
        service.issue_access_token(user_id, "applicant", ["cases:read"])
    )

    assert first.jti != second.jti


# Verify a token whose signature was edited is refused.
def test_access_token_signature_is_verified() -> None:
    service = build_service()
    header, payload, signature = service.issue_access_token(
        uuid4(), "applicant", ["cases:read"]
    ).split(".")
    forged = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(ValueError):
        service.read_access_token(f"{header}.{payload}.{forged}")


# Verify a token signed with a different secret is refused.
def test_access_token_from_another_secret_is_refused() -> None:
    service = build_service()
    foreign = build_service(secret="synthetic-other-secret")

    with pytest.raises(ValueError):
        service.read_access_token(
            foreign.issue_access_token(uuid4(), "applicant", ["cases:read"])
        )


# Verify an unsigned or weaker algorithm is refused outright.
@pytest.mark.parametrize("algorithm", ["none", "HS512", "RS256"])
def test_access_token_rejects_unsupported_algorithm(algorithm: str) -> None:
    forged = sign({"alg": algorithm, "typ": "JWT"}, claim_payload())

    with pytest.raises(ValueError):
        build_service().read_access_token(forged)


# Verify a token minted for another issuer is refused.
def test_access_token_rejects_wrong_issuer() -> None:
    service = build_service()
    other = build_service(issuer="some-other-issuer")

    with pytest.raises(ValueError):
        service.read_access_token(
            other.issue_access_token(uuid4(), "applicant", ["cases:read"])
        )


# Verify a token minted for another audience is refused.
def test_access_token_rejects_wrong_audience() -> None:
    service = build_service()
    other = build_service(audience="some-other-audience")

    with pytest.raises(ValueError):
        service.read_access_token(
            other.issue_access_token(uuid4(), "applicant", ["cases:read"])
        )


# Verify an expired token is refused even though its signature is valid.
def test_access_token_rejects_expired_token() -> None:
    service = build_service()
    expired = service.issue_access_token(
        uuid4(), "applicant", ["cases:read"], ttl_seconds=-1
    )

    with pytest.raises(ValueError):
        service.read_access_token(expired)


# Verify a token that expires exactly now is already refused.
def test_access_token_rejects_expiry_boundary() -> None:
    service = build_service()
    boundary = service.issue_access_token(
        uuid4(), "applicant", ["cases:read"], ttl_seconds=0
    )

    with pytest.raises(ValueError):
        service.read_access_token(boundary)


# Verify a token carrying the wrong type claim is refused.
def test_access_token_rejects_wrong_token_type() -> None:
    forged = sign({"alg": "HS256", "typ": "JWT"}, claim_payload(typ="refresh"))

    with pytest.raises(ValueError):
        build_service().read_access_token(forged)


# Verify structurally malformed tokens are refused.
@pytest.mark.parametrize(
    "token", ["", "not-a-token", "two.segments", "four.segments.here.now"]
)
def test_access_token_rejects_malformed_tokens(token: str) -> None:
    with pytest.raises(ValueError):
        build_service().read_access_token(token)


# Verify a token missing any strict claim is refused.
@pytest.mark.parametrize(
    "missing",
    ["sub", "role", "permissions", "typ", "exp", "iss", "aud", "jti"],
)
def test_access_token_rejects_missing_claims(missing: str) -> None:
    payload = claim_payload()
    payload.pop(missing)

    with pytest.raises(ValueError):
        build_service().read_access_token(
            sign({"alg": "HS256", "typ": "JWT"}, payload)
        )


# Verify a token whose subject is not a UUID is refused.
@pytest.mark.parametrize("subject", ["", "not-a-uuid", "12345"])
def test_access_token_rejects_malformed_subject(subject: str) -> None:
    forged = sign(
        {"alg": "HS256", "typ": "JWT"}, claim_payload(sub=subject)
    )

    with pytest.raises(ValueError):
        build_service().read_access_token(forged)


# Verify a token whose permission claim is not a list of scopes is refused.
@pytest.mark.parametrize(
    "permissions", ["cases:read", ["cases:read", 7], None, {"a": True}]
)
def test_access_token_rejects_malformed_permissions(
    permissions: object,
) -> None:
    with pytest.raises(ValueError):
        build_service().read_access_token(
            sign(
                {"alg": "HS256", "typ": "JWT"},
                claim_payload(permissions=permissions),
            )
        )
