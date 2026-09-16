"""Specialist destination labels must resolve to the pinned configuration."""

import pytest
from fastapi import HTTPException

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.service import load_configuration
from underwriteflow.reviews.router import (
    FALLBACK_SPECIALIST_LABEL,
    recover_review_command,
    require_specialist_label,
)
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


# Verify an unreadable configuration still requires a label for specialists.
def test_unreadable_configuration_still_requires_a_label() -> None:
    command = ReviewCommand(action="confirm", evidence_acknowledged=True)

    with pytest.raises(HTTPException) as error:
        require_specialist_label(command, "manual", None)

    assert error.value.status_code == 422


# Verify an unreadable configuration accepts only its fixed fallback label.
def test_unreadable_configuration_accepts_fallback_label() -> None:
    command = ReviewCommand(
        action="confirm",
        specialist_label=FALLBACK_SPECIALIST_LABEL,
        evidence_acknowledged=True,
    )

    require_specialist_label(command, "manual", None)


# Verify an unreadable configuration rejects an arbitrary specialist label.
def test_unreadable_configuration_rejects_unknown_label() -> None:
    command = ReviewCommand(
        action="confirm",
        specialist_label="unverifiable desk",
        evidence_acknowledged=True,
    )

    with pytest.raises(HTTPException) as error:
        require_specialist_label(command, "manual", None)

    assert error.value.status_code == 422


# Verify a retry can repair only a missing legacy specialist label.
def test_recovered_command_repairs_missing_specialist_label() -> None:
    stored = ReviewCommand(action="confirm", evidence_acknowledged=True)
    retry = ReviewCommand(
        action="override",
        selected_route="standard",
        specialist_label="synthetic desk",
        reason="This retry must not replace the stored decision.",
        evidence_acknowledged=True,
    )

    recovered = recover_review_command(
        stored,
        retry,
        "specialist",
        specialist_configuration(),
    )

    assert recovered.action == "confirm"
    assert recovered.selected_route is None
    assert recovered.reason is None
    assert recovered.specialist_label == "synthetic desk"


# Verify a valid checkpoint label remains authoritative during recovery.
def test_recovered_command_keeps_valid_specialist_label() -> None:
    stored = ReviewCommand(
        action="confirm",
        specialist_label="motor inspection",
        evidence_acknowledged=True,
    )
    retry = ReviewCommand(
        action="confirm",
        specialist_label="synthetic desk",
        evidence_acknowledged=True,
    )

    recovered = recover_review_command(
        stored,
        retry,
        "specialist",
        specialist_configuration(),
    )

    assert recovered.specialist_label == "motor inspection"


# Verify a retry replaces an invalid legacy label without changing the decision.
def test_recovered_command_repairs_invalid_specialist_label() -> None:
    stored = ReviewCommand(
        action="confirm",
        specialist_label="retired desk",
        evidence_acknowledged=True,
    )
    retry = ReviewCommand(
        action="confirm",
        specialist_label="motor inspection",
        evidence_acknowledged=True,
    )

    recovered = recover_review_command(
        stored,
        retry,
        "specialist",
        specialist_configuration(),
    )

    assert recovered.action == "confirm"
    assert recovered.selected_route is None
    assert recovered.specialist_label == "motor inspection"


# Verify a retry cannot alter a recovered non-specialist decision.
def test_recovered_command_keeps_non_specialist_decision() -> None:
    stored = ReviewCommand(
        action="override",
        selected_route="standard",
        reason="Stored checkpoint decision.",
        evidence_acknowledged=True,
    )
    retry = ReviewCommand(
        action="override",
        selected_route="specialist",
        specialist_label="synthetic desk",
        reason="Different retry decision.",
        evidence_acknowledged=True,
    )

    recovered = recover_review_command(
        stored,
        retry,
        "expedited",
        specialist_configuration(),
    )

    assert recovered == stored


# Verify recovery refuses an invalid replacement specialist label.
def test_recovered_command_rejects_invalid_replacement_label() -> None:
    stored = ReviewCommand(action="confirm", evidence_acknowledged=True)
    retry = ReviewCommand(
        action="confirm",
        specialist_label="unknown desk",
        evidence_acknowledged=True,
    )

    with pytest.raises(HTTPException) as error:
        recover_review_command(
            stored,
            retry,
            "specialist",
            specialist_configuration(),
        )

    assert error.value.status_code == 422
