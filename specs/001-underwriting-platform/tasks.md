<!-- ROUTE=direct | WRITE_READY=1 | READ_READY=0 | EXISTING=0 |
PLANNED_DISPATCH=0 | LEAD=task_generation | REASON=lead_faster |
DETAIL=One dependency graph is cheaper to author and validate directly. -->

# Tasks: Governed Underwriting Platform

**Input**: Design documents from `specs/001-underwriting-platform/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required. Write each focused test first, run it, and confirm it fails
for the intended reason before implementation.

**Delivery Gate**: Execute one phase at a time. After each phase, stop and
report changed files, Docker-based verification, remaining risks, and proposed
commit. Wait for explicit `continue` before committing or starting the next
phase. Obtain explicit approval before T003 because Phase 2 changes schema and
authentication. Obtain provider-change approval before T035.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different files and no dependency on an incomplete task
- **[Story]**: User story from `spec.md`
- Every task names its exact target path

## Phase 1: Setup and Baseline

**Purpose**: Prove existing behavior and reuse shared synthetic fixtures.

- [X] T001 Verify current auth, product, provider, workflow, review, and audit
  baselines in `api/tests/` and `web/src/*.test.ts*` through Docker Compose
- [X] T002 [P] Extend synthetic builders for users, roles, policies, RCs, and
  claims in `api/tests/fixtures/records.py`

**Checkpoint**: Baseline green; synthetic fixture vocabulary ready.

---

## Phase 2: Foundational Security and Persistence

**Purpose**: Add shared JWT, RBAC, refresh, and scope foundations.

**Critical**: Requires explicit schema and authentication approval first.

- [X] T003 Add failing RBAC migration and constraint tests in
  `api/tests/integration/test_dynamic_rbac_migration.py`
- [X] T004 Extend RBAC and refresh-session models without removing legacy
  fields in `api/src/underwriteflow/persistence/models.py`
  - Preserve `users.role`; backfill exactly one mapping for each known role.
  - `roles.code` is unique and stable; `title` is 1-200 characters;
    `description` is optional and at most 500 characters.
  - `permissions.code` is unique; role-permission pairs are unique.
  - `user_role_mappings.user_id` is unique: one role per user in this MVP.
  - Refresh digests are unique; expiry is required; revocation and replacement
    links are nullable; raw credentials are never stored.
- [X] T005 Add revision 07 for roles, permissions, role-permission mappings,
  user-role mappings, refresh sessions, seeds, and backfill in
  `api/alembic/versions/07_dynamic_rbac.py`
- [X] T006 [P] Add failing strict-JWT, refresh rotation, replay, issuer,
  audience, expiry, and tamper tests in `api/tests/unit/test_auth.py`
- [X] T007 Extend access JWT and refresh credential contracts in
  `api/src/underwriteflow/auth/schemas.py` and
  `api/src/underwriteflow/auth/service.py`
- [X] T008 Add failing current-user, stale-claim, disabled-user, ownership, and
  scope tests in `api/tests/integration/test_dynamic_authorization.py`
- [X] T009 Replace static role authorization with database scope resolution in
  `api/src/underwriteflow/auth/dependencies.py`
- [X] T010 Add JWT issuer, audience, access TTL, refresh TTL, and refresh
  pepper settings in `api/src/underwriteflow/config.py`, `.env.example`, and
  `compose.yaml` without logging their values

**Checkpoint**: Fresh migration succeeds; strict JWT and live scopes work;
legacy role column remains rollback-compatible.

---

## Phase 3: User Story 1 - Administer Secure Access (Priority: P1) MVP

**Goal**: Administrators manage synthetic users and custom roles; all secured
operations enforce current permissions.

**Independent Test**: Create two custom roles, assign separate users, log in,
refresh, inspect `/auth/me`, and prove allowed and denied operations reflect
the current database assignments.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing login, refresh, me, users, roles, and
  permission contract tests in `api/tests/contract/test_auth_rbac_contract.py`
- [X] T012 [P] [US1] Add failing admin journey and audit tests in
  `api/tests/integration/test_user_role_management.py`
- [X] T013 [P] [US1] Add failing refresh and role-management UI tests in
  `web/src/admin.test.tsx` and `web/src/api.test.ts`

### Implementation for User Story 1

- [X] T014 [US1] Add narrow user, role, and permission queries in
  `api/src/underwriteflow/auth/repository.py`
- [X] T015 [US1] Implement transactional user creation, deactivation, role
  replacement, permission replacement, and last-admin guard in
  `api/src/underwriteflow/auth/admin_service.py`
- [X] T016 [US1] Implement `/auth/login`, `/auth/refresh`, `/auth/me`, and the
  temporary `/auth/session` alias in `api/src/underwriteflow/auth/router.py`
- [X] T017 [US1] Add scoped `/users`, `/roles`, and `/permissions` routes in
  `api/src/underwriteflow/auth/admin_router.py`
- [X] T018 [US1] Append sanitized login, refresh, denial, user, role, and
  permission events through `api/src/underwriteflow/audit/events.py`
- [X] T019 [US1] Replace literal-role guards with scope dependencies while
  retaining ownership and underwriter-only finalization in
  `api/src/underwriteflow/{cases,reviews,queues,products,evaluation}/router.py`
- [X] T020 [US1] Add typed login, refresh, me, user, and role calls in
  `web/src/api-core.ts` and `web/src/api-staff.ts`
- [X] T021 [US1] Add in-memory refresh recovery and current-scope state in
  `web/src/app.tsx`
- [X] T022 [US1] Extend accessible user and role management controls in
  `web/src/admin.tsx` and `web/src/admin.css`

**Checkpoint**: US1 works independently; no token, digest, password, or
authorization header appears in errors, logs, or audit.

---

## Phase 4: User Story 2 - Configure Extraction and Rules (Priority: P1)

**Goal**: Administrators validate, preview, import, version, and activate
schema/rulebook configuration without code changes.

**Independent Test**: Reject an invalid configuration, activate a valid one,
create a case, activate a newer version, and prove the case remains pinned to
its original product and rulebook versions.

### Tests for User Story 2

- [X] T023 [P] [US2] Add failing reconciliation-schema and reference tests in
  `api/tests/unit/test_products.py`
- [X] T024 [P] [US2] Add failing YAML/JSON import, concurrent activation,
  history, and pinning tests in `api/tests/integration/test_product_import.py`
- [X] T025 [P] [US2] Add failing configuration preview/editor tests in
  `web/src/product-configuration.test.tsx` and
  `web/src/product-import.test.tsx`

### Implementation for User Story 2

- [X] T026 [US2] Add typed reconciliation definitions to
  `api/src/underwriteflow/products/schemas.py`
  - Check codes are unique per product version.
  - Kinds are `ncb_match`, `asset_match`, or `policy_lapse`.
  - Input keys reference declared fields and document codes.
  - Activation rejects missing or incompatible references.
- [X] T027 [US2] Accept validated YAML or JSON through the existing lifecycle
  in `api/src/underwriteflow/products/service.py`
- [X] T028 [US2] Enforce `schemas:edit`, audited activation, one active product
  version, and exact case pinning in `api/src/underwriteflow/products/router.py`
  and `api/src/underwriteflow/cases/service.py`
- [X] T029 [US2] Add fictional NCB, age, renewal, document, and reconciliation
  settings to `product-config/motor-private-car.yaml`,
  `product-config/life-individual-term.yaml`, and
  `product-config/health-individual-family-floater.yaml`
- [X] T030 [US2] Show reconciliation definitions and validation errors in
  `web/src/product-configuration.tsx` and `web/src/product-import.tsx`

**Checkpoint**: US2 independently validates and pins configuration; no real
insurer rule is hardcoded.

---

## Phase 5: User Story 3 - Extract and Reconcile Evidence (Priority: P1)

**Goal**: Existing providers emit schema-valid evidence; pure checks return
stable cleared, flagged, or missing verdicts with provenance.

**Independent Test**: Submit synthetic policy, RC, and claims documents with
known matches, mismatches, lapse, and omissions; verify exact ordered results.

### Tests for User Story 3

- [X] T031 [P] [US3] Add failing 100% branch tests for NCB, asset, lapse,
  missing inputs, normalization, leap day, and ordering in
  `api/tests/unit/test_reconciliation.py`
- [X] T032 [P] [US3] Add failing field-schema, page-locator, PII-redaction,
  usage, hash, and invalid-output tests in `api/tests/unit/test_providers.py`
- [X] T033 [P] [US3] Add failing sibling-failure, three-branch, deterministic
  join, and delta-resume tests in `api/tests/unit/test_workflow.py`
- [X] T034 [P] [US3] Add failing end-to-end synthetic motor evidence tests in
  `api/tests/integration/test_evidence_reconciliation.py`

### Implementation for User Story 3

- [X] T035 [US3] Add `FieldComparison`, `ReconciliationResult`, and pure NCB,
  asset, and lapse checks in `api/src/underwriteflow/workflow/reconciliation.py`
  - Status is exactly `CLEARED`, `FLAGGED_DISCREPANCY`, or
    `MISSING_EVIDENCE`.
  - Sort checks by code, comparisons by field key, and evidence by document ID
    plus source locator.
  - No database, provider, file, log, audit, or routing side effect is allowed.
- [X] T036 [US3] Extend requested field specifications and provider usage
  metadata in `api/src/underwriteflow/providers/schemas.py`
- [X] T037 [US3] Validate scalar/enum types and canonical result hashes in
  `api/src/underwriteflow/providers/service.py`
- [X] T038 [US3] Add configured Aadhaar, PAN, and contact redaction before
  Gemini only in `api/src/underwriteflow/providers/redaction.py`
- [X] T039 [US3] Reuse the existing adapters while returning shared metadata in
  `api/src/underwriteflow/providers/gemini.py`,
  `api/src/underwriteflow/providers/ollama.py`, and
  `api/src/underwriteflow/providers/fake.py`
- [X] T040 [US3] Preserve trusted local page boundaries in provider input in
  `api/src/underwriteflow/cases/submission.py`
- [X] T041 [US3] Invoke configured reconciliation after the existing join and
  map results to triage state in `api/src/underwriteflow/workflow/nodes.py` and
  `api/src/underwriteflow/workflow/state.py`
- [X] T042 [US3] Persist ordered results through existing validations and
  recommendation summaries in
  `api/src/underwriteflow/cases/evidence_persistence.py`
- [X] T043 [US3] Keep missing evidence as queue state and flagged results as a
  specialist signal in `api/src/underwriteflow/workflow/triage.py`

**Checkpoint**: US3 works with FakeProvider; Gemini/Ollama contract tests are
opt-in; pure reconciliation reaches 100% statement and branch coverage.

---

## Phase 6: User Story 4 - Review and Override a Case (Priority: P1)

**Goal**: Underwriters inspect discrepancy provenance and override only with
permission, evidence acknowledgement, and rationale.

**Independent Test**: Open a flagged case, deny an unauthorized override,
reject missing rationale, accept an authorized rationale, and finalize once.

### Tests for User Story 4

- [X] T044 [P] [US4] Add failing queue/review contract tests for result counts,
  provenance, confidence source, and scope denial in
  `api/tests/contract/test_review_contract.py`
- [X] T045 [P] [US4] Add failing override and duplicate-completion tests
  in `api/tests/integration/test_review_workflow.py`
- [X] T046 [P] [US4] Add failing accessible discrepancy and rationale tests in
  `web/src/case-review.test.tsx` and `web/src/confirm.test.tsx`

### Implementation for User Story 4

- [X] T047 [US4] Add reconciliation counts and status filters to
  `api/src/underwriteflow/queues/schemas.py` and
  `api/src/underwriteflow/queues/router.py`
- [X] T048 [US4] Add ordered comparisons, provenance, and confidence source to
  `api/src/underwriteflow/reviews/evidence.py` and
  `api/src/underwriteflow/reviews/schemas.py`
- [X] T049 [US4] Enforce `cases:override`, underwriter identity, rationale,
  row locking, review-cycle uniqueness, and idempotency in
  `api/src/underwriteflow/reviews/router.py` and
  `api/src/underwriteflow/queues/router.py`
- [X] T050 [US4] Extend review and queue response types in
  `web/src/types.ts` and `web/src/api-staff.ts`
- [X] T051 [US4] Render non-color discrepancy status, provenance, and required
  rationale in `web/src/case-review.tsx`, `web/src/confirm.tsx`, and
  `web/src/review.css`
- [X] T052 [US4] Render queue discrepancy/missing counts in
  `web/src/queue.tsx` and `web/src/queue.css`

**Checkpoint**: US4 independently proves human-only final authority and
exactly-once completion.

---

## Phase 7: User Story 5 - Inspect Audit History (Priority: P2)

**Goal**: Authorized reviewers reconstruct provider, rule, configuration, and
human actions without raw PII or mutable history.

**Independent Test**: Process and override one synthetic case; verify actor,
versions, hashes, token usage/unavailable marker, verdict, and rationale, then
prove update/delete fail.

### Tests for User Story 5

- [X] T053 [P] [US5] Add failing audit hash, token usage, unavailable marker,
  supersession, and PII-leak tests in `api/tests/unit/test_audit_events.py`
- [X] T054 [P] [US5] Add failing reconstruction and database immutability tests
  in `api/tests/integration/test_audit_enrichment.py` and
  `api/tests/integration/test_persistence.py`
- [X] T055 [P] [US5] Add failing audit chronology UI tests in
  `web/src/admin.test.tsx`

### Implementation for User Story 5

- [X] T056 [US5] Append provider/model, attempts, token counts or unavailable,
  redacted request hash, result hash, schema/rulebook versions, and evidence
  links through `api/src/underwriteflow/audit/events.py`
- [X] T057 [US5] Link automated verdicts, configuration changes, and human
  rationale to immutable events in
  `api/src/underwriteflow/cases/evidence_persistence.py`,
  `api/src/underwriteflow/products/service.py`, and
  `api/src/underwriteflow/reviews/router.py`
- [X] T058 [US5] Extend authorized audit filtering without mutation routes in
  `api/src/underwriteflow/queues/router.py` and
  `api/src/underwriteflow/queues/schemas.py`
- [X] T059 [US5] Render safe immutable chronology and supersession links in
  `web/src/admin.tsx`

**Checkpoint**: US5 reconstructs every decision while exposing no raw prompt,
file, credential, Aadhaar, PAN, or contact value.

---

## Phase 8: Polish and Cross-Cutting Verification

**Purpose**: Prove security, accessibility, deterministic behavior, scale, and
documentation across completed stories.

- [X] T060 [P] Add a bounded ten-case synthetic load probe in
  `scripts/pilot_load_probe.py`
- [X] T061 [P] Update architecture, privacy, RBAC, reconciliation, and known
  limits in `docs/ARCHITECTURE.md` and `docs/DEMO.md`
- [X] T062 Run full API, migration, and deterministic smoke verification for
  `api/tests/`, `api/alembic/`, and `scripts/smoke.py`
- [X] T063 Run full web tests, accessibility checks, and production build for
  `web/src/` and `web/package.json`
- [X] T064 Run secret, synthetic-data, line-length, file-size, and diff checks
  across `.env.example`, `api/`, `web/`, `product-config/`, and `scripts/`
- [X] T065 Execute every scenario in
  `specs/001-underwriting-platform/quickstart.md` and record actual results in
  `docs/RELEASE_READINESS.md`

**Checkpoint**: Acceptance evidence complete; no unapproved dependency,
provider, schema, retention, tracing, or architecture expansion.

---

## Dependencies and Execution Order

### Phase Dependencies

```text
Phase 1 Setup
  -> Phase 2 Foundation
     -> US1 Secure Access
     -> US2 Configuration
        -> US3 Evidence Reconciliation
US1 + US3 -> US4 Human Review
US1 + US3 + US4 -> US5 Audit Inspection
All selected stories -> Phase 8 Polish
```

- Phase 2 blocks every user story.
- US1 and US2 can begin independently after Phase 2.
- US3 depends on US2 because checks come from pinned configuration.
- US4 depends on US1 scopes and US3 discrepancy results.
- US5 depends on events emitted by US1, US3, and US4.
- Each phase ends at the project review-and-continue gate.

### Parallel Opportunities

- T002 can run while T001 verifies the baseline.
- T006 can run while T003 exercises the migration boundary.
- US1 test tasks T011-T013 target separate backend/integration/web files.
- US2 test tasks T023-T025 target separate unit/integration/web files.
- US3 test tasks T031-T034 target separate pure/provider/graph/integration
  boundaries.
- US4 test tasks T044-T046 target separate contract/integration/web files.
- US5 test tasks T053-T055 target separate unit/integration/web files.
- T060 and T061 can run after stories complete while final suites remain idle.

## Parallel Examples

| Story | Parallel test wave |
| --- | --- |
| US1 | T011 contract, T012 integration, T013 web |
| US2 | T023 schema, T024 integration, T025 web |
| US3 | T031 pure, T032 provider, T033 graph, T034 integration |
| US4 | T044 contract, T045 integration, T046 web |
| US5 | T053 unit, T054 integration, T055 web |

## Implementation Strategy

### MVP First

1. Complete Phase 1 and obtain approvals.
2. Complete Phase 2; stop for review.
3. Complete US1; validate its independent journey and stop.
4. This is the first deployable increment: secure dynamic administration.

### Incremental Underwriting Value

1. Add US2 configuration and validate pinning.
2. Add US3 extraction/reconciliation for core evidence value.
3. Add US4 governed review and exactly-once completion.
4. Add US5 complete audit reconstruction.
5. Run Phase 8 only for stories selected for release.

## Notes

- Reuse existing modules before creating any named new file.
- Keep every hand-written file below 400 lines and every line at most 80.
- Add one intent comment before every named function or method.
- Use bound SQLAlchemy expressions; never interpolate user input into SQL.
- Default tests use FakeProvider and visibly synthetic fixtures.
- Commit only after phase review and explicit `continue`.

---

## Phase 9: Convergence

- [X] T066 CRITICAL hash the exact redacted provider request and exact raw
  completion bytes in `api/src/underwriteflow/providers/gemini.py`,
  `api/src/underwriteflow/providers/ollama.py`,
  `api/src/underwriteflow/providers/service.py`, and provider audit tests per
  Constitution V and FR-028 (contradicts)
- [X] T067 CRITICAL make the local PII redaction policy validated and
  configurable in `api/src/underwriteflow/config.py`,
  `api/src/underwriteflow/providers/redaction.py`,
  `api/src/underwriteflow/providers/gemini.py`, and provider boundary tests per
  Constitution II and FR-014 (partial)
- [X] T068 CRITICAL fail closed on unapproved provider hosts, non-local Ollama
  URLs, and Gemini configurations without an explicit approved no-training
  project acknowledgement in `api/src/underwriteflow/config.py`,
  `api/src/underwriteflow/providers/factory.py`, `.env.example`,
  `compose.yaml`, and provider boundary tests per Constitution II (missing)
- [X] T069 CRITICAL audit invalid sessions, stale authorization, missing scopes,
  ownership denials, and underwriter-role denials without storing credentials
  in `api/src/underwriteflow/auth/dependencies.py`, protected routers, and
  `api/tests/integration/test_dynamic_authorization.py` per FR-008 and US1/AC3
  (missing)
- [X] T070 CRITICAL add pinned NCB tier progression, claims adjustment, and
  renewal
  boundary parameters to `api/src/underwriteflow/products/schemas.py`,
  `api/src/underwriteflow/workflow/reconciliation.py`, all three files under
  `product-config/`, and focused tests per FR-010 (missing)
- [ ] T071 CRITICAL add configured engine, chassis, and registration
  comparisons to
  `product-config/motor-private-car.yaml` and prove them end to end in
  `api/tests/integration/test_evidence_reconciliation.py` per FR-017 (missing)
- [ ] T072 return normalized compared values and stable explanations without
  retaining formatting-dependent raw values in
  `api/src/underwriteflow/workflow/reconciliation.py` and its unit and
  integration tests per FR-019 and FR-020 (partial)
- [ ] T073 after test-dependency approval, enforce 100% statement and branch
  coverage for `api/src/underwriteflow/workflow/reconciliation.py` in the
  Docker API test command per SC-011 (partial)
- [ ] T074 replace reused sequential cases in `scripts/pilot_load_probe.py`
  with fresh bounded concurrent probes and record the 10-case and 100-case
  latency, OCR, provider concurrency, database pool, checkpoint, queue, and
  storage measures required by the plan evaluation decision (partial)
- [ ] T075 split `web/src/access-admin.tsx`,
  `api/tests/unit/test_triage_workflow.py`, and `web/src/review.css` below 400
  lines and wrap over-80 hand-written lines in `api/`, `web/`,
  `product-config/`, and `scripts/` per T064 and the task constraints
  (contradicts)
