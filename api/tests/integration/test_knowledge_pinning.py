"""Case-start pinning coverage for the versioned knowledge store."""

import asyncio
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlalchemy import select

from fixtures.records import remove_case
from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from fixtures.synthetic_pdf import blank_pdf
from underwriteflow.database import Database
from underwriteflow.knowledge.pins import pin_case_knowledge
from underwriteflow.persistence.models import Case
from underwriteflow.app import create_app
from underwriteflow.config import Settings


DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)


# Load the mounted life corpus under one unique immutable version identity.
def life_corpus(version: str) -> str:
    path = Path("knowledge-config/life-individual-term/g1.yaml")
    return path.read_text().replace("version: g1", f"version: {version}")


# Import one life guideline through the administrator API.
def import_guideline(
    client: TestClient, headers: dict[str, str], version: str
) -> str:
    response = client.post(
        "/api/v1/knowledge/import",
        json={"scope": "guideline", "yaml": life_corpus(version)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


# Activate one imported guideline through the administrator API.
def activate_guideline(
    client: TestClient, headers: dict[str, str], version_id: str
) -> None:
    response = client.post(
        f"/api/v1/knowledge/versions/{version_id}/activate",
        headers=headers,
    )
    assert response.status_code == 200, response.text


# Create a life case with its required synthetic identity document.
def create_life_case(
    client: TestClient, headers: dict[str, str]
) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "life-individual-term",
            "idempotency_key": str(uuid4()),
            "payload": {
                "requested_cover": 1000000,
                "date_of_birth": "1990-01-01",
                "occupation_type": "office",
                "health_declaration": True,
            },
            "document_codes": ["identity_record"],
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    case_id = str(created.json()["id"])
    uploaded = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={
            "document": ("synthetic.pdf", blank_pdf(), "application/pdf")
        },
        data={"document_code": "identity_record"},
        headers=headers,
    )
    assert uploaded.status_code == 200, uploaded.text
    return case_id


# Read each case pin and its single pin audit-event count.
def read_pins(case_ids: list[str]) -> list[tuple[str | None, int]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            result = []
            for case_id in case_ids:
                cursor.execute(
                    "SELECT guideline_version_id FROM case_knowledge_pins "
                    "WHERE case_id = %s",
                    (case_id,),
                )
                pin = cursor.fetchone()
                cursor.execute(
                    "SELECT count(*) FROM audit_events WHERE case_id = %s "
                    "AND event_type = %s",
                    (case_id, "case_guidance_pinned"),
                )
                result.append((str(pin[0]) if pin and pin[0] else None,
                               cursor.fetchone()[0]))
            return result


# Invoke pinning twice through its real async persistence boundary.
async def pin_twice(case_id: str) -> None:
    database = Database(
        "postgresql+asyncpg://underwriteflow:synthetic-local-password"
        "@db:5433/underwriteflow"
    )
    try:
        async with database.session_factory() as session:
            case = await session.scalar(
                select(Case).where(Case.id == case_id)
            )
            assert case is not None
            await pin_case_knowledge(session, case, case.applicant_user_id)
            await pin_case_knowledge(session, case, case.applicant_user_id)
            await session.commit()
    finally:
        await database.close()


# Verify processing writes one insert-once pin and audit event.
def test_case_processing_creates_one_knowledge_pin() -> None:
    case_id = str(uuid4())
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE role = %s LIMIT 1",
                ("Applicant",),
            )
            applicant_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT v.id, r.id FROM product_versions v "
                "JOIN products p ON p.id = v.product_id "
                "JOIN rulebook_versions r ON r.product_version_id = v.id "
                "WHERE p.code = %s LIMIT 1",
                ("motor-private-car",),
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            cursor.execute(
                "INSERT INTO cases (id, applicant_user_id, "
                "product_version_id, rulebook_version_id, status, "
                "workflow_thread_id, idempotency_key) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s)",
                (
                    case_id,
                    applicant_id,
                    product_version_id,
                    rulebook_version_id,
                    "new",
                    f"case-{case_id}",
                    f"knowledge-pin-{case_id}",
                ),
            )
    asyncio.run(pin_twice(case_id))
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT guideline_version_id, regulation_version_id "
                "FROM case_knowledge_pins WHERE case_id = %s",
                (case_id,),
            )
            pin = cursor.fetchone()
            cursor.execute(
                "SELECT COUNT(*) FROM audit_events "
                "WHERE case_id = %s AND event_type = %s",
                (case_id, "case_guidance_pinned"),
            )
            audit_count = cursor.fetchone()[0]
    assert pin == (None, None)
    assert audit_count == 1
    remove_case(case_id)


# Verify public submission pins g1, preserves it through resubmission, and
# pins g2 for a new case after g2 activation.
def test_submission_pins_guideline_version_once() -> None:
    case_ids: list[str] = []
    first_version = f"pin-g1-{uuid4().hex[:8]}"
    second_version = f"pin-g2-{uuid4().hex[:8]}"
    with TestClient(create_app(Settings(generation_provider="fake"))) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        underwriter = login(client, UNDERWRITER)
        product = client.post(
            "/api/v1/products/life-individual-term/activate",
            json={"version": "v3"},
            headers=admin,
        )
        assert product.status_code == 200, product.text
        first_guideline = import_guideline(client, admin, first_version)
        activate_guideline(client, admin, first_guideline)

        first_case = create_life_case(client, applicant)
        case_ids.append(first_case)
        submitted = client.post(
            f"/api/v1/cases/{first_case}/submit", headers=applicant
        )
        assert submitted.status_code == 200, submitted.text
        requested = client.post(
            f"/api/v1/reviews/{first_case}",
            headers=underwriter,
            json={
                "action": "request_information",
                "reason": "Synthetic evidence request",
                "evidence_acknowledged": True,
            },
        )
        assert requested.status_code == 200, requested.text

        second_guideline = import_guideline(client, admin, second_version)
        activate_guideline(client, admin, second_guideline)
        resubmitted = client.post(
            f"/api/v1/cases/{first_case}/resubmit", headers=applicant
        )
        assert resubmitted.status_code == 200, resubmitted.text

        second_case = create_life_case(client, applicant)
        case_ids.append(second_case)
        submitted = client.post(
            f"/api/v1/cases/{second_case}/submit", headers=applicant
        )
        assert submitted.status_code == 200, submitted.text

    assert read_pins(case_ids) == [
        (first_guideline, 1),
        (second_guideline, 1),
    ]
    for case_id in case_ids:
        remove_case(case_id)
