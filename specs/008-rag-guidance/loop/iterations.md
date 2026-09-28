# Maker Iterations

Append-only. One record per `/speckit.loop.run` iteration. The maker never
marks the loop done. It records the story and criteria ready for checking.

<!-- Record format:
## Iteration <n> - <date>
- Story: <USn>
- Targeted criteria: <D-id>
- Change: <files and behavior>
- Maker self-assessment: <evidence believed ready>
- Open questions / risks: <checker or human attention>
- Handoff: ready-for-check
-->

## Iteration 1 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Added knowledge package marker and date validation tests and logic
  in `api/src/underwriteflow/knowledge/__init__.py`,
  `api/tests/unit/test_date_field.py`, and
  `api/src/underwriteflow/cases/validation.py`.
- Maker self-assessment: Date validation portion passes focused test; D1 is
  not ready because remaining US1 tasks are incomplete.
- Open questions / risks: T005 requires explicit user approval before adding
  life v3 config, synthetic evaluation DOBs, or resetting demo data. T004 and
  T006-T011 remain.
- Handoff: ready-for-check

## Iteration 2 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Fixed staff review finding R001 in
  `api/tests/unit/test_date_field.py:29`: future test input now uses an ISO
  string and reaches `not_future` validation.
- Maker self-assessment: R001 is fixed; focused date test passes. D1 remains
  pending because remaining US1 tasks are incomplete.
- Open questions / risks: T005 still requires explicit user approval. T004
  and T006-T011 remain.
- Handoff: ready-for-check

## Iteration 3 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Added failing-first integration coverage in
  `api/tests/integration/test_life_v3_config.py:10`; added approved life v3
  configuration in `product-config/life-individual-term-v3.yaml:1`; added
  synthetic dates to all 30 life evaluation payloads in
  `evaluation/cases.json`; checked T001-T005 in `specs/008-rag-guidance/
  tasks.md`.
- Maker self-assessment: T004 and T005 appear ready; D1 is not ready because
  T006-T011 remain incomplete. This is the maker's view, not a verdict.
- Open questions / risks: Checker should verify v3 bootstrap behavior and
  confirm the existing README reset procedure satisfies T005.
- Handoff: ready-for-check

## Iteration 4 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Fixed staff blocker R001 by adding v3 to
  `api/src/underwriteflow/products/import_configs.py:20`, pinning all 30 life
  fixtures to v3 in `evaluation/cases.json`, and asserting importer membership
  plus declared-version consistency in
  `api/tests/integration/test_life_v3_config.py:17`.
- Maker self-assessment: Staff blocker appears addressed; D1 is not ready
  because T006-T011 and the shared gate remain. This is the maker's view, not
  a verdict.
- Open questions / risks: Checker should run bootstrap and the full US1
  checkpoint, then reassess the staff review finding.
- Handoff: ready-for-check

## Iteration 5 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Added synthetic `date_of_birth` evidence to all 30 life fixtures
  in `evaluation/cases.json`; updated the built-in version count from 10 to
  11 in `api/tests/integration/test_environment_baseline.py`.
- Maker self-assessment: Evaluation baseline and loader regression appear
  fixed: focused checkpoint tests pass and metrics are perfect. D1 remains
  incomplete because T006-T011 and the shared gate remain. This is the
  maker's view, not a verdict.
- Open questions / risks: Current checkout exposed 26 life false positives,
  not 13; four intentional life missing-information cases remain. Checker
  should verify fresh-baseline behavior, dataset identity, and the full US1
  checkpoint.
- Handoff: ready-for-check

## Iteration 6 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Implemented T006-T011: added typed corpus parsing and validation in
  `api/src/underwriteflow/knowledge/corpus.py`, deterministic alignment in
  `api/src/underwriteflow/knowledge/alignment.py`, unit and integration tests,
  12-section `knowledge-config/life-individual-term/g1.yaml`, and read-only
  Compose mounts for `api` and `bootstrap`. Checked T006-T011 in
  `specs/008-rag-guidance/tasks.md`.
- Maker self-assessment: D1 appears maker-ready. Focused US1 tests pass;
  `make test-api`, `make test-web`, web build, and `make smoke` pass. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should independently verify corpus contract
  edge cases, fresh Compose mounts, and the US1 quickstart future-date flow.
- Handoff: ready-for-check

## Iteration 7 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Corrected T010 and the US1 checkpoint command in
  `specs/008-rag-guidance/tasks.md` to use the existing integration test at
  `api/tests/integration/test_life_corpus_alignment.py`.
- Maker self-assessment: D1 is maker-ready. The corrected focused checkpoint
  command passes 19 tests. This is the maker's view, not a verdict.
- Open questions / risks: Checker should rerun the full US1 checkpoint and
  confirm no other task-path mismatch remains.
- Handoff: ready-for-check

## Iteration 8 - 2026-09-28
- Story: US1
- Targeted criteria: D1
- Worktree: in place
- Change: Made journey contract tests independent of active motor product
  state in `api/tests/contract/test_journey_api.py:111,167` and
  `api/tests/contract/test_journey_staff.py:23`; each test selects motor v1
  before creating a draft and restores prior state afterward.
- Maker self-assessment: D1 remains maker-ready. US1 checkpoint passes with
  20 tests; journey tests pass with 6 tests; `make test-api`, `make test-web`,
  web build, and `make smoke` pass. This is the maker's view, not a verdict.
- Open questions / risks: Checker should rerun the US1 checkpoint and inspect
  test isolation around product activation.
- Handoff: ready-for-check
