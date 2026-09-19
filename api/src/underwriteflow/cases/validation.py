"""Pure application and document validation against a pinned configuration.

Split out of ``service.py`` to keep that file under the project's 400-line
limit.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from underwriteflow.products.rules import condition_matches
from underwriteflow.products.schemas import (
    ProductConfiguration,
    ProductDocument,
    ProductField,
)
from underwriteflow.workflow.reconciliation import APPLICATION_SOURCE


class CaseValidationError(ValueError):
    """Raised when intake data does not satisfy the pinned product."""


# Decide whether one configured document is required for this application.
def document_is_required(
    document: ProductDocument, payload: Mapping[str, Any]
) -> bool:
    if document.requirement == "required":
        return True
    return document.requirement == "conditional" and condition_matches(
        document.condition or {}, payload
    )


# Decide whether one configured field applies to this application.
def field_is_visible(field: ProductField, payload: Mapping[str, Any]) -> bool:
    return field.visible_when is None or condition_matches(
        field.visible_when, payload
    )


# List the document evidence fields the configured checks read.
def reconciliation_evidence_fields(
    configuration: ProductConfiguration,
) -> list[str]:
    return sorted(
        {
            field_name
            for check in configuration.reconciliations
            for source, field_name in check.inputs.items()
            if source != APPLICATION_SOURCE
        }
    )


# List the fields whose values an application must evidence.
#
# Only visible fields the applicant answered are requested, because an optional
# field nobody filled in is unanswered by choice. Evidence fields a configured
# check reads are always requested, so a comparison has something to read.
def requested_field_keys(
    configuration: ProductConfiguration, payload: Mapping[str, Any]
) -> list[str]:
    answered = [
        field.key
        for field in configuration.fields
        if field.key in payload and field_is_visible(field, payload)
    ]
    evidence_fields = reconciliation_evidence_fields(configuration)
    return answered + [
        key for key in evidence_fields if key not in answered
    ]


# Describe the value shape a provider must return for each requested field.
#
# Evidence fields a check reads have no declared application type, so they are
# requested as text rather than rejected as undeclared.
def field_specifications(
    configuration: ProductConfiguration, requested_fields: list[str]
) -> list[dict[str, object]]:
    declared = {field.key: field for field in configuration.fields}
    return [
        {
            "field_key": key,
            "value_type": (
                declared[key].type if key in declared else "text"
            ),
            "allowed_values": (
                list(declared[key].options) if key in declared else []
            ),
        }
        for key in requested_fields
    ]


# Return the required document codes that are not yet attached to the case.
def missing_document_codes(
    configuration: ProductConfiguration,
    provided_codes: Iterable[str],
    payload: Mapping[str, Any],
) -> list[str]:
    provided = set(provided_codes)
    return sorted(
        document.code
        for document in configuration.documents
        if document_is_required(document, payload)
        and document.code not in provided
    )


# Validate one answered field's type and range against its declaration.
def validate_field_value(field: ProductField, value: Any) -> None:
    if field.type == "integer" and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        raise CaseValidationError(f"invalid field type: {field.key}")
    if field.type == "number" and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        raise CaseValidationError(f"invalid field type: {field.key}")
    if field.type == "boolean" and not isinstance(value, bool):
        raise CaseValidationError(f"invalid field type: {field.key}")
    if field.type == "enum" and value not in field.options:
        raise CaseValidationError(f"invalid field option: {field.key}")
    minimum = field.validation.get("minimum")
    maximum = field.validation.get("maximum")
    try:
        outside_range = (minimum is not None and value < minimum) or (
            maximum is not None and value > maximum
        )
    except TypeError:
        outside_range = True
    if outside_range:
        raise CaseValidationError(f"invalid field range: {field.key}")


# Validate a partial draft: answered fields and document codes must be
# well-formed, but a required field or document may still be missing.
def validate_draft_application(
    payload: Mapping[str, Any],
    document_codes: Iterable[str],
    configuration: ProductConfiguration,
) -> None:
    for field in configuration.fields:
        if field.key in payload:
            validate_field_value(field, payload[field.key])
    known_documents = {document.code for document in configuration.documents}
    if not set(document_codes).issubset(known_documents):
        raise CaseValidationError("unsupported document code")


# Validate a complete submission: every journey-required field and document
# for the pinned, journey-filtered configuration must be present.
def validate_complete_application(
    payload: Mapping[str, Any],
    document_codes: Iterable[str],
    configuration: ProductConfiguration,
) -> None:
    validate_draft_application(payload, document_codes, configuration)
    for field in configuration.fields:
        visible = field_is_visible(field, payload)
        if field.required and visible:
            if field.key not in payload or payload[field.key] in (None, ""):
                raise CaseValidationError(f"missing field: {field.key}")
    provided_documents = set(document_codes)
    for document in configuration.documents:
        if (
            document_is_required(document, payload)
            and document.code not in provided_documents
        ):
            raise CaseValidationError(f"missing document: {document.code}")
