"""Run the deterministic Compose end-to-end demonstration flow."""

from fastapi.testclient import TestClient

from underwriteflow.app import create_app

SMOKE_KEY = "synthetic-compose-smoke-v5"
SMOKE_DOCUMENTS = (
    ("identity_record", "identity.pdf"),
    ("vehicle_record", "vehicle.pdf"),
    ("registration_certificate", "registration.pdf"),
)

# Field lines the fictional motor configuration requests. Extraction reads the
# document text layer, so a blank PDF yields no evidence and no final route.
# New business never asks for prior claims, and the identifier lines are the
# evidence the configured asset checks read.
MOTOR_EVIDENCE_LINES = [
    "vehicle_age: 4",
    "vehicle_use: personal",
    "chassis_number: SYNTHETIC-AGREED",
    "engine_number: SYNTHETIC-AGREED",
    "registration_number: SYNTHETIC-AGREED",
]


# Assemble the object table, cross-reference table, and trailer for one page.
def _assemble(content_stream: bytes) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(content_stream)).encode()
        + b" >>\nstream\n"
        + content_stream
        + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, body in enumerate(objects, 1):
        offsets.append(len(document))
        document += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_offset = len(document)
    document += f"xref\n0 {len(objects) + 1}\n".encode()
    document += b"0000000000 65535 f \n"
    for offset in offsets:
        document += f"{offset:010d} 00000 n \n".encode()
    document += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return bytes(document)


# Build a one-page PDF whose text layer extracts to the supplied lines.
def text_pdf(lines: list[str]) -> bytes:
    body = "BT /F1 12 Tf 72 720 Td 16 TL\n"
    for index, line in enumerate(lines):
        escaped = (
            line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        )
        if index:
            body += "T*\n"
        body += f"({escaped}) Tj\n"
    body += "ET"
    return _assemble(body.encode("latin-1"))


# Log in one fictional demo role and return bearer headers.
def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/session",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


# Upload only configured motor documents absent from the case.
def upload_missing_documents(
    client: TestClient, case_id: str, headers: dict[str, str]
) -> None:
    response = client.get(f"/api/v1/cases/{case_id}/documents", headers=headers)
    assert response.status_code == 200, response.text
    attached = {document["document_code"] for document in response.json()}
    content = text_pdf(MOTOR_EVIDENCE_LINES)
    for code, filename in SMOKE_DOCUMENTS:
        if code in attached:
            continue
        response = client.post(
            f"/api/v1/cases/{case_id}/documents",
            headers=headers,
            files={"document": (filename, content, "application/pdf")},
            data={"document_code": code},
        )
        assert response.status_code == 200, response.text


# Resume a fixed-key synthetic case from every valid smoke-flow status.
def recover_case(
    client: TestClient,
    case: dict[str, object],
    applicant: dict[str, str],
    underwriter: dict[str, str],
) -> dict[str, object]:
    case_id = str(case["id"])
    status = case["status"]
    if status == "new":
        upload_missing_documents(client, case_id, applicant)
        submitted = client.post(
            f"/api/v1/cases/{case_id}/submit", headers=applicant
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["recommendation"]["route"] == "expedited"
        status = "underwriter_review"
    if status == "underwriter_review":
        decision = client.post(
            f"/api/v1/reviews/{case_id}",
            headers=underwriter,
            json={"action": "confirm", "evidence_acknowledged": True},
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["status"] == "confirmed"
        status = "confirmed"
    if status in {"confirmed", "overridden", "completed"}:
        completion = client.post(
            f"/api/v1/completion/{case_id}", headers=underwriter
        )
        assert completion.status_code == 200, completion.text
        assert completion.json()["status"] == "completed"
        return completion.json()
    raise AssertionError(f"Unexpected smoke case status: {status}")


# Run intake, review, completion, retry, and audit assertions.
def run_smoke() -> None:
    with TestClient(create_app()) as client:
        administrator = login(
            client,
            "administrator@synthetic.test",
            "underwriteflow-demo-administrator",
        )
        activation = client.post(
            "/api/v1/products/motor-private-car/activate",
            headers=administrator,
            json={"version": "v5"},
        )
        assert activation.status_code == 200, activation.text
        applicant = login(
            client,
            "applicant@synthetic.test",
            "underwriteflow-demo-applicant",
        )
        case_response = client.post(
            "/api/v1/cases",
            headers=applicant,
            json={
                "product_code": "motor-private-car",
                "idempotency_key": SMOKE_KEY,
                "payload": {
                    "vehicle_age": 4,
                    "vehicle_use": "personal",
                },
                "document_codes": [
                    "identity_record",
                    "vehicle_record",
                    "registration_certificate",
                ],
            },
        )
        assert case_response.status_code == 200, case_response.text
        case = case_response.json()
        case_id = case["id"]
        underwriter = login(
            client,
            "underwriter@synthetic.test",
            "underwriteflow-demo-underwriter",
        )
        completion = recover_case(client, case, applicant, underwriter)
        repeated = client.post(
            f"/api/v1/completion/{case_id}",
            headers=underwriter,
        )
        assert repeated.json() == completion
        audit = client.get(
            f"/api/v1/audit/cases/{case_id}",
            headers=administrator,
        )
        assert audit.status_code == 200, audit.text
        event_types = {event["event_type"] for event in audit.json()}
        assert {"case_created", "case_completed"}.issubset(event_types)
    print("Compose smoke passed: intake, review, completion, retry, audit")


if __name__ == "__main__":
    run_smoke()
