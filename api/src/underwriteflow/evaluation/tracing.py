"""Optional redacted LangSmith trace support for synthetic evaluation."""

import os
from typing import Any

SENSITIVE_KEYS = {
    "api_key",
    "case_id",
    "content",
    "document",
    "document_text",
    "email",
    "password",
    "prompt",
    "raw_document",
    "token",
}


# Remove identifiers, credentials, prompts, and raw document content.
def redact_trace(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_trace(item)
            for key, item in value.items()
            if key.casefold() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [redact_trace(item) for item in value]
    return value


# Send only synthetic summary metadata when tracing is explicitly enabled.
def trace_summary(summary: dict[str, Any]) -> bool:
    if os.getenv("LANGSMITH_TRACING", "false").casefold() != "true":
        return False
    try:
        from langsmith import Client

        client = Client(
            api_url=os.getenv("LANGSMITH_ENDPOINT"),
            api_key=os.getenv("LANGSMITH_API_KEY"),
        )
        client.create_run(
            name="underwriteflow-synthetic-evaluation",
            run_type="chain",
            inputs={"dataset": "synthetic-evaluation"},
            outputs=redact_trace(summary),
            project_name=os.getenv("LANGSMITH_PROJECT", "underwriteflow-local"),
        )
        return True
    except Exception:
        return False
