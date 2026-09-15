import psycopg
from fastapi.testclient import TestClient

from underwriteflow.app import create_app


# Verify Compose bootstrap imports all three fictional product versions.
def test_bootstrap_imports_builtin_products() -> None:
    connection = psycopg.connect(
        "postgresql://underwriteflow:synthetic-local-password@"
        "db:5433/underwriteflow"
    )
    with connection, connection.cursor() as cursor:
        cursor.execute("SELECT code FROM products ORDER BY code")
        products = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) FROM product_versions WHERE status = 'draft'")
        draft_count = cursor.fetchone()[0]

    assert products == [
        "health-individual-family-floater",
        "life-individual-term",
        "motor-private-car",
    ]
    assert draft_count == 3


# Verify the additive migration inserts all fictional demo identities.
def test_migration_inserts_demo_accounts() -> None:
    connection = psycopg.connect(
        "postgresql://underwriteflow:synthetic-local-password@"
        "db:5433/underwriteflow"
    )
    with connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT email, role, is_active FROM users "
            "WHERE email LIKE %s ORDER BY email",
            ("%synthetic.test",),
        )
        accounts = cursor.fetchall()

    assert accounts == [
        ("administrator@synthetic.test", "Administrator", True),
        ("applicant@synthetic.test", "Applicant", True),
        ("underwriter@synthetic.test", "Underwriter", True),
    ]


# Verify only administrators can browse all configured product versions.
def test_administrator_can_list_products_for_configuration() -> None:
    with TestClient(create_app()) as client:
        admin_login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "administrator@synthetic.test",
                "password": "underwriteflow-demo-administrator",
            },
        )
        applicant_login = client.post(
            "/api/v1/auth/session",
            json={
                "email": "applicant@synthetic.test",
                "password": "underwriteflow-demo-applicant",
            },
        )
        admin_response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {admin_login.json()['token']}"},
        )
        applicant_response = client.get(
            "/api/v1/products",
            headers={
                "Authorization": f"Bearer {applicant_login.json()['token']}"
            },
        )

    assert admin_login.status_code == 200
    assert applicant_login.status_code == 200
    assert admin_response.status_code == 200
    assert [item["product_code"] for item in admin_response.json()] == [
        "health-individual-family-floater",
        "life-individual-term",
        "motor-private-car",
    ]
    assert applicant_response.status_code == 403
