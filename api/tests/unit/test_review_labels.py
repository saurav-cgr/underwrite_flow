"""Specialist destination labels must resolve to the pinned configuration."""

import pytest
from fastapi import HTTPException

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.service import load_configuration
from underwriteflow.reviews.router import require_specialist_label
from underwriteflow.reviews.schemas import ReviewCommand

SPECIALIST_CONFIGURATION = """
product_code: synthetic-motor
title: Synthetic Motor
family: motor
scope: Fictional demonstration only
description: Synthetic product configuration
version: v1
status: draft
fields:
  - key: vehicle_age
    label: Vehicle age
    type: integer
    required: true
    help_text: Enter a fictional vehicle age.
documents:
  - code: synthetic_identity
    title: Synthetic identity record
    requirement: required
    accepted_types: [application/pdf]
routing_rules:
  - code: synthetic_specialist
    condition: {field: vehicle_age, operator: greater_than, value: 12}
    route: specialist
    specialist_label: motor inspection
specialist_labels: [motor inspection, synthetic desk]
"""


# Build one small synthetic configuration for label validation tests.
def specialist_configuration() -> ProductConfiguration:
    return load_configuration(SPECIALIST_CONFIGURATION)


# Verify confirming a manual recommendation requires a configured label.
def test_manual_recommendation_requires_specialist_label() -> None:
    command = ReviewCommand(action="confirm", evidence_acknowledged=True)

    with pytest.raises(HTTPException) as error:
        require_specialist_label(command, "manual", specialist_configuration())

    assert error.value.status_code == 422


# Verify a configured label satisfies a manual recommendation.
def test_manual_recommendation_accepts_configured_label() -> None:
    command = ReviewCommand(
        action="confirm",
        specialist_label="synthetic desk",
        evidence_acknowledged=True,
    )

    require_specialist_label(command, "manual", specialist_configuration())


# Verify a label outside the pinned vocabulary is refused.
def test_manual_recommendation_rejects_unconfigured_label() -> None:
    command = ReviewCommand(
        action="confirm",
        specialist_label="synthetic unconfigured desk",
        evidence_acknowledged=True,
    )

    with pytest.raises(HTTPException) as error:
        require_specialist_label(command, "manual", specialist_configuration())

    assert error.value.status_code == 422


# Verify a non-specialist resolution never demands a label.
def test_standard_resolution_requires_no_label() -> None:
    command = ReviewCommand(
        action="override",
        selected_route="standard",
        reason="Synthetic override reason",
        evidence_acknowledged=True,
    )

    require_specialist_label(command, "manual", specialist_configuration())
