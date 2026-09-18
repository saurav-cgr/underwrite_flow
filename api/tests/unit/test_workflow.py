import asyncio
from collections import defaultdict

import pytest
from langgraph.checkpoint.memory import MemorySaver

from underwriteflow.providers.schemas import ExtractedField, ExtractionRequest, ExtractionResult
from underwriteflow.providers.service import ProviderError, TransientProviderError
from underwriteflow.workflow.graph import build_evidence_graph, thread_config


class RecordingProvider:
    """Deterministic provider that records branch calls for graph tests."""

    name = "recording"

    # Configure synthetic failures and concurrency counters for a test run.
    def __init__(self, failures: set[str] | None = None, transient_once: str | None = None) -> None:
        self.failures = failures or set()
        self.transient_once = transient_once
        self.calls: list[str] = []
        self.requests: list[ExtractionRequest] = []
        self.attempts: dict[str, int] = defaultdict(int)
        self.current = 0
        self.max_concurrency = 0

    # Return one synthetic field or the configured branch failure.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        document_id = request.document_name
        self.calls.append(document_id)
        self.requests.append(request)
        self.attempts[document_id] += 1
        if document_id in self.failures:
            raise ProviderError("synthetic provider failure")
        if document_id == self.transient_once and self.attempts[document_id] == 1:
            raise TransientProviderError("synthetic transient failure")
        self.current += 1
        self.max_concurrency = max(self.max_concurrency, self.current)
        await asyncio.sleep(0)
        self.current -= 1
        return ExtractionResult(
            fields=[
                ExtractedField(
                    field_name="synthetic_field",
                    value=document_id,
                    source_locator="line:1",
                    confidence=1.0,
                )
            ]
        )


# Return the same field value for every document so nothing conflicts.
class AgreeingProvider:
    """Deterministic provider returning one shared value for each field."""

    name = "agreeing"

    # Return one synthetic field with a value every document agrees on.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        del request
        return ExtractionResult(
            fields=[
                ExtractedField(
                    field_name="synthetic_field",
                    value="shared",
                    source_locator="line:1",
                    confidence=1.0,
                )
            ]
        )


# Build serializable synthetic documents for graph tests.
def documents(count: int) -> list[dict[str, str]]:    return [
        {
            "document_id": f"doc-{index}",
            "filename": f"doc-{index}",
            "content": "SYNTHETIC - FOR DEMONSTRATION ONLY",
        }
        for index in range(count)
    ]


# Verify each review cycle keeps the case identity and a fresh thread.
def test_thread_config_keeps_case_and_separates_cycles() -> None:
    first = thread_config("case-9", 0)
    second = thread_config("case-9", 1)

    assert first["configurable"]["thread_id"].startswith("case-case-9")
    assert second["configurable"]["thread_id"].startswith("case-case-9")
    assert (
        first["configurable"]["thread_id"]
        != second["configurable"]["thread_id"]
    )


# Verify administrator reference text reaches every provider branch request.
@pytest.mark.asyncio
async def test_evidence_graph_passes_reference_content_to_provider() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider, checkpointer=MemorySaver())

    await graph.ainvoke(
        {
            "case_id": "case-reference",
            "documents": documents(1),
            "requested_fields": ["synthetic_field"],
            "reference_content": "Synthetic reference material",
            "results": [],
        },
        config=thread_config("case-reference"),
    )

    assert provider.requests
    assert (
        provider.requests[0].reference_content
        == "Synthetic reference material"
    )


# Verify provider output is limited to the fields the application requested.
@pytest.mark.asyncio
async def test_evidence_graph_rejects_unrequested_provider_fields() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider, checkpointer=MemorySaver())

    result = await graph.ainvoke(
        {
            "case_id": "case-unrequested",
            "documents": documents(1),
            "requested_fields": ["expected_field"],
            "results": [],
        },
        config=thread_config("case-unrequested"),
    )

    assert result["results"][0]["error_code"] == "unrequested_field"
    assert result["results"][0]["fields"] == []
    assert result["reconciled_fields"] == []


# Verify all documents complete in stable order with no more than three active branches.
@pytest.mark.asyncio
async def test_evidence_graph_batches_documents_and_sorts_results() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider, checkpointer=MemorySaver())

    result = await graph.ainvoke(
        {
            "case_id": "case-1",
            "documents": documents(5),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=thread_config("case-1"),
    )

    assert [item["document_id"] for item in result["ordered_results"]] == [
        "doc-0",
        "doc-1",
        "doc-2",
        "doc-3",
        "doc-4",
    ]
    assert provider.calls == ["doc-0", "doc-1", "doc-2", "doc-3", "doc-4"]
    assert provider.max_concurrency <= 3


# Verify one failed branch does not discard successful sibling results.
@pytest.mark.asyncio
async def test_evidence_graph_isolates_branch_failure() -> None:
    provider = RecordingProvider(failures={"doc-1"})
    graph = build_evidence_graph(provider)

    result = await graph.ainvoke(
        {
            "case_id": "case-2",
            "documents": documents(3),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=thread_config("case-2"),
    )

    by_id = {item["document_id"]: item for item in result["ordered_results"]}
    assert by_id["doc-0"]["error_code"] is None
    assert by_id["doc-2"]["error_code"] is None
    assert by_id["doc-1"]["error_code"] == "provider_error"


# Verify transient retry stays within the failing document branch.
@pytest.mark.asyncio
async def test_evidence_graph_retries_only_transient_branch_errors() -> None:
    provider = RecordingProvider(transient_once="doc-1")
    graph = build_evidence_graph(provider, retry_count=1)

    result = await graph.ainvoke(
        {
            "case_id": "case-3",
            "documents": documents(2),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=thread_config("case-3"),
    )

    assert provider.attempts == {"doc-0": 1, "doc-1": 2}
    assert all(item["error_code"] is None for item in result["ordered_results"])


# Verify existing document results enable delta-only processing on a stable thread.
@pytest.mark.asyncio
async def test_evidence_graph_skips_already_processed_documents() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider, checkpointer=MemorySaver())
    existing = {
        "document_id": "doc-0",
        "filename": "doc-0",
        "fields": [],
        "error_code": None,
        "attempts": 1,
    }

    result = await graph.ainvoke(
        {
            "case_id": "case-4",
            "documents": documents(2),
            "requested_fields": ["synthetic_field"],
            "results": [existing],
        },
        config=thread_config("case-4"),
    )

    assert provider.calls == ["doc-1"]
    assert [item["document_id"] for item in result["ordered_results"]] == ["doc-0", "doc-1"]


# Verify all previously processed documents still reconcile their stored fields.
@pytest.mark.asyncio
async def test_evidence_graph_reconciles_when_no_documents_need_processing() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider)
    existing = [
        {
            "document_id": "doc-0",
            "filename": "doc-0",
            "fields": [
                {
                    "field_name": "synthetic_field",
                    "value": "stored",
                    "source_locator": "line:1",
                    "confidence": 1.0,
                }
            ],
            "error_code": None,
            "attempts": 1,
        }
    ]

    result = await graph.ainvoke(
        {
            "case_id": "case-processed",
            "documents": documents(1),
            "requested_fields": ["synthetic_field"],
            "results": existing,
        },
        config=thread_config("case-processed"),
    )

    assert provider.calls == []
    assert result["reconciled_fields"][0]["value"] == "stored"


# Verify checkpoint state can be read back using the stable case thread ID.
@pytest.mark.asyncio
async def test_evidence_graph_checkpoint_resume_state() -> None:
    checkpointer = MemorySaver()
    graph = build_evidence_graph(RecordingProvider(), checkpointer=checkpointer)
    config = thread_config("case-5")

    await graph.ainvoke(
        {
            "case_id": "case-5",
            "documents": documents(1),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=config,
    )

    checkpoint = await graph.aget_state(config)

    assert checkpoint.values["case_id"] == "case-5"
    assert checkpoint.values["ordered_results"][0]["document_id"] == "doc-0"


# Verify two documents disagreeing about one field produce a conflict.
@pytest.mark.asyncio
async def test_evidence_graph_reports_conflicting_field_values() -> None:
    provider = RecordingProvider()
    graph = build_evidence_graph(provider, checkpointer=MemorySaver())

    result = await graph.ainvoke(
        {
            "case_id": "case-conflict",
            "documents": documents(2),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=thread_config("case-conflict"),
    )

    assert [item["field_name"] for item in result["conflicts"]] == [
        "synthetic_field"
    ]
    assert result["conflicts"][0]["values"] == ["doc-0", "doc-1"]
    assert result["conflicts"][0]["document_ids"] == ["doc-0", "doc-1"]


# Verify documents that agree on a field reconcile without a conflict.
@pytest.mark.asyncio
async def test_evidence_graph_accepts_agreeing_field_values() -> None:
    graph = build_evidence_graph(AgreeingProvider(), checkpointer=MemorySaver())

    result = await graph.ainvoke(
        {
            "case_id": "case-agree",
            "documents": documents(3),
            "requested_fields": ["synthetic_field"],
            "results": [],
        },
        config=thread_config("case-agree"),
    )

    assert result["conflicts"] == []
    assert len(result["reconciled_fields"]) == 3


# Verify a requested field no document supplied is reported as missing.
@pytest.mark.asyncio
async def test_evidence_graph_reports_missing_requested_fields() -> None:
    graph = build_evidence_graph(
        RecordingProvider(), checkpointer=MemorySaver()
    )

    result = await graph.ainvoke(
        {
            "case_id": "case-missing",
            "documents": documents(1),
            "requested_fields": ["synthetic_field", "absent_field"],
            "results": [],
        },
        config=thread_config("case-missing"),
    )

    assert result["missing_information"] == ["absent_field"]
