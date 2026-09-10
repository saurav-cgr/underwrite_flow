import psycopg


# Verify Compose bootstrap imports all three fictional product versions.
def test_bootstrap_imports_builtin_products() -> None:
    connection = psycopg.connect(
        "postgresql://underwriteflow:synthetic-local-password@db:5432/underwriteflow"
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
