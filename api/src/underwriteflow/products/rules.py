"""Shared deterministic evaluation for fictional product routing rules."""

from pydantic import BaseModel

from underwriteflow.products.schemas import SUPPORTED_OPERATORS, RoutingRule


class ProductRuleError(ValueError):
    """Raised when a configured product rule cannot be evaluated safely."""


class RuleEvaluation(BaseModel):
    """Normalized result of one deterministic product rule."""

    rule_code: str
    triggered: bool
    route: str
    specialist_label: str | None = None
    error_code: str | None = None


# Evaluate one supported fictional condition against submitted application data.
def condition_matches(condition: dict[str, object], payload: dict[str, object]) -> bool:
    actual = payload.get(condition.get("field"))
    expected = condition.get("value")
    if condition.get("operator") == "equals":
        return actual == expected
    if condition.get("operator") == "greater_than":
        try:
            return actual is not None and actual > expected
        except TypeError:
            return False
    return False


# Evaluate one configured rule and preserve its deterministic route metadata.
def evaluate_rule(rule: RoutingRule, payload: dict[str, object]) -> RuleEvaluation:
    if rule.condition.get("operator") not in SUPPORTED_OPERATORS:
        raise ProductRuleError("unsupported rule operator")
    return RuleEvaluation(
        rule_code=rule.code,
        triggered=condition_matches(rule.condition, payload),
        route=rule.route,
        specialist_label=rule.specialist_label,
    )
