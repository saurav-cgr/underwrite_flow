# Implementation Plan: Exclude Prior Claims from New Business

**Branch**: `003-exclude-prior-claims` | **Date**: 2026-09-20 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`specs/003-exclude-prior-claims/spec.md`

## Summary

Add an immutable private-car motor product version that makes
`prior_claims` renewal-only. Reuse the existing journey filter for the
catalogue, intake, workflow, and review paths. Close two shared validation
gaps: reject payload fields absent from the journey-filtered configuration,
and validate journey applicability for reconciliation parameter fields.
Preserve all earlier product versions and pinned cases. Activation remains a
separate authenticated administrator action.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.9

**Primary Dependencies**: FastAPI 0.116, Pydantic 2, SQLAlchemy 2,
LangGraph 0.6, React 19

**Storage**: PostgreSQL 16 with JSONB product configurations and immutable
audit records; versioned YAML source configurations

**Testing**: pytest 8 with pytest-asyncio; Vitest 3 with Testing Library

**Target Platform**: Linux containers through Docker Compose; modern browser

**Project Type**: FastAPI modular monolith and React web application

**Performance Goals**: No material change to current form, submission, or
review latency; journey filtering and validation remain bounded by one
product configuration

**Constraints**: No schema migration, dependency, provider, authorization, or
external data-flow change; files remain under 400 lines and hand-written lines
at or below 80 characters

**Scale/Scope**: One motor product version, four shared backend boundaries,
selected evaluation fixtures, and focused regression coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Tenant and authorization boundary — PASS**: No tenant, session, role, or
  permission behavior changes.
- **Provider and local-data boundary — PASS**: No provider request, storage,
  tracing, or egress behavior changes.
- **Schema-driven extraction — PASS**: Journey applicability remains in the
  existing validated product configuration. No product field is hardcoded in
  workflow code.
- **Deterministic reconciliation — PASS**: The pure journey filter excludes
  inapplicable checks. Validation is strengthened before activation.
- **Immutable audit — PASS**: Earlier product versions, cases, and events are
  untouched. Import and activation continue through audited services.
- **Human authority — PASS**: Routing remains advisory and still pauses for
  authenticated underwriter confirmation.
- **Migration safety — PASS**: No data-model change is required. The immutable
  migration baseline is not edited.
- **Synthetic-data boundary — PASS**: Product content and tests remain clearly
  fictional.

## Project Structure

### Documentation (this feature)

```text
specs/003-exclude-prior-claims/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── journey-claims-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
product-config/
└── motor-private-car-v5.yaml

evaluation/
└── cases.json

scripts/
└── smoke.py

api/src/underwriteflow/
├── cases/
│   ├── router.py
│   └── validation.py
├── products/
│   ├── import_configs.py
│   └── journey.py
└── reviews/
    └── router.py

api/tests/
├── unit/
│   ├── test_cases.py
│   ├── test_evaluation.py
│   └── test_journey_configuration.py
├── integration/
│   └── test_journey_workflow.py
└── contract/
    └── test_review_contract.py
```

**Structure Decision**: Extend the existing product configuration and shared
journey-aware validation paths. The web form already consumes backend-filtered
fields, so no frontend source change is planned. Add tests only at boundaries
where behavior changes.

## Phase 0: Research Decisions

See [research.md](research.md). All technical unknowns are resolved.

## Phase 1: Design

- [data-model.md](data-model.md) records the unchanged persisted entities and
  the new immutable configuration version.
- [journey-claims-contract.md](contracts/journey-claims-contract.md) defines
  catalogue, intake, replacement, renewal, and review behavior.
- [quickstart.md](quickstart.md) provides focused validation commands and
  manual acceptance scenarios.

## Post-Design Constitution Check

- All pre-design gates remain **PASS**.
- The design adds no schema, dependency, provider, permission, or external
  integration.
- Configuration version `v5` is imported as a draft. A human administrator
  must explicitly activate it; implementation must not auto-activate it.
- Generic validation protects every journey and field rather than introducing
  product-specific application logic.
- Earlier product versions and pinned cases remain unchanged. Selected
  evaluation fixtures and the smoke path prove `v5` without inventing a new
  underwriting rule or breaking the required route balance.

## Complexity Tracking

No constitution violations require justification.
