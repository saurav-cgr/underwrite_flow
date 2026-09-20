from uuid import uuid4

import pytest

from underwriteflow.cases.schemas import ApplicationUpdate
from underwriteflow.cases.service import CaseService, CaseValidationError
from underwriteflow.cases.validation import (
    validate_complete_application,
    validate_draft_application,
)
from underwriteflow.persistence.models import Case
from underwriteflow.persistence.repositories import AuditRepository
from underwriteflow.products.schemas import filter_configuration_for_journey
from underwriteflow.products.service import load_configuration


MOTOR_CONFIGURATION = load_configuration(
    """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Synthetic vehicle age
documents:
  - code: identity_record
    title: Identity
    requirement: required
    accepted_types: [application/pdf]
  - code: inspection_photo
    title: Inspection
    requirement: conditional
    condition: {field: vehicle_age, operator: greater_than, value: 12}
    accepted_types: [image/png]
routing_rules:
  - code: standard
    condition: {field: vehicle_age, operator: greater_than, value: 0}
    route: standard
specialist_labels: [motor inspection]
"""
)

JOURNEY_CONFIGURATION = load_configuration(
    """
product_code: synthetic-motor-journey
title: Synthetic Motor Journey
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
supported_journeys: [new_business, renewal]
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Synthetic vehicle age
    applies_to: [new_business, renewal]
documents:
  - code: identity_record
    title: Identity
    requirement: required
    accepted_types: [application/pdf]
    applies_to: [new_business, renewal]
  - code: previous_policy
    title: Previous policy
    requirement: required
    accepted_types: [application/pdf]
    applies_to: [renewal]
    required_for: [renewal]
    stage: prior_policy
routing_rules:
  - code: standard
    condition: {field: vehicle_age, operator: greater_than, value: 0}
    route: standard
    applies_to: [new_business, renewal]
specialist_labels: [motor inspection]
"""
)


class FailingStorage:
    """Represent an upload volume whose file removal always fails."""

    # Fail every removal request like an unavailable volume.
    def delete(self, storage_key: str) -> None:
        raise OSError(f"synthetic storage failure: {storage_key}")


# Verify required product fields and conditional documents are enforced.
def test_complete_validation_checks_product_requirements() -> None:
    validate_complete_application(
        {"vehicle_age": 14},
        ["identity_record", "inspection_photo"],
        MOTOR_CONFIGURATION,
    )

    with pytest.raises(CaseValidationError):
        validate_complete_application(
            {"vehicle_age": 14}, ["identity_record"], MOTOR_CONFIGURATION
        )


# Verify a draft may omit required fields and required documents.
def test_draft_validation_allows_incomplete_answers() -> None:
    validate_draft_application({}, [], MOTOR_CONFIGURATION)
    validate_draft_application(
        {"vehicle_age": 3}, ["identity_record"], MOTOR_CONFIGURATION
    )


# Verify a draft still rejects a malformed answered field.
def test_draft_validation_rejects_invalid_field_type() -> None:
    with pytest.raises(CaseValidationError):
        validate_draft_application(
            {"vehicle_age": "not-a-number"}, [], MOTOR_CONFIGURATION
        )


# Verify a draft rejects a document code the product never declared.
def test_draft_validation_rejects_unsupported_document_code() -> None:
    with pytest.raises(CaseValidationError):
        validate_draft_application(
            {}, ["unknown_document"], MOTOR_CONFIGURATION
        )


# Verify a renewal-only document is unsupported once filtered to new business.
def test_journey_filter_hides_documents_not_applicable_to_the_journey() -> None:
    new_business = filter_configuration_for_journey(
        JOURNEY_CONFIGURATION, "new_business"
    )

    validate_draft_application(
        {}, ["identity_record"], new_business
    )
    with pytest.raises(CaseValidationError):
        validate_draft_application(
            {}, ["previous_policy"], new_business
        )


# Verify a renewal submission requires its prior-policy document.
def test_complete_validation_requires_renewal_prior_policy() -> None:
    renewal = filter_configuration_for_journey(
        JOURNEY_CONFIGURATION, "renewal"
    )

    with pytest.raises(CaseValidationError):
        validate_complete_application(
            {"vehicle_age": 3}, ["identity_record"], renewal
        )
    validate_complete_application(
        {"vehicle_age": 3},
        ["identity_record", "previous_policy"],
        renewal,
    )


# Verify a case cannot have its application replaced once review starts.
@pytest.mark.asyncio
async def test_replace_application_rejects_after_review_starts() -> None:
    case = Case(id=uuid4(), status="underwriter_review")
    service = CaseService(FailingStorage(), AuditRepository())

    with pytest.raises(CaseValidationError):
        await service.replace_application(
            None,
            case,
            ApplicationUpdate(payload={}, document_codes=[]),
            uuid4(),
        )
