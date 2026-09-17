"""Reviewer-facing evidence assembled from persisted case records."""

from uuid import UUID

from underwriteflow.cases.service import missing_document_codes
from underwriteflow.persistence.models import (
    Document,
    ExtractedField,
    Recommendation,
    Validation,
)
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.reviews.schemas import ReviewStartResponse

FALLBACK_SPECIALIST_LABEL = "Manual configuration review"


# Turn a stored machine identifier into a safe fallback display label.
def fallback_label(code: str) -> str:
    readable = " ".join(code.replace("_", " ").split())
    return readable.capitalize() or "Unnamed field"


# Build readable submitted facts and source-linked extracted evidence.
def build_review_evidence(
    application: dict[str, object],
    documents: list[Document],
    extracted_fields: list[ExtractedField],
    configuration: ProductConfiguration | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    configured_fields = {
        field.key: field for field in configuration.fields
    } if configuration else {}
    configured_documents = {
        document.code: document for document in configuration.documents
    } if configuration else {}
    configured_order = [
        field.key
        for field in configuration.fields
        if field.key in application
    ] if configuration else []
    remaining = sorted(set(application) - set(configured_order))
    facts = []
    for field_name in [*configured_order, *remaining]:
        field = configured_fields.get(field_name)
        facts.append(
            {
                "field_name": field_name,
                "field_label": (
                    field.label if field else fallback_label(field_name)
                ),
                "field_type": field.type if field else "unknown",
                "value": application[field_name],
            }
        )
    evidence: list[dict[str, object]] = []
    for document in documents:
        configured = configured_documents.get(document.document_code or "")
        evidence.append(
            {
                "document_id": str(document.id),
                "document_code": document.document_code,
                "document_title": (
                    configured.title if configured else document.filename
                ),
                "filename": document.filename,
                "content_type": document.content_type,
                "page_count": document.page_count,
                "source_type": "submitted_document",
            }
        )
    for extracted in extracted_fields:
        field = configured_fields.get(extracted.field_name)
        evidence.append(
            {
                "document_id": (
                    str(extracted.document_id)
                    if extracted.document_id
                    else None
                ),
                "field_name": extracted.field_name,
                "field_label": (
                    field.label
                    if field
                    else fallback_label(extracted.field_name)
                ),
                "field_type": field.type if field else "unknown",
                "value": extracted.value,
                "source_locator": extracted.source_locator,
                "extraction_method": extracted.extraction_method,
                "confidence": extracted.confidence,
                "conflict_status": extracted.conflict_status,
                "source_type": "extracted_field",
            }
        )
    return facts, evidence


# Assemble configured check results with ordered provenance for review.
#
# The comparison values come from deterministic code, never from a model, so
# every comparison reports its confidence source explicitly.
def reconciliation_view(
    validations: list[Validation],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for validation in sorted(
        validations, key=lambda item: item.rule_code
    ):
        details = dict(validation.details or {})
        details["comparisons"] = [
            {**comparison, "confidence_source": "deterministic"}
            for comparison in details.get("comparisons", [])
        ]
        results.append(details)
    return results


# Assemble the complete public evidence pack for one pending review.
def build_review_start_response(
    case_id: UUID,
    recommendation: Recommendation,
    application: dict[str, object],
    documents: list[Document],
    extracted_fields: list[ExtractedField],
    failures: list[Validation],
    configuration: ProductConfiguration | None,
    reconciliation: list[Validation] | None = None,
) -> ReviewStartResponse:
    summary = dict(recommendation.summary or {})
    submitted_facts, evidence = build_review_evidence(
        application,
        documents,
        extracted_fields,
        configuration,
    )
    return ReviewStartResponse(
        case_id=case_id,
        status="awaiting_human_review",
        recommendation=summary.get(
            "recommendation",
            {"route": recommendation.route, "factors": []},
        ),
        summary=summary.get("summary", {}),
        submitted_facts=submitted_facts,
        evidence=evidence,
        conflicts=[
            {
                "field_name": field.field_name,
                "value": field.value,
                "document_id": (
                    str(field.document_id) if field.document_id else None
                ),
                "source_locator": field.source_locator,
                "conflict_status": field.conflict_status,
            }
            for field in extracted_fields
            if field.conflict_status != "clear"
        ],
        missing_information=(
            []
            if configuration is None
            else missing_document_codes(
                configuration,
                [
                    document.document_code
                    for document in documents
                    if document.document_code
                ],
                application,
            )
        ),
        reconciliation=reconciliation_view(reconciliation or []),
        extraction_failures=[
            {"rule_code": failure.rule_code, "details": failure.details}
            for failure in failures
        ],
        specialist_options=(
            [FALLBACK_SPECIALIST_LABEL]
            if configuration is None
            else list(configuration.specialist_labels)
        ),
    )
