"""Make shared fixtures importable and restore test-mutated demo state.

Pytest adds a collected module's own directory to the import path, so a test
in `tests/integration` cannot reach `tests/fixtures` on its own. Loading this
conftest at the tests root puts that root on the path once, for every suite,
instead of each suite inserting paths for itself.
"""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from fixtures.records import motor_status, set_motor_status
from fixtures.support import ADMINISTRATOR, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings

KNOWLEDGE_DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Put product activation back the way the run found it, so a test that
# activates a product cannot leave the developer's demo stack with an empty
# applicant catalogue.
@pytest.fixture(scope="session", autouse=True)
def restore_product_status():
    try:
        found = motor_status()
    except Exception:
        # A suite that never reaches the database must not require it here.
        yield
        return
    yield
    set_motor_status(found)


# Restore every life guideline field that test activation mutates.
@pytest.fixture(scope="session", autouse=True)
def restore_life_guideline_status() -> object:
    try:
        with psycopg.connect(KNOWLEDGE_DATABASE_URL) as connection:
            prior = connection.execute(
                "SELECT k.id, k.status, k.activated_at FROM "
                "knowledge_versions k JOIN products p ON p.id = k.product_id "
                "WHERE k.scope = %s AND p.code = %s",
                ("guideline", "life-individual-term"),
            ).fetchall()
    except Exception:
        yield
        return
    yield
    with psycopg.connect(KNOWLEDGE_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE knowledge_versions SET status = %s "
            "WHERE product_id = (SELECT id FROM products WHERE code = %s) "
            "AND scope = %s",
            ("draft", "life-individual-term", "guideline"),
        )
        for version_id, status, activated_at in prior:
            connection.execute(
                "UPDATE knowledge_versions SET status = %s, activated_at = %s "
                "WHERE id = %s",
                (status, activated_at, version_id),
            )
        connection.commit()
        restored = connection.execute(
            "SELECT k.id, k.status, k.activated_at FROM knowledge_versions k "
            "JOIN products p ON p.id = k.product_id WHERE k.scope = %s "
            "AND p.code = %s",
            ("guideline", "life-individual-term"),
        ).fetchall()
    prior_by_id = {row[0]: row[1:] for row in prior}
    restored_by_id = {
        row[0]: row[1:] for row in restored if row[0] in prior_by_id
    }
    assert restored_by_id == prior_by_id


# Restore every regulation status a test mutates.
@pytest.fixture
def regulation_rollback() -> Iterator[None]:
    with psycopg.connect(KNOWLEDGE_DATABASE_URL) as connection:
        prior = connection.execute(
            "SELECT id, status, activated_at FROM knowledge_versions "
            "WHERE scope = %s",
            ("regulation",),
        ).fetchall()
    yield
    with psycopg.connect(KNOWLEDGE_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE knowledge_versions SET status = %s, activated_at = NULL "
            "WHERE scope = %s",
            ("draft", "regulation"),
        )
        for version_id, status, activated_at in prior:
            connection.execute(
                "UPDATE knowledge_versions SET status = %s, "
                "activated_at = %s WHERE id = %s",
                (status, activated_at, version_id),
            )
        connection.commit()
        restored = connection.execute(
            "SELECT id, status, activated_at FROM knowledge_versions "
            "WHERE scope = %s",
            ("regulation",),
        ).fetchall()
    prior_by_id = {row[0]: row[1:] for row in prior}
    restored_by_id = {
        row[0]: row[1:] for row in restored if row[0] in prior_by_id
    }
    assert restored_by_id == prior_by_id


# Build one administrator client whose regulation root is disposable.
@pytest.fixture
def regulation_client(
    tmp_path: Path, regulation_rollback: None
) -> Iterator[tuple[TestClient, dict[str, str], Path]]:
    settings = Settings(regulatory_root=str(tmp_path))
    with TestClient(create_app(settings)) as client:
        yield client, login(client, ADMINISTRATOR), tmp_path
