"""Journey types and pure journey-aware configuration operations.

Kept separate from ``schemas.py`` so that file stays under the project's
400-line limit. Every function here is duck-typed against the product
configuration models rather than importing them, which also avoids a
circular import between the two modules.
"""

from typing import Any, Literal

JourneyType = Literal["new_business", "renewal"]
DocumentStage = Literal["prior_policy", "supporting"]

DEFAULT_JOURNEYS: list[JourneyType] = ["new_business"]


# Return a fresh default single-journey list for a Pydantic field default.
def default_journeys() -> list[JourneyType]:
    return list(DEFAULT_JOURNEYS)


# Reject a journey list that is not fully declared as supported.
def require_subset(
    journeys: list[str], supported: set[str], where: str
) -> None:
    unsupported = sorted(set(journeys) - supported)
    if unsupported:
        raise ValueError(f"{where}: undeclared journeys {unsupported}")


# Reject a condition field unavailable on the given journey.
def require_journey_field(
    condition: dict[str, Any],
    fields_by_key: dict[str, Any],
    journey: str,
    where: str,
) -> None:
    field = fields_by_key.get(condition.get("field"))
    if field is not None and journey not in field.applies_to:
        raise ValueError(
            f"{where}: field {condition.get('field')!r} is not available "
            f"on journey {journey!r}"
        )


# Reject a reconciliation source unavailable on the given journey.
def require_reconciliation_journey(
    check: Any,
    fields_by_key: dict[str, Any],
    documents_by_code: dict[str, Any],
    journey: str,
    application_source: str,
) -> None:
    where = f"reconciliation {check.code}"
    claimed = check.inputs.get(application_source)
    if claimed is not None:
        field = fields_by_key.get(claimed)
        if field is not None and journey not in field.applies_to:
            raise ValueError(
                f"{where}: application field {claimed!r} is not available "
                f"on journey {journey!r}"
            )
    for source in check.inputs:
        if source == application_source:
            continue
        document = documents_by_code.get(source)
        if document is not None and journey not in document.applies_to:
            raise ValueError(
                f"{where}: document {source!r} is not available on "
                f"journey {journey!r}"
            )
    parameter_field = getattr(check.parameters, "claim_count_field", None)
    if parameter_field is not None:
        field = fields_by_key.get(parameter_field)
        if field is not None and journey not in field.applies_to:
            raise ValueError(
                f"{where}: parameter field {parameter_field!r} is not "
                f"available on journey {journey!r}"
            )


# Validate every field, document, rule, and reconciliation journey reference.
def validate_journeys(configuration: Any, application_source: str) -> None:
    supported = set(configuration.supported_journeys)
    fields_by_key = {field.key: field for field in configuration.fields}
    documents_by_code = {doc.code: doc for doc in configuration.documents}
    for field in configuration.fields:
        require_subset(field.applies_to, supported, f"field {field.key}")
    for document in configuration.documents:
        where = f"document {document.code}"
        require_subset(document.applies_to, supported, where)
        if document.required_for is not None:
            require_subset(
                document.required_for,
                set(document.applies_to),
                f"{where} required_for",
            )
        if (
            document.stage == "prior_policy"
            and "renewal" not in document.applies_to
        ):
            raise ValueError(
                f"{where}: prior_policy evidence must apply to renewal"
            )
    for rule in configuration.routing_rules:
        where = f"rule {rule.code}"
        require_subset(rule.applies_to, supported, where)
        for journey in rule.applies_to:
            require_journey_field(rule.condition, fields_by_key, journey, where)
    for check in configuration.reconciliations:
        require_subset(
            check.applies_to, supported, f"reconciliation {check.code}"
        )
        for journey in check.applies_to:
            require_reconciliation_journey(
                check,
                fields_by_key,
                documents_by_code,
                journey,
                application_source,
            )
    if "renewal" in supported:
        has_required_prior_policy = any(
            document.stage == "prior_policy"
            and document.required_for
            and "renewal" in document.required_for
            for document in configuration.documents
        )
        if not has_required_prior_policy:
            raise ValueError(
                "a renewal-supporting product requires at least one "
                "prior_policy document required for renewal"
            )


# Return the same configuration shape containing only items that apply to
# the given journey. Never mutates the input; the input remains reusable for
# any other journey.
def filter_configuration_for_journey(configuration: Any, journey: str) -> Any:
    if journey not in configuration.supported_journeys:
        raise ValueError(f"unsupported journey {journey!r}")
    return configuration.model_copy(
        update={
            "fields": [
                field
                for field in configuration.fields
                if journey in field.applies_to
            ],
            "documents": [
                document
                for document in configuration.documents
                if journey in document.applies_to
            ],
            "routing_rules": [
                rule
                for rule in configuration.routing_rules
                if journey in rule.applies_to
            ],
            "reconciliations": [
                check
                for check in configuration.reconciliations
                if journey in check.applies_to
            ],
        }
    )
