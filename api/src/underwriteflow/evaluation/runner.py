"""Command-line runner for the synthetic evaluation reference set."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from underwriteflow.evaluation.dataset import load_dataset
from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.tracing import trace_summary
from underwriteflow.products.service import load_configuration
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.product_subgraphs import select_product_subgraph
from underwriteflow.workflow.triage import recommend_triage_route

LOW_CONFIDENCE = 0.8


# Locate mounted product configurations or their source-checkout fallback.
def product_config_root() -> Path:
    mounted_path = Path("/app/product-config")
    if mounted_path.exists():
        return mounted_path
    return Path(__file__).resolve().parents[4] / "product-config"


# Load the fictional configurations used by deterministic product subgraphs.
def load_configurations() -> dict[str, Any]:
    return {
        configuration.product_code: configuration
        for path in product_config_root().glob("*.yaml")
        if (configuration := load_configuration(path.read_text()))
    }


# Read the documents a reference case supplies as evidence input.
def document_inputs(record: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "document_id": document["document_id"],
            "filename": document["filename"],
            "content": "\n".join(document["lines"]),
        }
        for document in record["documents"]
    ]


# Run one synthetic case through extraction, reconciliation, and routing.
async def run_record(
    record: dict[str, Any], configurations: dict[str, Any]
) -> dict[str, Any]:
    configuration = configurations[record["product_code"]]
    evidence_result = await build_evidence_graph(
        FakeProvider(), retry_count=0
    ).ainvoke(
        {
            "case_id": record["case_id"],
            "documents": document_inputs(record),
            "requested_fields": [field.key for field in configuration.fields],
            "reference_content": "",
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
            "low_confidence": any(
                (item.get("confidence") or 1.0) < LOW_CONFIDENCE
                for item in reconciled
            ),
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


# Evaluate one requested split and optionally emit a redacted trace.
async def run_evaluation(
    split: str | None = None, trace: bool = False
) -> dict[str, Any]:
    records = load_dataset()
    if split:
        records = [record for record in records if record.get("split") == split]
    configurations = load_configurations()
    evaluated = [await run_record(record, configurations) for record in records]
    summary = evaluate_records(evaluated)
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
