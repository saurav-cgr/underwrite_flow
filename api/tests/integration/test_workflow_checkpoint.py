import pytest

from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.checkpoint import postgres_checkpointer
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.state import thread_config


DATABASE_URL = "postgresql+asyncpg://underwriteflow:synthetic-local-password@db:5433/underwriteflow"


# Verify the supported PostgreSQL saver resumes a case by its stable thread ID.
@pytest.mark.asyncio
async def test_postgres_checkpoint_round_trip() -> None:
    config = thread_config("checkpoint-synthetic")
    async with postgres_checkpointer(DATABASE_URL) as checkpointer:
        graph = build_evidence_graph(FakeProvider(), checkpointer=checkpointer)
        await graph.ainvoke(
            {
                "case_id": "checkpoint-synthetic",
                "documents": [
                    {
                        "document_id": "doc-1",
                        "filename": "doc-1",
                        "content": "SYNTHETIC - FOR DEMONSTRATION ONLY\nsynthetic_field: value",
                    }
                ],
                "requested_fields": ["synthetic_field"],
                "results": [],
            },
            config=config,
        )

        checkpoint = await graph.aget_state(config)

    assert checkpoint.values["case_id"] == "checkpoint-synthetic"
    assert checkpoint.values["ordered_results"][0]["document_id"] == "doc-1"
