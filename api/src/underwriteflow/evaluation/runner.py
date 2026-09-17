"""Command-line runner for the synthetic evaluation reference set."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from underwriteflow.cases.service import (
    field_specifications,
    requested_field_keys,
)
from underwriteflow.evaluation.dataset import load_dataset
from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.tracing import trace_summary
from underwriteflow.products.service import load_configuration
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.nodes import branch_failures
from underwriteflow.workflow.product_subgraphs import select_product_subgraph
from underwriteflow.workflow.triage import (
    has_low_confidence,
    recommend_triage_route,
)


# Locate mounted product configurations or their source-checkout fallback.
def product_config_root() -> Path:
    mounted_path = Path("/app/product-config")
    if mounted_path.exists():
        return mounted_path
    return Path(__file__).resolve().parents[4] / "product-config"


# Load the earliest published fictional version of each product.
#
# The reference dataset was labelled against the first published version, so a
# later draft file on disk must not change its deterministic outcome.
def load_configurations() -> dict[str, Any]:
    configurations: dict[str, Any] = {}
    for path in sorted(product_config_root().glob("*.yaml")):
        configuration = load_configuration(path.read_text())
        current = configurations.get(configuration.product_code)
        if current is None or configuration.version < current.version:
            configurations[configuration.product_code] = configuration
    return configurations


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
    record: dict[str, Any], configurations: dict[str, Any]
) -> dict[str, Any]:
    configuration = configurations[record["product_code"]]
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
        record["product_code"], configurations
    ).ainvoke(
        {
            "product_code": record["product_code"],
            "payload": record["workflow_input"]["payload"],
        }
    )
    reconciled = list(evidence_result.get("reconciled_fields", []))
    conflicts = list(evidence_result.get("conflicts", []))
    missing = list(evidence_result.get("missing_information", []))
    recommendation = recommend_triage_route(
        {
            "case_id": record["case_id"],
            "evidence": reconciled,
            "conflicts": conflicts,
            "missing_information": missing,
            "risk_signals": product_result.get("risk_signals", []),
            "validations": product_result.get("validations", []),
            "processing_failures": branch_failures(evidence_result),
            "low_confidence": has_low_confidence(reconciled),
        }
    )["recommendation"]
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
    }


# Run every reference case through the pipeline and return produced output.
async def evaluate_cases(split: str | None = None) -> list[dict[str, Any]]:
    records = load_dataset()
    if split:
        records = [record for record in records if record.get("split") == split]
    configurations = load_configurations()
    return [await run_record(record, configurations) for record in records]


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
