import pytest

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.rules import ProductRuleError, evaluate_rule
from underwriteflow.workflow.product_subgraphs import (
    ProductSelectionError,
    build_product_subgraph,
    select_product_subgraph,
)


# Build one synthetic product configuration with a single fictional rule.
def product_configuration(
    code: str, family: str, field: str, rule_code: str, route: str
) -> ProductConfiguration:
    return ProductConfiguration.model_validate(
        {
            "product_code": code,
            "title": f"Synthetic {family}",
            "family": family,
            "scope": "Fictional demonstration only",
            "description": "Synthetic product configuration",
            "version": "v1",
            "fields": [
                {
                    "key": field,
                    "label": "Synthetic field",
                    "type": "integer",
                    "help_text": "Synthetic value",
                }
            ],
            "documents": [
                {
                    "code": "synthetic_document",
                    "title": "Synthetic document",
                    "requirement": "optional",
                    "accepted_types": ["application/pdf"],
                }
            ],
            "routing_rules": [
                {
                    "code": rule_code,
                    "condition": {"field": field, "operator": "greater_than", "value": 1},
                    "route": route,
                    "specialist_label": "synthetic review" if route == "specialist" else None,
                }
            ],
            "specialist_labels": ["synthetic review"],
        }
    )


# Verify configured deterministic rules produce a normalized route outcome.
def test_product_rule_engine_evaluates_configured_condition() -> None:
    configuration = product_configuration(
        "synthetic-motor", "motor", "vehicle_age", "age_specialist", "specialist"
    )

    result = evaluate_rule(configuration.routing_rules[0], {"vehicle_age": 14})

    assert result.rule_code == "age_specialist"
    assert result.triggered is True
    assert result.route == "specialist"
    assert result.specialist_label == "synthetic review"


# Verify exactly one selected product subgraph runs configured checks in stable order.
@pytest.mark.asyncio
async def test_selected_product_subgraph_only_processes_selected_product() -> None:
    configurations = {
        "synthetic-motor": product_configuration(
            "synthetic-motor", "motor", "vehicle_age", "motor_rule", "specialist"
        ),
        "synthetic-life": product_configuration(
            "synthetic-life", "life", "requested_cover", "life_rule", "standard"
        ),
        "synthetic-health": product_configuration(
            "synthetic-health", "health", "member_count", "health_rule", "expedited"
        ),
    }
    graph = select_product_subgraph("synthetic-life", configurations)

    result = await graph.ainvoke(
        {"product_code": "synthetic-life", "payload": {"requested_cover": 2}, "rule_results": []}
    )

    assert [item["rule_code"] for item in result["validations"]] == ["life_rule"]
    assert result["validations"][0]["status"] == "triggered"
    assert result["risk_signals"] == []


# Verify unsupported product selection fails before any graph executes.
def test_unsupported_product_subgraph_is_rejected() -> None:
    with pytest.raises(ProductSelectionError):
        select_product_subgraph("synthetic-unsupported", {})


# Verify invalid configured rule conditions fail safely at the rule boundary.
def test_invalid_rule_condition_is_rejected() -> None:
    configuration = product_configuration(
        "synthetic-motor", "motor", "vehicle_age", "age_specialist", "specialist"
    )
    rule = configuration.routing_rules[0].model_copy(
        update={"condition": {"field": "vehicle_age", "operator": "unknown", "value": 1}}
    )

    with pytest.raises(ProductRuleError):
        evaluate_rule(rule, {"vehicle_age": 14})


# Given one invalid rule, preserve the successful sibling result in the subgraph join.
@pytest.mark.asyncio
async def test_invalid_product_rule_preserves_sibling_results() -> None:
    configuration = product_configuration(
        "synthetic-motor", "motor", "vehicle_age", "age_specialist", "specialist"
    )
    valid_rule = configuration.routing_rules[0]
    invalid_rule = valid_rule.model_copy(
        update={
            "code": "invalid_operator",
            "condition": {"field": "vehicle_age", "operator": "unknown", "value": 1},
        }
    )
    configuration = configuration.model_copy(
        update={"routing_rules": [valid_rule, invalid_rule]}
    )

    result = await build_product_subgraph(configuration).ainvoke(
        {"product_code": configuration.product_code, "payload": {"vehicle_age": 14}}
    )

    assert [item["rule_code"] for item in result["validations"]] == [
        "age_specialist",
        "invalid_operator",
    ]
    assert result["validations"][0]["status"] == "triggered"
    assert result["validations"][1]["status"] == "error"
