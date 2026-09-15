# UnderwriteFlow MVP Implementation Plan

**Source of truth:** `docs/PRD.md`

**Reference pattern:** Decision Assistant's `docs/superpowers/plans/2026-08-05-decision-memory-assistant.md`

**Status:** Proposed for review

**Date:** 10 September 2026

## Goal

Build a local-first portfolio MVP that accepts fictional Indian motor, life, and health insurance applications, processes evidence through a resumable and partially parallel LangGraph workflow, recommends a triage route, and requires an authenticated underwriter to confirm or override it.

## Architecture

A React/TypeScript frontend calls a versioned `/api/v1` FastAPI modular monolith. PostgreSQL 16 stores cases, configurations, evidence, queues, audit events, and LangGraph checkpoints. The workflow uses one parent graph, bounded document fan-out, and one selected product subgraph. Deterministic rules govern routing; Gemini assists extraction and summarization behind a provider protocol; Ollama is optional. Docker Compose owns every runtime, test, migration, and build command.

## Proposed stack

- Docker Compose; Python 3.12 API; Node 24 web container.
- FastAPI, Pydantic 2, SQLAlchemy 2 async, Alembic, asyncpg, and Uvicorn.
- LangGraph with PostgreSQL checkpointing.
- PostgreSQL 16 using the pgvector image, without embedding retrieval in the MVP.
- Gemini generation by default; deterministic fake provider for tests; optional Ollama profile.
- Local PDF text extraction and local OCR for images/scans.
- React, TypeScript, Vite, React Router, native `fetch`, regular CSS, Vitest, and Testing Library.
- Optional LangSmith development traces and evaluation, disabled by default.

Dependency installation, the initial schema, authentication, provider choices, and external tracing remain explicit approval points under `AGENTS.md`; approving this plan does not silently approve those changes.

**Repository prerequisite:** This directory is not currently a Git repository. Before Step 1, initialize it or place it inside the intended repository so the review-then-commit protocol can operate; do not create a repository or remote without user approval.

## Delivery protocol

1. Implement exactly one numbered step at a time.
2. Start each behavior with a focused failing test or failing infrastructure check.
3. Make only the files named by that step, plus the minimum adjacent repair required for correctness.
4. Run the step's Docker-based verification and `git diff --check`.
5. Stop. Report changed files, verification, remaining risks, and the proposed commit message.
6. Wait for the user to review and explicitly say `continue`.
7. Commit only the reviewed step, then begin the next numbered step.

No step may be combined with another. A failed verification is reported and repaired within the same step; it is never hidden by moving forward.

## Coding rules applied to every step

- Keep every hand-written file below 400 lines; split before reaching the limit.
- Put a short intent comment immediately before every named Python or TypeScript/React function or method definition.
- Keep functions small enough that the comment describes one purpose.
- Keep underwriting rules in backend configuration/domain code, not React.
- Use typed schemas at API, provider, YAML, graph-state, and interrupt boundaries.
- Keep raw files, clients, sessions, and secrets out of LangGraph state.
- Use deterministic fake providers in normal tests and synthetic data everywhere.
- Never expose secrets, medical details, identifiers, full documents, or raw prompts in logs/traces.
- Never allow AI output to activate rules or finalize a route.

## Target repository structure

```text
underwrite_flow/
├── .env.example
├── .gitignore
├── compose.yaml
├── compose.isolated.yaml
├── compose.smoke.yaml
├── Makefile
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/versions/
│   ├── src/underwriteflow/
│   │   ├── auth/              # Demo identity and role enforcement
│   │   ├── cases/             # Intake, documents, evidence, review
│   │   ├── products/          # YAML validation and version activation
│   │   ├── workflow/          # Parent graph, nodes, subgraphs, state
│   │   ├── providers/         # Fake, Gemini, optional Ollama
│   │   ├── queues/            # Queue queries and transitions
│   │   ├── audit/             # Immutable business audit events
│   │   └── evaluation/        # Reference-label metrics
│   └── tests/{unit,integration,contract,fixtures}/
├── web/
│   ├── Dockerfile
│   └── src/{api,app,components,pages,test}/
├── product-config/
├── sample_data/
├── evaluation/
└── scripts/
```

## Implementation steps

### Step 1: Scaffold the Docker runtime

**Files:** `.gitignore`, `.env.example`, `compose.yaml`, `compose.isolated.yaml`, `Makefile`, `api/requirements.txt`, API/web Dockerfiles and manifests, minimal package roots.

**Work:**

- Mirror the proven Decision Assistant Compose shape: `db`, `api`, `web`, and optional-profile `ollama`.
- Add health checks, dependency ordering, bind-mounted source, named PostgreSQL/upload/Ollama/node-modules volumes, isolated-network override, and fake-provider smoke override.
- Configure Gemini as the intended default without requiring a key for health checks or deterministic tests.
- Add LangSmith variables with tracing off and `LANGSMITH_ENDPOINT=https://apac.api.smith.langchain.com`.
- Pin approved Python dependencies in `api/requirements.txt`; commit the frontend lockfile.

**Verify:** Compose configuration, image builds, container Python/Node versions, empty test commands, secret scan, and every hand-written file under 400 lines.

**Proposed commit:** `chore: scaffold UnderwriteFlow Docker runtime`

### Step 2: Add the API composition root and stable error contract

**Files:** API settings, database lifecycle, errors, request IDs, app factory, and unit tests.

**Work:**

- Add `/health`, `/ready`, CORS for the local web origin, and `/api/v1` business routing.
- Return stable sanitized errors with code, message, request ID, retryability, and optional safe details.
- Validate runtime configuration without printing secret values.

**Verify:** focused API tests inside Compose; health works without live providers; unknown routes use the error schema.

**Proposed commit:** `feat: add API foundation and error contract`

### Step 3: Create the initial PostgreSQL model and migration

**Files:** SQLAlchemy models, repositories, Alembic setup, `01_initial.py`, and integration tests.

**Work:**

- Model users, products, product/rulebook versions, reference documents, cases, submissions, documents, extracted fields, validations, risk signals, recommendations, reviews, audit events, and handoffs.
- Store LangGraph checkpoints in its supported PostgreSQL tables, separate from business audit tables.
- Add foreign keys, uniqueness, timestamps, immutable version links, and idempotency keys.

**Verify:** migrate a fresh database; inspect current revision; integration tests prove product-version pinning and append-only audit behavior.

**Approval:** This step requires explicit schema approval before execution.

**Proposed commit:** `feat: add UnderwriteFlow persistence baseline`

### Step 4: Implement demo authentication and three-role authorization

**Files:** auth schemas/service/router/dependencies, seed utility, and authorization tests.

**Work:**

- Implement Applicant, Underwriter, and Administrator roles only.
- Use short-lived signed sessions and Argon2 password hashes for fictional demo accounts.
- Enforce authorization in the backend for cases, reviews, audit access, and product configuration.

**Verify:** role matrix tests prove allowed actions and denial across another applicant's case; logs contain no credentials or tokens.

**Approval:** This step requires explicit authentication/authorization approval before execution.

**Proposed commit:** `feat: add demo role-based access control`

### Step 5: Build versioned product configuration

**Files:** three YAML files, product schemas/service/router/repository, admin tests, and import script.

**Work:**

- Define fictional motor-private-car, life-individual-term, and health-individual-family-floater configurations.
- Validate metadata, fields, conditional documents, routing rules, specialist labels, and version identity.
- Support validate, preview, activate, retire, and list-history operations.
- Pin in-progress cases to their starting product/rulebook versions; never infer active rules from documents.

**Verify:** invalid YAML cannot replace the active version; activation is audited; existing cases remain pinned.

**Proposed commit:** `feat: add versioned insurance product configuration`

### Step 6: Implement case intake and document storage

**Files:** case/document schemas, service, storage adapter, router, and tests.

**Work:**

- Create cases from the built-in applicant flow or documented synthetic API.
- Validate product-specific fields and conditional requirements using the pinned configuration.
- Store originals in the upload volume and metadata/hash in PostgreSQL.
- Accept supported PDFs/JPEGs/PNGs within configured count, size, and page limits; reject unsafe paths/types.

**Verify:** intake idempotency, ownership, limits, hashes, unsupported formats, and restart persistence.

**Proposed commit:** `feat: add application intake and document storage`

### Step 7: Add provider contracts and local document extraction

**Files:** provider protocol/fakes/Gemini/Ollama adapters, parser/OCR services, schemas, and unit/contract tests.

**Work:**

- Separate trusted system instruction from untrusted applicant/document content.
- Extract digital PDF text locally; run local OCR for scanned PDFs and images.
- Require structured, schema-validated model output with evidence locators and confidence.
- Retry transient provider failures only; return typed sanitized failures.

**Verify:** deterministic fake tests, malformed-output handling, prompt-injection fixture, locator preservation, and opt-in live contracts.

**Approval:** New provider/OCR dependencies or a provider change require explicit approval before execution.

**Proposed commit:** `feat: add document extraction and model providers`

### Step 8: Build the parallel LangGraph evidence pipeline

**Files:** graph state, reducers, document worker node, fan-out/join nodes, checkpoint setup, and graph tests.

**Work:**

- Create typed serializable state and start each run with a stable case `thread_id`.
- Fan out documents with `Send`, capped at three concurrent document branches per case.
- Preserve successful siblings when one document fails; retry transient failures only within that branch.
- Join with reducers, sort results deterministically, then reconcile evidence sequentially.

**Verify:** bounded concurrency, complete joins, stable ordering, sibling-failure isolation, branch-local retries, checkpoint resume, and delta processing.

**Proposed commit:** `feat: add parallel evidence-processing graph`

### Step 9: Add motor, life, and health subgraphs

**Files:** shared rule engine, three product subgraphs, specialist labels, and unit/graph tests.

**Work:**

- Select exactly one product subgraph from the case's pinned product code.
- Run only independent configured checks in parallel inside that subgraph.
- Return normalized validation results and risk signals; deterministic rule results outrank model observations.
- Keep fictional thresholds in versioned YAML, not source code.

**Verify:** selected-subgraph-only execution, product fixtures, reducer correctness, deterministic results, and unsupported-product handling.

**Proposed commit:** `feat: add product-specific triage subgraphs`

### Step 10: Assemble recommendations and human review interrupts

**Files:** summary/routing/review nodes, review API, schemas, and graph/integration tests.

**Work:**

- Assemble evidence-linked facts, conflicts, missing information, risk signals, and open questions.
- Apply precedence: unsupported/manual, needs information, specialist, standard, expedited.
- Recommend exactly one final triage route when sufficient information exists.
- Interrupt before final routing; resume the same thread after an authenticated confirm, override, or request-information command.

**Verify:** route precedence, evidence links, mandatory override reason, unauthorized resume denial, node restart safety, and no final route without human confirmation.

**Proposed commit:** `feat: add governed triage review checkpoint`

### Step 11: Implement queues, audit history, and idempotent completion

**Files:** queue/audit/handoff services and routers, mock webhook worker, and integration tests.

**Work:**

- Expose New, Needs Information, Underwriter Review, and Completed queues with product/route/specialist filters.
- Record immutable events for inputs, versions, transitions, outputs, underwriter actions, and completion.
- Finalize a confirmed route exactly once and optionally emit a minimal non-sensitive mock webhook.
- Keep checkpoint data operational and audit data user-inspectable.

**Verify:** queue transitions, audit reconstruction, retry without duplicate completion/webhook, and restart recovery.

**Proposed commit:** `feat: add queues audit trail and completion`

### Step 12: Build the React user journeys

**Files:** typed API client, app routing, shared components, role pages, CSS, and UI tests.

**Work:**

- Implement the approved nine-screen design: role entry; applicant dashboard; product selection; application form; documents; tracking; underwriter queue; case review; admin/audit.
- Add product-aware fields without duplicating routing rules in the browser.
- Make submitted facts, deterministic results, and AI observations visually distinct.
- Require evidence acknowledgement before confirmation and preserve an easy, reasoned override.

**Verify:** Vitest/Testing Library flows, API error states, keyboard use, focus, dialogs, labels, responsive layouts, and production build.

**Proposed commit:** `feat: build UnderwriteFlow web journeys`

### Step 13: Add synthetic evaluation and optional LangSmith tracing

**Files:** 90-case dataset, evaluation metrics/runner/API/UI, trace redaction, and tests.

**Work:**

- Add 30 visibly synthetic cases per product, split 60 development and 30 holdout, balanced across final routes.
- Measure route agreement, specialist recall, evidence accuracy, conflict/missing-data detection, unsupported claims, and workflow reliability.
- Enable LangSmith only through explicit environment configuration for synthetic development/evaluation traces.
- Redact identifiers and document content; application behavior must not depend on LangSmith availability.

**Verify:** dataset schema/balance, metric fixtures, tracing-off behavior, redaction, and opt-in APAC trace smoke.

**Approval:** Enabling external tracing or adding its SDK requires explicit approval before execution.

**Proposed commit:** `feat: add synthetic evaluation and optional tracing`

### Step 14: Complete deterministic smoke test and portfolio documentation

**Files:** smoke utilities, README, architecture diagram, demo guide, and final test adjustments.

**Work:**

- Run a fake-provider Compose flow: configure product, submit case/documents, process parallel graph, pause, confirm, complete, and inspect audit history.
- Document setup, Docker profiles, provider privacy boundary, LangSmith APAC configuration, architecture, limitations, and a 3–5 minute CV demo.
- Record actual evaluation results only; never invent metrics.

**Verify:** full API suite, web suite/build, fresh migration, Compose build/health, deterministic smoke, secret scan, line limits, and `git diff --check`.

**Proposed commit:** `docs: complete UnderwriteFlow MVP verification`

## Milestones

1. **Foundation:** Steps 1–4 establish runtime, API, persistence, and access control.
2. **Backend vertical slice:** Steps 5–10 process one synthetic case through configuration, parallel evidence analysis, recommendation, and human review.
3. **Complete product:** Steps 11–12 deliver queues, auditability, completion, and the approved user journeys.
4. **Portfolio proof:** Steps 13–14 provide reproducible evaluation, optional observability, smoke verification, and demo documentation.

At every milestone, review scope and remove optional work before adding infrastructure. LangSmith, Ollama, and the mock webhook are the first features to omit if they threaten the core human-governed triage demonstration.

## Main-branch remediation

The whole-branch PRD review identified follow-up work after Steps 1–14.
Execute the remediation plan in
`docs/MAIN_BRANCH_REMEDIATION_PLAN.md` under the same delivery protocol.
