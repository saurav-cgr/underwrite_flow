"""Integration coverage for checksum-verified regulation import."""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from sqlalchemy import select

from fixtures.regulation import (
    CLAUSE_LINES,
    entry_for_bytes,
    listed_entry,
    write_document,
    write_manifest,
)
from fixtures.synthetic_pdf import blank_pdf, text_pdf
from fixtures.support import APPLICANT, login
from underwriteflow.database import Database
from underwriteflow.knowledge.pins import pin_case_knowledge
from underwriteflow.persistence.models import Case

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)
ASYNC_DATABASE_URL = (
    "postgresql+asyncpg://underwriteflow:synthetic-local-password"
    "@db:5433/underwriteflow"
)


# Read one audit-event count for the rejected-file event.
def rejected_events() -> int:
    with psycopg.connect(DATABASE_URL) as connection:
        return connection.execute(
            "SELECT count(*) FROM audit_events WHERE event_type = %s",
            ("regulation_file_rejected",),
        ).fetchone()[0]


# Verify a folder import makes one draft and reports every file outcome.
def test_folder_import_creates_draft_and_reports_files(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_document(root, "altered.pdf", CLAUSE_LINES)
    (root / "insurance_act_1938.doc").write_bytes(b"synthetic act")
    write_manifest(
        root,
        [
            listed_entry(root, "circular.pdf"),
            listed_entry(root, "altered.pdf", sha256="0" * 64),
            listed_entry(root, "insurance_act_1938.doc"),
            {
                "id": "absent",
                "file": "absent.pdf",
                "title": "Absent circular",
                "issuer": "IRDAI",
                "date": "2024-05-29",
                "product_lines": ["life"],
                "sha256": "1" * 64,
            },
        ],
    )
    before = rejected_events()

    response = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scope"] == "regulation"
    assert body["status"] == "draft"
    assert body["content_type"] == "public_regulation"
    assert body["passage_count"] == 2
    reasons = {
        item["file"]: (item["status"], item["reason"])
        for item in body["files"]
    }
    assert reasons["circular.pdf"] == ("loaded", None)
    assert reasons["altered.pdf"] == ("rejected", "checksum_mismatch")
    assert reasons["insurance_act_1938.doc"] == (
        "reported",
        "unsupported_format",
    )
    assert reasons["absent.pdf"] == ("reported", "missing_file")
    assert rejected_events() == before + 1
    with psycopg.connect(DATABASE_URL) as connection:
        stored = connection.execute(
            "SELECT p.label, p.suggested_tags, p.source_locator "
            "FROM knowledge_passages p JOIN knowledge_versions v "
            "ON v.id = p.version_id WHERE v.id = %s "
            "ORDER BY p.passage_key",
            (body["id"],),
        ).fetchall()
    assert [row[0] for row in stored] == [
        "PUBLIC REGULATION - INFORMATIONAL",
        "PUBLIC REGULATION - INFORMATIONAL",
    ]
    assert stored[0][1] == ["cover-amount", "policyholder-protection"]
    assert stored[0][2] == "circular#page:1"


# Verify an approved upload is stored under the manifest file name.
def test_approved_upload_is_stored_and_loaded(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    content = text_pdf(CLAUSE_LINES)
    write_manifest(root, [entry_for_bytes("circular.pdf", content)])

    response = client.post(
        "/api/v1/knowledge/regulation/import",
        files={"file": ("upload.pdf", content, "application/pdf")},
        headers=admin,
    )

    assert response.status_code == 201, response.text
    assert response.json()["passage_count"] == 2
    assert (root / "circular.pdf").read_bytes() == content
    assert not list(root.glob("*.part"))


# Verify an approved upload joins a newer version on the next import.
def test_upload_after_first_import_reaches_a_version(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "early.pdf", CLAUSE_LINES)
    late = text_pdf(["1. Late clause\nLate clause body."])
    write_manifest(
        root,
        [
            listed_entry(root, "early.pdf"),
            entry_for_bytes("late.pdf", late),
        ],
    )
    first = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["passage_count"] == 2
    assert [item["status"] for item in first_body["files"]] == [
        "loaded",
        "reported",
    ]

    uploaded = client.post(
        "/api/v1/knowledge/regulation/import",
        files={"file": ("late.pdf", late, "application/pdf")},
        headers=admin,
    )
    assert uploaded.status_code == 201, uploaded.text
    uploaded_body = uploaded.json()
    again = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert again.status_code == 201, again.text
    again_body = again.json()

    assert uploaded_body["id"] != first_body["id"]
    assert uploaded_body["passage_count"] == 3
    assert again_body["id"] == uploaded_body["id"]
    assert again_body["passage_count"] == 3
    assert [item["status"] for item in again_body["files"]] == [
        "loaded",
        "loaded",
    ]


# Verify a manifest-only edit still produces a new version.
def test_manifest_product_lines_change_creates_new_version(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_manifest(
        root,
        [listed_entry(root, "circular.pdf", product_lines=["motor"])],
    )
    first = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert first.status_code == 201, first.text
    first_body = first.json()

    write_manifest(
        root,
        [listed_entry(root, "circular.pdf", product_lines=["life"])],
    )
    second = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )

    assert second.status_code == 201, second.text
    second_body = second.json()
    assert second_body["id"] != first_body["id"]
    with psycopg.connect(DATABASE_URL) as connection:
        stored = connection.execute(
            "SELECT product_lines FROM knowledge_passages "
            "WHERE version_id = %s ORDER BY passage_key LIMIT 1",
            (second_body["id"],),
        ).fetchone()
    assert stored[0] == ["life"]


# Verify an upload that matches no manifest entry writes nothing.
def test_unlisted_upload_is_rejected_and_audited(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_manifest(root, [listed_entry(root, "circular.pdf")])
    before = rejected_events()

    response = client.post(
        "/api/v1/knowledge/regulation/import",
        files={"file": ("other.pdf", blank_pdf(), "application/pdf")},
        headers=admin,
    )

    assert response.status_code == 422, response.text
    assert not (root / "other.pdf").exists()
    assert not list(root.glob("*.part"))
    assert rejected_events() == before + 1


# Verify an altered upload is rejected against its manifest checksum.
def test_altered_upload_is_rejected(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_manifest(
        root,
        [listed_entry(root, "circular.pdf", sha256="2" * 64)],
    )
    before = rejected_events()

    response = client.post(
        "/api/v1/knowledge/regulation/import",
        files={
            "file": (
                "circular.pdf",
                (root / "circular.pdf").read_bytes(),
                "application/pdf",
            )
        },
        headers=admin,
    )

    assert response.status_code == 422, response.text
    assert rejected_events() == before + 1


# Verify tags are accepted on drafts only and audited once.
def test_tag_acceptance_requires_a_draft(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
    write_document(root, "circular.pdf", CLAUSE_LINES)
    write_manifest(root, [listed_entry(root, "circular.pdf")])
    imported = client.post(
        "/api/v1/knowledge/regulation/import", headers=admin
    )
    assert imported.status_code == 201, imported.text
    version_id = imported.json()["id"]
    path = (
        f"/api/v1/knowledge/versions/{version_id}/passages/"
        "circular%231/tags"
    )

    unknown = client.put(
        path,
        json={"topic_tags": ["not-a-tag"], "limits": []},
        headers=admin,
    )
    accepted = client.put(
        path,
        json={
            "topic_tags": ["claim-settlement"],
            "limits": [
                {
                    "field": "requested_cover",
                    "operator": "greater_than",
                    "value": 0,
                }
            ],
        },
        headers=admin,
    )

    assert unknown.status_code == 422, unknown.text
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["topic_tags"] == ["claim-settlement"]
    assert accepted.json()["limits"][0]["field"] == "requested_cover"
    # A tag-only accept keeps the limits accepted earlier.
    retagged = client.put(
        path,
        json={"topic_tags": ["claim-settlement", "renewal"]},
        headers=admin,
    )
    assert retagged.status_code == 200, retagged.text
    assert retagged.json()["limits"][0]["field"] == "requested_cover"
    activated = client.post(
        f"/api/v1/knowledge/versions/{version_id}/activate",
        headers=admin,
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    later = client.put(
        path, json={"topic_tags": [], "limits": []}, headers=admin
    )
    assert later.status_code == 409, later.text


# Pin one case through the service boundary and read both stored pins.
async def pin_case(case_id: UUID) -> tuple[str | None, str | None]:
    database = Database(ASYNC_DATABASE_URL)
    try:
        async with database.session_factory() as session:
            case = await session.scalar(
                select(Case).where(Case.id == case_id)
            )
            assert case is not None
            await pin_case_knowledge(
                session, case, case.applicant_user_id
            )
            await session.commit()
    finally:
        await database.close()
    with psycopg.connect(DATABASE_URL) as connection:
        row = connection.execute(
            "SELECT guideline_version_id, regulation_version_id "
            "FROM case_knowledge_pins WHERE case_id = %s",
            (case_id,),
        ).fetchone()
    return (
        str(row[0]) if row and row[0] else None,
        str(row[1]) if row and row[1] else None,
    )


# Verify an active regulation version is pinned when a case starts.
def test_active_regulation_is_pinned_to_a_new_case(
    regulation_client: tuple[TestClient, dict[str, str], Path],
) -> None:
    client, admin, root = regulation_client
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
    applicant = login(client, APPLICANT)
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
            "document_codes": [],
        },
        headers=applicant,
    )
    assert created.status_code == 200, created.text
    case_id = UUID(created.json()["id"])

    _, regulation_pin = asyncio.run(pin_case(case_id))

    assert regulation_pin == version_id
