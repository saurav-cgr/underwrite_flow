# Research: Environment Baseline and Evaluation Loading

## Decision 1: Reuse the Existing Common Baseline

**Decision**: Keep `alembic upgrade head` followed by the current product
configuration importer as the only automatic initialization in every mode.

**Rationale**: Migrations already create the schema, three demo identities,
roles, permissions, and role mappings. Product import is validated and
idempotent. Neither path creates applications, cases, or documents.

**Alternatives considered**:

- Add a second baseline seeder: duplicates existing migrations and import.
- Seed sample cases during development startup: recreates the dataset the user
  explicitly removed.
- Activate product versions automatically: weakens explicit administrator
  authority and changes existing behavior.

## Decision 2: Add One Explicit Environment Mode

**Decision**: Add a validated `development | evaluation | production` setting.
Development remains the local default; Compose files set evaluation and
production explicitly.

**Rationale**: The loader needs one process-owned, fail-closed answer before it
touches persistence. The setting also makes environment behavior inspectable.

**Alternatives considered**:

- Infer mode from database names or credentials: fragile and secret-coupled.
- Use a separate Boolean only for loading: permits contradictory settings.
- Accept arbitrary environment strings: cannot enforce production denial.

## Decision 3: Use an Explicit Operator Command

**Decision**: Add one script invoked through Docker Compose and a Make target.
No service depends on it during startup.

**Rationale**: Loading 90 cases is operator work, not request-time behavior.
A command is easy to retry, inspect, and deny before persistence opens.

**Alternatives considered**:

- New public load endpoint: adds an unnecessary long-running mutation surface.
- New long-running loader service: idle infrastructure for a one-shot action.
- Run the existing end-to-end evaluator unchanged: it is not retry-safe and
  performs review and completion work beyond loading.

## Decision 4: Pin Exact Versions Without Activation

**Decision**: Minimally extend the existing case service so trusted internal
loading can supply an already-resolved product and rulebook version. Normal API
intake continues to resolve only the active version.

**Rationale**: The corpus spans several versions of one product. Sequential
activation would change administrator-controlled active state and append
unrelated activation events.

**Alternatives considered**:

- Activate versions group by group and restore afterward: more writes and
  failure recovery for state that need not change.
- Insert cases directly: bypasses validation, audit, and version ownership.
- Rewrite the corpus to one active version: destroys reference reproducibility.

## Decision 5: Reuse the Existing Workflow with the Fake Provider

**Decision**: Persist the cases and documents through existing services, then
submit incomplete stages with the deterministic `FakeProvider`. Expected labels
remain verification inputs rather than stored recommendations.

**Rationale**: Development users receive realistic persisted recommendations,
evidence, checkpoints, and audit without network calls or a second workflow.

**Alternatives considered**:

- Load draft cases only: omits much of the evaluation data users need to
  inspect.
- Copy expected outcomes into recommendation rows: turns labels into fabricated
  system decisions and bypasses workflow evidence.
- Use the configured provider: may cause external calls and nondeterminism.

## Decision 6: Reuse Existing Idempotency and Audit Storage

**Decision**: Namespace existing case idempotency keys by dataset SHA-256 and
source case ID. Mark verified records and final completion with append-only
audit events. Add no load-status table.

**Rationale**: Existing case uniqueness, document hashes, and audit JSON are
enough at the current 90-case scale. Completion can be recomputed from actual
records after restart.

**Alternatives considered**:

- New `evaluation_loads` table: adds a migration for state derivable from
  existing rows and audit.
- Filesystem-only marker: can disagree with database state after restart.
- Delete and reload: risks unrelated data and violates retry safety.

## Decision 7: Resume by Verification, Never Overwrite

**Decision**: On retry, verify the pinned version, journey, application,
documents, workflow status, and derived result. Skip exact matches and continue
only missing stages. Fail on any reserved-identity mismatch.

**Rationale**: This preserves developer changes and makes interruption safe
without cleanup or destructive reset behavior.

**Alternatives considered**:

- Blindly repeat uploads and submission: duplicates data or fails on status.
- Replace mismatched cases: can destroy developer-owned records.
- Roll back the entire 90-case load: unavailable across separate workflow and
  storage commits and unnecessary for a resumable command.

## Decision 8: Keep Production Blocking Narrow and Honest

**Decision**: Production retains schema, permissions, demo accounts, and
product configurations, but the loader exits before database or storage access.
Documentation states this is not a production-readiness guarantee.

**Rationale**: This directly implements the requested boundary without
claiming broader security or deployment hardening.

**Alternatives considered**:

- Remove evaluation files from production only: image or mount mistakes could
  still expose them and would not enforce the command boundary.
- Remove default demo accounts: contradicts the approved specification.
- Block all synthetic application creation: outside the loader's scope and the
  existing demonstration product model.
