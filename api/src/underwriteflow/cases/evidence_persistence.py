"""Persistence of produced evidence, validations, and their audit trail."""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import (
    build_audit_event,
    provider_activity,
    supersedes_details,
    version_details,
)
from underwriteflow.persistence.models import (
    Case,
    Document,
    ExtractedField,
    ProductVersion,
    Recommendation,
    RiskSignal,
    RulebookVersion,
    Validation,
)
from underwriteflow.persistence.repositories import AuditRepository

WORKFLOW_VERSION = "evidence-v1"

# Event types that one processing cycle replaces when it starts again.
SUBMISSION_EVENT_TYPES = ("case_submitted", "case_resubmitted")


# Remove the previous cycle's derived evidence before a new run.
async def clear_previous_evidence(session: AsyncSession, case: Case) -> None:
    for model in (ExtractedField, Validation, RiskSignal):
        await session.execute(delete(model).where(model.case_id == case.id))


# Describe reconciled evidence sources without copying any extracted value.
def evidence_provenance(
    reconciled: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "field_name": item.get("field_name"),
            "document_id": item.get("document_id"),
            "source_locator": item.get("source_locator"),
            "extraction_method": item.get("extraction_method"),
        }
        for item in reconciled
    ]


# Record which document versions and hashes the run consumed.
def document_identity(documents: list[Document]) -> list[dict[str, Any]]:
    return [
        {
            "document_id": document.id,
            "document_code": document.document_code,
            "content_hash": document.content_hash,
            "byte_size": document.byte_size,
        }
        for document in documents
    ]


# Build the sanitized audit details for one completed processing cycle.
async def cycle_details(
    session: AsyncSession,
    case: Case,
    evidence_result: dict[str, Any],
    product_result: dict[str, Any],
    triage_values: dict[str, Any],
    extraction_failures: list[dict[str, Any]],
    documents: list[Document],
) -> dict[str, Any]:
    reconciled = list(evidence_result.get("reconciled_fields", []))
    conflicts = list(evidence_result.get("conflicts", []))
    product_version = await session.scalar(
        select(ProductVersion).where(
            ProductVersion.id == case.product_version_id
        )
    )
    rulebook = await session.scalar(
        select(RulebookVersion).where(
            RulebookVersion.id == case.rulebook_version_id
        )
    )
    recommended = triage_values.get("recommendation", {})
    return {
        "review_cycle": case.review_cycle,
        "workflow_version": WORKFLOW_VERSION,
        "recommendation": recommended.get("route"),
        "recommendation_status": "pending_human_review",
        "conflicts": [str(item.get("field_name")) for item in conflicts],
        "missing_information": sorted(
            str(item) for item in evidence_result.get("missing_information", [])
        ),
        "evidence_provenance": evidence_provenance(reconciled),
        "validations": [
            {
                "rule_code": item.get("rule_code"),
                "status": item.get("status"),
            }
            for item in product_result.get("validations", [])
        ],
        "risk_signals": [
            item.get("code") for item in product_result.get("risk_signals", [])
        ],
        "documents": document_identity(documents),
        "provider_calls": provider_activity(
            list(
                evidence_result.get("ordered_results")
                or evidence_result.get("results", [])
            )
        ),
        "failed_documents": [
            {
                "document_id": failure.get("document_id"),
                "error_code": failure.get("error_code"),
            }
            for failure in extraction_failures
        ]
        + [
            {
                "document_id": result.get("document_id"),
                "error_code": result.get("error_code"),
            }
            for result in evidence_result.get("results", [])
            if result.get("error_code")
        ],
        **version_details(product_version, rulebook),
    }


# Persist evidence, validations, branch failures, and the audit event.
async def persist_case_evidence(
    session: AsyncSession,
    case: Case,
    actor_user_id: UUID,
    evidence_result: dict[str, Any],
    product_result: dict[str, Any],
    triage_values: dict[str, Any],
    extraction_failures: list[dict[str, Any]],
    documents: list[Document],
    event_type: str = "case_submitted",
) -> None:
    conflicting = {
        str(item["field_name"])
        for item in evidence_result.get("conflicts", [])
    }
    for item in evidence_result.get("reconciled_fields", []):
        if not item.get("source_locator"):
            continue
        session.add(
            ExtractedField(
                case_id=case.id,
                document_id=UUID(str(item["document_id"])),
                field_name=item["field_name"],
                value=item.get("value"),
                source_locator=item["source_locator"],
                extraction_method=item.get("extraction_method", "provider"),
                confidence=item.get("confidence"),
                conflict_status=(
                    "conflict" if item["field_name"] in conflicting else "clear"
                ),
            )
        )
    for validation in product_result.get("validations", []):
        session.add(
            Validation(
                case_id=case.id,
                rule_code=validation["rule_code"],
                status=validation["status"],
                details=validation,
            )
        )
    # Reconciliation results persist as validations, and each flagged
    # discrepancy also becomes a deterministic specialist signal.
    for result in evidence_result.get("reconciliation_results", []):
        session.add(
            Validation(
                case_id=case.id,
                rule_code=f"reconciliation:{result['check_code']}",
                status=str(result.get("status", "")).lower(),
                details=result,
            )
        )
        for discrepancy in result.get("discrepancies", []):
            session.add(
                RiskSignal(
                    case_id=case.id,
                    code=f"reconciliation_{discrepancy.get('code')}",
                    severity="medium",
                    explanation=(
                        "A configured reconciliation check found a "
                        "discrepancy between the application and its "
                        "evidence."
                    ),
                    source_type="deterministic",
                )
            )
    for signal in product_result.get("risk_signals", []):
        session.add(
            RiskSignal(
                case_id=case.id,
                code=signal["code"],
                severity=signal.get("severity", "high"),
                explanation=signal.get("explanation", ""),
                source_type=signal.get("source_type", "deterministic"),
            )
        )
    for failure in [
        *extraction_failures,
        *[
            {
                "document_id": result["document_id"],
                "filename": result["filename"],
                "error_code": result["error_code"],
            }
            for result in evidence_result.get("results", [])
            if result.get("error_code")
        ],
    ]:
        session.add(
            Validation(
                case_id=case.id,
                rule_code=f"document:{failure['document_id']}",
                status="error",
                details=failure,
            )
        )
    recommended = triage_values.get("recommendation", {})
    summary = {
        "summary": triage_values.get("summary", {}),
        "recommendation": recommended,
        "failures": len(extraction_failures),
    }
    existing = await session.scalar(
        select(Recommendation).where(Recommendation.case_id == case.id)
    )
    if existing is None:
        session.add(
            Recommendation(
                case_id=case.id,
                route=recommended.get("route"),
                status="pending_human_review",
                summary=summary,
                workflow_version=WORKFLOW_VERSION,
            )
        )
    else:
        existing.route = recommended.get("route")
        existing.status = "pending_human_review"
        existing.summary = summary
        existing.workflow_version = WORKFLOW_VERSION
    case.status = "underwriter_review"
    details = await cycle_details(
        session,
        case,
        evidence_result,
        product_result,
        triage_values,
        extraction_failures,
        documents,
    )
    superseded = await AuditRepository().latest_event_id(
        session, SUBMISSION_EVENT_TYPES, case_id=case.id
    )
    session.add(
        build_audit_event(
            event_type,
            {**details, **supersedes_details(superseded)},
            case_id=case.id,
            actor_user_id=actor_user_id,
        )
    )
    await session.commit()
