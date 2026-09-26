# Implementation Plan: Environment Baseline and Evaluation Loading

**Branch**: `004-environment-data-seeding` | **Date**: 2026-09-20 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`specs/004-environment-data-seeding/spec.md`

## Summary

Keep the existing migration and product-import bootstrap as the common
baseline for every environment. Add an explicit environment mode and one
operator-run loader that maps the existing 90-case evaluation corpus through
the current case, document, workflow, checkpoint, and audit services. The
loader uses stable dataset-derived identities, resumes partial loads, runs only
the deterministic fake provider, and refuses production before opening the
database or upload storage. Normal startup never invokes it.

## Technical Context

**Language/Version**: Python 3.12; Docker Compose configuration

**Primary Dependencies**: Existing FastAPI, Pydantic 2, SQLAlchemy 2 async,
Alembic, asyncpg, LangGraph, httpx, Pillow, and PyPDF dependencies

**Storage**: PostgreSQL 16 business and audit tables, PostgreSQL LangGraph
checkpoints, local upload volume, and the existing `evaluation/cases.json`

**Testing**: pytest and pytest-asyncio through Docker Compose; Compose contract
tests; existing deterministic evaluation and smoke suites

**Target Platform**: Local Linux containers orchestrated by Docker Compose

**Project Type**: FastAPI modular monolith with operator scripts and React web
client; this feature changes backend and deployment configuration only

**Performance Goals**: Deterministically load the current 90 cases and their
documents; no production latency or throughput target is introduced

**Constraints**: No automatic business seed, no real data, no external
provider or tracing, no production write, no duplicate cases or documents, no
new dependency, no schema migration, and no final insurance decision

**Scale/Scope**: Three environment modes, three default demo roles, ten
versioned product configurations, 90 evaluation cases, and the current
evaluation document set

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Tenant isolation and authorization — Pass**: One local deployment and
  existing demo identities; no cross-tenant access.
- **Local provider and data boundary — Pass**: Only local files, PostgreSQL,
  uploads, and `FakeProvider` are used.
- **Schema-driven extraction — Pass**: Existing versioned product and
  extraction schemas remain authoritative.
- **Deterministic reconciliation — Pass**: Existing workflow and pure rules
  run unchanged.
- **Immutable audit — Pass**: Existing services append normal events plus
  bounded load markers.
- **Product version pinning — Pass**: Each record pins its exact existing
  version.
- **Human authority — Pass**: The loader never reviews or finalizes.
- **Existing-code reuse — Pass**: Current migrations, imports, services,
  dataset, renderer, and provider are reused.
- **Synthetic data only — Pass**: The corpus label is preflighted and audited.
- **Migration safety — Pass**: No database shape changes are planned.

### Post-Design Re-check

The design adds no provider, dependency, authentication rule, schema, or
external data path. Exact-version creation is an internal extension of the
existing case service, not a second rule model. The production guard executes
before persistence construction. All gates remain passed.

## Project Structure

### Documentation (this feature)

```text
specs/004-environment-data-seeding/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── evaluation-loader.md
└── tasks.md
```

### Source Code (repository root)

```text
.env.example
compose.yaml
compose.evaluation.yaml
compose.production.yaml
Makefile
api/
├── src/underwriteflow/
│   ├── app.py
│   ├── config.py
│   ├── cases/service.py
│   └── evaluation/dataset.py
└── tests/
    ├── contract/test_environment_compose.py
    ├── integration/test_environment_baseline.py
    ├── integration/test_evaluation_loader.py
    └── unit/test_environment_config.py
scripts/
├── evaluate_e2e.py
├── load_evaluation_data.py
└── synthetic_pdf.py
evaluation/cases.json
product-config/*.yaml
```

**Structure Decision**: Extend the existing API, Compose, and script layout.
Keep the loader under `scripts/` beside its reusable dataset runner and
synthetic document renderer. Add no service, package layer, or database table.

## Phase 0: Research Decisions

See [research.md](research.md). The key choices are:

1. Reuse migrations and product import as the common baseline.
2. Add one validated environment mode with production fail-closed behavior.
3. Run loading only through an explicit Compose command.
4. Reuse exact product versions without activating or rewriting them.
5. Reuse existing services and the fake provider for persisted workflow data.
6. Use stable namespaced idempotency keys and audit completion markers instead
   of a new load-status table.

No technical clarification remains unresolved.

## Phase 1: Design

### Baseline

- Base, evaluation, and production Compose configurations set an explicit
  environment mode.
- Existing Alembic migrations create schema, demo accounts, roles, permissions,
  and role mappings in every mode.
- Existing product import loads all built-in immutable configurations.
- Startup never calls the evaluation loader and creates no case, submission,
  document, recommendation, or evaluation-result row.
- A safe read-only environment response exposes the selected mode and whether
  loading is permitted, without credentials or internal configuration.

### Loader

- `load_evaluation_data.py` checks environment mode before constructing
  database or storage objects and rejects production with a nonzero exit.
- It validates the whole corpus and configuration manifest before the first
  write and identifies the dataset by SHA-256.
- Stable idempotency keys use the dataset hash and source case ID.
- The existing case service gains the minimum internal path needed to create a
  case against an explicitly resolved product and rulebook version while
  retaining the same validation, submission shape, and audit behavior.
- Existing upload storage and case document service persist generated
  synthetic documents. Existing hashes allow exact retry checks.
- Existing submission workflow runs with `FakeProvider`; expected labels are
  assertions, never copied into recommendations.
- Per-case and final completion audit events contain only dataset hash, source
  ID, split, counts, and the synthetic label.

### Retry and Collision Rules

- A matching existing case is verified and resumed from its first incomplete
  stage.
- Matching documents are skipped by code and content hash.
- A mismatched version, journey, payload, document, or reserved identity fails
  safely without overwriting the existing record.
- The final completion event is appended only after all expected records are
  verified. A retry never duplicates completion events.
- Earlier committed records may remain after interruption, but they are never
  reported as a complete dataset until verification succeeds.

### Interfaces and Validation

- The operator contract is defined in
  [contracts/evaluation-loader.md](contracts/evaluation-loader.md).
- Persistent mappings and state transitions are defined in
  [data-model.md](data-model.md).
- Runnable acceptance checks are defined in [quickstart.md](quickstart.md).

## Complexity Tracking

No constitution violation or exceptional complexity is required.
