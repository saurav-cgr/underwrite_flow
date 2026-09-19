"""End-to-end configured reconciliation over synthetic motor evidence."""

from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from fixtures.records import remove_case
from fixtures.synthetic_pdf import text_pdf

from underwriteflow.app import create_app
from underwriteflow.config import Settings

DATABASE_URL = (
    "postgresql://underwriteflow:synthetic-local-password@"
    "db:5433/underwriteflow"
)

ADMINISTRATOR = (
    "administrator@synthetic.test",
    "underwriteflow-demo-administrator",
)
APPLICANT = ("applicant@synthetic.test", "underwriteflow-demo-applicant")

DOCUMENT_CODES = [
    "identity_record",
    "vehicle_record",
    "registration_certificate",
]

APPLICATION_FIELDS = ["vehicle_age: 2", "vehicle_use: personal"]


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, account: tuple[str, str]) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": account[0], "password": account[1]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# Activate one built-in motor version through the administrator API.
def activate(client: TestClient, version: str) -> None:
    headers = login(client, ADMINISTRATOR)
    response = client.post(
        "/api/v1/products/motor-private-car/activate",
        json={"version": version},
        headers=headers,
    )
    assert response.status_code == 200, response.text


# Create one applicant-owned motor case against the active version.
def create_case(
    client: TestClient,
    headers: dict[str, str],
    claimed_ncb_percent: int,
) -> str:
    created = client.post(
        "/api/v1/cases",
        json={
            "product_code": "motor-private-car",
            "idempotency_key": str(uuid4()),
            "payload": {
                "vehicle_age": 2,
                "vehicle_use": "personal",
                "prior_claims": 2,
                "claimed_ncb_percent": claimed_ncb_percent,
                "policy_start_date": "2026-01-15",
            },
            "document_codes": DOCUMENT_CODES,
        },
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return created.json()["id"]


# Build the synthetic uploads whose evidence either agrees or disagrees.
def uploads(
    claimed_ncb_percent: int,
    check_fields: bool = True,
    matching_assets: bool = True,
) -> list[tuple]:
    items = [
        (
            "identity_record",
            text_pdf(["identity_reference: SYNTHETIC-0001"]),
        )
    ]
    lines = [
        *APPLICATION_FIELDS,
        "prior_claims: 2",
        f"claimed_ncb_percent: {claimed_ncb_percent}",
        "policy_start_date: 2026-01-15",
    ]
    if check_fields:
        lines.extend(
            [
                "ncb_percent: 20",
                "policy_expiry: 2026-01-05",
                "engine_number: SYNTH ENG 0001",
                "chassis_number: synth-chs-0001",
                "registration_number: SYNTH RC 0001",
            ]
        )
    items.append(("vehicle_record", text_pdf(lines)))
    suffix = "0001" if matching_assets else "0002"
    items.append(
        (
            "registration_certificate",
            text_pdf(
                [
                    f"engine_number: SYNTH-ENG-{suffix}",
                    f"chassis_number: SYNTH-CHS-{suffix}",
                    f"registration_number: SYNTH-RC-{suffix}",
                ]
            ),
        )
    )
    return items


# Upload each synthetic document and return the case's submission response.
def submit_case(
    client: TestClient,
    headers: dict[str, str],
    case_id: str,
    items: list[tuple],
) -> dict[str, object]:
    for code, content in items:
        uploaded = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"document": ("synthetic.pdf", content, "application/pdf")},
            data={"document_code": code},
            headers=headers,
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = client.post(
        f"/api/v1/cases/{case_id}/submit", headers=headers
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


# Read the reconciliation validations and signals persisted for one case.
def read_case_checks(
    case_id: str,
) -> tuple[list[tuple[str, str]], list[str]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT rule_code, status FROM validations "
                "WHERE case_id = %s AND rule_code LIKE 'reconciliation:%%' "
                "ORDER BY rule_code",
                (case_id,),
            )
            validations = [tuple(row) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT code FROM risk_signals WHERE case_id = %s "
                "AND code LIKE 'reconciliation_%%' ORDER BY code",
                (case_id,),
            )
            signals = [row[0] for row in cursor.fetchall()]
    return validations, signals


# Read one persisted reconciliation result by its stable configured code.
def read_check_details(case_id: str, code: str) -> dict[str, object]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT details FROM validations WHERE case_id = %s "
                "AND rule_code = %s",
                (case_id, f"reconciliation:{code}"),
            )
            return cursor.fetchone()[0]


# Run one synthetic case against the check-bearing motor version.
def run_case(
    claimed_ncb_percent: int,
    check_fields: bool = True,
    matching_assets: bool = True,
) -> tuple[str, dict[str, object]]:
    settings = Settings(generation_provider="fake")
    with TestClient(create_app(settings)) as client:
        activate(client, "v3")
        headers = login(client, APPLICANT)
        case_id = create_case(client, headers, claimed_ncb_percent)
        response = submit_case(
            client,
            headers,
            case_id,
            uploads(claimed_ncb_percent, check_fields, matching_assets),
        )
    return case_id, response


# Verify agreeing evidence clears every configured motor check.
def test_agreeing_evidence_clears_all_motor_checks() -> None:
    case_id = ""
    try:
        case_id, response = run_case(0)
        validations, signals = read_case_checks(case_id)

        assert validations == [
            ("reconciliation:motor_chassis_match", "cleared"),
            ("reconciliation:motor_engine_match", "cleared"),
            ("reconciliation:motor_ncb_match", "cleared"),
            ("reconciliation:motor_registration_match", "cleared"),
            ("reconciliation:motor_renewal_lapse", "cleared"),
        ]
        assert signals == []
        assert response["recommendation"]["route"] != "needs_information"
        engine = read_check_details(case_id, "motor_engine_match")
        comparison = engine["comparisons"][0]
        assert comparison["left"] == "syntheng0001"
        assert comparison["right"] == "syntheng0001"
        assert comparison["explanation_code"] == (
            "asset_identifiers_match"
        )
    finally:
        if case_id:
            remove_case(UUID(case_id))
        with TestClient(create_app()) as client:
            activate(client, "v1")


# Verify every configured asset conflict is flagged end to end.
def test_disagreeing_evidence_flags_the_case() -> None:
    case_id = ""
    try:
        case_id, response = run_case(20, matching_assets=False)
        validations, signals = read_case_checks(case_id)

        assert validations == [
            ("reconciliation:motor_chassis_match", "flagged_discrepancy"),
            ("reconciliation:motor_engine_match", "flagged_discrepancy"),
            ("reconciliation:motor_ncb_match", "flagged_discrepancy"),
            (
                "reconciliation:motor_registration_match",
                "flagged_discrepancy",
            ),
            ("reconciliation:motor_renewal_lapse", "cleared"),
        ]
        assert signals == [
            "reconciliation_asset_mismatch",
            "reconciliation_asset_mismatch",
            "reconciliation_asset_mismatch",
            "reconciliation_ncb_progression_mismatch",
        ]
        assert response["recommendation"]["route"] == "specialist"
    finally:
        if case_id:
            remove_case(UUID(case_id))
        with TestClient(create_app()) as client:
            activate(client, "v1")


# Verify absent evidence a check needs keeps the case in the queue state.
def test_absent_evidence_queues_the_case() -> None:
    case_id = ""
    try:
        case_id, response = run_case(0, check_fields=False)
        validations, signals = read_case_checks(case_id)

        assert validations == [
            ("reconciliation:motor_chassis_match", "missing_evidence"),
            ("reconciliation:motor_engine_match", "missing_evidence"),
            ("reconciliation:motor_ncb_match", "missing_evidence"),
            (
                "reconciliation:motor_registration_match",
                "missing_evidence",
            ),
            ("reconciliation:motor_renewal_lapse", "missing_evidence"),
        ]
        assert signals == []
        assert response["recommendation"]["route"] == "needs_information"
    finally:
        if case_id:
            remove_case(UUID(case_id))
        with TestClient(create_app()) as client:
            activate(client, "v1")
