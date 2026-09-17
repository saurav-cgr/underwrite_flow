<!-- ROUTE=mixed | WRITE_READY=1 | READ_READY=3 | EXISTING=0 |
PLANNED_DISPATCH=3 | LEAD=architecture,integration,artifacts |
REASON=parallel_gain |
DETAIL=Three independent research tracks reduce plan latency. -->

# Implementation Plan: Governed Underwriting Platform

**Branch**: `phase2` | **Feature Key**: `001-underwriting-platform` |
**Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`specs/001-underwriting-platform/spec.md`

## Summary

Extend the existing FastAPI modular monolith rather than introducing another
service or provider stack. Replace fixed demo roles with database-backed users,
roles, permissions, role mappings, strict JWT bearer access, and rotated refresh
sessions. Reuse Argon2, the current auth dependency, Gemini/Ollama adapters,
local PDF/OCR extraction, bounded LangGraph fan-out, versioned product YAML,
PostgreSQL persistence, queue UI, and append-only audit infrastructure.

Add typed, configuration-driven reconciliation for NCB, asset identifiers, and
policy lapse. Provider outputs remain evidence only; pure deterministic rules
produce ordered `ReconciliationResult` values and feed the existing human
review interrupt. No model may authorize, route finally, or mutate business
state.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.9; React 19; Node 24

**Primary Dependencies**: FastAPI 0.116, SQLAlchemy 2.0, Pydantic 2,
Argon2, LangGraph 0.6, asyncpg, httpx, React, Vite

**Storage**: PostgreSQL 16/pgvector for business records, audit, and
checkpoints; local Docker volume for synthetic uploads

**Testing**: pytest 8 with pytest-asyncio; Vitest with Testing Library;
deterministic fake provider for normal suites

**Target Platform**: Self-hosted Linux containers through Docker Compose

**Project Type**: React web application plus FastAPI modular monolith

**Performance Goals**: 95% of ordinary interactions within two seconds; 95%
of submitted cases review-ready within 60 seconds; ten simultaneous processing
jobs; three provider branches per case

**Constraints**: Single tenant; synthetic data only; human final authority;
Gemini default and Ollama optional through existing adapters; local raw files;
append-only audit; additive migrations; no new infrastructure without evidence

**Scale/Scope**: 100 applications/day, 20 simultaneous users, ten documents
and 50 pages per application, ten simultaneous cases, 90-day completed-case
planning horizon

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Single tenant**: one deployment, database, upload volume, and provider
  configuration per fictional insurer; no tenant key or shared platform.
- **JWT and dynamic authorization**: bearer access tokens carry `sub`, role,
  and permission snapshots; every secured request revalidates the active user
  and current database permissions before authorization.
- **Provider boundary**: reuse the existing provider protocol, factory,
  Gemini adapter, Ollama adapter, and fake; redact configured PII locally
  before Gemini; Ollama remains local.
- **Schema-driven extraction**: derive requested fields and reconciliation
  definitions from the pinned product configuration; validate every provider
  response through the shared Pydantic path.
- **Pure reconciliation**: NCB, lapse, and asset checks are side-effect-free,
  deterministic functions with complete statement and branch coverage.
- **Immutable audit**: reuse the append-only audit table and database trigger;
  append actor, versions, outcome, provider metadata, token usage, and hashes.
- **Human authority**: only an authenticated underwriter may confirm or
  override the final route; overrides require rationale.
- **Existing-code-first**: all proposed changes extend current modules; no
  microservice, cache, queue, object store, provider stack, or web framework.
- **Approval gates**: implementation MUST pause before the additive schema
  migration, JWT/auth changes, provider payload changes, or any dependency
  addition. This plan grants no implementation approval.

Post-design result: **PASS**. No constitutional violation or justified
exception remains.

## Project Structure

### Documentation (this feature)

```text
specs/001-underwriting-platform/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── reconciliation.md
│   └── rest-api.md
└── tasks.md                 # Created later by $speckit-tasks
```

### Source Code (repository root)

```text
api/
├── alembic/versions/       # One additive revision after revision 06
├── src/underwriteflow/
│   ├── auth/               # Extend JWT, refresh, users, roles, scopes
│   ├── audit/              # Reuse sanitized append-only event builder
│   ├── cases/              # Reuse intake and submission
│   ├── persistence/        # Extend models and narrow repositories
│   ├── products/           # Extend versioned configuration schemas
│   ├── providers/          # Reuse existing adapters
│   ├── queues/             # Extend discrepancy summaries
│   ├── reviews/            # Reuse human interrupt and rationale rules
│   └── workflow/           # Add pure reconciliation before triage
└── tests/
    ├── contract/
    ├── integration/
    └── unit/
web/
└── src/                    # Extend client, auth, admin, queue
product-config/             # Add reconciliation definitions to YAML
```

**Structure Decision**: Preserve the current two-project web application and
backend modular monolith. Add files only at existing responsibility boundaries;
do not create another service or generic repository layer.

## RESHADED Architecture

### R - Requirements

Functional scope is fixed by [spec.md](./spec.md): JWT login/refresh/me,
database-backed dynamic RBAC, versioned configuration, existing provider-based
extraction, deterministic reconciliation, discrepancy queue, human override,
and immutable audit.

Non-functional rules:

- 95% ordinary reads and writes complete within two seconds.
- 95% case submissions reach review-ready state within 60 seconds, excluding
  human wait time.
- Committed business, audit, upload, and checkpoint state survives container
  restart; the MVP has no contractual high-availability target.
- Provider or OCR failure becomes typed visible review state, never case loss.
- Identical normalized evidence and pinned rules produce byte-stable ordered
  reconciliation payloads.
- Authorization changes apply on the next protected request despite JWT claim
  snapshots, because database state remains authoritative.

### E - Estimation

Use the finalized pilot envelope, not hypothetical internet scale:

- `100 / (8 × 3,600) = 0.0035` average submissions/second during an
  eight-hour workday.
- At 15 ordinary requests per case, `1,500 / 28,800 = 0.052` average RPS.
  A 20× interaction burst is about 1.1 RPS; size and test for 5 RPS.
- Ten processing cases × three branches = 30 simultaneous provider calls.
- Typical upload volume: `100 × 10 × 2 MB = 2 GB/day`; accepted maximum is
  `100 × 10 × 10 MB = 10 GB/day`.
- A 90-day upload horizon needs about 180 GB typical or 900 GB at the accepted
  ceiling. Provisioning MUST use measured document sizes before pilot.
- Structured state estimate: `0.5 MB × 100 × 90 = 4.5 GB`; reserve 10 GB for
  PostgreSQL data plus indexes and headroom, then validate with sample cases.
- Maximum OCR work is `100 × 50 = 5,000 pages/day`; latency tests MUST measure
  seconds per page and ten-case bursts.

### S - Storage Schema

Keep all current tables. Add roles, permissions, role-permission mappings,
user-role mappings, and refresh sessions in one additive migration. Preserve
`users.role` during transition; backfill mappings from its three known values
and stop reading it after cutover. Do not drop a column in this feature.

Reuse product versions for extraction and reconciliation configuration. Reuse
validations for persisted reconciliation outcomes and audit events for provider
and human decision metadata. Avoid new provider-run or discrepancy tables until
query or retention evidence proves JSONB details insufficient.

Full fields, constraints, relationships, and transitions are in
[data-model.md](./data-model.md).

### H - High-Level Design

```text
Browser
  -> FastAPI modular monolith
     -> JWT validation + PostgreSQL-backed scope resolution
     -> case/configuration/document REST modules
     -> local PDF text extraction or OCR
     -> existing Gemini | Ollama | fake provider adapter
     -> bounded LangGraph evidence fan-out (max 3)
     -> pure reconciliation + deterministic triage
     -> underwriter interrupt -> idempotent completion
     -> PostgreSQL business/audit/checkpoint state
     -> local upload volume for raw synthetic files
```

No load balancer is added for the single-host MVP. `/health` remains process
health; `/ready` remains database readiness. A production edge, TLS terminator,
or multiple API workers requires a deployment request outside this feature.

### A - APIs

Add `/api/v1/auth/login`, `/auth/refresh`, and dynamic `/users`, `/roles`, and
`/permissions` administration. Preserve `/auth/session` temporarily as a login
alias so the existing web client can migrate without a flag day. Keep all case,
document, product, review, queue, audit, and completion endpoints; extend their
typed payloads rather than add parallel routes.

All errors retain the sanitized envelope and `X-Request-ID`. Secured endpoints
declare one or more scopes and still apply applicant ownership and explicit
underwriter-finalization checks. See
[contracts/rest-api.md](./contracts/rest-api.md).

### D - Detailed Design

#### Authentication and authorization

- Extend the existing HMAC service to emit strict three-segment HS256 JWTs.
  Access claims: `sub`, `role`, `permissions`, `typ`, `iat`, `exp`, `iss`,
  `aud`, `jti`, and `authz_version`.
- Treat role and permission claims as a client-visible snapshot only. On every
  secured request, resolve the active user and current role permissions from
  PostgreSQL and reject a version mismatch or missing required scope.
- Keep Argon2 password hashing. Do not add bcrypt or a second password path.
- Use a rotated, random opaque refresh credential stored only as a keyed hash.
  Replay revokes its replacement chain. Keep access and refresh credentials in
  browser memory; page reload requires login.
- Preserve applicant ownership after scope checks. Preserve underwriter-only
  confirm, override, and completion even for broad administrator roles.

#### Extraction and reconciliation

- Keep `ExtractionProvider.extract`, factory selection, Gemini/Ollama adapters,
  local extraction, retries, fake provider, and shared `parse_result`.
- Extend `ExtractionRequest` with the pinned field specification. Validate
  field name, scalar type, enum, count, and source locator centrally.
- Prefix locally extracted text with trusted page boundaries so provider
  locators can be checked against real pages.
- Run configurable pure checks after the existing generic evidence join.
  Fixed check implementations are `ncb_match`, `asset_match`, and
  `policy_lapse`; configuration supplies field/document keys and thresholds.
- Sort results by configured check code and evidence by document ID and source
  locator. Convert flagged and missing results into existing validations and
  triage inputs.
- Redact configured PII before Gemini. Never redact local persisted evidence or
  underwriter review data. Ollama receives local payloads only.

#### Audit and persistence

- Hash canonical redacted provider request and validated response payloads with
  SHA-256. Store provider/model, token counts or explicit unavailable markers,
  attempts, schema/rulebook versions, and hashes in append-only audit details.
- Never store access tokens, refresh credentials, signing material, passwords,
  raw prompts, or full documents in audit details.
- Use existing transactions, row locks, review-cycle uniqueness, and handoff
  idempotency. Business state and matching audit events commit together.

#### Caching, sharding, and spikes

- No Redis, application cache, database sharding, replica, worker, or message
  queue. Pilot scale and immediate configuration correctness do not justify
  them.
- Existing file/page/count limits, branch cap, provider timeout/retry bounds,
  row locks, and idempotency keys form the first spike controls.
- If ten-case load tests miss the 60-second target, first add one process-local
  submission semaphore and visible queued state. Add a worker only if measured
  long requests exhaust API capacity after that smaller control.

### E - Evaluation

Primary bottlenecks are inline OCR/provider time, 30 possible provider calls,
CPU-bound OCR, and unpaged queue reads. Failure domains are the single API
container, PostgreSQL, local upload volume, and external Gemini endpoint.

Mitigations already available: persistent volumes, resumable checkpoints,
branch-local retry, sibling-failure isolation, cautious specialist routing,
row locks, and idempotent completion. Before pilot claims, run synthetic
ten-case and 100-case probes, record OCR seconds/page, provider p95, database
pool use, checkpoint bytes, queue latency, and upload volume.

Known residual risks:

- PostgreSQL and upload volume are separate single points of failure; restore
  must cover both consistently.
- No automated retention job or approved backup/restore runbook is evidenced.
- Hosted-provider PII redaction can remove fields needed for extraction; each
  schema must classify fields as locally retained, pseudonymized, or forbidden.
- Permission snapshots in JWTs can become stale; database authorization is the
  authority, so availability depends on PostgreSQL.

### D - Distinctive Feature

Use a **case evidence budget**: at most ten documents, ten MB per document,
50 pages per case, three simultaneous extraction branches, and 50,000
reference characters. Crossing a budget produces a typed evidence gap and
human review instead of truncation, guessed data, or infrastructure scaling.
This one control bounds upload storage, OCR CPU, provider concurrency, cost,
checkpoint size, and failure impact while preserving visible uncertainty.

## Complexity Tracking

No constitutional violation needs justification. Deferred infrastructure is
listed explicitly so later measurements, not speculation, trigger expansion.
