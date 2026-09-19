# Tasks: Journey, Product Authoring, and Evaluation

**Input**: Design documents from
`specs/002-journey-authoring-evaluation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`,
`data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. Write each focused test first and confirm failure.

**Delivery rule**: Complete one delivery phase only. Report changed files,
verification, risks, and proposed commit. Wait for explicit `continue`
before commit or next phase.

## Format

- **[P]**: Safe to run in parallel after preceding dependencies.
- **[US1]**, **[US2]**, **[US3]**: User-story traceability.
- Every task names exact files.

## Phase 1: Setup

**Purpose**: Confirm baseline and approval boundary.

- [X] T001 Run current API, web, build, and smoke baselines from
  `specs/002-journey-authoring-evaluation/quickstart.md`; record blockers
  there before feature edits.
- [X] T002 Obtain explicit schema-migration approval before creating
  `api/alembic/versions/08_case_journey.py`; stop if approval is absent.

**Checkpoint**: Baseline known. Migration approved.

---

## Phase 2: Foundational Journey Contract

**Purpose**: Add shared persisted journey and configuration semantics.

**Critical**: This phase blocks every user story.

### Tests

- [X] T003 [P] Add migration upgrade, backfill, constraint, and downgrade
  tests in `api/tests/integration/test_journey_migration.py`.
- [X] T004 [P] Add journey defaults, subsets, document-stage, reference, and
  pure-filter tests in `api/tests/unit/test_journey_configuration.py`.
- [X] T005 [P] Add legacy semantic re-import and immutable-hash tests in
  `api/tests/unit/test_product_legacy_import.py` (split from
  `test_products.py` to stay under the 400-line file limit).

### Implementation

- [X] T006 Add revision 08 in
  `api/alembic/versions/08_case_journey.py`: `journey_type` is non-null,
  defaults/backfills to `new_business`, accepts only `new_business` or
  `renewal`, and downgrade removes its constraint then column.
- [X] T007 Add the constrained `journey_type` field to `Case` in
  `api/src/underwriteflow/persistence/models.py`.
- [X] T008 Add journey schema and pure filtering in
  `api/src/underwriteflow/products/schemas.py` (cross-reference validation
  and the pure filter itself live in the new
  `api/src/underwriteflow/products/journey.py` to stay under the 400-line
  file limit): `supported_journeys` is a unique, non-empty list defaulting to
  `[new_business]`; `applies_to` is a non-empty supported subset defaulting
  to `[new_business]`; `required_for` is null or a subset of document
  `applies_to`; `stage` defaults to `supporting` and accepts only
  `prior_policy` or `supporting`.
- [X] T009 Normalize stored and incoming configurations before legacy version
  conflict checks in `api/src/underwriteflow/products/service.py`; preserve
  existing stored payloads and hashes.
- [X] T010 Run Phase 2 checks from
  `specs/002-journey-authoring-evaluation/quickstart.md`; report results and
  proposed commit, then wait for `continue`.

**Checkpoint**: Legacy configurations remain new-business-only. Journey model
works. No behavior or UI work starts before review.

---

## Phase 3: User Story 1 - Correct Insurance Journey

**Priority**: P1

**Goal**: Support first-class new-business and renewal journeys through
intake, evidence, workflow, staff review, audit, and completion.

**Independent Test**: Complete motor new-business and renewal cases. Verify
only journey-applicable fields, documents, rules, and checks run. Verify
journey remains visible through human-confirmed completion.

### Tests

- [X] T011 [P] [US1] Add create, application-replacement, configuration, and
  catalogue contracts in `api/tests/contract/test_journey_api.py`.
  (trimmed scope: create/journey default, catalogue journey filter,
  application replace + ownership; queue/review/audit contracts deferred
  to T014.)
- [X] T012 [P] [US1] Add partial-save, complete-submit, ownership, status, and
  document-applicability tests in `api/tests/unit/test_cases.py`.
- [X] T013 [P] [US1] Add new-business, renewal, missing-policy, unreadable
  evidence, rule-filter, pinning, and reload scenarios in
  `api/tests/integration/test_journey_workflow.py`.
  (trimmed scope: renewal prior-policy enforcement at submit and
  new-business exclusion of renewal-only requirements; unreadable
  evidence/pinning/reload scenarios deferred.)
- [X] T014 [P] [US1] Add journey queue, review, audit, handoff, and idempotent
  completion contracts in `api/tests/contract/test_journey_staff.py`.
- [X] T015 [P] [US1] Add keyboard-accessible journey choice, unsupported
  product, staged renewal, and reload tests in
  `web/src/journey-flow.test.tsx`.

### Implementation

- [X] T016 [US1] Add immutable motor v4 and health v3 journey configurations
  in `product-config/motor-private-car-v4.yaml` and
  `product-config/health-individual-family-floater-v3.yaml`; register both
  in `api/src/underwriteflow/products/import_configs.py`.
- [X] T017 [US1] Add journey, application, and document-stage types in
  `api/src/underwriteflow/cases/schemas.py`: journey defaults to
  `new_business`, draft payload defaults to `{}`, legacy document codes
  default to `[]`, and responses expose immutable journey.
- [X] T018 [US1] Split partial draft validation from complete submission
  validation, replace owned mutable applications, reject non-applicable
  documents, and audit keys only in
  `api/src/underwriteflow/cases/service.py`
  (validation helpers split into `api/src/underwriteflow/cases/validation.py`
  to stay under the 400-line limit).
- [X] T019 [US1] Add owner-only
  `PUT /cases/{case_id}/application`, journey responses, and pinned
  application recovery in `api/src/underwriteflow/cases/router.py`.
- [X] T020 [US1] Filter active catalogue results by journey and return
  supported journeys in `api/src/underwriteflow/products/router.py`.
- [X] T021 [US1] Enforce complete stored answers and actual uploaded documents,
  then pass filtered configuration into existing graphs in
  `api/src/underwriteflow/cases/submission.py`.
- [X] T022 [US1] Add journey filtering/output to queue and completion, plus
  journey in handoff and audit details, in
  `api/src/underwriteflow/queues/schemas.py` and
  `api/src/underwriteflow/queues/router.py`.
- [X] T023 [US1] Add journey to review-start and review-decision responses in
  `api/src/underwriteflow/reviews/schemas.py` and
  `api/src/underwriteflow/reviews/router.py`.
- [X] T024 [US1] Add journey, application replacement, staged document, queue,
  review, and completion types/calls in `web/src/types.ts`,
  `web/src/api.ts`, `web/src/api-products.ts`, and
  `web/src/api-staff.ts`.
- [X] T025 [US1] Add journey-first selection and eligible-product display in
  `web/src/journey-selection.tsx` and integrate it in
  `web/src/app.tsx`.
- [X] T026 [US1] Implement new-business form-first and renewal
  prior-policy-first flows with reload recovery in
  `web/src/application-form.tsx`, `web/src/documents.tsx`, and
  `web/src/tracking.tsx`.
  (trimmed scope: `web/src/tracking.tsx` needed no change; the staged
  order and reload recovery live in `application-form.tsx`,
  `documents.tsx`, and `app.tsx`'s screen wiring. Reload recovery
  restores journey, case, pinned configuration, and document state, all
  already durable server-side; it does not prefill previously entered
  form answers, since no endpoint returns stored draft payload back to
  the client.)
- [ ] T027 [US1] Run US1 API/UI tests, full web build, and human-authority
  checks from `specs/002-journey-authoring-evaluation/quickstart.md`; report
  results and proposed commit, then wait for `continue`.

**Checkpoint**: US1 works independently. No admin-builder work starts before
review.

---

## Phase 4: User Story 2 - Guided Product Authoring

**Priority**: P2

**Goal**: Let administrators create products and versions using one guided
builder while preserving expert YAML, immutable drafts, and explicit
activation.

**Independent Test**: Build a blank product, reject invalid references, import
draft, activate, and confirm catalogue appearance. Clone and export without
changing active or pinned versions.

### Tests

- [X] T028 [P] [US2] Add normalized preview, configuration read, export,
  permission, corrupt payload, and YAML round-trip tests in
  `api/tests/contract/test_product_authoring.py`.
- [X] T029 [P] [US2] Add blank, clone, upload, identity-lock, validation, and
  semantic-diff state tests in `web/src/product-builder-state.test.ts`.
  Trimmed: upload normalization is server-driven (preview endpoint), so its
  coverage lives in T030/T039 UI tests, not a pure state-module function.
- [X] T030 [P] [US2] Add seven-section, keyboard, focus, labels, error summary,
  non-color diff, import, and activation tests in
  `web/src/product-builder.test.tsx`. Trimmed: activation itself is already
  covered end to end in `product-configuration.test.tsx`; this file verifies
  the import hand-off (`onImported`) that makes the new draft reachable.
- [X] T031 [P] [US2] Add draft-hidden, activation-visible, and case-pinning
  integration coverage in
  `api/tests/integration/test_product_builder_lifecycle.py`.

### Implementation

- [X] T032 [US2] Return normalized configuration from preview and add validated
  read/export service operations in
  `api/src/underwriteflow/products/service.py`. Preview now returns the full
  normalized configuration plus its original summary counts (additive, so
  the existing expert-YAML preview screen stays unaffected).
- [X] T033 [US2] Add administrator-only configuration and canonical YAML
  export endpoints in `api/src/underwriteflow/products/router.py`; use
  `application/yaml` and sanitized attachment names. Split the existing
  reference-document endpoints into
  `api/src/underwriteflow/products/reference_router.py` to keep both files
  under the 400-line limit.
- [X] T034 [US2] Add complete product configuration types, normalized preview,
  read, and export calls in `web/src/types.ts` and
  `web/src/api-products.ts`. Full config type lives in
  `product-builder-state.ts` (T035); reused `requestBlob` for export text,
  no `types.ts` change needed.
- [X] T035 [US2] Implement one browser configuration object, blank defaults,
  clone normalization, local completeness checks, and stable semantic diff in
  `web/src/product-builder-state.ts`.
- [X] T036 [US2] Build accessible wizard shell, source selection, identity,
  family, version, and journeys in `web/src/product-builder.tsx`. Family is
  fixed by the entry point (T040), so shown read-only, not editable here.
- [X] T037 [US2] Build applicant-field and staged-document editors in
  `web/src/product-builder-evidence.tsx`.
- [X] T038 [US2] Build routing-rule, reconciliation, parameter, and specialist
  label editors in `web/src/product-builder-rules.tsx`. Trimmed: no
  NCB/renewal reconciliation-parameter editor (untested, no consumer yet);
  add when a reconciliation kind needs configurable parameters in the UI.
- [X] T039 [US2] Add normalized preview, active-version diff, JSON through
  `yaml_text` import, and stale-preview invalidation (via `yamlHash`, reused
  from `product-import.tsx`) in `web/src/product-builder-review.tsx`.
  Trimmed: canonical export applies to persisted versions, already served by
  the existing history panel (T033/T034); nothing to export before import.
- [X] T040 [US2] Add Create product/Create version entry points, preserve YAML
  expert path, and keep activation confirmation in
  `web/src/product-configuration.tsx`. `web/src/admin.tsx` is the unrelated
  audit workspace screen; product config lives only in
  `product-configuration.tsx`, so it needed no change.
- [X] T041 [US2] Run US2 API/UI/accessibility tests and production build from
  `specs/002-journey-authoring-evaluation/quickstart.md`; report results and
  proposed commit, then wait for `continue`. Found and fixed a pre-existing
  test bug along the way: three integration tests picked motor-private-car's
  product/rulebook version with an unordered `LIMIT 1` query, which silently
  depended on row order. The repo seeds motor-private-car with v1-v4
  (`product-config/motor-private-car-v*.yaml`), so once physical row order
  shifted, the query could return a non-active version and break document
  requirements. Pinned all three (one shared fixture, two inline copies) to
  `version = 'v1'`.

**Checkpoint**: US2 works independently. No isolated-evaluation work starts
before review.

---

## Phase 5: User Story 3 - Isolated End-to-End Evaluation

**Priority**: P3

**Goal**: Keep fast offline metrics and add repeatable public-HTTP evaluation
with fresh isolated storage and no development-state writes.

**Independent Test**: Run the isolated 90-case command twice. Verify fresh
state, identical deterministic fields, complete artifacts, human review,
idempotent completion, and unchanged development rows/files.

### Tests

- [ ] T042 [P] [US3] Add 90-case journey/version distribution, uniqueness,
  supported-version, and route-balance tests in
  `api/tests/unit/test_evaluation.py`.
- [X] T043 [P] [US3] Add mocked HTTP flow, stable result, atomic write,
  sanitized failure, and nonzero-exit tests in
  `api/tests/unit/test_evaluation_e2e.py`. Trimmed: mocks cover login,
  one case's create/upload/submit, atomic write, and the failure/exit-code
  shape only — not the full 9-step review/completion orchestration, which
  T051's live double-run against the real stack verifies instead of a mock
  that would just re-describe the same system. `pytest.importorskip` keeps
  this module from blocking `make test-api` before T047 adds the runner
  script it targets.
- [X] T044 [P] [US3] Add rendered Compose isolation tests for no ports, named
  volumes, development network, DB URL in runner, live provider, or tracing in
  `api/tests/contract/test_evaluation_compose.py`. Parses the YAML directly
  (no stack needed); skips cleanly via `pytest.skip` until T048 adds the
  file, so it doesn't block `make test-api` either.

### Implementation

- [X] T045 [US3] Add `journey_type` and exact
  `configuration_version` to all records while preserving required product,
  journey, split, and 30/30/30 route counts in `evaluation/cases.json`.
  Extended `evaluation/generate_evidence.py` to select fields/checks by
  (product, version, journey) instead of one config per product, then
  regenerated. 15 motor (v4) and 15 health (v3) records flipped to renewal
  (suffixes 6-10/16-20/26-30 per product, route/split untouched); life stays
  30 new-business on v1, since no life version supports renewal yet. Known
  gap for T046: the offline runner still picks the earliest version per
  product and ignores `journey_type`/`configuration_version`, so it
  currently evaluates the new renewal records against v1/v1 (a safe subset,
  hence still green) rather than their exact declared version.
- [X] T046 [US3] Load exact versions, filter by journey, and retain current
  in-memory API metrics in
  `api/src/underwriteflow/evaluation/runner.py` and
  `api/src/underwriteflow/evaluation/dataset.py`. Moved config loading into
  `dataset.load_configuration_manifest()` (keyed by product+version); runner
  looks up each record's exact `configuration_version` and filters it with
  the existing `filter_configuration_for_journey` before evaluating. No
  metrics/router change, so the in-process admin evaluation endpoint is
  untouched.
- [ ] T047 [US3] Implement dataset preflight, public HTTP orchestration,
  synthetic PDF reuse, representative reviews, double completion, queue/audit
  checks, and atomic success/failure output in `scripts/evaluate_e2e.py`;
  include schema version, pass flag, provider, hashes, counts, metrics,
  reviewed/completed counts, sorted failures, and elapsed seconds only.
- [ ] T048 [US3] Add standalone tmpfs database, bootstrap, API, and runner with
  fake provider, tracing disabled, internal network, no ports, and no named
  volumes in `compose.evaluation.yaml`.
- [ ] T049 [US3] Add `evaluate-e2e` lifecycle/exit propagation to
  `Makefile` and ignore only `evaluation/results/` in `.gitignore`.
- [ ] T050 [US3] Add CI execution of `make evaluate-e2e` and always retain
  `evaluation/results/e2e.json` in
  `.github/workflows/evaluation.yml`.
- [ ] T051 [US3] Run `make evaluate-e2e` twice and compare deterministic
  fields per `specs/002-journey-authoring-evaluation/contracts/evaluation.md`;
  verify development rows, files, containers, and volumes remain unchanged.
- [ ] T052 [US3] Report US3 files, commands, artifact hashes, remaining risks,
  and proposed commit using
  `specs/002-journey-authoring-evaluation/quickstart.md`; wait for
  `continue`.

**Checkpoint**: US3 works independently. All planned product gaps are closed.

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Prove combined behavior without expanding scope.

- [ ] T053 [P] Update journey, builder, evaluation, limitations, and synthetic
  data guidance in `README.md`, `docs/ARCHITECTURE.md`,
  `docs/DEMO.md`, and `docs/RELEASE_READINESS.md`.
- [ ] T054 Run full API/web suites, production build, smoke, evaluation,
  secret scan, line-length check, file-size check, and `git diff --check`
  using `Makefile` and
  `specs/002-journey-authoring-evaluation/quickstart.md`.
- [ ] T055 Confirm no automated approval, decline, binding, pricing, issue,
  renewal, or cancellation; record final evidence and risks in
  `docs/RELEASE_READINESS.md`.

---

## Dependencies and Execution Order

### Phase Dependencies

- Phase 1 has no dependency.
- Phase 2 depends on Phase 1 and explicit migration approval.
- US1 depends on Phase 2.
- US2 technically depends on Phase 2; delivery protocol waits for US1 review.
- US3 depends on US1 contracts; delivery protocol waits for US2 review.
- Phase 6 depends on all selected user stories.

### User Story Dependencies

- **US1**: Foundation only. Delivers MVP.
- **US2**: Foundation for journey-aware configuration. No US1 UI dependency.
- **US3**: US1 public journey contracts and built-in versions. No builder
  runtime dependency.

### Within Each Phase

1. Write focused tests. Confirm failure.
2. Add minimum implementation.
3. Run focused and regression checks.
4. Report files, verification, risks, and proposed commit.
5. Wait for explicit `continue`.

## Parallel Opportunities

### US1

- T011-T015 can run together.
- Backend contracts T017-T023 can proceed separately from web T024-T026 after
  response shapes settle.

### US2

- T028-T031 can run together.
- T032-T033 and T035 can proceed together after tests fail.
- T037 and T038 touch separate section components.

### US3

- T042-T044 can run together.
- T047 and T048 touch separate runner and infrastructure files after contracts
  settle.
- T049 and T050 touch separate automation files.

## Implementation Strategy

### MVP First

1. Complete Setup.
2. Complete Foundational Journey Contract.
3. Complete US1.
4. Stop and validate both journeys plus human confirmation.

### Incremental Delivery

1. US1: correct journey and evidence behavior.
2. US2: nontechnical product authoring.
3. US3: isolated production-shaped evidence.
4. Polish: combined release proof.

### Scope Guards

- Add no dependency.
- Add no second rule engine, provider stack, or mutable draft table.
- Do not alter prior migrations or product-version files.
- Do not expose evaluation ports or development storage.
- Use synthetic data only.
- Preserve authenticated human final authority.
