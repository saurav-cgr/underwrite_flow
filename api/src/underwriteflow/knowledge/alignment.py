"""Deterministic alignment between corpus claims and product config."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from underwriteflow.knowledge.corpus import GuidelineCorpus, Threshold
from underwriteflow.products.schemas import ProductConfiguration

NUMBER_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?(?![A-Za-z0-9])"
)


# Compare numeric values without treating formatting as a mismatch.
def values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return left == right


# Return one stable mismatch issue for a threshold claim.
def threshold_mismatch(
    section_id: str, threshold: Threshold, rule_value: Any
) -> dict[str, Any]:
    return {
        "code": "threshold_mismatch",
        "section_id": section_id,
        "stated": threshold.value,
        "rule_value": rule_value,
        "rule_code": threshold.rule_code,
    }


# Compare a threshold with one condition-shaped product rule.
def condition_issue(
    section_id: str,
    threshold: Threshold,
    condition: dict[str, Any],
) -> dict[str, Any] | None:
    operator = condition.get("operator") or "equals"
    expected = condition.get("value")
    if (
        threshold.field != condition.get("field")
        or threshold.operator != operator
        or not values_equal(threshold.value, expected)
    ):
        return threshold_mismatch(section_id, threshold, expected)
    return None


# Match one threshold to a routing rule, document condition, or parameter.
def align_threshold(
    section_id: str,
    threshold: Threshold,
    configuration: ProductConfiguration,
) -> dict[str, Any] | None:
    code = threshold.rule_code
    if code.startswith("document:"):
        document_code = code.removeprefix("document:")
        document = next(
            (
                item
                for item in configuration.documents
                if item.code == document_code
            ),
            None,
        )
        if document is None or document.condition is None:
            return {
                "code": "unknown_rule",
                "section_id": section_id,
                "rule_code": code,
            }
        return condition_issue(section_id, threshold, document.condition)
    if code.startswith("reconciliation:"):
        reconciliation_code = code.removeprefix("reconciliation:")
        check = next(
            (
                item
                for item in configuration.reconciliations
                if item.code == reconciliation_code
            ),
            None,
        )
        parameter = getattr(check, "parameters", None) if check else None
        expected = getattr(parameter, threshold.field, None)
        if check is None or parameter is None or expected is None:
            return {
                "code": "unknown_rule",
                "section_id": section_id,
                "rule_code": code,
            }
        if threshold.operator != "equals" or not values_equal(
            threshold.value, expected
        ):
            return threshold_mismatch(section_id, threshold, expected)
        return None
    rule = next(
        (item for item in configuration.routing_rules if item.code == code),
        None,
    )
    if rule is None:
        return {
            "code": "unknown_rule",
            "section_id": section_id,
            "rule_code": code,
        }
    return condition_issue(section_id, threshold, rule.condition)


# Find body numbers that are absent from thresholds and section bands.
def undeclared_numbers(
    section: Any,
) -> list[dict[str, Any]]:
    allowed = [
        threshold.value
        for threshold in section.thresholds
        if isinstance(threshold.value, (int, float))
        and not isinstance(threshold.value, bool)
    ]
    allowed.extend(
        value
        for value in (
            section.age_min,
            section.age_max,
            section.sum_assured_min,
            section.sum_assured_max,
        )
        if value is not None
    )
    issues = []
    for match in NUMBER_PATTERN.finditer(section.body):
        text = match.group().replace(",", "")
        number: int | float = (
            float(text) if "." in text else int(text)
        )
        if not any(values_equal(number, value) for value in allowed):
            issues.append(
                {
                    "code": "undeclared_number",
                    "section_id": section.id,
                    "number": number,
                }
            )
    return issues


# Validate every corpus claim and prose number against one product version.
def check_alignment(
    corpus: GuidelineCorpus,
    configuration: ProductConfiguration,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if (
        corpus.product_code != configuration.product_code
        or corpus.aligned_product_version != configuration.version
    ):
        issues.append(
            {
                "code": "product_version_not_found",
                "product_code": corpus.product_code,
                "version": corpus.aligned_product_version,
            }
        )
    for section in corpus.sections:
        for threshold in section.thresholds:
            issue = align_threshold(
                section.id,
                threshold,
                configuration,
            )
            if issue is not None:
                issues.append(issue)
        issues.extend(undeclared_numbers(section))
    return {"valid": not issues, "issues": issues}
