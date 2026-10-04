"""Stored guidance endpoint latency regression."""

import time
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from fixtures.records import remove_case, seed_case
from fixtures.support import UNDERWRITER, login
from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Verify five stored guidance reads stay below the three-second screen budget.
def test_stored_guidance_reads_under_three_seconds() -> None:
    case_id = uuid4()
    seed_case(case_id)
    try:
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO case_guidance "
                    "(id, case_id, review_cycle, kind, status, body, "
                    "citations) VALUES (gen_random_uuid(), %s, %s, %s, %s, "
                    "%s, %s)",
                    (
                        case_id,
                        0,
                        "route_explanation",
                        "generated",
                        '{"text":"Stored synthetic guidance.",'
                        '"missing_items":[]}',
                        '[{"version":"g1",'
                        '"passage_key":"synthetic-section"}]',
                    ),
                )
        settings = Settings(generation_provider="fake")
        with TestClient(create_app(settings)) as client:
            headers = login(client, UNDERWRITER)
            started = time.perf_counter()
            responses = [
                client.get(
                    f"/api/v1/reviews/{case_id}/guidance",
                    headers=headers,
                )
                for _ in range(5)
            ]
            elapsed = time.perf_counter() - started
        assert all(response.status_code == 200 for response in responses)
        assert elapsed < 3
    finally:
        remove_case(case_id)
