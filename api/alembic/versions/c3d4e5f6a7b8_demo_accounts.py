"""Add the three fictional demo accounts to the fresh local database."""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2e0f1d3c4a5"
branch_labels = None
depends_on = None

DEMO_ACCOUNTS = (
    {
        "id": "00000000-0000-0000-0000-000000000101",
        "email": "applicant@synthetic.test",
        "display_name": "Synthetic Applicant",
        "role": "Applicant",
        "password_hash": (
            "$argon2id$v=19$m=65536,t=3,p=4$VZbd65rzyKhy9kG3Au22Sg$"
            "jc07Y+UtLQnGZvR5IGSRlVIOw1m4VG6QSCrZxtMv+sU"
        ),
    },
    {
        "id": "00000000-0000-0000-0000-000000000102",
        "email": "underwriter@synthetic.test",
        "display_name": "Synthetic Underwriter",
        "role": "Underwriter",
        "password_hash": (
            "$argon2id$v=19$m=65536,t=3,p=4$UK8YVH+C4nG3A6Tx4O6Szg$"
            "VZSFpuyMbzqY9d8vGMs2xJZ2ndGjFhyteQmxSkGcNHI"
        ),
    },
    {
        "id": "00000000-0000-0000-0000-000000000103",
        "email": "administrator@synthetic.test",
        "display_name": "Synthetic Administrator",
        "role": "Administrator",
        "password_hash": (
            "$argon2id$v=19$m=65536,t=3,p=4$Y3lsPpGMHTP/6jFglUAS7A$"
            "SnSA/+9dQbSqn1XWefkcT716CzpaOII0lKW2pLPMOeE"
        ),
    },
)


# Insert the fictional accounts without replacing existing local identities.
def upgrade() -> None:
    statement = sa.text(
        """
        INSERT INTO users (
            id, email, display_name, role, password_hash, is_active
        ) VALUES (
            CAST(:id AS uuid), :email, :display_name, :role,
            :password_hash, true
        )
        ON CONFLICT (email) DO NOTHING
        """
    )
    for account in DEMO_ACCOUNTS:
        op.execute(statement.bindparams(**account))


# Remove only unused accounts created by this migration on downgrade.
def downgrade() -> None:
    statement = sa.text(
        """
        DELETE FROM users AS demo
        WHERE demo.email IN (
            :applicant_email, :underwriter_email, :administrator_email
        )
          AND NOT EXISTS (
              SELECT 1 FROM product_versions
              WHERE activated_by_user_id = demo.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM reference_documents
              WHERE uploaded_by_user_id = demo.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM cases
              WHERE applicant_user_id = demo.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM reviews
              WHERE reviewer_user_id = demo.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM audit_events
              WHERE actor_user_id = demo.id
          )
        """
    )
    op.execute(
        statement.bindparams(
            applicant_email=DEMO_ACCOUNTS[0]["email"],
            underwriter_email=DEMO_ACCOUNTS[1]["email"],
            administrator_email=DEMO_ACCOUNTS[2]["email"],
        )
    )
