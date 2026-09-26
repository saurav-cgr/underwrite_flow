"""Application-owned provider protocol."""

from typing import Protocol

from underwriteflow.providers.schemas import ExtractionRequest, ExtractionResult


class ExtractionProvider(Protocol):
    """Common contract for deterministic and remote extraction providers."""

    # Stable provider identity recorded in immutable audit events.
    name: str

    # Extract only requested fields from isolated document content.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        ...
