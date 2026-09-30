"""Deterministic, informational checks between rules and regulations."""

from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.knowledge.alignment import values_equal
from underwriteflow.knowledge.repository import KnowledgeRepository
from underwriteflow.products.schemas import (
    ProductConfiguration,
    condition_value,
)


# Read one value from either a model-like object or a plain mapping.
def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


# Return true when a rule value falls inside an accepted flagged zone.
def _violates(rule: Any, limit: dict[str, Any]) -> bool:
    rule_value = condition_value(rule)
    limit_value = limit.get("value")
    operator = limit.get("operator")
    try:
        left = Decimal(str(rule_value))
        right = Decimal(str(limit_value))
    except (InvalidOperation, ValueError, TypeError):
        return operator == "equals" and values_equal(
            rule_value, limit_value
        )
    if not left.is_finite() or not right.is_finite():
        return False
    if operator == "greater_than":
        return left > right
    if operator == "greater_than_or_equal":
        return left >= right
    if operator == "less_than":
        return left < right
    if operator == "less_than_or_equal":
        return left <= right
    if operator == "equals":
        return left == right
    return True


# Infer controlled topic names from a product field for related clauses.
def _rule_topics(field: str) -> set[str]:
    normalized = field.replace("_", "-")
    topics = {normalized}
    for marker, topic in (
        ("cover", "cover-amount"),
        ("occupation", "occupation"),
        ("health", "health-declaration"),
        ("identity", "identity"),
        ("income", "income-record"),
        ("policy", "previous-policy"),
        ("lapse", "lapse-gap"),
        ("age", "age"),
    ):
        if marker in normalized:
            topics.add(topic)
    return topics


# Build deterministic flags and topic-related clauses for one product draft.
def build_conformance(
    configuration: ProductConfiguration,
    regulation_version: str | None,
    passages: Iterable[Any],
) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    related: list[dict[str, Any]] = []
    passage_list = list(passages)
    for rule in configuration.routing_rules:
        condition = rule.condition
        field = condition.get("field")
        if not isinstance(field, str):
            continue
        topics = _rule_topics(field)
        related_keys: list[str] = []
        for passage in passage_list:
            tags = set(_get(passage, "topic_tags", []) or [])
            key = _get(passage, "passage_key")
            if key and topics.intersection(tags):
                related_keys.append(key)
            for limit in _get(passage, "limits", []) or []:
                if limit.get("field") != field:
                    continue
                if not _violates(condition, limit):
                    continue
                flags.append(
                    {
                        "rule_code": rule.code,
                        "field": field,
                        "rule_value": condition_value(condition),
                        "clause": {
                            "passage_key": key,
                            "limit": limit,
                        },
                        "label": _get(passage, "label"),
                    }
                )
        if related_keys:
            related.append(
                {
                    "rule_code": rule.code,
                    "passage_keys": sorted(set(related_keys)),
                }
            )
    return {
        "regulation_version": regulation_version,
        "flags": flags,
        "related": related,
    }


# Return one stable condition value for the change-impact report.
def _condition_value(condition: dict[str, Any]) -> Any:
    return condition_value(condition)


# Compare routing rules and conditional documents against an active version.
def build_change_impact(
    configuration: ProductConfiguration,
    active_configuration: ProductConfiguration | None,
) -> dict[str, Any]:
    if active_configuration is None:
        return {
            "against_version": None,
            "added_rules": [rule.code for rule in configuration.routing_rules],
            "removed_rules": [],
            "changed_thresholds": [],
            "changed_documents": [],
        }
    before_rules = {
        rule.code: rule for rule in active_configuration.routing_rules
    }
    after_rules = {rule.code: rule for rule in configuration.routing_rules}
    changed_thresholds = []
    for code in sorted(before_rules.keys() & after_rules.keys()):
        before = before_rules[code].condition
        after = after_rules[code].condition
        if before != after:
            changed_thresholds.append(
                {
                    "rule_code": code,
                    "from": _condition_value(before),
                    "to": _condition_value(after),
                }
            )
    before_documents = {
        document.code: document
        for document in active_configuration.documents
    }
    after_documents = {
        document.code: document for document in configuration.documents
    }
    changed_documents = []
    for code in sorted(before_documents.keys() | after_documents.keys()):
        before = before_documents.get(code)
        after = after_documents.get(code)
        before_shape = before.model_dump(mode="json") if before else None
        after_shape = after.model_dump(mode="json") if after else None
        if before_shape != after_shape:
            before_value = (
                _condition_value(before.condition)
                if before is not None and before.condition is not None
                else before_shape
            )
            after_value = (
                _condition_value(after.condition)
                if after is not None and after.condition is not None
                else after_shape
            )
            changed_documents.append(
                {
                    "document_code": code,
                    "from": before_value,
                    "to": after_value,
                }
            )
    return {
        "against_version": active_configuration.version,
        "added_rules": sorted(after_rules.keys() - before_rules.keys()),
        "removed_rules": sorted(before_rules.keys() - after_rules.keys()),
        "changed_thresholds": changed_thresholds,
        "changed_documents": changed_documents,
    }


# Load active regulatory clauses and product version for one preview request.
async def preview_conformance(
    session: AsyncSession,
    configuration: ProductConfiguration,
) -> dict[str, Any]:
    repository = KnowledgeRepository()
    active_regulation = await repository.list_active_shared(
        session, "regulation"
    )
    regulation = active_regulation[0] if active_regulation else None
    passages = (
        await repository.list_passages(session, regulation.id)
        if regulation is not None
        else []
    )
    active_product = await repository.active_product_version(
        session, configuration.product_code
    )
    active_configuration = None
    if active_product is not None:
        try:
            active_configuration = ProductConfiguration.model_validate(
                active_product.configuration
            )
        except ValueError:
            active_configuration = None
    return {
        "conformance": build_conformance(
            configuration,
            regulation.version if regulation is not None else None,
            passages,
        ),
        "change_impact": build_change_impact(
            configuration, active_configuration
        ),
    }


# Return only conformance flags for activation audit records.
async def activation_conformance(
    session: AsyncSession,
    configuration: ProductConfiguration,
) -> dict[str, Any]:
    return (await preview_conformance(session, configuration))["conformance"]
