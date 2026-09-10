from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile

from underwriteflow.cases.schemas import CaseCreate
from underwriteflow.cases.service import CaseValidationError, validate_application
from underwriteflow.cases.storage import UploadStorage
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


# Verify required product fields and conditional documents are enforced.
def test_application_validation_checks_product_requirements() -> None:
    application = CaseCreate(
        product_code="synthetic-motor",
        idempotency_key="synthetic-case-1",
        payload={"vehicle_age": 14},
        document_codes=["identity_record", "inspection_photo"],
    )

    validate_application(application, MOTOR_CONFIGURATION)

    missing = application.model_copy(update={"document_codes": ["identity_record"]})
    with pytest.raises(CaseValidationError):
        validate_application(missing, MOTOR_CONFIGURATION)


# Verify uploads use generated case-scoped keys and preserve content hashes.
@pytest.mark.asyncio
async def test_upload_storage_rejects_unsafe_types_and_hashes_content(tmp_path: Path) -> None:
    storage = UploadStorage(tmp_path)
    upload = UploadFile(
        filename="../../synthetic.pdf",
        file=BytesIO(b"SYNTHETIC - FOR DEMONSTRATION ONLY"),
        headers={"content-type": "application/pdf"},
    )

    stored = await storage.save(upload, "case-123")

    assert stored.storage_key.startswith("case-123/")
    assert ".." not in stored.storage_key
    assert stored.byte_size == len(b"SYNTHETIC - FOR DEMONSTRATION ONLY")
    assert stored.content_hash
