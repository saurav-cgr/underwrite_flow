from underwriteflow.persistence.models import AuditEvent, Case, ProductVersion


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
        getattr(constraint, "name", None) == "uq_product_versions_product_version"
        for constraint in constraints
    )
