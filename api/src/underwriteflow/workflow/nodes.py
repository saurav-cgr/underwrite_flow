"""Evidence worker, fan-out, join, and reconciliation nodes."""

from collections.abc import Mapping
from typing import Any

from langgraph.types import Send

from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.providers.schemas import (
    DocumentPage,
    ExtractionRequest,
    FieldSpecification,
)
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
    trusted_page_locator,
)
from underwriteflow.workflow.reconciliation import reconcile
from underwriteflow.workflow.reducers import sort_results
from underwriteflow.workflow.state import DocumentResult, DocumentWorkerState, EvidenceState

MAX_DOCUMENT_BRANCHES = 3


# List document branches that produced no usable evidence.
def branch_failures(
    evidence_result: Mapping[str, Any],
) -> list[dict[str, object]]:
    return [
        {
            "document_id": result.get("document_id"),
            "filename": result.get("filename"),
            "error_code": result.get("error_code"),
        }
        for result in evidence_result.get("results", [])
        if result.get("error_code")
    ]


# Extract one document branch with retries limited to transient provider failures.
async def extract_document(
    state: DocumentWorkerState,
    provider: ExtractionProvider,
    retry_count: int,
) -> dict[str, list[DocumentResult]]:
    document = state["document"]
    # Trusted page boundaries let a provider line number become a page locator.
    pages = [
        DocumentPage.model_validate(page)
        for page in document.get("pages", [])
    ]
    request = ExtractionRequest(
        document_name=document["document_id"],
        content=document["content"],
        requested_fields=state["requested_fields"],
        reference_content=state.get("reference_content", ""),
        field_specifications=[
            FieldSpecification.model_validate(specification)
            for specification in state.get("field_specifications", [])
        ],
        pages=pages,
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
                        "document_code": document.get("document_code"),
                        "filename": document["filename"],
                        "fields": (
                            []
                            if unrequested
                            else [
                                field.model_copy(
                                    update={
                                        "source_locator": (
                                            trusted_page_locator(
                                                pages,
                                                field.source_locator,
                                            )
                                        )
                                    }
                                ).model_dump(mode="json")
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
                    "document_code": document.get("document_code"),
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
            {
                "document": document,
                "requested_fields": state.get("requested_fields", []),
                "field_specifications": state.get(
                    "field_specifications", []
                ),
                "reference_content": state.get("reference_content", ""),
            },
        )
        for document in pending[:MAX_DOCUMENT_BRANCHES]
    ]


# Mark a completed batch for the next fan-out decision.
def join_evidence(state: EvidenceState) -> dict[str, list[DocumentResult]]:
    return {"ordered_results": sort_results(state.get("results", []))}


# Return the comparable form of an extracted value for conflict detection.
def comparable_value(value: object) -> str:
    return str(value).strip()


# Group reconciled fields that disagree about the same field name.
def conflicting_fields(
    reconciled: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in reconciled:
        name = str(item.get("field_name", ""))
        if not name:
            continue
        grouped.setdefault(name, []).append(item)
    conflicts: list[dict[str, object]] = []
    for name in sorted(grouped):
        sources = grouped[name]
        distinct = sorted(
            {comparable_value(item.get("value")) for item in sources}
        )
        if len(distinct) < 2:
            continue
        conflicts.append(
            {
                "field_name": name,
                "values": distinct,
                "document_ids": sorted(
                    {str(item.get("document_id")) for item in sources}
                ),
                "sources": [
                    {
                        "document_id": str(item.get("document_id")),
                        "source_locator": item.get("source_locator"),
                        "value": item.get("value"),
                    }
                    for item in sorted(
                        sources,
                        key=lambda entry: (
                            str(entry.get("document_id")),
                            str(entry.get("source_locator")),
                        ),
                    )
                ],
            }
        )
    return conflicts


# List requested fields that no document supplied a value for.
def absent_requested_fields(
    reconciled: list[dict[str, object]], requested_fields: list[str]
) -> list[str]:
    supplied = {
        str(item.get("field_name"))
        for item in reconciled
        if item.get("value") is not None and item.get("value") != ""
    }
    return sorted(
        field for field in set(requested_fields) if field not in supplied
    )


# Reconcile successful fields sequentially after all document branches finish.
def reconcile_evidence(state: EvidenceState) -> dict[str, object]:
    reconciled: list[dict[str, object]] = []
    ordered_results = state.get("ordered_results") or sort_results(state.get("results", []))
    for result in ordered_results:
        for field in result["fields"]:
            reconciled.append(
                {
                    "document_id": result["document_id"],
                    "document_code": result.get("document_code"),
                    **field,
                }
            )
    checks = state.get("reconciliation_checks", [])
    # Reconciliation is a pure step, so it runs inside the join and never
    # performs its own database, provider, or audit work.
    outcome = reconcile(
        checks=checks,
        application=state.get("application", {}),
        evidence=reconciled,
        rule_version=state.get("rule_version", ""),
    )
    return {
        "reconciled_fields": reconciled,
        "conflicts": conflicting_fields(reconciled),
        "missing_information": absent_requested_fields(
            reconciled, state.get("requested_fields", [])
        ),
        "reconciliation_results": outcome["results"],
        "reconciliation_status": outcome["overall_status"],
    }
