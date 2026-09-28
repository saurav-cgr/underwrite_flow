"""Permission and response contracts for the US2 knowledge API."""

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from fixtures.support import ADMINISTRATOR, APPLICANT, UNDERWRITER, login
from underwriteflow.app import create_app


# Read the shipped synthetic corpus for administrator endpoint checks.
def corpus() -> str:
    path = Path("/app/knowledge-config/life-individual-term/g1.yaml")
    if not path.exists():
        path = Path("knowledge-config/life-individual-term/g1.yaml")
    return path.read_text()


# Verify administrator access and explicit denial for non-administrator roles.
def test_knowledge_permissions_and_preview_limit() -> None:
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        underwriter = login(client, UNDERWRITER)
        validated = client.post(
            "/api/v1/knowledge/validate",
            json={"scope": "guideline", "yaml": corpus()},
            headers=admin,
        )
        assert validated.status_code == 200
        assert validated.json()["valid"] is True
        for headers in (applicant, underwriter):
            denied = client.get(
                "/api/v1/knowledge/versions", headers=headers
            )
            assert denied.status_code == 403


# Verify every administrator endpoint, response shape, and role refusal.
def test_knowledge_admin_lifecycle_contract() -> None:
    version = f"contract-{uuid4().hex[:12]}"
    text = corpus().replace("version: g1", f"version: {version}")
    with TestClient(create_app()) as client:
        admin = login(client, ADMINISTRATOR)
        applicant = login(client, APPLICANT)
        underwriter = login(client, UNDERWRITER)
        payload = {"scope": "guideline", "yaml": text}

        validated = client.post(
            "/api/v1/knowledge/validate", json=payload, headers=admin
        )
        imported = client.post(
            "/api/v1/knowledge/import", json=payload, headers=admin
        )
        assert validated.status_code == 200
        assert validated.json()["valid"] is True
        assert imported.status_code == 201
        version_id = imported.json()["id"]
        assert imported.json()["status"] == "draft"

        listed = client.get("/api/v1/knowledge/versions", headers=admin)
        preview = client.get(
            f"/api/v1/knowledge/versions/{version_id}/preview",
            params={"limit": 100},
            headers=admin,
        )
        offset_page = client.get(
            f"/api/v1/knowledge/versions/{version_id}/preview",
            params={"offset": 2, "limit": 2},
            headers=admin,
        )
        over_limit = client.get(
            f"/api/v1/knowledge/versions/{version_id}/preview",
            params={"limit": 101},
            headers=admin,
        )
        assert listed.status_code == 200
        assert any(item["id"] == version_id for item in listed.json())
        assert preview.status_code == 200
        assert len(preview.json()["passages"]) <= 100
        assert offset_page.status_code == 200
        assert [item["passage_key"] for item in offset_page.json()[
            "passages"
        ]] == [
            "life-age-sixty-one-plus",
            "life-cover-high-sum-assured",
        ]
        assert over_limit.status_code == 422

        activated = client.post(
            f"/api/v1/knowledge/versions/{version_id}/activate",
            headers=admin,
        )
        retired = client.post(
            f"/api/v1/knowledge/versions/{version_id}/retire",
            headers=admin,
        )
        assert activated.status_code == 200
        assert activated.json()["status"] == "active"
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"

        protected = [
            ("post", "/api/v1/knowledge/validate", payload),
            ("post", "/api/v1/knowledge/import", payload),
            ("get", "/api/v1/knowledge/versions", None),
            (
                "get",
                f"/api/v1/knowledge/versions/{version_id}/preview",
                None,
            ),
            (
                "post",
                f"/api/v1/knowledge/versions/{version_id}/activate",
                None,
            ),
            (
                "post",
                f"/api/v1/knowledge/versions/{version_id}/retire",
                None,
            ),
        ]
        for headers in (applicant, underwriter):
            for method, path, body in protected:
                request = {"headers": headers}
                if method == "post":
                    request["json"] = body
                response = getattr(client, method)(path, **request)
                assert response.status_code == 403, (method, path)
