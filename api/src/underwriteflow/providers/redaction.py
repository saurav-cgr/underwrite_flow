"""Configured redaction of personal identifiers before an external provider.

Document text is untrusted data, and an external provider must never receive
personal identifiers. The patterns below are the configured demonstration set
for the synthetic MVP, and redaction happens only on the external Gemini path.
"""

import re

from underwriteflow.providers.schemas import (
    DocumentPage,
    ExtractionRequest,
)

REDACTION_MARKER = "[redacted]"

# Configured demonstration patterns for the fictional evaluation data.
AADHAAR_PATTERN = re.compile(r"(?<!\d)[2-9]\d{3}\s?\d{4}\s?\d{4}(?!\d)")
PAN_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z]{5}\d{4}[A-Z](?![A-Z0-9])")
EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"(?<![\d-])(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)")

# Aadhaar and PAN first so the phone pattern cannot claim their digits.
REDACTION_PATTERNS = (
    AADHAAR_PATTERN,
    PAN_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
)


# Replace every configured personal identifier with a redaction marker.
def redact_personal_data(text: str) -> str:
    redacted = text
    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub(REDACTION_MARKER, redacted)
    return redacted


# Redact one document page while keeping its trusted locator intact.
def redacted_page(page: DocumentPage) -> DocumentPage:
    return page.model_copy(update={"text": redact_personal_data(page.text)})


# Copy one request with redacted document and reference content.
def redacted_request(request: ExtractionRequest) -> ExtractionRequest:
    return request.model_copy(
        update={
            "content": redact_personal_data(request.content),
            "reference_content": redact_personal_data(
                request.reference_content
            ),
            "pages": [redacted_page(page) for page in request.pages],
        }
    )
