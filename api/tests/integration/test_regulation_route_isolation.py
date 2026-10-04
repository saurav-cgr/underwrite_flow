"""Route isolation checks for the informational regulation corpus."""

import asyncio
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from fixtures.regulation import (
    CLAUSE_LINES,
    listed_entry,
    write_document,
    write_manifest,
)
from underwriteflow.evaluation.metrics import evaluate_records
from underwriteflow.evaluation.runner import evaluate_cases
from underwriteflow.products import rules as rules_module
from underwriteflow.workflow import nodes as nodes_module

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Import and activate one synthetic regulation version for a case set.
def activate_regulation(
    client: TestClient, admin: dict[str, str], root: Path
) -> str:
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_manifest(root, [listed_entry(root, "circular.pdf")])
    imported = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert imported.status_code == 201, imported.text
    version_id = imported.json()["id"]
    activated = client.post(
        f"/api/v1/knowledge/versions/{version_id}/activate",
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    return version_id


# Read the routes one evaluation run produces, in dataset order.
def routes(records: list[dict]) -> list[str]:
    return [record["prediction"]["route"] for record in records]


# Verify the whole reference case set routes identically with regulation.
def test_routes_are_identical_with_and_without_regulation(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    # Guidance is enabled so both runs read the knowledge tables.
    without = asyncio.run(evaluate_cases(guidance_enabled=True))

    version_id = activate_regulation(client, admin, root)
    # Prove the second run really had an active regulation corpus.
    with psycopg.connect(DATABASE_URL) as connection:
        clauses = connection.execute(
            "SELECT count(*) FROM knowledge_passages p "
            "JOIN knowledge_versions v ON v.id = p.version_id "
            "WHERE v.id = %s AND v.status = %s",
            (version_id, "active"),
        ).fetchone()[0]
    assert clauses >= 1
    with_regulation = asyncio.run(evaluate_cases(guidance_enabled=True))

    assert len(without) == 90
    assert routes(with_regulation) == routes(without)
    assert evaluate_records(with_regulation)["route_agreement"] == 1.0


# Verify no routing module can reach the regulation loader.
def test_routing_modules_never_import_regulation() -> None:
    workflow_root = Path(nodes_module.__file__).parent
    sources = sorted(workflow_root.glob("*.py")) + [
        Path(rules_module.__file__)
    ]

    assert sources
    for path in sources:
        text = path.read_text()
        assert "knowledge.regulation" not in text, path
        assert "from underwriteflow.knowledge import" not in text, path
