"""Development-only LangGraph export checks."""

from underwriteflow.workflow.dev import (
    evidence_graph,
    health_graph,
    life_graph,
    motor_graph,
    triage_graph,
)


# Verify the development server can load every graph it advertises.
def test_development_graphs_are_compiled() -> None:
    graphs = [
        evidence_graph,
        triage_graph,
        motor_graph,
        life_graph,
        health_graph,
    ]

    assert all(graph.get_graph().nodes for graph in graphs)
