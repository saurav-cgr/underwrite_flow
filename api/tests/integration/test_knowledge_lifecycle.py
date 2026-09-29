"""Administrator lifecycle coverage for fictional guideline versions."""

import asyncio
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from fixtures.support import ADMINISTRATOR, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings
from underwriteflow.database import Database
from underwriteflow.knowledge.service import KnowledgeService


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)
ASYNC_DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Read the shipped synthetic corpus and give it a unique immutable version.
def corpus(version: str, aligned: str = "v3") -> str:
    path = Path("/app/knowledge-config/life-individual-term/g1.yaml")
    if not path.exists():
        path = Path("knowledge-config/life-individual-term/g1.yaml")
    return (
        path.read_text()
        .replace("version: g1", f"version: {version}")
        .replace(
            "aligned_product_version: v3",
            f"aligned_product_version: {aligned}",
        )
    )


# Import one corpus through the public administrator endpoint.
def import_version(client: TestClient, headers: dict[str, str], text: str):
    response = client.post(
        "/api/v1/knowledge/import",
        json={"scope": "guideline", "yaml": text},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# Verify import, preview, invalid activation, and activation replacement.
def test_guideline_lifecycle() -> None:
    first = f"test-{uuid4().hex[:12]}"
    second = f"test-{uuid4().hex[:12]}"
    with TestClient(create_app()) as client:
        headers = login(client, ADMINISTRATOR)
        active = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=headers,
        )
        assert active.status_code == 200, active.text
        first_result = import_version(client, headers, corpus(first))
        assert first_result["status"] == "draft"
        assert first_result["passage_count"] == 12
        preview = client.get(
            f"/api/v1/knowledge/versions/{first_result['id']}/preview",
            headers=headers,
        )
        assert preview.status_code == 200
        assert preview.json()["passages"][0]["label"] == (
            "SYNTHETIC - FOR DEMONSTRATION ONLY"
        )
        invalid = import_version(
            client,
            headers,
            corpus(f"{first}-invalid", aligned="v2"),
        )
        refused = client.post(
            f"/api/v1/knowledge/versions/{invalid['id']}/activate",
            headers=headers,
        )
        assert refused.status_code == 422
        second_result = import_version(client, headers, corpus(second))
        first_active = client.post(
            f"/api/v1/knowledge/versions/{first_result['id']}/activate",
            headers=headers,
        )
        second_active = client.post(
            f"/api/v1/knowledge/versions/{second_result['id']}/activate",
            headers=headers,
        )
        repeated_active = client.post(
            f"/api/v1/knowledge/versions/{second_result['id']}/activate",
            headers=headers,
        )
        same_content = import_version(client, headers, corpus(first))
        conflict_text = corpus(first).replace(
            "High requested cover", "Changed requested cover"
        )
        conflict = client.post(
            "/api/v1/knowledge/import",
            json={"scope": "guideline", "yaml": conflict_text},
            headers=headers,
        )
    assert first_active.status_code == 200, first_active.text
    assert second_active.status_code == 200, second_active.text
    assert repeated_active.status_code == 200, repeated_active.text
    assert same_content["id"] == first_result["id"]
    assert conflict.status_code == 409, conflict.text

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, details FROM audit_events "
                "WHERE event_type = %s AND details ->> 'product_code' = %s "
                "AND details ->> 'version' IN (%s, %s) "
                "ORDER BY occurred_at, id",
                (
                    "knowledge_version_activated",
                    "life-individual-term",
                    first,
                    second,
                ),
            )
            events = cursor.fetchall()
    assert len(events) == 2
    assert events[1][1]["previous_version"] == first
    assert events[1][1]["supersedes_event_id"] == str(events[0][0])


# Verify validation aligns against named inactive product versions.
def test_validation_uses_named_product_version() -> None:
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        activated = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=admin,
        )
        assert activated.status_code == 200, activated.text
        validated = client.post(
            "/api/v1/knowledge/validate",
            json={
                "scope": "guideline",
                "yaml": corpus(
                    f"named-{uuid4().hex[:12]}", aligned="v2"
                ),
            },
            headers=admin,
        )
    assert validated.status_code == 200, validated.text
    assert validated.json()["valid"] is True


# Run one import in an isolated transaction for concurrency coverage.
async def concurrent_import(text: str, actor_id):
    database = Database(ASYNC_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            try:
                await KnowledgeService().import_guideline(
                    session, text, actor_id
                )
            except Exception as error:
                return type(error).__name__
            return "ok"
    finally:
        await database.close()


# Run one activation in an isolated transaction for concurrency coverage.
async def concurrent_activation(version_id: str, actor_id):
    database = Database(ASYNC_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            try:
                await KnowledgeService().activate(
                    session, version_id, actor_id
                )
            except Exception as error:
                return type(error).__name__
            return "ok"
    finally:
        await database.close()


# Await two isolated operations in one event loop.
async def gather_pair(left, right):
    return await asyncio.gather(left, right)


# Verify unique lifecycle races return domain conflicts, not DB errors.
def test_concurrent_lifecycle_conflicts_are_safe() -> None:
    first = f"race-{uuid4().hex[:12]}"
    second = f"race-{uuid4().hex[:12]}"
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        headers = login(client, ADMINISTRATOR)
        first_result = import_version(client, headers, corpus(first))
        second_result = import_version(client, headers, corpus(second))

    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE role = %s LIMIT 1",
                ("Administrator",),
            )
            actor_id = cursor.fetchone()[0]

    same_text = corpus(f"same-{uuid4().hex[:12]}")
    import_results = asyncio.run(
        gather_pair(
            concurrent_import(same_text, actor_id),
            concurrent_import(same_text, actor_id),
        )
    )
    assert "IntegrityError" not in import_results

    activation_results = asyncio.run(
        gather_pair(
            concurrent_activation(first_result["id"], actor_id),
            concurrent_activation(second_result["id"], actor_id),
        )
    )
    assert sorted(activation_results) == [
        "KnowledgeConflictError",
        "ok",
    ]
