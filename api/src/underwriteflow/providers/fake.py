"""Deterministic provider used by normal tests and local smoke checks."""

from underwriteflow.providers.schemas import (
    ExtractedField,
    ExtractionRequest,
    ExtractionResult,
)
from underwriteflow.providers.service import parse_result


class FakeProvider:
    """Extract simple synthetic key-value lines without a remote model."""

    # Extract requested fields from deterministic synthetic lines.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        requested = set(request.requested_fields)
        fields: list[ExtractedField] = []
        for line_number, line in enumerate(request.content.splitlines(), 1):
            if ":" not in line:
                continue
            field_name, value = (part.strip() for part in line.split(":", 1))
            if field_name in requested:
                fields.append(
                    ExtractedField(
                        field_name=field_name,
                        value=value,
                        source_locator=f"line:{line_number}",
                        confidence=1.0,
                        extraction_method="fake",
                    )
                )
        # Local extraction reports no token usage, so it stays unavailable.
        return parse_result(
            [field.model_dump(mode="json") for field in fields],
            "fake",
            request.field_specifications,
        )
