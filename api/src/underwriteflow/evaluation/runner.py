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
from underwriteflow.workflow.product_subgraphs import select_product_subgraph
from underwriteflow.workflow.triage import recommend_triage_route


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


# Run one synthetic case through its selected product subgraph and triage node.
async def run_record(
    record: dict[str, Any], configurations: dict[str, Any]
) -> dict[str, Any]:
    workflow_input = record["workflow_input"]
    graph = select_product_subgraph(record["product_code"], configurations)
    product_result = await graph.ainvoke(
        {
            "product_code": record["product_code"],
            "payload": workflow_input["payload"],
        }
    )
    state = {
        "case_id": record["case_id"],
        "evidence": workflow_input["evidence"],
        "conflicts": workflow_input["conflicts"],
        "missing_information": workflow_input["missing_information"],
        "risk_signals": product_result["risk_signals"],
        "validations": product_result["validations"],
    }
    recommendation = recommend_triage_route(state)["recommendation"]
    return {
        **record,
        "prediction": {
            "route": recommendation["route"],
            "evidence": [item["code"] for item in workflow_input["evidence"]],
            "conflict": bool(workflow_input["conflicts"]),
            "missing": bool(workflow_input["missing_information"]),
            "unsupported_claims": 0,
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
