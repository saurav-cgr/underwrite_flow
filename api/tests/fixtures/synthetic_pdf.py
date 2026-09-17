"""Deterministic synthetic PDFs with a real extractable text layer.

Every PDF in this repository was previously built with
``PdfWriter.add_blank_page``, so local extraction was only ever exercised
against an empty result. These helpers embed a real content stream, which lets
the integration tests drive extraction, reconciliation, and routing end to end.
"""

from io import BytesIO
from pathlib import Path
from uuid import UUID

from pypdf import PdfWriter

UPLOAD_ROOT = Path("/data/uploads")

# Field lines the built-in fictional motor configuration requests.
MOTOR_EVIDENCE_LINES = [
    "vehicle_age: 2",
    "vehicle_use: personal",
    "prior_claims: 0",
]

# Lines that carry no requested field, used for supporting documents.
IDENTITY_ONLY_LINES = ["identity_reference: SYNTHETIC-0001"]

# Prior-policy facts the configured no-claim-bonus and lapse checks read.
PREVIOUS_POLICY_LINES = [
    "ncb_percent: 20",
    "policy_expiry: 2025-09-01",
]

# Registration identifiers the configured asset match compares.
REGISTRATION_CERTIFICATE_LINES = [
    "engine_number: SYNTH-ENG-0001",
    "chassis_number: SYNTH-CHS-0001",
    "registration_number: SYNTH-RC-0001",
]

# Claims facts the configured no-claim-bonus check adjusts against.
CLAIMS_HISTORY_LINES = ["claim_count: 0"]

# One line set per fictional motor document code, so a test can seed any
# document combination without restating the field vocabulary.
MOTOR_DOCUMENT_LINES: dict[str, list[str]] = {
    "identity_record": IDENTITY_ONLY_LINES,
    "vehicle_record": MOTOR_EVIDENCE_LINES,
    "previous_policy": PREVIOUS_POLICY_LINES,
    "registration_certificate": REGISTRATION_CERTIFICATE_LINES,
    "claims_history": CLAIMS_HISTORY_LINES,
}

# The motor documents every submittable synthetic case starts with.
DEFAULT_DOCUMENT_CODES = ("identity_record", "vehicle_record")


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


# Build a one-page PDF with no text layer at all.
def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


# Write one synthetic document to the volume the API extracts from.
def write_upload(case_id: UUID, document_code: str, content: bytes) -> None:
    directory = UPLOAD_ROOT / str(case_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{document_code}.pdf").write_bytes(content)
