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

## Iteration 9 - 2026-09-28
- Story: US2
- Targeted criteria: D2
- Worktree: in place
- Change: Added migration `09_knowledge_base.py`, knowledge ORM and
  lifecycle services, administrator API, case pinning, draft bootstrap import,
  Compose mounts, and the administrator knowledge screen. Added US2 API and
  web tests and FK-safe fixture cleanup.
- Maker self-assessment: D2 is maker-ready. Focused US2 tests pass; full API
  gate passes 583 tests, full web gate passes 175 tests, web build passes, and
  `make smoke` passes. This is the maker's view, not a verdict.
- Open questions / risks: Checker should inspect activation race behavior,
  invalid-draft reporting, pin ordering, and the quickstart US2 flow.
- Handoff: ready-for-check

## Iteration 10 - 2026-09-28
- Targeted criteria: R002 staff-review follow-up; no RAG criterion changed
- Worktree: in place
- Change: Added isolated recovery coverage in
  `api/tests/unit/test_evaluation_loader.py:218` for restoring present but
  corrupted evaluation-document bytes.
- Maker self-assessment: R002 now has unit-level regression coverage. R001
  remains intentionally unchanged because the reviewer marked its current
  corpus-scale cost negligible. This is the maker's view, not a verdict.
- Open questions / risks: This follow-up is outside US2 implementation scope;
  checker should confirm no broader performance change is warranted.
- Handoff: ready-for-check

## Iteration 11 - 2026-09-28
- Targeted criteria: US2 staff-review findings R001-R005; D2 unchanged
- Worktree: in place
- Change: Added bootstrap-import and Compose coverage in
  `api/tests/unit/test_import_corpora.py:11` and
  `api/tests/contract/test_environment_compose.py:180`; expanded lifecycle
  idempotence, conflict, and activation-audit assertions in
  `api/tests/integration/test_knowledge_lifecycle.py:76`; expanded every
  knowledge API endpoint and role refusal in
  `api/tests/contract/test_knowledge_api.py:40`; added public submission,
  resubmission, g1/g2 pin stability, and pin-audit coverage in
  `api/tests/integration/test_knowledge_pinning.py:184`; preserved real audit
  timestamps in `api/src/underwriteflow/knowledge/pins.py:47`; added YAML
  import status coverage in `web/src/knowledge-admin.test.tsx:74`; updated
  the audit contract for the new pin event in
  `api/tests/contract/test_audit_contract.py:54`.
- Maker self-assessment: Latest US2 review findings appear addressed; D2
  remains maker-ready. Full API, web, build, and smoke gates pass. This is the
  maker's view, not a verdict.
- Open questions / risks: Checker should independently rerun the US2
  checkpoint and inspect the new public pinning flow and audit ordering.
- Handoff: ready-for-check

## Iteration 12 - 2026-09-28
- Targeted criteria: D2; checker failures 1-3
- Worktree: in place
- Change: Mapped concurrent import and activation `IntegrityError` to
  `KnowledgeConflictError` in
  `api/src/underwriteflow/knowledge/service.py:211-235,284-332`;
  made activation idempotent for an already-active version at lines 265-271;
  flushed sibling retirement before target activation at lines 291-298;
  added lifecycle and concurrency regression coverage in
  `api/tests/integration/test_knowledge_lifecycle.py:84-195`.
- Maker self-assessment: D2 remains maker-ready. US2 checkpoint passes 8
  tests; `make test-api` passes 589 tests; `make test-web` passes 176 tests;
  web build and `make smoke` pass. This is the maker's view, not a verdict.
- Open questions / risks: Checker should independently reproduce the three
  reported races and verify API responses remain 409 without duplicate audit
  events. No new migration required.
- Handoff: ready-for-check

## Iteration 13 - 2026-09-28
- Targeted criteria: D2; staff warnings R001, RC02/R003, R002
- Worktree: in place
- Change: Added unlocked knowledge reads and SQL passage pagination in
  `api/src/underwriteflow/knowledge/repository.py:91-147` and switched
  summary/preview reads in
  `api/src/underwriteflow/knowledge/router.py:38,133-143`;
  validated corpora against named product versions and required active status
  only during activation in
  `api/src/underwriteflow/knowledge/service.py:117-160,287-289`;
  added offset-page and inactive-version regression coverage in
  `api/tests/contract/test_knowledge_api.py:68-88` and
  `api/tests/integration/test_knowledge_lifecycle.py:129-150`.
  Added administrator next/previous preview controls and API query coverage
  in `web/src/api-knowledge.ts:29-45`,
  `web/src/knowledge-admin.tsx:72-95,190-221`, and
  `web/src/knowledge-admin.test.tsx:76-107`.
- Maker self-assessment: D2 remains maker-ready. US2 checkpoint passes 9
  tests; `make test-api` passes 590 tests; `make test-web` passes 177 tests;
  web build and `make smoke` pass. This is the maker's view, not a verdict.
- Open questions / risks: Checker should confirm R001 read paths never call
  `FOR UPDATE`, R002 activation semantics, and R003 SQL-level pagination.
  `RC02` was treated as the latest review's R003 label.
- Handoff: ready-for-check

## Iteration 14 - 2026-09-28
- Targeted criteria: D2; latest staff warning R001
- Worktree: in place
- Change: Added SQL `COUNT` in
  `api/src/underwriteflow/knowledge/repository.py:149-158`; changed
  `KnowledgeService.summary` to use it at
  `api/src/underwriteflow/knowledge/service.py:246-264`; added a unit
  regression test in `api/tests/unit/test_knowledge_service.py:11-35` that
  rejects passage-body loading during summary.
- Maker self-assessment: D2 remains maker-ready. US2 checkpoint passes 9
  tests; focused summary test passes; `make test-api` passes 591 tests;
  `make test-web` passes 177 tests; web build and `make smoke` pass. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should confirm preview summary performs one
  count query plus one bounded page query for large corpora.
- Handoff: ready-for-check

## Iteration 15 - 2026-09-28
- Story: US3
- Targeted criteria: D3
- Worktree: in place
- Change: Added additive migration `10_knowledge_retrieval.py` with pgvector,
  generated full-text search, GIN, and HNSW indexes; added custom `Vector`
  type and passage mapping. Added deterministic and Gemini embedding
  providers, bounded import embedding writes, case facts, hybrid RRF
  retrieval, 30-question life evaluation data, and evaluation script. Added
  unit, migration, embedding, retrieval, and recall coverage.
- Maker self-assessment: D3 is maker-ready. Focused US3 tests pass 17 tests;
  retrieval evaluation passes 30/30; `make test-api` passes 606 tests;
  `make test-web` passes 177 tests; web build and `make smoke` pass. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should inspect Gemini batch endpoint shape,
  generated-column ORM mapping, exact-code lexical ranking, and active-version
  selection in the evaluation script. No new migration is required.
- Handoff: ready-for-check

## Iteration 16 - 2026-09-28
- Story: US3 review repair
- Targeted criteria: D3; review findings R001-R002
- Worktree: in place
- Change: Changed `knowledge/import_corpora.py` to use the configured
  embedding provider, with provider-identity coverage in
  `api/tests/unit/test_import_corpora.py`. Added intent comments for nested
  vector serializers in `persistence/vector.py`. Set fake provider explicitly
  for smoke/evaluation bootstrap services.
- Maker self-assessment: D3 remains maker-ready. Repair tests pass 12 tests;
  `make test-api` passes 606 tests; `make test-web` passes 177 tests; web
  build and `make smoke` pass. This is the maker's view, not a verdict.
- Open questions / risks: Checker should rerun review-20260928-175000.md and
  verify Gemini bootstrap/query provider identity with approved credentials.
- Handoff: ready-for-check

## Iteration 17 - 2026-09-28
- Story: US3 review repair
- Targeted criteria: D3; review finding R003
- Worktree: in place
- Change: Added Gemini API key, embedding model, no-training acknowledgement,
  host allowlist, redaction terms, and timeout settings to the Compose
  bootstrap service. Added contract coverage requiring bootstrap and API
  embedding settings to match, plus Gemini builder configuration coverage.
  Smoke and evaluation bootstrap overrides keep fake embeddings deterministic.
- Maker self-assessment: D3 remains maker-ready. R003 tests pass 22 tests;
  `make test-api` passes 608 tests; `make smoke` passes. This is the maker's
  view, not a verdict.
- Open questions / risks: Checker should rerun the R003 review with a
  credentialed Gemini configuration; live provider calls remain opt-in.
- Handoff: ready-for-check

## Iteration 18 - 2026-09-28
- Targeted criteria: D3; checker failures for test coverage and comments
- Worktree: in place
- Change: Added intent comments before nested helpers in
  `api/tests/integration/test_retrieval.py:34`,
  `api/tests/integration/test_retrieval_recall.py:24`,
  `api/tests/integration/test_knowledge_embeddings.py:40`, and
  `api/tests/unit/test_embedding_providers.py:45`. Added an absent-age
  retrieval assertion at `api/tests/integration/test_retrieval.py:66` and
  migration assertions for `vector(768)` and `vector_cosine_ops` at
  `api/tests/integration/test_knowledge_migration.py:70-103`.
- Maker self-assessment: D3 appears maker-ready. Focused repair tests pass
  18 tests; `make test-api` passes 608 tests; `make smoke` passes. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should independently rerun the US3
  checkpoint and confirm the named tests now lock every required detail.
- Handoff: ready-for-check

## Iteration 19 - 2026-09-28
- Targeted criteria: D3; DEBT-012 and DEBT-013
- Worktree: in place
- Change: Added explicit `EMBEDDING_PROVIDER` selection in
  `api/src/underwriteflow/config.py:34` and
  `api/src/underwriteflow/providers/embedding.py:149`. Local Compose,
  evaluation, smoke, and `.env.example` use fake embeddings; approved Gemini
  keeps explicit acknowledgement, host, key, and redaction checks. Retrieval
  integration tests no longer activate drafts and recall selects shipped `g1`
  by identity in `api/tests/integration/test_retrieval_recall.py:35`.
- Maker self-assessment: DEBT-012 and DEBT-013 appear addressed; D3 remains
  checker-pass. Checker should verify fresh local startup, provider parity,
  and that retrieval tests leave active guideline state unchanged. This is the
  maker's view, not a verdict.
- Open questions / risks: Existing development data already has retired `g1`
  from earlier checker probes; restore requires the documented local reset or
  a new corpus version. No reset performed.
- Handoff: ready-for-check

## Iteration 20 - 2026-09-28
- Targeted criteria: D2/D3 review findings R001-R002
- Worktree: in place
- Change: `web/src/knowledge-admin.tsx:14-20,190-210` now renders passage
  identifier, topic, age band, and sum-assured band; UI assertions cover all
  metadata in `web/src/knowledge-admin.test.tsx:49-58`. The embedding builder
  now rejects configured Ollama embeddings in
  `api/src/underwriteflow/providers/embedding.py:149-156`, with unit coverage
  in `api/tests/unit/test_embedding_providers.py:97-108`.
- Maker self-assessment: R001 and R002 appear addressed. Focused web/API
  tests pass; `make test-web` passes 177 tests; web build passes. This is the
  maker's view, not a verdict.
- Open questions / risks: Checker should verify metadata labels against FR-001
  and confirm Ollama rejection is preferable to an adapter.
- Handoff: ready-for-check
