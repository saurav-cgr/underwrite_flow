# Data Model: Governed Underwriting Platform

## Model Rules

- `api/alembic/versions/01_initial.py` remains unchanged.
- All schema work uses one additive revision after revision 06.
- Existing UUID identities and foreign keys remain stable.
- `users.role` remains during migration but stops granting authority.
- Audit events remain append-only through the existing database trigger.
- Product and rulebook versions remain immutable once pinned to a case.

## Relationship Overview

```text
User 1---1 UserRoleMapping *---1 Role
Role 1---* RolePermission *---1 Permission
User 1---* RefreshSession

Product 1---* ProductVersion 1---* RulebookVersion
Case *---1 ProductVersion
Case *---1 RulebookVersion
Case 1---* Document 1---* ExtractedField
Case 1---* Validation
Case 1---* Review
Case 1---* AuditEvent
Case 1---0..1 Recommendation
Case 1---0..1 Handoff
```

One user has one active role for this MVP. The mapping table makes role
configuration dynamic without inventing multi-role merge semantics. Multiple
roles per user can be added later by relaxing the unique user constraint and
defining conflict rules.

## New and Extended Entities

### User (existing, extended)

Purpose: authenticated fictional person and stable actor identity.

| Field | Type | Rules |
| --- | --- | --- |
| `id` | UUID | Existing primary key |
| `email` | string | Existing unique normalized login name |
| `display_name` | string | Existing, 1-200 characters |
| `password_hash` | string | Existing Argon2 encoded hash |
| `is_active` | boolean | Existing; false rejects every session |
| `role` | string | Legacy migration source; no runtime authority |
| `created_at` | timestamp | Existing immutable timestamp |

Validation:

- Email is trimmed and case-folded before lookup and creation.
- Passwords are never returned, logged, audited, or stored in plaintext.
- Referenced users are deactivated, not deleted.

### Role (new)

Purpose: administrator-configurable named permission set.

| Field | Type | Rules |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `code` | string | Unique, stable machine identifier |
| `title` | string | Human-readable, 1-200 characters |
| `description` | string | Optional, at most 500 characters |
| `is_active` | boolean | Inactive roles grant no permissions |
| `is_system` | boolean | Seeded roles cannot be deleted |
| `created_by_user_id` | UUID | Active administrator FK |
| `created_at` | timestamp | Immutable creation time |

Validation:

- Codes use lowercase letters, digits, and underscores.
- A role code is immutable after creation.
- Deactivation is rejected if it would leave no active administrator.

### Permission (new)

Purpose: stable scope catalogue enforced by backend dependencies.

| Field | Type | Rules |
| --- | --- | --- |
| `id` | UUID | Primary key |
| `code` | string | Unique scope such as `cases:read` |
| `title` | string | Human-readable label |
| `description` | string | Optional explanation |
| `created_at` | timestamp | Immutable creation time |

Seeded scopes include all current permission values plus `cases:override`,
`users:manage`, and `schemas:edit`. Administrators compose roles from the fixed
catalogue; this feature does not create executable permission code at runtime.

### RolePermission (new)

Purpose: many-to-many membership between roles and permission scopes.

| Field | Type | Rules |
| --- | --- | --- |
| `role_id` | UUID | FK to role |
| `permission_id` | UUID | FK to permission |
| `assigned_by_user_id` | UUID | Administrator FK |
| `created_at` | timestamp | Immutable assignment time |

Constraints:

- Composite primary or unique key on `(role_id, permission_id)`.
- Removing a mapping appends an audit event in the same transaction.
- Inactive roles are not resolved during authorization.

### UserRoleMapping (new)

Purpose: assign one configured role to one user.

| Field | Type | Rules |
| --- | --- | --- |
| `user_id` | UUID | Primary/unique FK to user |
| `role_id` | UUID | FK to active role |
| `assigned_by_user_id` | UUID | Administrator FK |
| `created_at` | timestamp | Assignment time |

Constraints:

- Exactly one row per active user after migration.
- Changing a role replaces the mapping transactionally and appends audit.
- The final active user with `users:manage` cannot lose that capability.

### RefreshSession (new)

Purpose: rotate and revoke refresh credentials without storing raw tokens.

| Field | Type | Rules |
| --- | --- | --- |
| `id` | UUID | Primary key and token family identifier |
| `user_id` | UUID | FK to active user |
| `token_digest` | string | Unique keyed digest, never returned |
| `expires_at` | timestamp | Required absolute expiry |
| `revoked_at` | timestamp | Null while active |
| `replaced_by_id` | UUID | Nullable self-FK to rotated successor |
| `created_at` | timestamp | Immutable issue time |

Constraints:

- Raw refresh credentials exist only in the login/refresh response and caller
  memory.
- One credential can rotate once. Reuse of a revoked credential revokes its
  replacement chain.
- Disabled users cannot refresh.
- Expired and revoked rows are retained only as long as required for replay
  detection under the approved retention policy.

## Existing Entities Reused

### ProductVersion

The existing `configuration` JSONB gains validated sections, not columns:

```json
{
  "fields": [],
  "documents": [],
  "routing_rules": [],
  "reconciliations": [
    {
      "code": "motor_ncb_match",
      "kind": "ncb_match",
      "inputs": {
        "application": "claimed_ncb_percent",
        "previous_policy": "ncb_percent",
        "claims_history": "claim_count"
      }
    }
  ]
}
```

Rules:

- `code` is unique within a configuration version.
- `kind` is one supported pure implementation.
- Input keys reference declared configured fields and document roles.
- Activation rejects missing or incompatible references.
- Existing cases continue using their pinned JSONB version.

### ExtractedField

Reuse existing fields. `value` remains JSONB so typed Pydantic scalar values
round-trip without per-field columns. `source_locator`, `document_id`,
`confidence`, and `extraction_method` retain provenance.

New validation behavior:

- Field names must be requested by the pinned schema.
- Values must match configured scalar or enum type.
- Source locators must identify a real local page boundary.
- Invalid fields fail that provider branch visibly.

### Validation

Reuse one row per persisted reconciliation check.

| Existing field | Reconciliation use |
| --- | --- |
| `rule_code` | Stable configured check code |
| `status` | `cleared`, `flagged_discrepancy`, or `missing_evidence` |
| `details` | Compared values, reason, evidence refs, rule version |
| `evidence_locator` | Primary locator when one exists |

No separate discrepancy table is required for current query patterns.

### AuditEvent

Reuse the existing append-only entity and database mutation trigger.

Auth and RBAC events include actor, target user/role IDs, action, and changed
scope codes. They exclude credentials, password hashes, JWTs, refresh digests,
and authorization headers.

Provider events include provider/model, attempts, token counts or explicit
unavailable values, redacted request hash, validated result hash, schema
version, and document/case references. They exclude raw prompts and files.

### Review and Handoff

Reuse existing review-cycle uniqueness, mandatory override reason, row locks,
and idempotent handoff. Dynamic permissions do not replace the explicit
underwriter identity requirement.

## Value Objects

### AccessTokenClaims

```text
sub: UUID string
role: stable role code
permissions: sorted unique scope strings
typ: "access"
iat: issued-at Unix time
exp: expiry Unix time
iss: configured issuer
aud: configured audience
jti: random token identifier
```

The role and permissions are snapshots. Authorization compares them with the
active user's current database role and scopes; mismatch requires a new token.

### ReconciliationInput

```text
case_id: UUID
product_version: string
rulebook_version: string
application: normalized configured values
evidence: ordered extracted values with document and source locators
checks: ordered active reconciliation definitions
```

No database session, provider client, file bytes, or secret enters this object.

### FieldComparison

```text
field_key: string
left: normalized value or null
right: normalized value or null
matched: boolean or null when missing
evidence: ordered source references
explanation_code: stable non-sensitive code
```

### ReconciliationResult

```text
check_code: stable configured identifier
kind: ncb_match | asset_match | policy_lapse
status: CLEARED | FLAGGED_DISCREPANCY | MISSING_EVIDENCE
comparisons: ordered FieldComparison list
discrepancies: ordered stable codes
evidence: ordered source references
rule_version: pinned rulebook version
```

Overall case state is derived by precedence:

1. Any `MISSING_EVIDENCE` keeps the case in needs-information state.
2. Otherwise any `FLAGGED_DISCREPANCY` is a specialist signal.
3. Otherwise all configured checks are `CLEARED`.

This result informs triage; it never becomes a final insurance decision.

## State Transitions

### Refresh Session

```text
ACTIVE -> ROTATED -> REVOKED
ACTIVE -> REVOKED
ACTIVE -> EXPIRED
ROTATED + replay -> revoke replacement chain
```

### Role Assignment

```text
legacy users.role -> backfilled UserRoleMapping
assigned role A -> transactional replacement with role B
active role -> inactive role grants no access
```

### Configuration

```text
DRAFT -> VALIDATED -> ACTIVE -> RETIRED
```

Only one product version is active per product, while each case remains pinned
to the version selected when processing started.

### Case Evidence

```text
uploaded -> locally extracted -> provider validated -> reconciled
provider/local failure -> visible review gap
reconciled -> human review interrupt -> confirmed/overridden
confirmed/overridden -> idempotent completion
```

## Migration Strategy

1. Obtain explicit approval for schema and authentication changes.
2. Add the five new RBAC/session tables in one revision after revision 06.
3. Seed permissions and the three existing system roles idempotently.
4. Backfill one user-role mapping from every known `users.role` value.
5. Fail migration if any legacy role cannot map exactly; never guess.
6. Deploy database-backed scope reads while retaining the legacy column.
7. Remove legacy runtime reads only after contract and integration tests pass.
8. Defer column removal to a separately approved later migration.
