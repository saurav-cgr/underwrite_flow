# Tasks: Environment Baseline and Evaluation Loading

**Input**: Design documents from
`specs/004-environment-data-seeding/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/evaluation-loader.md`, `quickstart.md`

**Tests**: Required by the specification, project constitution, and
`AGENTS.md`. Write each focused test first and confirm it fails before the
matching implementation.

**Organization**: Tasks are grouped by user story. All paths are relative to
the repository root.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no
  incomplete dependency.
- **[Story]**: Maps the task to one specification user story.

## Phase 1: Setup

**Purpose**: Establish failing contracts for the shared environment boundary.

- [X] T001 [P] Add failing settings tests in
  `api/tests/unit/test_environment_config.py` for the exact enum constraint
  `development | evaluation | production`, development default, and the
  derived rule that evaluation loading is allowed only outside production.
- [X] T002 [P] Add failing Compose contracts in
  `api/tests/contract/test_environment_compose.py` proving explicit base,
  evaluation, and production modes and proving no startup command invokes the
  evaluation loader.

---

## Phase 2: Foundational

**Purpose**: Add shared mode validation and authoritative corpus preflight.

**Critical**: Complete this phase before any user-story implementation.

- [X] T003 Implement the validated environment mode and derived loading flag
  in `api/src/underwriteflow/config.py` until T001 passes; unsupported values
  must prevent startup and mode must remain fixed for the process lifetime.
- [X] T004 Configure `ENVIRONMENT_MODE` in `.env.example`, `compose.yaml`,
  `compose.evaluation.yaml`, and new `compose.production.yaml` until T002
  passes, without adding a loader startup dependency or production-readiness
  claim.
- [X] T005 [P] Add failing corpus-preflight tests in
  `api/tests/unit/test_evaluation_dataset_preflight.py` for exactly 90 unique
  cases, exact `SYNTHETIC - FOR DEMONSTRATION ONLY` labels, supported splits,
  journeys, route balance, and resolvable product/version pairs.
- [X] T006 Move the reusable corpus preflight into
  `api/src/underwriteflow/evaluation/dataset.py` and update
  `scripts/evaluate_e2e.py` to call it until T005 and existing evaluation tests
  pass without duplicating validation logic.

**Checkpoint**: Environment mode and corpus validation are reusable by all
stories.

---

## Phase 3: User Story 1 - Start with the Common Baseline (Priority: P1)

**Goal**: Every environment starts with schema, permissions, default demo
accounts, and product configurations, but no sample business records.

**Independent Test**: Initialize each mode from empty storage and verify the
common baseline, all three demo logins, zero cases/submissions/documents, and
an unchanged second initialization.

### Tests for User Story 1

- [X] T007 [P] [US1] Add failing fresh-storage baseline coverage in
  `api/tests/integration/test_environment_baseline.py` for the exact three
  active demo identities, existing roles/scopes, all built-in product
  versions, zero business records, and duplicate-free reinitialization.
- [X] T008 [P] [US1] Add a failing safe-status contract test in
  `api/tests/unit/test_app.py` for only `environment` and
  `evaluation_loading_allowed`, with no credential, URL, key, token, or path.

### Implementation for User Story 1

- [X] T009 [US1] Add the read-only environment status response in
  `api/src/underwriteflow/app.py` using validated settings until T008 passes;
  do not expose another configuration field or add authentication behavior.
- [X] T010 [US1] Run T002, T007, T008, existing product-import tests, and all
  three documented demo login checks through Docker Compose; record any
  necessary minimal baseline repair in the already-owned files from T004 or
  `api/src/underwriteflow/products/import_configs.py`.

**Checkpoint**: User Story 1 is independently usable and is the MVP.

---

## Phase 4: User Story 2 - Load Evaluation Data on Demand (Priority: P2)

**Goal**: One explicit command loads and verifies the authoritative evaluation
corpus in development or evaluation without duplicates or unrelated changes.

**Independent Test**: Load the corpus twice into development and verify one
complete 90-case dataset, unchanged unrelated records, safe interruption and
retry, exact version pinning, and no human completion.

### Tests for User Story 2

- [X] T011 [P] [US2] Add failing exact-version case-creation tests in
  `api/tests/unit/test_cases.py` proving trusted internal creation pins the
  requested existing product and rulebook without activation while normal API
  intake still selects only the active version.
- [X] T012 [P] [US2] Add failing loader unit tests in
  `api/tests/unit/test_evaluation_loader.py` for dataset SHA-256 identity,
  stable `evaluation:<sha256>:<source_case_id>` keys, deterministic ordering,
  sanitized JSON output, and fake-provider-only execution.
- [X] T013 [P] [US2] Add failing integration coverage in
  `api/tests/integration/test_evaluation_loader.py` for exact payload,
  journey, version, document-code/hash, workflow-result, and audit mappings;
  include repeat, unrelated-record, interruption, retry, and collision cases.

### Implementation for User Story 2

- [X] T014 [US2] Minimally extend exact-version resolution in
  `api/src/underwriteflow/cases/service.py` until T011 passes, reusing the
  existing validation, submission, rulebook, and audit path and keeping the
  file below 400 lines.
- [X] T015 [US2] Implement preflight and stable record loading in
  `scripts/load_evaluation_data.py` using the existing dataset loader,
  `scripts/synthetic_pdf.py`, `CaseService`, `UploadStorage`, and
  `FakeProvider`; never activate product versions or call an external provider.
- [X] T016 [US2] Complete resumable verification and append-only markers in
  `scripts/load_evaluation_data.py`: skip exact documents by code/hash, resume
  missing stages, reject mismatches with `evaluation_record_collision`, append
  each record marker once, and append the dataset marker only after all 90
  records verify.
- [X] T017 [US2] Add the explicit `load-evaluation-data` command to `Makefile`
  and the read-only corpus mount needed by the evaluation service in
  `compose.evaluation.yaml`; normal `up` must never run the command.
- [X] T018 [US2] Run T005, T011-T013, the existing end-to-end evaluation tests,
  and `make load-evaluation-data` twice; verify 90 cases, the current expected
  document count, zero duplicate rows/files/events, and zero review,
  completion, or handoff actions.

**Checkpoint**: User Stories 1 and 2 work independently; no second seed corpus
or load-status table exists.

---

## Phase 5: User Story 3 - Block Evaluation Data in Production (Priority: P3)

**Goal**: Production refuses the same loader before database, storage, or
audit access while retaining the common baseline.

**Independent Test**: Invoke the loader in production mode and verify the
stable refusal code, nonzero exit, zero writes, and an unchanged usable
baseline.

### Tests for User Story 3

- [X] T019 [P] [US3] Add a failing production-guard unit test in
  `api/tests/unit/test_evaluation_loader.py` that spies on database and upload
  construction and expects neither to occur before
  `evaluation_load_forbidden` is returned.
- [X] T020 [P] [US3] Add a failing production no-write integration case in
  `api/tests/integration/test_evaluation_loader.py` covering cases,
  submissions, documents, recommendations, checkpoints, audit events, and
  upload files while confirming the common baseline remains usable.

### Implementation for User Story 3

- [X] T021 [US3] Add the fail-closed production check as the first executable
  loader step in `scripts/load_evaluation_data.py` until T019 and T020 pass;
  emit only environment, `complete: false`, and
  `evaluation_load_forbidden` with a nonzero exit.
- [X] T022 [US3] Extend `api/tests/contract/test_environment_compose.py` to
  render `compose.yaml` plus `compose.production.yaml`, prove the API receives
  production mode, and prove no service command automatically loads data.
- [X] T023 [US3] Run the production command from
  `specs/004-environment-data-seeding/quickstart.md` and verify zero evaluation
  writes without deleting or resetting any volume.

**Checkpoint**: All three stories satisfy their independent acceptance tests.

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Document the operator path and prove existing safeguards remain.

- [X] T024 [P] Document baseline contents, the explicit loader command,
  production refusal, synthetic-only scope, and non-production-readiness in
  `README.md`; keep credentials referenced only through existing documented
  fictional demo values.
- [X] T025 Run the full gates from
  `specs/004-environment-data-seeding/quickstart.md`, then `make test-api`,
  `make test-web`, the web production build, `make smoke`, secret scanning,
  line-length checks, file-size checks, and `git diff --check`; record no live
  Gemini, Ollama, or LangSmith call and no human-authority regression.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup**: T001 and T002 can start immediately in parallel.
- **Foundational**: T003-T006 follow setup and block all stories.
- **US1**: T007-T010 require T003 and T004.
- **US2**: T011-T018 require T003-T006; they do not require US1's status
  endpoint.
- **US3**: T019-T023 require the T015 loader entry point and T004 production
  mode; production behavior remains independently testable.
- **Polish**: T024-T025 follow all selected stories.

### User Story Completion Order

```text
Setup ──> Foundation ──┬──> US1 (common baseline / MVP)
                       └──> US2 (explicit load)
                              └──> US3 (production refusal)
                                     └──> Polish
```

### Within Each Story

- Write and run the listed tests first; confirm failure.
- Implement only enough behavior to pass the focused tests.
- Run the story's independent acceptance check.
- Under `AGENTS.md`, stop at the approved implementation-step boundary,
  report changed files, verification, risks, and proposed commit, then wait for
  explicit `continue` before committing or beginning the next step.

## Parallel Opportunities

### User Story 1

```text
T007: Fresh-storage baseline integration coverage
T008: Safe environment-status unit contract
```

### User Story 2

```text
T011: Exact-version case-service tests
T012: Loader unit contract tests
T013: Loader persistence and retry integration tests
```

### User Story 3

```text
T019: Production guard unit test
T020: Production zero-write integration test
```

## Implementation Strategy

### MVP First

1. Complete T001-T006.
2. Complete T007-T010 for User Story 1.
3. Stop and validate the common baseline independently.

### Incremental Delivery

1. Deliver US1: predictable baseline with zero automatic business records.
2. Deliver US2: explicit, deterministic, resumable evaluation-data loading.
3. Deliver US3: fail-closed production refusal.
4. Complete cross-cutting documentation and full regression gates.

## Notes

- No dependency, provider, authentication rule, or schema migration is planned.
- No task may introduce a second evaluation corpus or sample-case seed.
- No task may auto-run the loader during startup.
- No task may confirm, override, complete, or hand off a loaded case.
- Keep every hand-written file below 400 lines and every line at 80 columns or
  fewer; split before exceeding either limit.

---

## Phase 7: Convergence

- [X] T026 CRITICAL Require an authenticated loader actor and persist its
  `actor_user_id` on every loader audit marker, while adding the exact pinned
  product and rulebook version identities to each per-case marker, per
  Constitution V (contradicts)
- [X] T027 Validate every required persisted product version and matching
  rulebook before the loader's first business or audit write, and add a
  no-write regression test for a missing baseline dependency, per plan: loader
  preflight (partial)
- [ ] T028 Reject reserved-record collisions for a mismatched product,
  rulebook, exact document set or hash, and derived missing-data or conflict
  result, with focused regression coverage for each mismatch, per plan: retry
  and collision rules (partial)
- [ ] T029 Catch corpus preflight and unexpected command failures at the CLI
  boundary, emit one sanitized JSON failure object, exit nonzero, and add a
  traceback-leak regression test, per contract: output (partial)
- [ ] T030 Make the exact-version case-creation test arrange or select an
  inactive product version deterministically instead of assuming
  `motor-private-car:v5` is inactive, per T011 (partial)
