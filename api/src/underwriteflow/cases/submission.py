"""Applicant submission: local extraction, evidence workflow, persistence."""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.cases.service import CaseValidationError, missing_document_codes
from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Document,
    ExtractedField,
    ProductVersion,
    Recommendation,
    RiskSignal,
    Submission,
    Validation,
)
from underwriteflow.providers.extraction import (
    ExtractionError,
    LocalDocumentExtractor,
)
from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.product_subgraphs import build_product_subgraph
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import build_triage_graph

WORKFLOW_VERSION = "evidence-v1"


class SubmissionService:
    """Run the bounded evidence workflow for one submitted case."""

    # Configure the provider, upload volume, and retry bound for this run.
    def __init__(
        self,
        provider: ExtractionProvider,
        upload_root: str,
        database_url: str,
        retry_count: int = 2,
    ) -> None:
        self.provider = provider
        self.upload_root = Path(upload_root)
        self.database_url = database_url
        self.retry_count = retry_count

    # Read local text for every document, recording typed extraction failures.
    def extract_documents(
        self, documents: list[Document]
    ) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
        extractor = LocalDocumentExtractor()
        inputs: list[dict[str, str]] = []
        failures: list[dict[str, object]] = []
        for document in documents:
            try:
                local = extractor.extract(
                    self.upload_root / document.storage_key,
                    document.content_type,
                )
            except ExtractionError:
                failures.append(
                    {
                        "document_id": str(document.id),
                        "filename": document.filename,
                        "error_code": "extraction_failed",
                    }
                )
                continue
            inputs.append(
                {
                    "document_id": str(document.id),
                    "filename": document.filename,
                    "content": "\n".join(page.text for page in local.pages),
                }
            )
        return inputs, failures

    # Run the bounded evidence graph and return its reconciled output.
    async def run_evidence_graph(
        self,
        case: Case,
        document_inputs: list[dict[str, str]],
        requested_fields: list[str],
    ) -> dict[str, object]:
        graph = build_evidence_graph(
            self.provider, retry_count=self.retry_count
        )
        return await graph.ainvoke(
            {
                "case_id": str(case.id),
                "documents": document_inputs,
                "requested_fields": requested_fields,
                "results": [],
            },
            config=thread_config(str(case.id), case.review_cycle),
        )

    # Reuse a paused checkpoint or run triage up to the human interrupt.
    async def run_triage_graph(
        self, case: Case, state: dict[str, object]
    ) -> dict[str, object]:
        config = thread_config(str(case.id), case.review_cycle)
        async with postgres_checkpointer(self.database_url) as checkpointer:
            graph = build_triage_graph(checkpointer=checkpointer)
            snapshot = await graph.aget_state(config)
            if snapshot.values.get("recommendation"):
                return dict(snapshot.values)
            result = await graph.ainvoke(state, config=config)
            return dict(result)

    # Build the deterministic triage input from produced evidence.
    def build_triage_state(
        self,
        case: Case,
        documents: list[Document],
        evidence_result: dict[str, object],
        product_result: dict[str, object],
    ) -> dict[str, object]:
        reconciled = list(evidence_result.get("reconciled_fields", []))
        evidence = [
            {
                "document_id": str(document.id),
                "filename": document.filename,
                "source_locator": document.storage_key,
                "source_type": "submitted_document",
            }
            for document in documents
        ]
        evidence.extend(
            {
                "document_id": item.get("document_id"),
                "field_name": item.get("field_name"),
                "value": item.get("value"),
                "source_locator": item.get("source_locator"),
                "source_type": "extracted_field",
            }
            for item in reconciled
        )
        return {
            "case_id": str(case.id),
            "evidence": evidence,
            "conflicts": [],
            "missing_information": [],
            "risk_signals": product_result.get("risk_signals", []),
            "validations": product_result.get("validations", []),
            "low_confidence": any(
                (item.get("confidence") or 1.0) < 0.8 for item in reconciled
            ),
        }

    # Persist evidence, validations, branch failures, and the recommendation.
    async def persist(
        self,
        session: AsyncSession,
        case: Case,
        actor_user_id: UUID,
        evidence_result: dict[str, object],
        product_result: dict[str, object],
        triage_values: dict[str, object],
        extraction_failures: list[dict[str, object]],
    ) -> None:
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
                    conflict_status="clear",
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
        existing = await session.scalar(
            select(Recommendation).where(Recommendation.case_id == case.id)
        )
        if existing is None:
            session.add(
                Recommendation(
                    case_id=case.id,
                    route=recommended.get("route"),
                    status="pending_human_review",
                    summary={
                        "summary": triage_values.get("summary", {}),
                        "recommendation": recommended,
                        "failures": len(extraction_failures),
                    },
                    workflow_version=WORKFLOW_VERSION,
                )
            )
        case.status = "underwriter_review"
        session.add(
            AuditEvent(
                case_id=case.id,
                actor_user_id=actor_user_id,
                event_type="case_submitted",
                details={"recommendation": recommended.get("route")},
            )
        )
        await session.commit()
    # Validate evidence, run the workflow, and persist every produced record.
    async def submit(
        self, session: AsyncSession, case: Case, actor_user_id: UUID
    ) -> dict[str, object]:
        if case.status != "new":
            raise CaseValidationError("case is not open for submission")
        product_version = await session.scalar(
            select(ProductVersion).where(
                ProductVersion.id == case.product_version_id
            )
        )
        if product_version is None:
            raise CaseValidationError("case configuration is unavailable")
        configuration = ProductConfiguration.model_validate(
            product_version.configuration
        )
        submission = await session.scalar(
            select(Submission).where(Submission.case_id == case.id)
        )
        if submission is None:
            raise CaseValidationError("case submission is unavailable")
        payload = submission.payload.get("application", {})
        documents = list(
            await session.scalars(
                select(Document).where(Document.case_id == case.id)
            )
        )
        missing = missing_document_codes(
            configuration,
            [
                document.document_code
                for document in documents
                if document.document_code
            ],
            payload,
        )
        if missing:
            raise CaseValidationError(
                "missing documents: " + ", ".join(missing)
            )
        requested_fields = [field.key for field in configuration.fields]
        document_inputs, extraction_failures = self.extract_documents(documents)
        product_result = await build_product_subgraph(configuration).ainvoke(
            {
                "product_code": configuration.product_code,
                "payload": payload,
                "rule_results": [],
            }
        )
        evidence_result = await self.run_evidence_graph(
            case, document_inputs, requested_fields
        )
        triage_values = await self.run_triage_graph(
            case,
            self.build_triage_state(
                case, documents, evidence_result, product_result
            ),
        )
        await self.persist(
            session,
            case,
            actor_user_id,
            evidence_result,
            product_result,
            triage_values,
            extraction_failures,
        )
        return {
            "status": "underwriter_review",
            "recommendation": triage_values.get("recommendation", {}),
        }
