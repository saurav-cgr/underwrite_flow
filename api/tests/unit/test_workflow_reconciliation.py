"""Configured reconciliation inside the parent evidence graph.

The graph cases here prove the join runs configured checks over synthetic
documents and maps provider line locators onto trusted page evidence.
"""

import pytest

from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.graph import build_evidence_graph

NCB_CHECK = {
    "code": "motor_ncb_match",
    "kind": "ncb_match",
    "inputs": {
        "application": "claimed_ncb_percent",
        "previous_policy": "ncb_percent",
    },
}

ASSET_CHECK = {
    "code": "motor_asset_match",
    "kind": "asset_match",
    "inputs": {
        "previous_policy": "registration_number",
        "vehicle_record": "registration_number",
    },
}


# Build page-labelled synthetic documents that carry configured evidence.
def reconciliation_documents(
    policy_lines: list[str],
    vehicle_lines: list[str],
) -> list[dict[str, object]]:
    # Render one document with its trusted page boundary in the content.
    def one(document_id: str, lines: list[str]) -> dict[str, object]:
        text = "\n".join(lines)
        return {
            "document_id": document_id,
            "document_code": document_id,
            "filename": f"{document_id}.pdf",
            "content": f"page:1\n{text}",
            "pages": [
                {
                    "page_number": 1,
                    "text": text,
                    "source_locator": "page:1",
                }
            ],
        }

    return [
        one("previous_policy", policy_lines),
        one("vehicle_record", vehicle_lines),
    ]


# Run one reconciliation-enabled evidence graph over synthetic documents.
async def run_reconciliation_graph(
    documents_input: list[dict[str, object]],
    application: dict[str, object],
) -> dict[str, object]:
    graph = build_evidence_graph(FakeProvider(), retry_count=0)
    return await graph.ainvoke(
        {
            "case_id": "case-reconciliation",
            "documents": documents_input,
            "requested_fields": [
                "claimed_ncb_percent",
                "ncb_percent",
                "registration_number",
            ],
            "field_specifications": [],
            "reference_content": "",
            "application": application,
            "reconciliation_checks": [ASSET_CHECK, NCB_CHECK],
            "rule_version": "v1",
            "results": [],
        }
    )


# Verify the join runs the configured checks and clears agreeing evidence.
@pytest.mark.asyncio
async def test_evidence_graph_reconciles_configured_checks() -> None:
    state = await run_reconciliation_graph(
        reconciliation_documents(
            ["ncb_percent: 20", "registration_number: MH12AB1234"],
            ["registration_number: mh-12-ab-1234"],
        ),
        {"claimed_ncb_percent": 20},
    )

    assert state["reconciliation_status"] == "CLEARED"
    codes = [item["check_code"] for item in state["reconciliation_results"]]
    assert codes == ["motor_asset_match", "motor_ncb_match"]
    assert all(
        item["status"] == "CLEARED"
        for item in state["reconciliation_results"]
    )


# Verify a provider line number becomes a trusted page locator.
@pytest.mark.asyncio
async def test_evidence_graph_maps_evidence_to_trusted_pages() -> None:
    state = await run_reconciliation_graph(
        reconciliation_documents(
            ["ncb_percent: 20", "registration_number: MH12AB1234"],
            ["registration_number: MH12AB1234"],
        ),
        {"claimed_ncb_percent": 20},
    )

    locators = [
        reference["source_locator"]
        for result in state["reconciliation_results"]
        for comparison in result["comparisons"]
        for reference in comparison["evidence"]
    ]
    assert locators == ["page:1", "page:1"]
    assert all(
        field["source_locator"] == "page:1"
        for field in state["reconciled_fields"]
    )


# Verify a configured mismatch raises a flagged discrepancy in graph state.
@pytest.mark.asyncio
async def test_evidence_graph_flags_configured_discrepancy() -> None:
    state = await run_reconciliation_graph(
        reconciliation_documents(
            ["ncb_percent: 20", "registration_number: MH12AB1234"],
            ["registration_number: MH12AB1234"],
        ),
        {"claimed_ncb_percent": 35},
    )

    assert state["reconciliation_status"] == "FLAGGED_DISCREPANCY"
    flagged = next(
        item
        for item in state["reconciliation_results"]
        if item["check_code"] == "motor_ncb_match"
    )
    assert flagged["discrepancies"] == [
        {
            "code": "ncb_mismatch",
            "field_key": "ncb_percent",
            "expected": 35,
            "actual": 20,
        }
    ]


# Verify evidence a configured check cannot read reports missing evidence.
@pytest.mark.asyncio
async def test_evidence_graph_reports_missing_check_evidence() -> None:
    state = await run_reconciliation_graph(
        reconciliation_documents(
            ["registration_number: MH12AB1234"],
            ["registration_number: MH12AB1234"],
        ),
        {"claimed_ncb_percent": 20},
    )

    assert state["reconciliation_status"] == "MISSING_EVIDENCE"
    missing = next(
        item
        for item in state["reconciliation_results"]
        if item["check_code"] == "motor_ncb_match"
    )
    assert missing["status"] == "MISSING_EVIDENCE"
    assert missing["comparisons"] == []
