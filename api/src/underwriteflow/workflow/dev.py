"""Development-only graphs exported for LangGraph Dev and Studio."""

from pathlib import Path

from underwriteflow.products.service import load_configuration
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.workflow.graph import build_evidence_graph
from underwriteflow.workflow.product_subgraphs import build_product_subgraph
from underwriteflow.workflow.triage import build_triage_graph

PRODUCT_CONFIG_ROOT = Path("/app/product-config")


# Compile one fictional product graph for interactive local inspection.
def development_product_graph(filename: str):
    configuration = load_configuration(
        (PRODUCT_CONFIG_ROOT / filename).read_text()
    )
    return build_product_subgraph(configuration)


evidence_graph = build_evidence_graph(FakeProvider())
triage_graph = build_triage_graph()
motor_graph = development_product_graph("motor-private-car.yaml")
life_graph = development_product_graph("life-individual-term.yaml")
health_graph = development_product_graph(
    "health-individual-family-floater.yaml"
)
