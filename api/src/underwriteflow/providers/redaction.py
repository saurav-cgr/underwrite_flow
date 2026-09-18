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


# Replace mandatory patterns and configured literals with a redaction marker.
def redact_personal_data(
    text: str, extra_terms: tuple[str, ...] = ()
) -> str:
    redacted = text
    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub(REDACTION_MARKER, redacted)
    for term in extra_terms:
        redacted = re.sub(
            re.escape(term),
            REDACTION_MARKER,
            redacted,
            flags=re.IGNORECASE,
        )
    return redacted


# Redact one document page while keeping its trusted locator intact.
def redacted_page(
    page: DocumentPage, extra_terms: tuple[str, ...] = ()
) -> DocumentPage:
    return page.model_copy(
        update={"text": redact_personal_data(page.text, extra_terms)}
    )


# Copy one request with redacted document and reference content.
def redacted_request(
    request: ExtractionRequest, extra_terms: tuple[str, ...] = ()
) -> ExtractionRequest:
    return request.model_copy(
        update={
            "content": redact_personal_data(request.content, extra_terms),
            "reference_content": redact_personal_data(
                request.reference_content, extra_terms
            ),
            "pages": [
                redacted_page(page, extra_terms) for page in request.pages
            ],
        }
    )
