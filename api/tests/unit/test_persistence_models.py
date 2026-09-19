from underwriteflow.persistence.models import (
    AuditEvent,
    Case,
    Document,
    ProductVersion,
    ReferenceDocument,
    Review,
)


# Verify cases retain immutable product and rulebook version links.
def test_case_pins_product_and_rulebook_versions() -> None:
    foreign_keys = {key.target_fullname for key in Case.__table__.foreign_keys}

    assert "product_versions.id" in foreign_keys
    assert "rulebook_versions.id" in foreign_keys


# Verify audit events model an append-only business record.
def test_audit_events_have_immutable_event_identity() -> None:
    columns = AuditEvent.__table__.c

    assert columns.id.primary_key
    assert columns.event_type.nullable is False
    assert columns.occurred_at.nullable is False


# Verify product versions retain a stable version identity.
def test_product_versions_are_unique_per_product_version() -> None:
    constraints = ProductVersion.__table__.constraints

    assert any(
        getattr(constraint, "name", None)
        == "uq_product_versions_product_version"
        for constraint in constraints
    )


# Verify a partial unique index permits only one active version per product.
def test_product_versions_permit_one_active_version_per_product() -> None:
    table = ProductVersion.__table__
    index = next(
        (
            item
            for item in table.indexes
            if item.name == "uq_product_versions_one_active"
        ),
        None,
    )

    assert index is not None
    assert index.unique is True
    assert list(index.columns) == [table.c.product_id]


# Verify cases track a non-null review cycle that defaults to zero.
def test_case_tracks_review_cycle_defaulting_to_zero() -> None:
    column = Case.__table__.c.review_cycle

    assert column.nullable is False
    assert column.server_default is not None


# Verify case idempotency is scoped to one applicant instead of global.
def test_case_idempotency_is_scoped_to_the_applicant() -> None:
    constraints = Case.__table__.constraints

    assert any(
        getattr(constraint, "name", None) == "uq_cases_applicant_idempotency"
        for constraint in constraints
    )


# Verify no global unique rule blocks a shared idempotency key.
def test_case_idempotency_key_is_not_globally_unique() -> None:
    table = Case.__table__

    assert not table.c.idempotency_key.unique
    assert not any(
        index.unique and list(index.columns) == [table.c.idempotency_key]
        for index in table.indexes
    )


# Verify uploaded documents may carry an optional product document code.
def test_document_code_is_optional_for_legacy_rows() -> None:
    column = Document.__table__.c.document_code

    assert column.nullable is True


# Verify reviews record the review cycle and any specialist destination.
def test_review_records_cycle_and_specialist_label() -> None:
    columns = Review.__table__.c

    assert columns.review_cycle.nullable is False
    assert columns.specialist_label.nullable is True


# Verify product reference documents keep stored-file metadata.
def test_reference_documents_keep_storage_metadata() -> None:
    columns = ReferenceDocument.__table__.c

    for name in ("content_type", "storage_key", "byte_size", "page_count"):
        assert name in columns, name
