"""Sanitized construction of append-only business audit events.

Every audit event in the application is built here so one place decides what
is safe to persist. Details are bounded and stripped of secret-shaped keys
before they reach the database, and no single value can carry a whole
document: a long string is truncated at ``MAX_STRING_CHARS``.
"""

import math
import re
from datetime import date, datetime
from typing import Any
from uuid import UUID

from underwriteflow.persistence.models import AuditEvent

# Detail keys matching this pattern are dropped before an event is persisted.
SENSITIVE_KEY_PATTERN = re.compile(
    r"password|passphrase|secret|token|credential|authorization"
    r"|api[_-]?key|private[_-]?key|session|cookie|signature",
    re.IGNORECASE,
)

# Exact detail keys that are safe even though their names look sensitive.
ALLOWED_KEYS = frozenset({"prompt_tokens", "completion_tokens"})

# Exact detail keys that would carry raw prompt or document content.
# "content_hash" and "prompt_tokens" deliberately stay outside this set.
DENIED_KEYS = frozenset(
    {
        "body",
        "chunk",
        "content",
        "document_text",
        "excerpt",
        "message",
        "messages",
        "page_text",
        "pages",
        "prompt",
        "prompts",
        "raw",
        "snippet",
        "text",
    }
)

# Longest free-text value retained, which bounds any document excerpt.
MAX_STRING_CHARS = 200

# Longest mapping or sequence retained for one detail entry.
MAX_ITEMS = 50

# Deepest nested mapping retained before a value is replaced by a marker.
MAX_DEPTH = 4

# Marker written in place of a value the builder refused to persist.
TRUNCATED = "[truncated]"


# Reduce one arbitrary value to a bounded, JSON-safe audit detail value.
def _sanitize_value(value: Any, depth: int = 0) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        if len(text) > MAX_STRING_CHARS:
            return text[:MAX_STRING_CHARS] + "…"
        return text
    if depth >= MAX_DEPTH:
        return TRUNCATED
    if isinstance(value, dict):
        return sanitize_details(value, depth + 1)
    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            _sanitize_value(item, depth + 1)
            for item in list(value)[:MAX_ITEMS]
        ]
    return str(value)[:MAX_STRING_CHARS]


# Drop secret-shaped keys and bound every value in one detail mapping.
def sanitize_details(
    details: dict[Any, Any], depth: int = 0
) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        name = str(key)
        if name.casefold() in DENIED_KEYS:
            continue
        if (
            name.casefold() not in ALLOWED_KEYS
            and SENSITIVE_KEY_PATTERN.search(name)
        ):
            continue
        if len(sanitized) >= MAX_ITEMS:
            break
        sanitized[name] = _sanitize_value(value, depth)
    return sanitized


# Build one sanitized append-only audit event.
def build_audit_event(
    event_type: str,
    details: dict[Any, Any] | None = None,
    *,
    case_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> AuditEvent:
    return AuditEvent(
        case_id=case_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        details=sanitize_details(details or {}),
    )


# Describe one pinned product and rulebook version for an audit event.
def version_details(
    product_version: Any,
    rulebook_version: Any | None = None,
) -> dict[str, Any]:
    details: dict[str, Any] = {}
    if product_version is not None:
        details["product_version_id"] = str(product_version.id)
        details["product_version"] = product_version.version
        details["product_content_hash"] = product_version.content_hash
    if rulebook_version is not None:
        details["rulebook_version_id"] = str(rulebook_version.id)
        details["rulebook_version"] = rulebook_version.version
        details["rulebook_content_hash"] = rulebook_version.content_hash
    return details


# Describe one provider call per document without copying document content.
def provider_activity(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "document_id": result.get("document_id"),
            "document_code": result.get("document_code"),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "attempts": result.get("attempts"),
            "prompt_tokens": result.get("prompt_tokens"),
            "completion_tokens": result.get("completion_tokens"),
            "usage_unavailable": bool(
                result.get("usage_unavailable", True)
            ),
            "request_hash": result.get("request_hash") or None,
            "result_hash": result.get("result_hash") or None,
            "error_code": result.get("error_code"),
        }
        for result in results
    ]


# Point one event at the earlier event it replaces.
def supersedes_details(previous_event_id: UUID | None) -> dict[str, Any]:
    if previous_event_id is None:
        return {}
    return {"supersedes_event_id": previous_event_id}
