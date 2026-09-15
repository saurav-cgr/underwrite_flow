"""Evidence worker, fan-out, join, and reconciliation nodes."""

from langgraph.types import Send

from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.providers.schemas import ExtractionRequest
from underwriteflow.providers.service import ProviderError, TransientProviderError
from underwriteflow.workflow.reducers import sort_results
from underwriteflow.workflow.state import DocumentResult, DocumentWorkerState, EvidenceState

MAX_DOCUMENT_BRANCHES = 3


# Extract one document branch with retries limited to transient provider failures.
async def extract_document(
    state: DocumentWorkerState,
    provider: ExtractionProvider,
    retry_count: int,
) -> dict[str, list[DocumentResult]]:
    document = state["document"]
    request = ExtractionRequest(
        document_name=document["document_id"],
        content=document["content"],
        requested_fields=state["requested_fields"],
    )
    attempts = 0
    while True:
        attempts += 1
        try:
            result = await provider.extract(request)
            requested = set(state["requested_fields"])
            accepted = [
                field
                for field in result.fields
                if field.field_name in requested
            ]
            # Any field the application did not request fails the branch.
            unrequested = len(accepted) != len(result.fields)
            return {
                "results": [
                    {
                        "document_id": document["document_id"],
                        "filename": document["filename"],
                        "fields": (
                            []
                            if unrequested
                            else [
                                field.model_dump(mode="json")
                                for field in accepted
                            ]
                        ),
                        "error_code": (
                            "unrequested_field" if unrequested else None
                        ),
                        "attempts": attempts,
                    }
                ]
            }
        except TransientProviderError:
            if attempts <= retry_count:
                continue
            error_code = "transient_provider_error"
        except ProviderError:
            error_code = "provider_error"
        return {
            "results": [
                {
                    "document_id": document["document_id"],
                    "filename": document["filename"],
                    "fields": [],
                    "error_code": error_code,
                    "attempts": attempts,
                }
            ]
        }


# Send only the next three unprocessed documents to bounded parallel branches.
def fan_out_documents(state: EvidenceState) -> list[Send] | str:
    processed = {result["document_id"] for result in state.get("results", [])}
    pending = [
        document
        for document in state.get("documents", [])
        if document["document_id"] not in processed
    ]
    if not pending:
        return "reconcile_evidence"
    return [
        Send(
            "extract_document",
            {"document": document, "requested_fields": state.get("requested_fields", [])},
        )
        for document in pending[:MAX_DOCUMENT_BRANCHES]
    ]


# Mark a completed batch for the next fan-out decision.
def join_evidence(state: EvidenceState) -> dict[str, list[DocumentResult]]:
    return {"ordered_results": sort_results(state.get("results", []))}


# Reconcile successful fields sequentially after all document branches finish.
def reconcile_evidence(state: EvidenceState) -> dict[str, list[dict[str, object]]]:
    reconciled: list[dict[str, object]] = []
    ordered_results = state.get("ordered_results") or sort_results(state.get("results", []))
    for result in ordered_results:
        for field in result["fields"]:
            reconciled.append(
                {
                    "document_id": result["document_id"],
                    **field,
                }
            )
    return {"reconciled_fields": reconciled}
