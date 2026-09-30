"""Command-line runner for the synthetic evaluation reference set."""

import argparse
import asyncio
import json
from typing import Any

from sqlalchemy import select

from underwriteflow.cases.service import (
    field_specifications,
    requested_field_keys,
)
from underwriteflow.evaluation.dataset import (
    load_configuration_manifest,
    load_dataset,
)
from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.tracing import trace_summary
from underwriteflow.config import get_settings
from underwriteflow.database import Database
from underwriteflow.knowledge.explainer import RouteExplainer
from underwriteflow.persistence.knowledge_models import KnowledgeVersion
from underwriteflow.persistence.models import Product
from underwriteflow.products.schemas import (
    ProductConfiguration,
    filter_configuration_for_journey,
)
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.nodes import branch_failures
from underwriteflow.workflow.product_subgraphs import select_product_subgraph
from underwriteflow.providers.embedding import FakeEmbeddingProvider
from underwriteflow.providers.guidance import FakeGuidanceProvider
from underwriteflow.workflow.state import thread_config
from underwriteflow.workflow.triage import (
    build_triage_graph,
    has_low_confidence,
)
from langgraph.checkpoint.memory import MemorySaver


# Read the documents a reference case supplies as evidence input.
def document_inputs(record: dict[str, Any]) -> list[dict[str, object]]:
    return [
        {
            "document_id": document["document_id"],
            "document_code": document["document_id"],
            "filename": document["filename"],
            "content": "\n".join(document["lines"]),
            "pages": [],
        }
        for document in record["documents"]
    ]


# Run one synthetic case through extraction, reconciliation, and routing.
async def run_record(
    record: dict[str, Any],
    configurations: dict[tuple[str, str], ProductConfiguration],
    guidance_enabled: bool = False,
    explainer: RouteExplainer | None = None,
    guideline_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    manifest_key = (record["product_code"], record["configuration_version"])
    configuration = filter_configuration_for_journey(
        configurations[manifest_key], record["journey_type"]
    )
    requested_fields = requested_field_keys(
        configuration, record["workflow_input"]["payload"]
    )
    evidence_result = await build_evidence_graph(
        FakeProvider(), retry_count=0
    ).ainvoke(
        {
            "case_id": record["case_id"],
            "documents": document_inputs(record),
            "requested_fields": requested_fields,
            "field_specifications": field_specifications(
                configuration, requested_fields
            ),
            "reference_content": "",
            "application": record["workflow_input"]["payload"],
            "reconciliation_checks": [
                check.model_dump(mode="json")
                for check in configuration.reconciliations
            ],
            "rule_version": configuration.version,
            "results": [],
        }
    )
    product_result = await select_product_subgraph(
        record["product_code"], {record["product_code"]: configuration}
    ).ainvoke(
        {
            "product_code": record["product_code"],
            "payload": record["workflow_input"]["payload"],
        }
    )
    reconciled = list(evidence_result.get("reconciled_fields", []))
    conflicts = list(evidence_result.get("conflicts", []))
    missing = list(evidence_result.get("missing_information", []))
    triage_state = {
        "case_id": record["case_id"],
        "evidence": reconciled,
        "conflicts": conflicts,
        "missing_information": missing,
        "risk_signals": product_result.get("risk_signals", []),
        "validations": product_result.get("validations", []),
        "processing_failures": branch_failures(evidence_result),
        "low_confidence": has_low_confidence(reconciled),
        "guidance_context": {
            "case_id": record["case_id"],
            "product_code": record["product_code"],
            "guideline_version_id": (guideline_ids or {}).get(
                record["product_code"]
            ),
        },
    }
    graph = build_triage_graph(
        checkpointer=MemorySaver(),
        explainer=explainer if guidance_enabled else None,
    )
    graph_result = await graph.ainvoke(
        triage_state,
        config=thread_config(record["case_id"]),
    )
    recommendation = graph_result["recommendation"]
    return {
        **record,
        "prediction": {
            "route": recommendation["route"],
            "evidence": sorted(
                result["document_id"]
                for result in evidence_result.get("results", [])
                if not result.get("error_code")
            ),
            "conflict": bool(conflicts),
            "missing": bool(missing),
            "claim_count": len(reconciled),
            "unsupported_claims": sum(
                1 for item in reconciled if not item.get("source_locator")
            ),
        },
        "workflow_succeeded": True,
        "explanation_status": (
            graph_result.get("route_explanation") or {}
        ).get("status"),
    }


# Run every reference case through the pipeline and return produced output.
async def evaluate_cases(
    split: str | None = None,
    guidance_enabled: bool = False,
    guideline_ids: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    records = load_dataset()
    if split:
        records = [record for record in records if record.get("split") == split]
    configurations = load_configuration_manifest()
    if not guidance_enabled:
        return [
            await run_record(record, configurations)
            for record in records
        ]
    database = Database(get_settings().database_url)
    try:
        async with database.session_factory() as session:
            if guideline_ids is None:
                result = await session.execute(
                    select(Product.code, KnowledgeVersion.id)
                    .join(
                        KnowledgeVersion,
                        KnowledgeVersion.product_id == Product.id,
                    )
                    .where(
                        KnowledgeVersion.scope == "guideline",
                        KnowledgeVersion.status == "active",
                    )
                )
                guideline_ids = {
                    code: str(version_id) for code, version_id in result
                }
            explainer = RouteExplainer(
                session,
                FakeGuidanceProvider(),
                FakeEmbeddingProvider(),
            )
            return [
                await run_record(
                    record,
                    configurations,
                    guidance_enabled=True,
                    explainer=explainer,
                    guideline_ids=guideline_ids,
                )
                for record in records
            ]
    finally:
        await database.close()


# Evaluate one requested split and optionally emit a redacted trace.
async def run_evaluation(
    split: str | None = None, trace: bool = False
) -> dict[str, Any]:
    summary = evaluate_records(await evaluate_cases(split))
    summary["split"] = split or "all"
    summary["trace_sent"] = trace_summary(summary) if trace else False
    return summary


# Parse runner flags and print only safe evaluation metrics.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("development", "holdout"))
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    summary = asyncio.run(run_evaluation(args.split, args.trace))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
