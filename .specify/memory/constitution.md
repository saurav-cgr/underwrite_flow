<!-- ROUTE=direct | WRITE_READY=1 | READ_READY=0 | EXISTING=0 |
PLANNED_DISPATCH=0 | LEAD=constitution | REASON=lead_faster |
DETAIL=One constitution file; delegation transfer cost exceeds direct edit. -->
# UnderwriteFlow Constitution

## Core Principles

### I. Single-Tenant Isolation and Dynamic Authorization

Each UnderwriteFlow deployment MUST serve exactly one insurer. Components MUST
NOT communicate across tenants, query another tenant's data, share database
state, or depend on a global data platform. Tenant isolation MUST be enforced
by independent deployment boundaries, not only by application filters.

Sessions MUST use signed JWT bearer tokens supplied only through the
`Authorization: Bearer <token>` header. Every protected request MUST validate
the token signature, issuer, audience, expiry, user identity, and active status.
Browser cookie sessions and anonymous privileged access are prohibited.

Authorization MUST use administrator-configurable roles composed from explicit
permission scopes. At minimum, the scope model MUST support `cases:read`,
`cases:override`, `users:manage`, and `schemas:edit`. Permissions MUST be
resolved for the authenticated user and enforced at every protected operation;
role names alone MUST NOT grant implicit access.

### II. Existing Provider and Data Boundary

UnderwriteFlow MUST operate as a self-hosted application in a
tenant-controlled environment. Raw documents, OCR output, extracted payloads,
databases, indexes, vector stores, checkpoints, and audit records MUST remain
inside that environment. They MUST NOT be sent to external storage, database,
vector-store, embedding, tracing, or public AI services.

The existing Gemini adapter is the default approved external LLM provider. The
existing Ollama adapter is the approved optional local provider. Both MUST be
selected through the existing application-owned provider protocol and factory;
a second provider stack MUST NOT be introduced. Gemini requests MUST use an
enterprise or commercial Google Cloud project configuration whose applicable
terms and settings explicitly disable retention and use of request or response
data for model training. Unapproved LLM endpoints and direct calls that bypass
the existing provider boundary are prohibited.

Before any payload crosses an external model boundary, a local preprocessing
pipeline MUST detect and redact applicant Aadhaar and PAN identifiers, contact
details, and other configured PII. Raw files, unredacted PII, credentials,
hidden application state, and unrelated documents MUST NOT be sent to Gemini.

Network egress MUST fail closed and use domain allowlists. External requests
MUST contain only task-required, approved payload fields and use authenticated,
encrypted transport.

### III. Schema-Driven Structured Extraction

PDF parsing and text extraction MUST run locally before any provider request.
Gemini and Ollama extraction MUST reuse the existing adapters, shared request
and result schemas, structured JSON mode, and Pydantic validation path. Every
response MUST be parsed and validated against the active schema; invalid output
MUST be rejected rather than repaired or accepted implicitly. Structured output
guarantees syntax and shape only; deterministic rules and source evidence MUST
verify meaning.

Extraction schemas, document mappings, policy schedules, validation,
reconciliation, and routing rulebooks MUST be driven by validated, locally
versioned JSON or YAML configuration. Administrators MUST be able to preview
and configure these artifacts without changing application code. Activation
MUST be explicit, authorized, audited, and immutable for cases already pinned
to a version. Configuration MUST remain insurer-neutral and MUST NOT hardcode a
real insurer's format, workflow, or rule.

### IV. Pure, Deterministic Reconciliation

One core reconciliation engine MUST support motor, term life, health, and later
configured insurance products. It MUST deterministically identify missing,
conflicting, stale, or unmapped evidence across each product's configured
document set. For motor, this includes registration certificates, previous
policies, and claim histories when required by the active rulebook; equivalent
product-specific evidence MUST be configuration-driven for life and health.
Every finding MUST cite source evidence and applicable versioned rules, then be
presented to a human underwriter. The engine MUST NOT make a final insurance
decision. Business rules, No-Claim Bonus tier calculations, and evidence
reconciliation checks MUST be side-effect-free pure Python functions. NCB
checking, policy lapse calculation, and asset string matching MUST remain pure
and independently testable. These functions MUST have 100% statement and branch
test coverage. Configuration and source evidence MUST be explicit inputs;
outputs MUST be deterministic for identical inputs.

### V. Identity-Linked Immutable Audit

Every document mapping, extraction, reconciliation finding, rule execution,
automated recommendation, workflow transition, configuration action, and human
underwriter action MUST append an immutable local audit event. Each event MUST
record the authenticated JWT user ID, timestamp, case or configuration identity,
input and output references, and exact extraction schema and rulebook versions.
Audit history MUST support deterministic reconstruction without relying on
mutable workflow checkpoints or external telemetry. Each provider invocation
MUST record hashes of the exact prompt and completion payloads, provider and
model identifiers, and schema version without storing prohibited raw PII.
Every automated verdict and human override MUST record its rationale and
referenced evidence. Audit records MUST use append-only, tamper-evident database
storage; correction MUST append a superseding event rather than alter or delete
history.

## Operational Constraints

- PostgreSQL is the business source of truth; workflow checkpoints are separate
  operational state and MUST NOT replace audit events.
- Uploaded documents are untrusted data and MUST NOT be treated as instructions.
- Only synthetic applicant, document, insurer, product, and rule data is
  allowed.
- Deterministic rules outrank model suggestions. Model output MUST be validated
  against typed schemas and linked to source evidence before use.
- Missing information is a queue state, not a final triage route.
- UnderwriteFlow may recommend expedited, standard, or specialist review only.
  An authenticated underwriter MUST confirm or override every final route.
- Storage, indexing, and observability MUST fail closed at the tenant-controlled
  environment boundary. LLM egress MUST fail closed unless an administrator
  selects the existing Gemini adapter and configures an approved Gemini project,
  domain allowlist, and active redaction policy. Ollama MUST remain local.

## Delivery and Compliance Gates

- Before adding code, dependencies, schemas, provider paths, or UI components,
  implementation work MUST search for an existing project-owned equivalent.
  Compatible code MUST be reused or minimally extended. A new implementation
  is allowed only when the existing path cannot satisfy a documented
  requirement; the plan or review MUST record that reason.
- Every specification and implementation plan MUST identify the tenant boundary,
  local data flows, configuration versions, reconciliation behavior, audit
  events, and human decision boundary affected by the change.
- Tests MUST cover JWT validation, scope enforcement, blocked unapproved
  providers, existing provider-boundary enforcement, Gemini domain allowlisting,
  mandatory Gemini redaction, no-training Gemini configuration, local Ollama
  isolation, structured-output validation, configuration version pinning,
  deterministic reconciliation, evidence provenance, immutable auditing, and
  required human confirmation.
- Schema and rulebook changes MUST be additive or explicitly migrated. Existing
  cases MUST retain the exact versions selected when processing began.
- Reviews MUST reject hardcoded insurer logic, unversioned product behavior,
  mutable audit history, invalid JWT or implicit role authorization, unapproved
  LLM providers, duplicate provider stacks, calls bypassing the existing
  provider boundary, unredacted external
  case-data transmission, Gemini project terms allowing model training, and any
  automated approval, decline, binding, pricing, issue, renewal, or cancellation
  action.
- Exceptions to any MUST require a constitution amendment before implementation;
  ordinary design documents cannot waive these principles.

## Governance

This constitution supersedes conflicting project guidance. Amendments require a
documented proposal, impact analysis, explicit maintainer approval, and updates
to affected specifications or plans before implementation. Version changes use
semantic versioning: MAJOR for incompatible governance changes, MINOR for new or
materially expanded principles, and PATCH for non-semantic clarification.

Every feature review MUST verify compliance before merge. Reviewers MUST record
any constitutional impact and block work that violates a non-negotiable rule.
The temporary Sync Impact Report at this file's top MUST be removed before the
amendment is committed.

**Version**: 4.0.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-09-17
