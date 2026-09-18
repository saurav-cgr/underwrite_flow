"""Sanitization guarantees for append-only audit events."""

from datetime import datetime, timezone
from uuid import uuid4

from underwriteflow.audit.events import (
    MAX_ITEMS,
    MAX_STRING_CHARS,
    TRUNCATED,
    build_audit_event,
    provider_activity,
    sanitize_details,
    supersedes_details,
    version_details,
)


# Verify secret-shaped detail keys are dropped at every nesting level.
def test_secret_shaped_keys_are_dropped_at_any_depth() -> None:
    sanitized = sanitize_details(
        {
            "product_code": "motor-private-car",
            "api_key": "synthetic-value",
            "nested": {"password": "synthetic-value", "kept": 1},
            "items": [{"token": "synthetic-value", "kept": 2}],
            "authorization_header": "Bearer synthetic",
            "session_secret": "synthetic-value",
        }
    )

    assert sanitized == {
        "product_code": "motor-private-car",
        "nested": {"kept": 1},
        "items": [{"kept": 2}],
    }


# Verify one value can never carry a whole document body.
def test_long_text_is_truncated_to_the_bound() -> None:
    sanitized = sanitize_details({"reason": "A" * 5_000})

    assert len(sanitized["reason"]) == MAX_STRING_CHARS + 1
    assert sanitized["reason"].endswith("…")
    assert sanitized["reason"] == "A" * MAX_STRING_CHARS + "…"


# Verify collections and nesting are both bounded.
def test_collections_and_nesting_are_bounded() -> None:
    sanitized = sanitize_details(
        {
            "items": list(range(MAX_ITEMS + 30)),
            "deep": {"a": {"b": {"c": {"d": {"e": 1}}}}},
        }
    )

    assert len(sanitized["items"]) == MAX_ITEMS
    assert sanitized["deep"] == {"a": {"b": {"c": {"d": TRUNCATED}}}}


# Verify identifiers and timestamps stay readable and JSON-safe.
def test_identifiers_and_timestamps_are_coerced() -> None:
    case_id = uuid4()
    occurred_at = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    sanitized = sanitize_details(
        {
            "case_id": case_id,
            "occurred_at": occurred_at,
            "count": 3,
            "flagged": True,
            "absent": None,
        }
    )

    assert sanitized["case_id"] == str(case_id)
    assert sanitized["occurred_at"] == occurred_at.isoformat()
    assert sanitized["count"] == 3
    assert sanitized["flagged"] is True
    assert sanitized["absent"] is None


# Verify non-finite floats never reach a JSON column.
def test_non_finite_floats_become_null() -> None:
    sanitized = sanitize_details({"a": float("nan"), "b": float("inf")})

    assert sanitized == {"a": None, "b": None}


# Verify the builder records identity and sanitized details together.
def test_builder_produces_a_sanitized_event() -> None:
    case_id = uuid4()
    actor_id = uuid4()
    event = build_audit_event(
        "case_created",
        {"product_code": "motor-private-car", "api_key": "synthetic-value"},
        case_id=case_id,
        actor_user_id=actor_id,
    )

    assert event.event_type == "case_created"
    assert event.case_id == case_id
    assert event.actor_user_id == actor_id
    assert event.details == {"product_code": "motor-private-car"}


# Verify product and rulebook identity are recorded with their hashes.
def test_version_details_records_ids_versions_and_hashes() -> None:
    class Version:
        def __init__(self) -> None:
            self.id = uuid4()
            self.version = "v1"
            self.content_hash = "synthetic-hash"

    product = Version()
    rulebook = Version()
    details = version_details(product, rulebook)

    assert details["product_version_id"] == str(product.id)
    assert details["product_version"] == "v1"
    assert details["product_content_hash"] == "synthetic-hash"
    assert details["rulebook_version_id"] == str(rulebook.id)
    assert details["rulebook_version"] == "v1"
    assert details["rulebook_content_hash"] == "synthetic-hash"


# Verify a missing rulebook version is simply omitted.
def test_version_details_tolerates_an_absent_rulebook() -> None:
    class Version:
        id = uuid4()
        version = "v1"
        content_hash = "synthetic-hash"

    details = version_details(Version(), None)

    assert "rulebook_version_id" not in details
    assert "product_version_id" in details


# Verify provider metadata keeps hashes, attempts, and usage without content.
def test_provider_activity_records_usage_hashes_and_no_content() -> None:
    activity = provider_activity(
        [
            {
                "document_id": "0b0b0b0b-0000-4000-8000-00000000d0c1",
                "document_code": "vehicle_record",
                "attempts": 2,
                "provider": "gemini",
                "model": "gemini-synthetic",
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "usage_unavailable": False,
                "request_hash": "a" * 64,
                "result_hash": "b" * 64,
                "error_code": None,
                "fields": [{"field_name": "prior_claims", "value": 1}],
                "content": "synthetic document text",
            }
        ]
    )

    assert activity == [
        {
            "document_id": "0b0b0b0b-0000-4000-8000-00000000d0c1",
            "document_code": "vehicle_record",
            "provider": "gemini",
            "model": "gemini-synthetic",
            "attempts": 2,
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "usage_unavailable": False,
            "request_hash": "a" * 64,
            "result_hash": "b" * 64,
            "error_code": None,
        }
    ]


# Verify a failed branch reports attempts with no usage and no result hash.
def test_provider_activity_reports_a_failed_branch() -> None:
    activity = provider_activity(
        [
            {
                "document_id": "0b0b0b0b-0000-4000-8000-00000000d0c2",
                "document_code": "identity_record",
                "attempts": 3,
                "provider": "fake",
                "error_code": "transient_provider_error",
            }
        ]
    )

    assert activity == [
        {
            "document_id": "0b0b0b0b-0000-4000-8000-00000000d0c2",
            "document_code": "identity_record",
            "provider": "fake",
            "model": None,
            "attempts": 3,
            "prompt_tokens": None,
            "completion_tokens": None,
            "usage_unavailable": True,
            "request_hash": None,
            "result_hash": None,
            "error_code": "transient_provider_error",
        }
    ]


# Verify one superseding event points only at the event it replaces.
def test_supersedes_details_links_only_a_known_earlier_event() -> None:
    earlier = uuid4()

    assert supersedes_details(earlier) == {"supersedes_event_id": earlier}
    assert supersedes_details(None) == {}


# Verify raw prompt and file content can never become audit detail.
def test_raw_content_keys_are_refused_at_any_depth() -> None:
    sanitized = sanitize_details(
        {
            "content": "Synthetic Aadhaar 2345 6789 0123",
            "content_hash": "synthetic-content-hash",
            "prompt": "raw prompt",
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "document_text": "Synthetic Applicant",
            "pages": ["page one"],
            "nested": {"text": "excerpt", "byte_size": 10},
            "result_hash": "synthetic-result-hash",
        }
    )

    assert sanitized == {
        "content_hash": "synthetic-content-hash",
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "nested": {"byte_size": 10},
        "result_hash": "synthetic-result-hash",
    }
