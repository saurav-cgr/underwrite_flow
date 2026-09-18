"""Applicant submission: local extraction, evidence workflow, persistence."""

from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.cases.evidence_persistence import (
    clear_previous_evidence,
    persist_case_evidence,
)
from underwriteflow.cases.local_reading import (
    extract_documents,
    load_reference_content,
)
from underwriteflow.cases.service import (
    CaseValidationError,
    field_specifications,
    missing_document_codes,
    requested_field_keys,
)
from underwriteflow.persistence.models import (
    Case,
    Document,
    ProductVersion,
    Submission,
)
from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.nodes import branch_failures
from underwriteflow.workflow.product_subgraphs import build_product_subgraph
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import (
    build_triage_graph,
    has_low_confidence,
)


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

    # Run the bounded evidence graph and return its reconciled output.
    async def run_evidence_graph(
        self,
        case: Case,
        document_inputs: list[dict[str, object]],
        requested_fields: list[str],
        reference_content: str = "",
        application: dict[str, object] | None = None,
        configuration: ProductConfiguration | None = None,
    ) -> dict[str, object]:
        graph = build_evidence_graph(
            self.provider, retry_count=self.retry_count
        )
        return await graph.ainvoke(
            {
                "case_id": str(case.id),
                "documents": document_inputs,
                "requested_fields": requested_fields,
                "field_specifications": (
                    field_specifications(configuration, requested_fields)
                    if configuration is not None
                    else []
                ),
                "reference_content": reference_content,
                "application": application or {},
                "reconciliation_checks": (
                    [
                        check.model_dump(mode="json")
                        for check in configuration.reconciliations
                    ]
                    if configuration is not None
                    else []
                ),
                "rule_version": (
                    configuration.version
                    if configuration is not None
                    else ""
                ),
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
        extraction_failures: list[dict[str, object]],
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
            "conflicts": list(evidence_result.get("conflicts", [])),
            "missing_information": list(
                evidence_result.get("missing_information", [])
            ),
            "reconciliation_results": list(
                evidence_result.get("reconciliation_results", [])
            ),
            "reconciliation_status": str(
                evidence_result.get("reconciliation_status", "")
            ),
            "risk_signals": product_result.get("risk_signals", []),
            "validations": product_result.get("validations", []),
            "processing_failures": [
                *extraction_failures,
                *branch_failures(evidence_result),
            ],
            "low_confidence": has_low_confidence(reconciled),
        }

    # Route a case whose pinned configuration cannot be read to manual review.
    async def route_unsupported_case(
        self,
        session: AsyncSession,
        case: Case,
        actor_user_id: UUID,
        event_type: str,
        clear_evidence: bool,
    ) -> dict[str, object]:
        if clear_evidence:
            await clear_previous_evidence(session, case)
        documents = list(
            await session.scalars(
                select(Document).where(Document.case_id == case.id)
            )
        )
        # The reason is carried in the triage input and persisted as a
        # validation so the review screen can explain why a human is needed.
        failure = {
            "rule_code": "unsupported_product",
            "status": "error",
            "details": {"reason": "unreadable_product_configuration"},
        }
        triage_values = await self.run_triage_graph(
            case,
            {
                "case_id": str(case.id),
                "evidence": [],
                "conflicts": [],
                "missing_information": [],
                "risk_signals": [],
                "validations": [failure],
                "processing_failures": [],
                "low_confidence": False,
                "unsupported_product": True,
            },
        )
        await persist_case_evidence(
            session,
            case,
            actor_user_id,
            {},
            {"validations": [failure]},
            triage_values,
            [],
            documents,
            event_type=event_type,
        )
        return {
            "status": "underwriter_review",
            "recommendation": triage_values.get("recommendation", {}),
        }

    # Start the first workflow cycle for a newly created case.
    async def submit(
        self, session: AsyncSession, case: Case, actor_user_id: UUID
    ) -> dict[str, object]:
        if case.status != "new":
            raise CaseValidationError("case is not open for submission")
        return await self.run_cycle(
            session,
            case,
            actor_user_id,
            event_type="case_submitted",
            clear_evidence=False,
        )

    # Start a fresh cycle for a case the underwriter returned for information.
    async def resubmit(
        self, session: AsyncSession, case: Case, actor_user_id: UUID
    ) -> dict[str, object]:
        if case.status != "needs_information":
            raise CaseValidationError("case does not need more information")
        case.review_cycle += 1
        await session.flush()
        return await self.run_cycle(
            session,
            case,
            actor_user_id,
            event_type="case_resubmitted",
            clear_evidence=True,
        )

    # Validate evidence, run the workflow, and persist every produced record.
    async def run_cycle(
        self,
        session: AsyncSession,
        case: Case,
        actor_user_id: UUID,
        event_type: str,
        clear_evidence: bool,
    ) -> dict[str, object]:
        product_version = await session.scalar(
            select(ProductVersion).where(
                ProductVersion.id == case.product_version_id
            )
        )
        if product_version is None:
            raise CaseValidationError("case configuration is unavailable")
        try:
            configuration = ProductConfiguration.model_validate(
                product_version.configuration
            )
        except ValidationError:
            # A pinned configuration the application can no longer read cannot
            # be processed deterministically, so a human decides the route.
            return await self.route_unsupported_case(
                session,
                case,
                actor_user_id,
                event_type,
                clear_evidence,
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
        if clear_evidence:
            await clear_previous_evidence(session, case)
        requested_fields = requested_field_keys(configuration, payload)
        document_inputs, extraction_failures = extract_documents(
            self.upload_root, documents
        )
        product_result = await build_product_subgraph(configuration).ainvoke(
            {
                "product_code": configuration.product_code,
                "payload": payload,
                "rule_results": [],
            }
        )
        reference_content = await load_reference_content(
            session, self.upload_root, case
        )
        evidence_result = await self.run_evidence_graph(
            case,
            document_inputs,
            requested_fields,
            reference_content,
            application=payload,
            configuration=configuration,
        )
        triage_values = await self.run_triage_graph(
            case,
            self.build_triage_state(
                case,
                documents,
                evidence_result,
                product_result,
                extraction_failures,
            ),
        )
        await persist_case_evidence(
            session,
            case,
            actor_user_id,
            evidence_result,
            product_result,
            triage_values,
            extraction_failures,
            documents,
            event_type=event_type,
        )
        return {
            "status": "underwriter_review",
            "recommendation": triage_values.get("recommendation", {}),
        }
