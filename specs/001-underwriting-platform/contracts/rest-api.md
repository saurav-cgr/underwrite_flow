# REST API Contract

Base path: `/api/v1`

Transport: JSON over HTTP except multipart document upload and binary document
preview. GraphQL and gRPC are out of scope.

## Common Security

Secured operations require:

```http
Authorization: Bearer <access-jwt>
```

Access JWT claims:

```json
{
  "sub": "00000000-0000-0000-0000-000000000102",
  "role": "underwriter",
  "permissions": ["cases:override", "cases:read"],
  "typ": "access",
  "iat": 1789600000,
  "exp": 1789600900,
  "iss": "underwriteflow",
  "aud": "underwriteflow-web",
  "jti": "generated-uuid"
}
```

Role and permission claims are snapshots. The API authorizes against current
active database assignments and rejects stale claims.

Common error envelope:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Forbidden",
    "request_id": "generated-uuid",
    "retryable": false
  }
}
```

Every response retains `X-Request-ID`. Validation failures reveal no secrets,
raw provider content, or internal exceptions.

## Authentication

### `POST /auth/login`

Public. Authenticates one active synthetic user.

Request:

```json
{
  "email": "underwriter@synthetic.test",
  "password": "provided-at-runtime"
}
```

Response `200`:

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-random-value",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_expires_in": 28800
}
```

Errors: `401 invalid_credentials`, `403 inactive_user`.

### `POST /auth/session`

Temporary compatibility alias for the current web client. It authenticates the
same request and returns the legacy `{token, token_type, expires_in}` body so
the running client keeps working until it migrates to `/auth/login`. It is
removed only in a later contract change.

### `POST /auth/refresh`

Public but credential-protected. Rotates one refresh credential.

Request:

```json
{
  "refresh_token": "opaque-random-value"
}
```

Response `200`: same shape as login, with new access and refresh credentials.

Errors: `401 invalid_refresh`, `401 refresh_reuse_detected`,
`403 inactive_user`.

### `GET /auth/me`

Scope: authenticated user.

Response `200`:

```json
{
  "id": "00000000-0000-0000-0000-000000000102",
  "email": "underwriter@synthetic.test",
  "display_name": "Synthetic Underwriter",
  "role": {"id": "generated-uuid", "code": "underwriter"},
  "permissions": ["cases:override", "cases:read"]
}
```

## Users and Roles

All operations require `users:manage`.

### `GET /admin/users`

Returns active and inactive users. Query parameters: `status`, `limit`, and
opaque `cursor`. Default limit 50, maximum 100.

### `POST /admin/users`

```json
{
  "email": "reviewer@synthetic.test",
  "display_name": "Synthetic Reviewer",
  "password": "initial-secret",
  "role_id": "generated-uuid"
}
```

Creates an active user, hashes the password with Argon2, assigns one role, and
appends audit in one transaction. Response `201` excludes password material.

### `PATCH /admin/users/{user_id}`

Allows `display_name`, `is_active`, and `role_id`. Deactivation revokes active
refresh sessions. Rejects removal of the final active administrator.

### `GET /admin/roles`

Returns role metadata and sorted permission scopes.

### `POST /admin/roles`

```json
{
  "code": "claims_reviewer",
  "title": "Claims Reviewer",
  "description": "Synthetic claims review role",
  "permissions": ["cases:read"]
}
```

Creates one role and its permission mappings transactionally. Response `201`.

### `PATCH /admin/roles/{role_id}`

Allows `title`, `description`, `is_active`, and complete replacement of the
permission list. Unknown permission codes fail with `422`.

### `GET /admin/permissions`

Returns the fixed permission catalogue. This feature does not allow runtime
creation of executable permission codes.

## Configuration

Write operations require `schemas:edit`; reads require
`product_config:read` or the narrower existing route permission.

Existing routes remain:

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/products` | List products and active versions |
| POST | `/products/validate` | Validate YAML without persistence |
| POST | `/products/preview` | Render validated effects |
| POST | `/products/import` | Persist a draft version |
| GET | `/products/{code}/history` | List immutable versions |
| POST | `/products/{code}/activate` | Activate one version |
| POST | `/products/{code}/retire` | Retire one version |

Validation includes field, document, routing, and reconciliation references.
Activation never changes cases already pinned to a version.

## Cases and Documents

Existing paths and payloads remain authoritative:

| Method | Path | Required authority |
| --- | --- | --- |
| POST | `/cases` | `cases:write` plus applicant identity |
| GET | `/cases` | `cases:read` plus ownership filtering |
| GET | `/cases/{case_id}` | `cases:read` plus ownership |
| GET | `/cases/{case_id}/configuration` | Same as case read |
| POST | `/cases/{case_id}/documents` | `cases:write` plus ownership |
| GET | `/cases/{case_id}/documents` | `cases:read` plus ownership |
| DELETE | `/cases/{case_id}/documents/{id}` | write plus ownership |
| POST | `/cases/{case_id}/submit` | write plus ownership |
| POST | `/cases/{case_id}/resubmit` | write plus ownership |

Submit/resubmit returns an awaiting-review recommendation after extraction and
reconciliation reach the existing human interrupt. Provider failure is a typed
review signal, not an unhandled error.

## Queue, Review, and Completion

### `GET /queues`

Scope: `cases:read`. Existing `status` and `awaiting_handoff` filters remain.
Each item adds counts for cleared, flagged, and missing reconciliation checks.

### `POST /reviews/{case_id}/start`

Scope: `cases:read`; underwriter identity required. Returns the existing review
pack plus ordered reconciliation results and confidence source labels.

### `POST /reviews/{case_id}`

Scope: `cases:override`; underwriter identity required.

Existing request remains:

```json
{
  "action": "override",
  "selected_route": "specialist",
  "specialist_label": "Document consistency review",
  "reason": "Synthetic engine number mismatch requires review",
  "evidence_acknowledged": true
}
```

Override and information-request reasons are mandatory. Duplicate review-cycle
commands return the existing conflict response and do not append twice.

### `POST /completion/{case_id}`

Scope: `cases:override`; underwriter identity required. Completion remains
idempotent and succeeds only after confirmed or overridden final routing.

## Audit

### `GET /audit/cases/{case_id}`

Scope: `audit:read`. Returns existing immutable events. Provider events expose
hashes, provider/model identifiers, token counts or `null` with an unavailable
marker, attempts, and schema versions. Raw prompts and documents never appear.

Global user/role audit access MAY be added as a filtered `GET /audit` route
only if the admin UI needs it during implementation; case audit remains
unchanged.

## Scope Catalogue

Minimum scopes used by this feature:

- `cases:read`
- `cases:write`
- `cases:override`
- `users:manage`
- `schemas:edit`
- `audit:read`
- `evaluation:run`

Existing equivalent scope names are migrated once, not maintained as permanent
aliases.
