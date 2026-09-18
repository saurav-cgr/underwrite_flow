"""Sanitization bounds and personal-identifier guarantees for audit events."""

import json
import re

from fastapi.testclient import TestClient
from fixtures.records import set_motor_status
from fixtures.support import (
    ADMINISTRATOR,
    APPLICANT,
    create_motor_case,
    login,
    submit_motor_case,
    upload_documents,
)
from fixtures.synthetic_pdf import IDENTITY_ONLY_LINES, text_pdf

from underwriteflow.app import create_app
from underwriteflow.audit.events import (
    ALLOWED_KEYS,
    DENIED_KEYS,
    MAX_ITEMS,
    MAX_STRING_CHARS,
    SENSITIVE_KEY_PATTERN,
)
from underwriteflow.config import Settings
from underwriteflow.providers.redaction import (
    AADHAAR_PATTERN,
    EMAIL_PATTERN,
    PAN_PATTERN,
)

# Shaped patterns the audit trail must never contain anywhere.
FORBIDDEN_PATTERNS = (AADHAAR_PATTERN, PAN_PATTERN, EMAIL_PATTERN)

# Literal synthetic identifiers an uploaded document carries.
FORBIDDEN_VALUES = (
    "2345 6789 0123",
    "ABCDE1234F",
    "applicant@synthetic.test",
    "9876543210",
)

# A synthetic identity document carrying identifiers no audit may retain.
IDENTIFIER_DOCUMENT_LINES = [
    "identity_reference: SYNTHETIC-0001",
    "aadhaar_number: 2345 6789 0123",
    "pan_number: ABCDE1234F",
    "contact_email: applicant@synthetic.test",
    "contact_phone: 9876543210",
]

# The agreeing motor evidence lines every synthetic submission reuses.
AGREEING_VEHICLE_LINES = [
    "vehicle_age: 2",
    "vehicle_use: personal",
    "prior_claims: 0",
]


# Process one synthetic motor case and return its immutable audit trail.
def processed_case_events(
    client: TestClient, vehicle_lines: list[str]
) -> list[dict]:
    applicant = login(client, APPLICANT)
    created = create_motor_case(client, applicant)
    case_id = str(created["id"])
    upload_documents(
        client,
        applicant,
        case_id,
        [
            ("identity_record", text_pdf(IDENTITY_ONLY_LINES)),
            ("vehicle_record", text_pdf(vehicle_lines)),
        ],
    )
    submit_motor_case(client, applicant, case_id)
    response = client.get(
        f"/api/v1/audit/cases/{case_id}", headers=login(client, ADMINISTRATOR)
    )
    assert response.status_code == 200, response.text
    return response.json()


# Verify every persisted value stays bounded and free of secret-shaped keys.
def test_persisted_events_are_bounded_and_secret_free() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            events = processed_case_events(client, AGREEING_VEHICLE_LINES)
    finally:
        set_motor_status("draft")

    assert events
    for event in events:
        assert_bounded_and_secret_free(event["details"])


# Verify the audit trail never retains document text or personal identifiers.
def test_audit_never_stores_document_text_or_identifiers() -> None:
    set_motor_status("active")
    try:
        with TestClient(
            create_app(Settings(generation_provider="fake"))
        ) as client:
            events = processed_case_events(client, IDENTIFIER_DOCUMENT_LINES)
    finally:
        set_motor_status("draft")

    serialized = json.dumps(events)
    assert any(
        event["event_type"] == "case_submitted" for event in events
    ), serialized[:200]
    for value in FORBIDDEN_VALUES:
        assert value not in serialized, value
    for pattern in FORBIDDEN_PATTERNS:
        assert re.search(pattern, serialized) is None, pattern
    # Only bounded identifiers and hashes are persisted, never raw content.
    assert "identity_reference" not in serialized
    assert "SYNTHETIC-0001" not in serialized


# Walk one detail tree asserting the sanitization bound and key policy.
def assert_bounded_and_secret_free(details: object) -> None:
    if isinstance(details, str):
        assert len(details) <= MAX_STRING_CHARS + 1, details[:80]
        return
    if isinstance(details, list):
        assert len(details) <= MAX_ITEMS
        for item in details:
            assert_bounded_and_secret_free(item)
        return
    if isinstance(details, dict):
        assert len(details) <= MAX_ITEMS
        for key, value in details.items():
            name = str(key).casefold()
            assert name not in DENIED_KEYS, key
            if name not in ALLOWED_KEYS:
                assert not SENSITIVE_KEY_PATTERN.search(str(key)), key
            assert_bounded_and_secret_free(value)
