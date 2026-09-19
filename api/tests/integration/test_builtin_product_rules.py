"""Pinned parameters in additive fictional product configuration versions."""

import psycopg

from fixtures.records import DATABASE_URL


# Verify every additive v2 product pins its applicable renewal and NCB rules.
def test_builtin_v2_products_pin_reconciliation_parameters() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT products.code, product_versions.configuration "
                "FROM product_versions JOIN products ON products.id = "
                "product_versions.product_id WHERE product_versions.version "
                "= 'v2' ORDER BY products.code"
            )
            configurations = dict(cursor.fetchall())

    assert set(configurations) == {
        "health-individual-family-floater",
        "life-individual-term",
        "motor-private-car",
    }
    for configuration in configurations.values():
        renewal = next(
            check
            for check in configuration["reconciliations"]
            if check["kind"] == "policy_lapse"
        )
        assert renewal["parameters"] == {
            "maximum_gap_days": 30,
            "boundary": "inclusive",
        }
    motor = configurations["motor-private-car"]
    ncb = next(
        check
        for check in motor["reconciliations"]
        if check["kind"] == "ncb_match"
    )
    assert ncb["parameters"] == {
        "tiers": [0, 20, 25, 35, 45, 50],
        "claim_count_field": "prior_claims",
        "claims_reset_threshold": 1,
        "claims_reset_tier": 0,
    }
