"""Selected product subgraphs for deterministic fictional rule evaluation."""

from functools import partial

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from underwriteflow.products.rules import (
    ProductRuleError,
    RuleEvaluation,
    evaluate_rule,
)
from underwriteflow.products.schemas import ProductConfiguration, RoutingRule
from underwriteflow.workflow.state import (
    ProductRuleInput,
    ProductRuleResult,
    ProductRuleWorkerState,
    ProductState,
)


class ProductSelectionError(ValueError):
    """Raised when a case requests an unsupported or unavailable product."""


# Evaluate one configured rule in an isolated deterministic branch.
def evaluate_product_rule(
    state: ProductRuleWorkerState,
) -> dict[str, list[ProductRuleResult]]:
    rule = RoutingRule.model_validate(state["rule"])
    try:
        evaluation = evaluate_rule(rule, state["payload"])
    except ProductRuleError:
        evaluation = RuleEvaluation(
            rule_code=rule.code,
            triggered=False,
            route=rule.route,
            specialist_label=rule.specialist_label,
            error_code="invalid_rule",
        )
    return {"rule_results": [evaluation.model_dump(mode="json")]}


# Fan out all independent rules from the selected product configuration.
def fan_out_product_rules(
    state: ProductState, rules: list[ProductRuleInput]
) -> list[Send] | str:
    if not rules:
        return "normalize_product_results"
    return [
        Send(
            "evaluate_product_rule",
            {"rule": rule, "payload": state["payload"]},
        )
        for rule in rules
    ]


# Normalize deterministic rule outcomes and specialist signals in stable order.
def normalize_product_results(
    state: ProductState,
) -> dict[str, list[dict[str, object]]]:
    results = sorted(
        state.get("rule_results", []),
        key=lambda result: result["rule_code"],
    )
    validations: list[dict[str, object]] = []
    risk_signals: list[dict[str, object]] = []
    for result in results:
        error_code = result["error_code"]
        validations.append(
            {
                "rule_code": result["rule_code"],
                "status": (
                    "error"
                    if error_code
                    else "triggered" if result["triggered"] else "clear"
                ),
                "route": result["route"],
                "source_type": "deterministic",
                "error_code": error_code,
            }
        )
        if (
            not error_code
            and result["triggered"]
            and result["route"] == "specialist"
        ):
            risk_signals.append(
                {
                    "code": result["rule_code"],
                    "severity": "high",
                    "explanation": (
                        "Configured rule triggered: "
                        f"{result['rule_code']}"
                    ),
                    "specialist_label": result["specialist_label"],
                    "source_type": "deterministic",
                }
            )
    return {"validations": validations, "risk_signals": risk_signals}


# Compile only the subgraph for the supplied pinned product configuration.
def build_product_subgraph(
    configuration: ProductConfiguration,
    checkpointer: BaseCheckpointSaver | None = None,
):
    rules = [
        rule.model_dump(mode="json")
        for rule in configuration.routing_rules
    ]
    builder = StateGraph(ProductState)
    builder.add_node("evaluate_product_rule", evaluate_product_rule)
    builder.add_node("normalize_product_results", normalize_product_results)
    builder.add_conditional_edges(
        START,
        partial(fan_out_product_rules, rules=rules),
        ["evaluate_product_rule", "normalize_product_results"],
    )
    builder.add_edge("evaluate_product_rule", "normalize_product_results")
    builder.add_edge("normalize_product_results", END)
    return builder.compile(checkpointer=checkpointer)


# Select exactly one supported product subgraph for a pinned case.
def select_product_subgraph(
    product_code: str,
    configurations: dict[str, ProductConfiguration],
    checkpointer: BaseCheckpointSaver | None = None,
):
    configuration = configurations.get(product_code)
    if configuration is None or configuration.product_code != product_code:
        raise ProductSelectionError("unsupported product configuration")
    return build_product_subgraph(configuration, checkpointer)
