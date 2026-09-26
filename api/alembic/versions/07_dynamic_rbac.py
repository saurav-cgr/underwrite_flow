"""Add database-backed roles, permissions, and refresh sessions.

Revision 07 is the additive step behind dynamic authorization. It creates the
role, permission, role-permission, user-role, and refresh-session tables,
seeds the fixed scope catalogue and the three fictional system roles, and
backfills exactly one role mapping for every existing user.

The legacy ``users.role`` column is preserved so the cutover stays reversible.
It stops granting authority once ``auth/dependencies.py`` resolves scopes from
these tables, and its removal is deferred to a separately approved revision.

Revision ID: 07
Revises: e5f6a7b8c9d0
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "07"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None

# Legacy `users.role` values mapped to exactly one stable role code each.
LEGACY_ROLE_CODES = {
    "Applicant": "applicant",
    "Underwriter": "underwriter",
    "Administrator": "administrator",
}

# The three fictional system roles, as (id, code, title, description).
SYSTEM_ROLES = (
    (
        "00000000-0000-0000-0000-000000000201",
        "applicant",
        "Applicant",
        "Fictional applicant who owns and submits cases.",
    ),
    (
        "00000000-0000-0000-0000-000000000202",
        "underwriter",
        "Underwriter",
        "Fictional underwriter who confirms or overrides a route.",
    ),
    (
        "00000000-0000-0000-0000-000000000203",
        "administrator",
        "Administrator",
        "Fictional administrator who manages users and configuration.",
    ),
)

# The fixed scope catalogue, as (id, code, title).
PERMISSION_CATALOGUE = (
    ("00000000-0000-0000-0000-000000000301", "cases:read", "Read cases"),
    ("00000000-0000-0000-0000-000000000302", "cases:write", "Write cases"),
    (
        "00000000-0000-0000-0000-000000000303",
        "cases:override",
        "Override a triage route",
    ),
    ("00000000-0000-0000-0000-000000000304", "reviews:read", "Read reviews"),
    ("00000000-0000-0000-0000-000000000305", "reviews:write", "Write reviews"),
    ("00000000-0000-0000-0000-000000000306", "audit:read", "Read audit"),
    (
        "00000000-0000-0000-0000-000000000307",
        "product_config:read",
        "Read product configuration",
    ),
    (
        "00000000-0000-0000-0000-000000000308",
        "product_config:write",
        "Import or activate product configuration",
    ),
    ("00000000-0000-0000-0000-000000000309", "users:manage", "Manage users"),
    (
        "00000000-0000-0000-0000-00000000030a",
        "schemas:edit",
        "Edit extraction and rulebook schemas",
    ),
    (
        "00000000-0000-0000-0000-00000000030b",
        "evaluation:run",
        "Run the synthetic evaluation",
    ),
)

# Seeded role-to-scope pairs, which mirror the pre-migration role matrix.
ROLE_SCOPES = (
    ("applicant", "cases:read"),
    ("applicant", "cases:write"),
    ("underwriter", "cases:read"),
    ("underwriter", "cases:override"),
    ("underwriter", "reviews:read"),
    ("underwriter", "reviews:write"),
    ("administrator", "cases:read"),
    ("administrator", "cases:write"),
    ("administrator", "cases:override"),
    ("administrator", "reviews:read"),
    ("administrator", "reviews:write"),
    ("administrator", "audit:read"),
    ("administrator", "product_config:read"),
    ("administrator", "product_config:write"),
    ("administrator", "users:manage"),
    ("administrator", "schemas:edit"),
    ("administrator", "evaluation:run"),
)


# Abort the upgrade while any persisted legacy role has no exact mapping.
def raise_on_unmappable_roles() -> None:
    found = (
        op.get_bind()
        .execute(sa.text("SELECT DISTINCT role FROM users ORDER BY role"))
        .fetchall()
    )
    unknown = sorted(row[0] for row in found if row[0] not in LEGACY_ROLE_CODES)
    if not unknown:
        return
    raise RuntimeError(
        "cannot add dynamic RBAC because these legacy user roles have no "
        f"exact mapping: {unknown}. Map them in LEGACY_ROLE_CODES before "
        "upgrading; this revision never guesses a role."
    )


# Create the RBAC and refresh-session tables.
def create_tables() -> None:
    op.create_table(
        "roles",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_table(
        "user_role_mappings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_digest", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )


# Seed the fixed scope catalogue and the three fictional system roles.
def seed_roles_and_permissions() -> None:
    permission_statement = sa.text(
        "INSERT INTO permissions (id, code, title) "
        "VALUES (CAST(:id AS uuid), :code, :title) "
        "ON CONFLICT (code) DO NOTHING"
    )
    for identifier, code, title in PERMISSION_CATALOGUE:
        op.execute(
            permission_statement.bindparams(
                id=identifier, code=code, title=title
            )
        )
    role_statement = sa.text(
        "INSERT INTO roles (id, code, title, description, is_active, "
        "is_system) VALUES (CAST(:id AS uuid), :code, :title, :description, "
        "true, true) ON CONFLICT (code) DO NOTHING"
    )
    for identifier, code, title, description in SYSTEM_ROLES:
        op.execute(
            role_statement.bindparams(
                id=identifier,
                code=code,
                title=title,
                description=description,
            )
        )
    pair_statement = sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT roles.id, permissions.id FROM roles, permissions "
        "WHERE roles.code = :role_code AND permissions.code = :scope "
        "ON CONFLICT DO NOTHING"
    )
    for role_code, scope in ROLE_SCOPES:
        op.execute(pair_statement.bindparams(role_code=role_code, scope=scope))


# Give every existing user exactly one mapping derived from its legacy role.
def backfill_user_role_mappings() -> None:
    cases = " ".join(
        f"WHEN '{legacy}' THEN '{code}'"
        for legacy, code in LEGACY_ROLE_CODES.items()
    )
    op.execute(
        sa.text(
            "INSERT INTO user_role_mappings (user_id, role_id) "
            "SELECT users.id, roles.id FROM users JOIN roles "
            f"ON roles.code = CASE users.role {cases} END "
            "ON CONFLICT (user_id) DO NOTHING"
        )
    )
    unmapped = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM users LEFT JOIN user_role_mappings "
                "ON user_role_mappings.user_id = users.id "
                "WHERE user_role_mappings.user_id IS NULL"
            )
        )
        .scalar()
    )
    if unmapped:
        raise RuntimeError(
            f"backfill left {unmapped} users without a role mapping"
        )


# Add the RBAC and refresh-session foundation additively.
def upgrade() -> None:
    raise_on_unmappable_roles()
    create_tables()
    seed_roles_and_permissions()
    backfill_user_role_mappings()


# Remove only the tables this additive revision introduced.
def downgrade() -> None:
    op.drop_table("user_role_mappings")
    op.drop_table("role_permissions")
    op.drop_table("refresh_sessions")
    op.drop_table("roles")
    op.drop_table("permissions")

