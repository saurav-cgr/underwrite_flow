# Research: Governed Underwriting Platform

## Method

Research followed the requested RESHADED order: requirements, estimation,
schema, high-level design, APIs, detailed design, evaluation, and distinctive
feature. The framework supplies ordering, not mandatory infrastructure. The
project constitution, current code, finalized MVP decisions, and measured
pilot targets remain authoritative.

Reference: user-provided article, *Stop Designing Systems Randomly: A
Practical Architecture Framework (RESHADED)*.

## Decision 1: Extend the Modular Monolith

**Decision**: Keep one FastAPI service, one React application, one PostgreSQL
database, local upload storage, and optional Ollama in Docker Compose.

**Rationale**: The existing code already owns authentication, case intake,
providers, workflow, products, queues, reviews, and audit. Pilot load is 100
cases/day and 20 simultaneous users. A second service adds coordination and
failure modes without removing the dominant OCR/provider bottleneck.

**Alternatives considered**:

- Auth microservice: rejected; one tenant and one API need no network boundary.
- Separate extraction workers: deferred until ten-case tests show request
  exhaustion after a process-local concurrency limit.
- Redis, Kafka, or Celery: rejected by MVP constraints and absent need.

## Decision 2: Reuse Existing Authentication Primitives

**Decision**: Extend `AuthService`, bearer parsing, Argon2 password hashing,
active-user lookup, and route dependencies. Emit strict HS256 access JWTs with
role and permission snapshots, but authorize against current PostgreSQL state.

**Rationale**: Existing code already verifies Argon2 passwords, signs sessions,
parses bearer headers, loads active users, and protects routes. Replacing it
would duplicate security-sensitive behavior. Database resolution makes role
changes and user deactivation effective on the next request even when token
claims are stale.

**Alternatives considered**:

- Trust JWT permission claims until expiry: rejected; dynamic RBAC changes
  would not take effect immediately.
- Add a JWT dependency: deferred; the existing narrow HMAC implementation can
  be extended to one strictly validated HS256 algorithm. Any dependency change
  requires separate approval.
- Browser cookies: rejected; the required contract is direct bearer tokens and
  the existing browser client already keeps credentials in memory.

## Decision 3: Rotate Stateful Refresh Credentials

**Decision**: Use short-lived access JWTs plus random opaque refresh
credentials. Store only keyed hashes, expiry, revocation, and replacement links
in PostgreSQL. Rotate on every refresh and revoke the replacement chain on
replay.

**Rationale**: Access JWTs stay compact while server-side refresh state enables
logout, disabled-user checks, and replay response. No raw credential or token
hash enters audit details.

**Alternatives considered**:

- Long-lived access JWT only: rejected; revocation and permission changes are
  too slow.
- Stateless refresh JWT: rejected; replay cannot be invalidated reliably.
- Persistent browser storage: rejected for MVP; memory limits credential
  exposure and reload may require login.

## Decision 4: Add Normalized RBAC Tables Additively

**Decision**: Add `roles`, `permissions`, `role_permissions`,
`user_role_mappings`, and `refresh_sessions` after migration 06. Keep the
existing `users` table and legacy `users.role` column during transition.

**Rationale**: Normalized mappings support administrator-defined roles and
granular scopes with database constraints. Keeping the legacy column avoids a
destructive migration and permits a controlled cutover. Existing user IDs and
foreign keys remain stable.

**Alternatives considered**:

- Store permissions in one role JSON column: rejected; uniqueness and joins
  are clearer with the user-requested permissions table.
- Rewrite `01_initial.py`: prohibited; the baseline is immutable.
- Drop `users.role` immediately: rejected; column drops require separate
  approval and add rollback risk.

## Decision 5: Preserve Existing Provider Contracts

**Decision**: Keep `ExtractionProvider`, `build_provider`, Gemini, Ollama,
FakeProvider, `ExtractionRequest`, `ExtractionResult`, and shared parsing.
Extend the request with a pinned field specification and extend the result with
provider metadata only where required.

**Rationale**: All providers already share one typed asynchronous contract.
Gemini and Ollama already enforce JSON responses, and `parse_result` already
validates Pydantic output. Central extension gives both providers identical
validation without a parallel SDK or adapter stack.

**Alternatives considered**:

- Replace Gemini HTTP code with another SDK: rejected; no demonstrated gap and
  it conflicts with existing-code-first governance.
- Per-product provider adapters: rejected; schemas and rulebooks, not provider
  classes, own product variation.
- Provider-specific result types: rejected; reconciliation needs one normalized
  evidence form.

## Decision 6: Redact Only at the External Boundary

**Decision**: Keep raw synthetic documents and extracted evidence local. Apply
configured PII detection and redaction to the canonical payload immediately
before Gemini transmission. Ollama stays local. Hash the exact redacted Gemini
payload used for the request.

**Rationale**: Underwriters need local evidence values and provenance. Global
redaction would destroy those records, while boundary redaction satisfies the
external-provider rule. Configuration must classify fields that cannot remain
useful after redaction.

**Alternatives considered**:

- Redact persisted evidence: rejected; human review and reconciliation would
  lose required facts.
- Audit raw prompts: rejected; hashes and metadata support correlation without
  retaining PII-bearing prompt content.
- Heuristic audit sanitization alone: rejected; it removes secret-shaped keys,
  not PII-shaped values.

## Decision 7: Add Pure Configured Reconciliation

**Decision**: Add one pure reconciliation module with fixed implementations for
`ncb_match`, `asset_match`, and `policy_lapse`. Product YAML supplies check
codes, source fields, document roles, normalization, and thresholds.

**Rationale**: Fixed pure functions are small, testable, and deterministic.
Configuration preserves insurer neutrality and later product extension. The
existing graph already joins evidence sequentially after bounded parallel
extraction, which is the correct insertion point.

**Alternatives considered**:

- Ask Gemini to decide discrepancies: rejected; model output cannot own a
  deterministic business verdict.
- New reconciliation graph: rejected; three sequential pure checks do not need
  orchestration.
- Hardcode motor field names inside the functions: rejected; product schemas
  must remain pluggable.

## Decision 8: Reuse Validation and Audit Persistence

**Decision**: Persist reconciliation outcomes as existing `Validation` rows and
include the complete ordered `ReconciliationResult` in the recommendation
summary. Append provider-run and rule events through the current audit builder
and repository.

**Rationale**: Current queue, triage, persistence, and audit paths already
understand validations and append-only events. New tables would duplicate data
without a proven query requirement.

**Alternatives considered**:

- Add `provider_runs` and `discrepancies` tables now: rejected; JSONB event and
  validation details meet current read patterns.
- Store prompt/completion bodies: rejected; hashes, schema version, provider,
  model, attempts, and usage are sufficient for local audit correlation.
- Make audit events mutable: prohibited by constitution and database trigger.

## Decision 9: Preserve Human-Authority Checks

**Decision**: Dynamic scopes protect ordinary actions, but final review,
override, and completion also require an authenticated underwriter identity.
Administrator breadth does not imply underwriting authority.

**Rationale**: A configurable role system must not erase the product's human
authority boundary. Ownership checks remain separate from scopes for applicant
case access.

**Alternatives considered**:

- Grant every action through configurable scopes alone: rejected; an
  administrator could accidentally gain final decision authority.
- Encode decision authority only in the UI: rejected; backend Python owns all
  authorization decisions.

## Decision 10: Pilot-Scale Capacity, No Sharding or Cache

**Decision**: Design for 5 ordinary RPS, ten simultaneous cases, and at most 30
provider calls. Keep one PostgreSQL instance and uncached version-pinned reads.
Use existing limits and measure before adding infrastructure.

**Rationale**: Average ordinary traffic is about 0.052 RPS; a 20× burst is
about 1.1 RPS. OCR and provider latency dominate. Caching dynamic permissions
or product versions risks stale security or configuration for no measured gain.

**Alternatives considered**:

- Database sharding: rejected; one tenant and thousands, not billions, of rows.
- Redis permission/config cache: rejected; immediate correctness matters more.
- Read replica: deferred; there is no availability target or read bottleneck.

## Decision 11: Case Evidence Budget

**Decision**: Treat the existing ten-document, ten-MB/document, 50-page,
three-branch, and 50,000-reference-character limits as one case evidence budget.
Budget exhaustion produces a typed gap and human review.

**Rationale**: One domain-specific budget bounds storage, OCR, provider cost,
latency, checkpoint growth, and blast radius without adding infrastructure or
silently losing evidence.

**Alternatives considered**:

- Accept unlimited uploads and scale later: rejected; resource use becomes
  unbounded before value is proven.
- Truncate silently: rejected; missing evidence must be visible.

## Resolved Unknowns

- **JWT library**: no new dependency in the plan; extend the existing narrow
  HMAC implementation. Revisit only after security review proves it unsafe.
- **Role freshness**: database state is authoritative on every secured request.
- **Provider stack**: existing Gemini/Ollama/Fake contract only.
- **Reconciliation persistence**: existing validations and audit events.
- **Scale**: finalized MVP numbers; no internet-scale assumptions.
- **Availability**: restart-safe local MVP, no contractual HA target.
- **Caching/sharding**: none until measured thresholds fail.
- **Retention**: planning uses the documented 90-day case horizon; automatic
  deletion remains outside this feature pending an approved retention policy.
