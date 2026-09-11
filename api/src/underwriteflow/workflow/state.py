"""Serializable state and stable result reducers for evidence processing."""

from typing import Annotated, TypedDict

from underwriteflow.workflow.reducers import append_results


class DocumentInput(TypedDict):
    """Text-only document input; file bytes remain outside graph state."""

    document_id: str
    filename: str
    content: str


class DocumentResult(TypedDict):
    """Serializable result for one document branch."""

    document_id: str
    filename: str
    fields: list[dict[str, object]]
    error_code: str | None
    attempts: int


class EvidenceState(TypedDict, total=False):
    """Parent graph state shared by fan-out, join, and reconciliation nodes."""

    case_id: str
    documents: list[DocumentInput]
    requested_fields: list[str]
    results: Annotated[list[DocumentResult], append_results]
    ordered_results: list[DocumentResult]
    reconciled_fields: list[dict[str, object]]


class DocumentWorkerState(TypedDict):
    """Payload delivered to one isolated document worker branch."""

    document: DocumentInput
    requested_fields: list[str]


# Return a stable thread configuration for one case workflow run.
def thread_config(case_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": f"case-{case_id}"}}
