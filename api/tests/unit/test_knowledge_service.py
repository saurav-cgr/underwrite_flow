"""Unit coverage for knowledge summary persistence behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from underwriteflow.knowledge.service import KnowledgeService


# Verify summary counts passages without loading their document bodies.
@pytest.mark.asyncio
async def test_summary_uses_passage_count_query() -> None:
    repository = SimpleNamespace(
        count_passages=AsyncMock(return_value=12),
        list_passages=AsyncMock(
            side_effect=AssertionError("summary loaded passage bodies")
        ),
    )
    version = SimpleNamespace(
        id="version-id",
        scope="guideline",
        version="g1",
        status="draft",
        content_type="synthetic_guidance",
        validation={"valid": True, "issues": []},
        activated_at=None,
    )

    summary = await KnowledgeService(repository=repository).summary(
        None, version, "life-individual-term"
    )

    assert summary["passage_count"] == 12
    repository.count_passages.assert_awaited_once_with(None, "version-id")
