# Implementation Plan: Journey, Product Authoring, and Evaluation

**Branch**: `phase2` |
**Feature Key**: `002-journey-authoring-evaluation` |
**Date**: 2026-09-18 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`specs/002-journey-authoring-evaluation/spec.md`

## Summary

Extend the existing case and product contracts with a persisted
`new_business | renewal` journey. Filter the pinned product configuration
before current validation, reconciliation, and routing so one deterministic
engine serves both journeys. Add a draft application replacement operation and
surface journey through applicant, staff, audit, and handoff views.

Build the administrator wizard directly on the existing product configuration,
JSON/YAML loader, immutable draft import, and explicit activation lifecycle.
Add configuration read and canonical YAML export; keep normalized diff in the
browser.

Retain fast in-memory evaluation and add a standalone tmpfs-backed Compose
stack whose thin runner exercises public HTTP contracts with the fake provider.
No new runtime dependency, service architecture, rule engine, or mutable draft
store is introduced.

## Technical Context

**Language/Version**: Python 3.12; TypeScript 5.9; React 19; Node 24

**Primary Dependencies**: FastAPI 0.116, SQLAlchemy 2.0, Pydantic 2, Alembic,
LangGraph 0.6, asyncpg, httpx, PyYAML, React, Vite

**Storage**: PostgreSQL 16/pgvector for business, audit, and checkpoint data;
local upload volume; JSON file for isolated evaluation results

**Testing**: pytest and pytest-asyncio; Vitest and Testing Library; Docker
Compose smoke and evaluation checks; deterministic fake provider

**Target Platform**: Self-hosted Linux containers through Docker Compose

**Project Type**: FastAPI modular monolith plus React web application

**Performance Goals**: Preserve current 95% under two seconds for ordinary
interactions and 95% review-ready within 60 seconds; sequential 90-case
evaluation favors determinism over throughput

**Constraints**: Single tenant; synthetic data only; human final authority;
local raw files; append-only audit; additive migration; no new dependency;
no published evaluation ports; no shared development state

**Scale/Scope**: Three fictional products, two journeys, 90 evaluation cases,
100 applications/day pilot envelope, ten documents per case

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Tenant and local boundary**: Business data remains in the existing
  deployment. The evaluation stack is a separate single-tenant environment
  with tmpfs data, internal networking, and no access to development storage.
- **Authorization**: Existing JWT and database-backed permissions protect case,
  product, review, audit, and evaluation operations. Application replacement
  adds an explicit applicant-owner check.
- **Provider boundary**: Existing Gemini, Ollama, and fake provider adapters are
  unchanged. Isolated evaluation forces the fake provider and disables tracing.
- **Configuration**: Journey metadata extends the one validated, versioned
  product schema. Activation stays explicit, authorized, audited, and
  prospective.
- **Determinism**: Journey applicability is a pure filter before the existing
  deterministic rules and reconciliation engine. Evaluation pins versions and
  hashes.
- **Audit**: Case creation, application replacement, processing, configuration,
  human review, and completion continue to append sanitized actor-linked
  events. Journey is included without applicant field values.
- **Human authority**: The feature recommends only the existing three routes.
  Renewal is a journey, not an automated renewal decision. Confirmation and
  idempotent completion remain mandatory.
- **Migration**: Revision 08 adds and backfills one case column; migration
  history and existing product versions remain immutable.
- **Synthetic data**: Product additions, applicants, documents, roles, and
  evaluation artifacts remain clearly fictional.
- **Existing-code-first**: Current schemas, services, endpoints, PDF generator,
  metrics, fake provider, and Compose image are reused.

Post-design result: **PASS**. Schema implementation still requires the explicit
approval gate in `AGENTS.md`; this design does not grant that approval.

## Project Structure

### Documentation (this feature)

```text
specs/002-journey-authoring-evaluation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── evaluation.md
│   ├── product-configuration.md
│   └── rest-api.md
└── tasks.md                 # Generated later by $speckit-tasks
```

### Source Code (repository root)

```text
api/
├── alembic/versions/        # Add revision 08 only
├── src/underwriteflow/
│   ├── cases/               # Journey intake and draft updates
│   ├── products/            # Journey schema, filtering, read/export
│   ├── workflow/            # Reuse current graphs with filtered config
│   ├── queues/              # Journey in queue/audit/completion views
│   └── evaluation/          # Reuse offline metrics and dataset loader
└── tests/
web/src/                     # Journey flow and product builder
product-config/              # New immutable motor and health versions
evaluation/                  # Revised dataset and ignored result directory
scripts/                     # Thin public-HTTP evaluation runner
compose.evaluation.yaml      # Standalone isolated stack
Makefile                     # evaluate-e2e entry point
.github/workflows/           # Same evaluation command in CI
```

**Structure Decision**: Preserve the modular monolith and web application.
Extend existing responsibility boundaries. The evaluation runner is an
operator script, not another application service or rule engine.

## Implementation Design

### 1. Journey Contract and Migration

- Add migration 08 with non-null `cases.journey_type`, default/backfill
  `new_business`, and a two-value check constraint. Downgrade removes only
  this constraint and column.
- Add journey metadata and cross-journey reference validation to the existing
  product schema. Legacy omission means new-business-only.
- Add a pure configuration-for-journey filter and use it everywhere fields,
  documents, routing rules, or reconciliations are selected.
- Add new motor v4 and health v3 files with both journeys. Keep life v1
  new-business-only and preserve every prior file.
- Normalize stored and incoming legacy configurations before treating a hash
  mismatch as a version conflict; never rewrite the stored payload or hash.

### 2. Journey Behavior and Applicant UI

- Create cases with immutable journey and optional initial answers. Validate
  only supplied draft values at create/update; enforce completeness at
  submit/resubmit from the stored application and actual document rows.
- Add owner-only `PUT /cases/{id}/application` as complete replacement for
  mutable `new` or `needs_information` cases. Audit metadata only.
- Return application, journey, and document stage in the pinned configuration
  response. Return journey in case, queue, review, completion, audit details,
  and handoff payloads.
- Applicant UI chooses journey first. New business stays form-first. Renewal
  creates the case, uploads required prior-policy evidence, edits the form,
  adds supporting evidence, then submits. Reload reconstructs state from case,
  configuration/application, and document APIs.
- Reject unsupported product/journey pairs, non-applicable document uploads,
  missing renewal policy evidence, and journey mutation. Unreadable evidence
  uses current needs-information/cautious-routing behavior.

### 3. Administrator Product Builder

- Use one typed browser object matching the backend configuration contract.
  Blank, clone, and uploaded YAML converge on this object; the expert YAML path
  remains available.
- Extend preview to return the normalized configuration. Send builder state as
  JSON text through existing validate/preview/import requests.
- Add version configuration read and canonical YAML export endpoints. Do not
  add a builder write endpoint, frontend YAML library, or server draft table.
- Implement the seven requested accessible sections. Use native controls and
  fixed choices for types, operators, routes, reconciliation kinds, and content
  types. Reference choices come from current field, document, and label codes.
- Compare normalized candidate and active objects in the browser by stable
  identifiers. Import persists an immutable draft; activation remains a
  separate confirmation. Active versions are clone-only.

### 4. Isolated Evaluation

- Add `journey_type` and `configuration_version` to every reference record.
  Preserve 30 cases per product and route; split motor and health 15/15 across
  journeys and keep all 30 life cases new-business.
- Change offline evaluation to load each record's exact configuration and
  filter it by journey. Keep its API and administrator panel in memory.
- Add a standalone database, bootstrap, API, and runner Compose stack. Use
  tmpfs for database and uploads, internal networking, fake provider, retry
  zero, tracing false, evaluation-only credentials, no ports, and no named
  volumes.
- The HTTP runner validates the dataset, activates exact versions,
  authenticates synthetic roles, drives all 90 cases, and checks expected
  metrics. It reviews a representative successful subset, confirms routes,
  completes twice, and verifies queues and audit through public endpoints.
- Atomically write `evaluation/results/e2e.json` on success or failure. Add
  the directory to `.gitignore`. Exit nonzero for any failed invariant.
- Add `make evaluate-e2e` and a GitHub Actions job invoking that exact target
  and retaining the result file even on failure. Teardown uses
  `down --remove-orphans`, never `down -v`.

## Delivery and Approval Gates

1. **Journey contract and migration**: stop before applying revision 08 for
   explicit schema approval; then verify upgrade, backfill, downgrade, legacy
   config, and hash compatibility before review and commit.
2. **Journey behavior and UI**: verify both flows, reload, routing, queues,
   audit, human confirmation, and idempotent completion; stop for review.
3. **Admin builder**: verify blank, clone, upload, preview, diff, import,
   activation, export, accessibility, and pinning; stop for review.
4. **Isolated evaluation**: verify dataset, Compose isolation, two fresh runs,
   stable deterministic output, CI artifact, and unchanged development state;
   stop for review.

Each step follows `docs/IMPLEMENTATION_PLAN.md`: focused failing test first,
one reviewed step at a time, proposed commit reported, and explicit
`continue` required before commit or later work.

## Complexity Tracking

No constitutional violation or exceptional complexity is introduced.
