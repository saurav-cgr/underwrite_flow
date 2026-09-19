"""Checkpoint-ready parent evidence graph."""

from functools import partial

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.workflow.nodes import (
    extract_document,
    fan_out_documents,
    join_evidence,
    reconcile_evidence,
)
from underwriteflow.workflow.state import EvidenceState, thread_config


# Compile one parent graph with a provider kept outside serializable state.
def build_evidence_graph(
    provider: ExtractionProvider,
    retry_count: int = 2,
    checkpointer: BaseCheckpointSaver | None = None,
):
    builder = StateGraph(EvidenceState)
    builder.add_node(
        "extract_document",
        partial(extract_document, provider=provider, retry_count=retry_count),
    )
    builder.add_node("join_evidence", join_evidence)
    builder.add_node("reconcile_evidence", reconcile_evidence)
    builder.add_conditional_edges(
        START,
        fan_out_documents,
        ["extract_document", "reconcile_evidence"],
    )
    builder.add_edge("extract_document", "join_evidence")
    builder.add_conditional_edges(
        "join_evidence",
        fan_out_documents,
        ["extract_document", "reconcile_evidence"],
    )
    builder.add_edge("reconcile_evidence", END)
    return builder.compile(checkpointer=checkpointer)
