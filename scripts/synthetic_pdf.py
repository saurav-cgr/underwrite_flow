"""Minimal real document bytes for the standalone evaluation runner.

Mirrors api/tests/fixtures/synthetic_pdf.py: evaluate_e2e.py has no access
to the test package, so it needs its own minimal real-PDF byte assembler
instead of the plain text the offline evaluator can get away with.
"""

from io import BytesIO
from typing import Any

from PIL import Image


# Assemble the object table, cross-reference table, and trailer for one page.
def _assemble_pdf(content_stream: bytes) -> bytes:
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
    return _assemble_pdf(body.encode("latin-1"))


# Build a minimal one-pixel JPEG for document codes that only accept images.
def blank_jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color=(255, 255, 255)).save(buffer, "JPEG")
    return buffer.getvalue()


# Map each document code to its accepted content types for one version.
def document_types(configuration: Any) -> dict[str, list[str]]:
    return {
        document.code: document.accepted_types
        for document in configuration.documents
    }


# Build the upload tuple for one document, honoring its accepted types
# when known; defaults to a PDF, matching the pinned mocked-HTTP tests.
def document_upload(
    document: dict[str, Any], accepted_types: dict[str, list[str]] | None
) -> tuple[str, bytes, str]:
    types = (accepted_types or {}).get(
        document["document_id"], ["application/pdf"]
    )
    if "application/pdf" in types:
        content = text_pdf(document["lines"])
        return document["filename"], content, "application/pdf"
    stem = document["filename"].rsplit(".", 1)[0]
    return f"{stem}.jpg", blank_jpeg(), "image/jpeg"
