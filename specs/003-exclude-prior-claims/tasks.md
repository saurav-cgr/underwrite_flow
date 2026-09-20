---

description: "Tasks for excluding prior claims from new business"
---

# Tasks: Exclude Prior Claims from New Business

**Input**: Design documents from
`specs/003-exclude-prior-claims/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required. Write focused failing tests before each behavior change.

**Organization**: Tasks are grouped by user story. Each implementation phase
ends at the repository's approval gate: report changes, verification, risks,
and a proposed commit, then wait for `continue`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because files and dependencies do not overlap
- **[Story]**: Maps the task to its specification user story
- Every task names its exact target file

## Phase 1: Setup and Baseline

**Purpose**: Prove the existing behavior before changing it.

- [X] T001 Baseline api/tests/integration/test_journey_workflow.py

  Confirm current motor `v4` accepts prior claims for both journeys and retain
  the result for comparison. Do not edit production files in this task.

---

## Phase 2: Shared Foundations

**Purpose**: Add the immutable configuration and generic validation guards
needed by every story.

**Critical**: Finish this phase before user-story work.

- [X] T002 [P] Test unknown-field rejection in api/tests/unit/test_cases.py

  Add a focused failing test proving a journey-filtered draft rejects
  `prior_claims` when that field is not in the applicable field set. Also prove
  the matching renewal configuration accepts and validates the same field.

- [X] T003 [P] Test api/tests/unit/test_journey_configuration.py

  Add a focused failing test proving an NCB `claim_count_field` unavailable on
  the reconciliation journey makes the configuration invalid.

- [X] T004 [P] Add motor version v5 in product-config/motor-private-car-v5.yaml

  Copy immutable `v4`, change only the version plus
  `prior_claims.applies_to: [renewal]` and
  `prior_claims_standard.applies_to: [renewal]`, and retain the renewal-only
  NCB check and all synthetic labels.

- [X] T005 Register v5 in api/src/underwriteflow/products/import_configs.py

  Append the new file to `CONFIGURATION_FILES`; do not activate it or modify
  an earlier configuration version.

- [X] T006 [P] Guard api/src/underwriteflow/cases/validation.py

  Make `validate_draft_application` compare payload keys with the supplied
  journey-filtered fields and raise one deterministic, field-specific
  `CaseValidationError` before persistence.

- [X] T007 [P] Validate api/src/underwriteflow/products/journey.py

  Extend the existing generic reconciliation journey check so
  `parameters.claim_count_field` must be available on every applicable
  journey. Do not special-case the name `prior_claims`.

**Checkpoint**: Run T002 and T003 tests. Stop and report changed files,
verification, remaining risks, and proposed commit
`feat: add renewal-only prior claims config`. Wait for `continue` before any
commit or Phase 3 work.

---

## Phase 3: User Story 1 - Start Without Prior Claims (Priority: P1)

**Goal**: A motor new-business applicant using `v5` never sees, submits, or is
reviewed against prior claims.

**Independent Test**: Activate `v5`, complete a new-business case without
prior claims, reach human review, and confirm no field, rule, missing item, or
reconciliation result mentions prior claims. A stale payload receives 422.

### Tests for User Story 1

- [X] T008 [P] [US1] Test api/tests/integration/test_journey_workflow.py

  Cover catalogue and case-configuration omission, accepted valid creation,
  precise 422 responses for stale create and replacement payloads, successful
  submission, and absence from review results.

- [X] T009 [P] [US1] Test api/tests/contract/test_review_contract.py

  Prove a `v5` new-business review excludes prior claims from submitted facts,
  evidence, missing information, and reconciliation output while retaining the
  existing response shape and human-review state.

- [X] T010 [P] [US1] Add v5 dataset checks in api/tests/unit/test_evaluation.py

  Require every `v5` motor new-business record to omit prior claims, retain 90
  cases, and preserve the 30/30/30 expected-route distribution.

### Implementation for User Story 1

- [X] T011 [P] [US1] Fix api/src/underwriteflow/cases/router.py

  Preserve status 422 for create and replacement, expose only the deterministic
  unsupported-field message, and keep unrelated validation errors generic.

- [X] T012 [P] [US1] Fix api/src/underwriteflow/reviews/router.py

  Apply the existing journey filter before building review evidence and handle
  an unsupported or unreadable pinned configuration through the existing safe
  fallback.

- [X] T013 [P] [US1] Update current fixtures in evaluation/cases.json

  Move motor new-business expedited and specialist records to `v5`, remove
  prior claims from their application payloads and document text, and leave
  claim-driven standard records pinned to historical `v1`.

- [X] T014 [US1] Verify specs/003-exclude-prior-claims/quickstart.md

  Run the focused unit, integration, and contract commands. Confirm rejected
  payloads create no case, replacement, or audit event.

**Checkpoint**: Stop and report changed files, verification, remaining risks,
and proposed commit `fix: exclude prior claims from new business`. Wait for
`continue` before any commit or Phase 4 work.

---

## Phase 4: User Story 2 - Preserve Renewal Claims Handling (Priority: P2)

**Goal**: Motor renewal under `v5` retains the prior-claims field, routing
rule, validation, and NCB reconciliation.

**Independent Test**: Activate `v5`, complete a renewal with a prior policy and
prior claims, and confirm the field, rule, and reconciliation remain usable.

### Tests for User Story 2

- [ ] T015 [US2] Test v5 in api/tests/integration/test_journey_workflow.py

  Assert the renewal catalogue and pinned case configuration include
  `prior_claims`; a complete renewal accepts it; the configured standard rule
  and NCB check can consume it; omission still fails when required.

- [ ] T016 [US2] Verify api/tests/integration/test_journey_workflow.py

  Run the focused file and confirm legacy renewal tests and the new `v5`
  scenario pass without changing production behavior beyond Phase 2.

**Checkpoint**: Stop and report changed files, verification, remaining risks,
and proposed commit `test: preserve renewal prior claims`. Wait for `continue`
before any commit or Phase 5 work.

---

## Phase 5: User Story 3 - Keep Versioned Cases Stable (Priority: P3)

**Goal**: Earlier cases retain their pinned behavior while cases created after
`v5` activation use the corrected journey rules.

**Independent Test**: Create a `v4` new-business case, activate `v5`, then
prove the old case still accepts and displays its pinned fields while a new
case omits and rejects prior claims.

### Tests for User Story 3

- [ ] T017 [US3] Test pinning in api/tests/integration/test_journey_workflow.py

  Assert product and rulebook version identities, unchanged historical case
  behavior, corrected new-case behavior, and append-only import and activation
  audit events with the authenticated administrator actor.

- [ ] T018 [US3] Verify api/tests/integration/test_journey_workflow.py

  Run the focused file and confirm activation does not rewrite the earlier
  submission, configuration, recommendation, or audit history.

**Checkpoint**: Stop and report changed files, verification, remaining risks,
and proposed commit `test: preserve pinned claims behavior`. Wait for
`continue` before any commit or final-phase work.

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Put the corrected version on the deterministic smoke path and run
the repository gates.

- [ ] T019 Update the v5 smoke path in scripts/smoke.py

  Activate `v5`, omit prior claims from new-business intake and synthetic
  document text, and retain mandatory human confirmation.

- [ ] T020 Run all gates in specs/003-exclude-prior-claims/quickstart.md

  Run the complete API suite, web suite, production web build, and deterministic
  smoke test through Docker Compose. Do not enable live providers or tracing.

- [ ] T021 Check specs/003-exclude-prior-claims/plan.md

  Run whitespace, line-length, file-size, secret, synthetic-data, and migration
  checks. Confirm no dependency, schema migration, provider, authorization, or
  external-flow change was introduced.

**Checkpoint**: Stop and report final changed files, all verification results,
remaining risks, and proposed commit
`test: validate prior claims journey split`. Wait for `continue` before the
commit.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1** starts immediately.
- **Phase 2** depends on the baseline and blocks every user story.
- **US1, US2, and US3** are logically testable after Phase 2.
- Execute US1, US2, then US3 to avoid overlap in
  `api/tests/integration/test_journey_workflow.py` and to honor approval gates.
- **Phase 6** depends on all selected stories.

### User Story Dependencies

- **US1 (P1)** depends only on Phase 2 and is the MVP.
- **US2 (P2)** depends only on Phase 2; it verifies preserved renewal behavior.
- **US3 (P3)** depends only on Phase 2; it compares immutable versions.

### Within Each User Story

- Write and run the focused test before its production behavior change.
- Configuration precedes import registration and activation-based tests.
- Shared validators precede endpoint and review integration.
- Stop at every checkpoint; do not combine approval steps or commit early.

## Parallel Opportunities

- T002, T003, and T004 touch separate files and can run together.
- After their tests fail, T006 and T007 can run together.
- T008, T009, and T010 can run together.
- After those tests fail, T011, T012, and T013 can run together.
- US2 and US3 are logically independent but should not edit the shared
  integration test file simultaneously.

## Parallel Example: User Story 1

```text
Task T008: API journey regressions in test_journey_workflow.py
Task T009: Review response regressions in test_review_contract.py
Task T010: Evaluation invariants in test_evaluation.py

Then:

Task T011: Safe case validation details in cases/router.py
Task T012: Journey-filtered review configuration in reviews/router.py
Task T013: Current v5 evaluation fixtures in evaluation/cases.json
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2, then stop for approval.
2. Complete US1 only.
3. Run T014 and stop for approval.
4. Demonstrate a `v5` new-business case reaching human review without claims.

### Incremental Delivery

1. Add the immutable version and shared guards.
2. Deliver US1 new-business behavior.
3. Prove US2 renewal compatibility.
4. Prove US3 historical version stability.
5. Update smoke coverage and run all repository gates.

## Notes

- No schema migration, dependency, UI component, or provider change is planned.
- Never edit `motor-private-car-v1` through `v4`.
- Never auto-activate `v5`; an authenticated administrator must do so.
- All fixtures and records remain synthetic.
- No commit occurs until the user approves the preceding checkpoint with
  `continue`.
