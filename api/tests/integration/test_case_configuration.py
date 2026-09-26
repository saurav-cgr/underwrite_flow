"""The pinned case configuration an applicant's documents screen needs."""

from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.records import create_user, remove_case, remove_user
from fixtures.records import set_motor_status

from underwriteflow.app import create_app

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

CASE_KEYS = {
    "id",
    "product_code",
    "product_version",
    "rulebook_version",
    "status",
    "journey",
}


# Log in one fictional demo role and return bearer headers.
def login(
    client: TestClient, email: str, password: str
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Create one applicant-owned motor case and return its case id.
def create_case(client: TestClient, headers: dict[str, str], age: int) -> str:
    # An older vehicle makes the inspection photo a required document.
    codes = ["identity_record", "vehicle_record"]
    if age > 12:
        codes.append("inspection_photo")
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": {
                "vehicle_age": age,
                "vehicle_use": "personal",
                "prior_claims": 0,
            },
            "document_codes": codes,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return created.json()["id"]


# Insert one extra synthetic applicant so ownership can be tested.
def create_second_applicant() -> str:
    return str(create_user(display_name="Second Synthetic Applicant"))


# Insert one synthetic motor case owned by the supplied applicant.
def create_owned_case(applicant_user_id: str) -> str:
    case_id = uuid4()
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT product_versions.id, rulebook_versions.id
                FROM product_versions
                JOIN products ON products.id = product_versions.product_id
                JOIN rulebook_versions
                  ON rulebook_versions.product_version_id = product_versions.id
                WHERE products.code = %s
                LIMIT 1
                """,
                ("motor-private-car",),
            )
            product_version_id, rulebook_version_id = cursor.fetchone()
            cursor.execute(
                """
                INSERT INTO cases (
                    id, applicant_user_id, product_version_id,
                    rulebook_version_id, status, workflow_thread_id,
                    idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    applicant_user_id,
                    product_version_id,
                    rulebook_version_id,
                    "new",
                    f"case-{case_id}",
                    f"configuration-{case_id}",
                ),
            )
    return str(case_id)


# Verify the pinned configuration and resolved requirements are returned.
def test_case_configuration_resolves_requirements() -> None:
    set_motor_status("active")
    try:
        with TestClient(create_app()) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            young = create_case(client, applicant, age=2)
            old = create_case(client, applicant, age=14)

            response = client.get(
                f"/api/v1/cases/{young}/configuration", headers=applicant
            )
            assert response.status_code == 200, response.text
            pack = response.json()
            assert pack["case_id"] == young
            assert pack["product_code"] == "motor-private-car"
            assert pack["product_version"] == "v1"
            assert pack["rulebook_version"]
            assert "routing_rules" not in pack

            assert [field["key"] for field in pack["fields"]] == [
                "vehicle_age",
                "vehicle_use",
                "prior_claims",
                "policy_start_date",
            ]
            assert all(field["help_text"] for field in pack["fields"])

            requirements = {
                document["code"]: document for document in pack["documents"]
            }
            assert requirements["identity_record"]["required"] is True
            assert requirements["identity_record"]["accepted_types"] == [
                "application/pdf",
                "image/jpeg",
                "image/png",
            ]
            assert requirements["inspection_photo"]["required"] is False

            conditional = client.get(
                f"/api/v1/cases/{old}/configuration", headers=applicant
            )
            assert conditional.status_code == 200, conditional.text
            resolved = {
                document["code"]: document["required"]
                for document in conditional.json()["documents"]
            }
            assert resolved["inspection_photo"] is True
    finally:
        set_motor_status("draft")


# Remove the synthetic ownership fixtures so demo accounts stay intact.
def remove_case_and_applicant(case_id: str, applicant_user_id: str) -> None:
    if not case_id or not applicant_user_id:
        return
    remove_case(UUID(case_id))
    remove_user(UUID(applicant_user_id))


# Verify one applicant cannot read another applicant's pinned configuration.
def test_case_configuration_rejects_another_applicant() -> None:
    set_motor_status("active")
    applicant_id = ""
    other_case = ""
    try:
        applicant_id = create_second_applicant()
        other_case = create_owned_case(applicant_id)
        with TestClient(create_app()) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            response = client.get(
                f"/api/v1/cases/{other_case}/configuration",
                headers=applicant,
            )
            assert response.status_code == 403, response.text
    finally:
        remove_case_and_applicant(other_case, applicant_id)
        set_motor_status("draft")


# Verify a case keeps its pinned version once its product is deactivated.
def test_case_configuration_survives_an_inactive_catalogue() -> None:
    set_motor_status("active")
    try:
        with TestClient(create_app()) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            case_id = create_case(client, applicant, age=2)

        set_motor_status("draft")

        with TestClient(create_app()) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            catalogue = client.get(
                "/api/v1/products/catalog", headers=applicant
            )
            assert catalogue.status_code == 200, catalogue.text
            offered = {
                entry["product_code"] for entry in catalogue.json()
            }
            assert "motor-private-car" not in offered

            response = client.get(
                f"/api/v1/cases/{case_id}/configuration", headers=applicant
            )
            assert response.status_code == 200, response.text
            assert [item["code"] for item in response.json()["documents"]] == [
                "identity_record",
                "vehicle_record",
                "inspection_photo",
            ]
    finally:
        set_motor_status("draft")


# Verify the case listing stays compact and free of configuration payloads.
def test_case_listing_stays_compact() -> None:
    set_motor_status("active")
    try:
        with TestClient(create_app()) as client:
            applicant = login(
                client,
                "applicant@synthetic.test",
                "underwriteflow-demo-applicant",
            )
            case_id = create_case(client, applicant, age=2)

            listing = client.get("/api/v1/cases", headers=applicant)
            assert listing.status_code == 200, listing.text
            entry = next(
                item
                for item in listing.json()
                if item["id"] == case_id
            )
            assert set(entry) == CASE_KEYS
    finally:
        set_motor_status("draft")
