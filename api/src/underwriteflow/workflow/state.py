"""Serializable state and stable result reducers for evidence processing."""

from typing import Annotated, TypedDict

from underwriteflow.workflow.reducers import append_product_results, append_results


class DocumentInput(TypedDict):
    """Text-only document input; file bytes remain outside graph state."""

    document_id: str
    filename: str
    content: str


class DocumentResult(TypedDict):
    """Serializable result for one document branch."""

    document_id: str
    filename: str
    fields: list[dict[str, object]]
    error_code: str | None
    attempts: int


class EvidenceState(TypedDict, total=False):
    """Parent graph state shared by fan-out, join, and reconciliation nodes."""

    case_id: str
    documents: list[DocumentInput]
    requested_fields: list[str]
    results: Annotated[list[DocumentResult], append_results]
    ordered_results: list[DocumentResult]
    reconciled_fields: list[dict[str, object]]


class DocumentWorkerState(TypedDict):
    """Payload delivered to one isolated document worker branch."""

    document: DocumentInput
    requested_fields: list[str]


class ProductRuleInput(TypedDict):
    """Serializable configured rule delivered to one product branch."""

    code: str
    condition: dict[str, object]
    route: str
    specialist_label: str | None


class ProductRuleResult(TypedDict):
    """Serializable deterministic result for one configured product rule."""

    rule_code: str
    triggered: bool
    route: str
    specialist_label: str | None
    error_code: str | None


class ProductState(TypedDict, total=False):
    """State for one selected product subgraph."""

    product_code: str
    payload: dict[str, object]
    rule_results: Annotated[list[ProductRuleResult], append_product_results]
    validations: list[dict[str, object]]
    risk_signals: list[dict[str, object]]


class ProductRuleWorkerState(TypedDict):
    """Payload delivered to one configured product-rule branch."""

    rule: ProductRuleInput
    payload: dict[str, object]


# Return a stable thread configuration for one case workflow run.
def thread_config(case_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": f"case-{case_id}"}}
