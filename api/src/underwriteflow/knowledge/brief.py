"""Deterministic specialist brief assembly without any model call."""

from typing import Any

MAX_SUGGESTED_CITATIONS = 3


# Assemble sourced evidence, triggered rules, and passages for specialists.
def build_brief(
    route: str,
    evidence: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    passages: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if route != "specialist":
        return None
    filenames = {
        item.get("document_id"): item.get("filename")
        for item in evidence
        if item.get("filename")
    }
    return {
        "evidence": [
            {
                "field_name": item["field_name"],
                "value": item.get("value"),
                "document": filenames.get(item.get("document_id")),
                "source_locator": item["source_locator"],
            }
            for item in evidence
            if item.get("field_name") and item.get("source_locator")
        ],
        "rules": [
            str(item["rule_code"])
            for item in validations
            if item.get("status") == "triggered"
        ],
        "passages": passages,
        "suggested_citations": [
            item["citation"] for item in passages[:MAX_SUGGESTED_CITATIONS]
        ],
    }
