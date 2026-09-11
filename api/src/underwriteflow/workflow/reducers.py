"""Deterministic reducers for parallel evidence results."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from underwriteflow.workflow.state import DocumentResult


# Append branch updates without mutating the prior graph state.
def append_results(
    current: list["DocumentResult"] | None, updates: list["DocumentResult"] | None
) -> list["DocumentResult"]:
    return [*(current or []), *(updates or [])]


# Sort results by stable document identity before sequential reconciliation.
def sort_results(results: list["DocumentResult"]) -> list["DocumentResult"]:
    return sorted(results, key=lambda result: (result["document_id"], result["filename"]))
