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

## Iteration 21 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T040-T041
- Worktree: in place
- Change: Added additive migration `11_case_guidance.py`, mapped
  `CaseGuidance` in `persistence/knowledge_models.py`, and extended
  `test_knowledge_migration.py` for the table and unique cycle-kind key.
  Rebuilt the bootstrap image so the new revision is available.
- Maker self-assessment: T040-T041 appear ready; D4 remains pending because
  guidance provider, workflow, persistence, API, web, and shared gates remain.
  This is the maker's view, not a verdict.
- Open questions / risks: Checker should verify downgrade scope, foreign-key
  behavior, and the migration against a fresh database.
- Handoff: ready-for-check

## Iteration 22 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T042-T043
- Worktree: in place
- Change: Added deterministic and Gemini guidance contracts in
  `api/src/underwriteflow/providers/guidance.py`. Added bounded word-count,
  pinned citation, JSON-mode, untrusted-context, redaction, and builder tests
  in `api/tests/unit/test_guidance_provider.py`.
- Maker self-assessment: T042-T043 appear ready; D4 remains pending because
  workflow integration, storage, API, web, and shared gates remain. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should inspect citation validation against
  retrieved versions and verify provider failures never expose credentials.
- Handoff: ready-for-check

## Iteration 23 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T044-T045
- Worktree: in place
- Change: Added pinned retrieval and bounded fallback behavior in
  `api/src/underwriteflow/knowledge/explainer.py`; added the optional
  `workflow/explain.py` node and triage edge; added guidance context and
  route explanation state; passed configured guidance and embedding providers
  into case submission. Added four focused node tests.
- Maker self-assessment: T044-T045 appear ready; D4 remains pending because
  stored guidance, API, web, e2e, and shared gates remain. This is the maker's
  view, not a verdict.
- Open questions / risks: Checker should verify async graph checkpoint
  behavior, audit-event commit ordering, and no route mutation on fallbacks.
- Handoff: ready-for-check

## Iteration 24 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T046-T050
- Worktree: in place
- Change: Added insert-once `case_guidance` persistence and
  `route_explanation_stored` audit events; wired storage after triage. Added
  underwriter-only `GET /reviews/{case_id}/guidance`, contract coverage,
  restart-stability/duplicate-write integration coverage, and five-read timing
  coverage.
- Maker self-assessment: T046-T050 appear ready; D4 remains pending because
  web work, e2e timing, and shared gates remain. This is the maker's view,
  not a verdict.
- Open questions / risks: Checker should verify real generated guidance is
  stored before the interrupt and the route remains unchanged across all
  evaluation cases.
- Handoff: ready-for-check

## Iteration 25 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T051
- Worktree: in place
- Change: Moved the route-selection and decision controls into
  `web/src/review-actions.tsx`; `web/src/case-review.tsx` now owns only case
  review state and layout. Existing case-review tests pass unchanged.
- Maker self-assessment: T051 appears ready; D4 remains pending because the
  guidance panel, Playwright timing test, and shared gates remain. This is the
  maker's view, not a verdict.
- Open questions / risks: Checker should verify keyboard behavior and the
  action form's behavior remains identical in needs-information and manual
  routes.
- Handoff: ready-for-check

## Iteration 26 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T052 and T055
- Worktree: in place
- Change: Added typed guidance API contracts and `fetchGuidance`; added
  accessible `GuidancePanel` with one stored read, citations, missing-item
  reasons, synthetic label, template badge, and unavailable status; mounted
  it in `case-review.tsx`. Added Vitest coverage and kept existing review
  tests passing.
- Maker self-assessment: T052 and T055 appear ready; D4 remains pending
  because Playwright setup/timing and shared gates remain. This is the maker's
  view, not a verdict.
- Open questions / risks: Checker should verify one request on case opening,
  keyboard/accessibility behavior, and no generation call from the browser.
- Handoff: ready-for-check

## Iteration 27 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T053
- Worktree: in place
- Change: Added exact-pinned Playwright 1.55.0 setup, Vite e2e exclusion and
  internal-host allowlist, Compose health checks, and `make test-e2e`.
- Maker self-assessment: T053 appears ready; D4 remains pending until the
  Playwright scenario and complete shared checkpoint pass. This is the
  maker's view, not a verdict.
- Open questions / risks: Checker should verify the Compose health dependency
  and dependency lock consistency.
- Handoff: ready-for-check

## Iteration 28 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T054
- Worktree: in place
- Change: Added the five-case Playwright timing flow with synthetic applicant
  setup, explicit v5 activation, route-shaped inputs, and underwriter queue
  checks. The final run printed `468, 452, 561, 410, 510` milliseconds.
- Maker self-assessment: T054 appears ready; D4 remains pending until the
  complete shared checkpoint pass. This is the maker's view, not a verdict.
- Open questions / risks: Checker should verify route coverage and whether
  the blank synthetic image intentionally exercises needs-information state.
- Handoff: ready-for-check

## Iteration 29 - 2026-09-28
- Story: US4
- Targeted criteria: D4; T040-T055 and shared checkpoint
- Worktree: in place
- Change: Ran migration, focused API tests, full API gate, full web gate,
  web build, smoke, API restart health, and exact `make test-e2e`.
- Maker self-assessment: All US4 tasks are checked; D4 is ready for an
  independent checker pass. This is the maker's view, not a verdict.
- Open questions / risks: npm reports four existing dependency audit findings
  in the Playwright container; no live provider check was run.
- Handoff: ready-for-check

## Iteration 30 - 2026-09-28
- Story: US4
- Targeted criteria: D4; staff findings R001-R004
- Worktree: in place
- Change: Provider parsing now preserves unknown citations for explainer-side
  filtering and `citation_dropped` audit events. Generated explanations now
  fall back when any requested missing item lacks a valid cited reason. Added
  Gemini adapter-path and missing-item omission tests, plus real submission,
  checkpoint restart, and human-resume integration coverage. Removed the
  reported trailing whitespace.
- Maker self-assessment: D4 is maker-ready after the staff repairs. This is
  the maker's view, not a verdict.
- Open questions / risks: Checker should verify the new active-corpus graph
  test and independently rerun the US4 checkpoint.
- Handoff: ready-for-check

## Iteration 31 - 2026-09-29
- Story: US4 checker-failure repair
- Targeted criteria: D4; checker failures from iteration 30
- Worktree: in place
- Change: Ollama guidance now disables optional explanation generation without
  aborting submission in `api/src/underwriteflow/providers/guidance.py:277`.
  Added all-90 route comparison with the optional explanation node enabled
  and disabled in `api/src/underwriteflow/evaluation/runner.py:50` and
  `api/tests/integration/test_route_explanation.py:239`. Contract now reads
  review state before and after guidance in
  `api/tests/contract/test_guidance_api.py:17`. Added the missing nested-test
  intent comment in `api/tests/unit/test_explain_node.py:255`.
  Reworked `web/e2e/guidance-timing.spec.ts` to activate life guideline data,
  create one case per route plus needs-information, verify route coverage,
  and assert stored explanation text within three seconds.
- Maker self-assessment: D4 appears maker-ready. This is the maker's view,
  not a verdict.
- Verification: focused API tests 5 pass; `make test-api` 627 pass;
  `make test-web` 180 pass; web build passes; smoke passes; E2E passes with
  timings 476, 428, 548, 450, 512 ms. `make test-e2e` build was blocked by
  Docker registry timeout; equivalent no-build Compose E2E passed.
- Open questions / risks: Checker should independently rerun full US4
  checkpoint, inspect npm audit findings, and verify Ollama submission with
  its provider profile.
- Handoff: ready-for-check

## Iteration 32 - 2026-09-29
- Story: US4 checker-failure repair
- Targeted criteria: D4; T046/SC-003
- Worktree: in place
- Change: Replaced the evaluation runner's stub explainer and direct route
  calculation with `build_triage_graph` and the real `RouteExplainer` in
  `api/src/underwriteflow/evaluation/runner.py:20-196`. Guidance-enabled runs
  load active guideline IDs, use fake providers, and read recommendations
  from graph output. Added fresh staff review at
  `specs/008-rag-guidance/reviews/review-20260929-085740.md`.
- Maker self-assessment: D4 is maker-ready. This is the maker's view, not a
  verdict.
- Verification: focused US4 tests 36 pass; `make test-api` 627 pass;
  `make test-web` 180 pass; web build passes; `make smoke` passes;
  `git diff --check` passes.
- Open questions / risks: Checker should independently mutation-test the
  graph-output assertion, inspect active guideline pin behavior, and review
  the two staff conditions: npm audit findings and unignored test output.
- Handoff: ready-for-check

## Iteration 33 - 2026-09-29
- Story: US4 staff-warning repair
- Targeted criteria: D4; staff findings R001-R002
- Worktree: in place
- Change: Upgraded exact web test dependencies to Playwright 1.63.0 and
  Vitest 5.0.2 in `web/package.json` and `web/package-lock.json`. Matched the
  E2E image to `mcr.microsoft.com/playwright:v1.63.0-noble` in
  `compose.yaml`. Added `web/test-results/` to `.gitignore`.
- Maker self-assessment: D4 remains maker-ready; both staff warnings appear
  resolved. This is the maker's view, not a verdict.
- Verification: `npm audit --audit-level=high` reports 0 vulnerabilities;
  web tests 180 pass; web build passes; E2E passes with timings 469, 433,
  369, 406, 336 ms; `git diff --check` passes.
- Open questions / risks: Checker should independently inspect dependency
  compatibility and rerun the shared story checkpoint.
- Handoff: ready-for-check

## Iteration 34 - 2026-09-29
- Story: US4 escalation-gate repair
- Targeted criteria: D4; checker iteration 33 failure (vitest major bump)
- Worktree: in place
- Change: User approved the `vitest` 3.2.7 to 5.0.2 bump in session; approval
  recorded under T053 in `specs/008-rag-guidance/tasks.md`. Restored two
  blank lines removed in `api/src/underwriteflow/cases/submission.py`
  (class docstring, before `run_evidence_graph`; staff R005).
- Maker self-assessment: D4 appears maker-ready. This is the maker's view,
  not a verdict.
- Verification: submission tests 10 pass. Full gate not rerun; no code
  behavior changed since checker iteration 33 (all other gates passed).
- Open questions / risks: DEBT-020, DEBT-021, staff R002-R004 still open.
- Handoff: ready-for-check

## Iteration 35 - 2026-09-29
- Story: US4 debt repair
- Targeted criteria: D4; DEBT-020, DEBT-021 (staff R002)
- Worktree: in place
- Change: `RouteExplainer` retrieval catch narrowed from `Exception` to
  `(ProviderError, SQLAlchemyError)` and now logs case id and exception
  class only (`knowledge/explainer.py`). Test asserts the log and no message
  leak (`tests/unit/test_explain_node.py`). Evaluation records now carry
  `explanation_status` (`evaluation/runner.py`); SC-003 test asserts at least
  one generated/template explanation
  (`tests/integration/test_route_explanation.py`).
- Maker self-assessment: DEBT-020 and DEBT-021 resolved; D4 stays
  maker-ready. This is the maker's view, not a verdict.
- Verification: `make test-api` 627 pass, 100% coverage. Web, build, smoke,
  E2E not rerun (no web change).
- Open questions / risks: other exception types from `retrieve` (e.g. a
  non-Provider embedding error) now propagate and fail submission; checker
  should confirm that is acceptable. Shared-session abort on DB error still
  unhandled. Staff R003, R004 open.
- Handoff: ready-for-check

## Iteration 36 - 2026-09-29
- Story: US4 checker-failure repair (iteration 35 verdict)
- Targeted criteria: D4; failures (1) transaction abort, (2) order-dependent
  SC-003 test, (3) `submission.py` at 400 lines
- Worktree: in place
- Change: (1) `RouteExplainer` runs `retrieve` inside
  `session.begin_nested()` so a failed query rolls back a savepoint only
  (`knowledge/explainer.py`); new
  `test_retrieval_database_error_keeps_session_usable` runs `SELECT 1/0` on a
  real session then a follow-up statement; removing the savepoint fails it.
  (2) New `active_guideline` fixture in
  `tests/integration/test_route_explanation.py` activates a unique life
  guideline and restores the prior active one (or retires its own); used by
  the SC-003 and submission-graph tests, so SC-003 passes alone and leaves
  the dev DB unchanged. (3) Guidance context dict moved to
  `build_guidance_context` in `knowledge/case_facts.py`; `submission.py` is
  now 390 lines.
- Maker self-assessment: D4 appears maker-ready. This is the maker's view,
  not a verdict.
- Verification: `make test-api` 628 pass, 100% coverage; SC-003 test alone
  passes with no active guideline; savepoint mutant killed. Web, build,
  smoke, E2E not rerun (no web or Compose change).
- Open questions / risks: vitest 5.0.2 approval is user-stated in session,
  recorded in tasks.md T053; checker cannot see the session, human to
  confirm. Staff R003, R004 open.
- Handoff: ready-for-check

## Iteration 37 - 2026-09-29
- Story: US4 checker-failure repair
- Targeted criteria: D4; DEBT-021 and active guideline fixture cleanup
- Worktree: in place
- Change: `evaluate_cases` now accepts explicit guideline IDs. SC-003 imports
  a draft guideline and passes its ID without activating it. The submission
  fixture asserts temporary-version retirement and restores the prior active
  version with bound SQL, then asserts the restored status.
- Maker self-assessment: DEBT-021 and the reported database-state failure
  appear repaired; D4 is maker-ready. This is the maker's view, not a verdict.
- Verification: focused route-explanation file 4 passed; SC-003 alone passed;
  submission graph test alone passed; `make test-api` passed with 628 tests;
  active life guideline stayed unchanged across both isolated tests;
  `git diff --check` passed. Web tests, web build, smoke, and E2E not rerun.
- Open questions / risks: checker should verify direct status restoration is
  acceptable for test cleanup and rerun the complete US4 checkpoint. The full
  API gate exposed other activation tests mutating guideline state; a session
  fixture now restores the prior state after the full suite. DEBT-021 remains
  open pending checker verification. Vitest 5.0.2 approval remains recorded
  in T053 and M-022. Staff R003 and R004 remain open.
- Handoff: ready-for-check

## Iteration 38 - 2026-09-29
- Story: US4 checker-failure repair
- Targeted criteria: D4; staff R003, R004, DEBT-022
- Worktree: in place
- Change: `web-e2e` now mounts `web_node_modules`, preventing `npm ci` from
  writing host dependencies. `RouteExplainer` retries only
  `TransientProviderError` up to `retry_count`; non-transient failures still
  use the deterministic template. Test teardown snapshots and restores every
  pre-existing life-guideline status and `activated_at`, including no active
  version, without a `g1` fallback.
- Maker self-assessment: R003, R004, and DEBT-022 appear ready for checker
  review; D4 remains maker-ready. This is the maker's view, not a verdict.
- Verification: focused API tests pass (11); `make test-api`, `make test-web`,
  web build, smoke, and `make test-e2e` pass. E2E timings: 327, 304, 344,
  255, and 331 ms. `git diff --check` passes.
- Open questions / risks: checker should independently verify retry scope,
  no-active-state restoration, and named-volume isolation.
- Handoff: ready-for-check

## Iteration 39 - 2026-09-29
- Story: US4 checker-failure repair
- Targeted criteria: D4; R003, DEBT-022, criterion 7
- Worktree: in place
- Change: Isolated `test_journey_migration.py` in disposable database
  `underwriteflow_journey_migration`; `web-e2e` now uses its own
  `web_e2e_node_modules` volume. Added staff review
  `reviews/review-20260929-111953.md`.
- Maker self-assessment: D4 is maker-ready after the two reported failures
  are repaired and the fresh staff review is recorded. This is the maker's
  view, not a verdict.
- Verification: focused migration test 1 passed; `make test-api` 629 passed;
  `make test-web` 180 passed; web build passed; `make smoke` passed; no-build
  Playwright E2E passed. Canonical `make test-e2e` hit a Docker registry
  timeout loading `node:24-alpine`.
- Open questions / risks: checker should rerun canonical E2E when registry
  access works and independently verify the disposable database cleanup.
- Handoff: ready-for-check

## Iteration 40 - 2026-09-29
- Story: US5 Underwriter Case Q&A
- Targeted criteria: D5
- Worktree: in place
- Change: T056-T063. User approved T057 migration in this session.
  - `api/alembic/versions/12_case_questions.py`: additive `case_questions`
    table with 1-1,000 character check and `(case_id, created_at)` index.
  - `persistence/knowledge_models.py`: `CaseQuestion`.
  - `knowledge/questions.py`: `ask_question` / `list_questions`. Retrieval
    uses the pinned guideline only. Passages need fused score > 1/61, so
    vector and lexical retrieval must agree. No hit, no pin, provider error,
    or no valid citation stores exactly `not covered by guidelines`.
    Foreign citations emit `citation_dropped` (`output_kind: case_answer`).
    `case_question_answered` audit holds ids, covered, and citation keys.
  - `providers/guidance.py`: `GuidanceRequest.untrusted` carries the
    question and extracted evidence. Gemini `answer` uses a separate
    untrusted-data system instruction. Fake `answer` ignores untrusted
    content.
  - `knowledge/guidance_router.py`: `POST`/`GET
    /reviews/{case_id}/questions` (201, 422, 403, 404).
  - Web: `guidance-questions.tsx` mounted in `guidance-panel.tsx`;
    `api-knowledge.ts` and `types-knowledge.ts` extended.
  - Tests: `test_case_questions.py` (7), contract additions (4),
    migration test, Gemini answer unit test, Vitest
    `guidance-questions.test.tsx` (5). Injection fixture in
    `tests/fixtures/injection.py`. `remove_case` deletes `case_questions`.
- Maker self-assessment: D5 is maker-ready. This is the maker's view, not a
  verdict.
- Verification: new tests failed before implementation; `alembic upgrade
  head` reaches `12_case_questions`; focused API tests 13 passed;
  `make test-api` 642 passed at 100% coverage; `make test-web` 185 passed;
  web build passed; `make smoke` exit 0. Live quickstart US5 against the
  running stack: covered answer cites `g1:life-occupation-hazardous`;
  uncovered answer is exact fallback; injected twin gives the same answer
  and citations and the same route; 3 audit rows without question text;
  shared history is oldest first; Administrator and Applicant get 403 on
  both endpoints.
- Open questions / risks:
  - Live PDF extraction does not store the injected `document_note` line
    (it keeps configured fields only), so the live run proves route and
    answer stability, not provider isolation. The integration test proves
    isolation by seeding extracted evidence directly.
  - Relevance gate 1/61 is coarse (ponytail comment in `questions.py`).
  - Provider failure is stored as the fallback phrase, not an error.
  - Fresh staff review for US5 is not yet recorded (criterion 7).
  - Bootstrap image needed a rebuild to see migration 12.
  - The live check left two synthetic life cases in developer data.
- Handoff: ready-for-check

## Iteration 41 - 2026-09-29
- Story: US5 checker-failure repair
- Targeted criteria: D5; checker iteration 40 failures (1)-(3)
- Worktree: in place
- Change:
  - (1) `knowledge/guidance_router.py`: `_optional` builds the guidance
    and embedding providers, mapping `ProviderError` to `None` with a
    class-name warning. `knowledge/questions.py`: a `None` embedder yields
    no passages, so the answer is the exact fallback with no provider call.
    Contract test `test_question_unusable_providers_return_fallback`
    (unacknowledged Gemini, Ollama) returns 201 fallback.
  - (3) `questions.py`: provider text equal to `not covered by guidelines`
    clears citations, so `covered=false`. Integration test
    `test_cited_fallback_text_is_not_covered`. Fake `answer` now honours
    `text_override`.
  - (2) Staff review `reviews/review-20260929-134127.md`: APPROVED WITH
    CONDITIONS, 0 blockers, 3 warnings, 5 suggestions. Written in the maker
    session; not independent.
  - Review R002 repaired after the review: `web/src/guidance-panel.tsx`
    also mounts `GuidanceQuestions` when the explanation fetch fails;
    Vitest `keeps questions available when guidance fails`.
- Maker self-assessment: D5 is maker-ready. This is the maker's view, not a
  verdict.
- Verification: both new API tests failed before the fix; the new Vitest
  test failed before the R002 fix. Focused API suites 22 passed;
  `make test-api` 644 passed at 100% coverage; `make test-web` 186 passed
  (after R002); web build passed; `make smoke` exit 0 (before R002, API-only
  change since). No lines over 80 columns; files below 400 lines.
- Open questions / risks:
  - Review R001: injection coverage seeds `extracted_fields`; live PDF
    extraction does not store the injected line.
  - Review R003: migration 12 needs human confirmation before commit
    freezes it.
  - Staff review ran in the maker session; checker should weigh that
    against criterion 7's role split.
  - Suggestions R004-R008 left unapplied.
- Handoff: ready-for-check

## Iteration 42 - 2026-09-29
- Story: US5 checker-failure repair
- Targeted criteria: D5; checker failure: injection fixture inserted
  `extracted_fields` directly, so no uploaded document or extraction path
  was tested (T058).
- Worktree: in place
- Change:
  - `api/tests/fixtures/injection.py`: replaced the direct
    `extracted_fields` insert with synthetic identity-record PDFs. The
    injected PDF puts the instruction in the configured `holder_name`
    field (life v3 `life_identity_match` evidence field); the clean twin
    uses `Synthetic Holder`.
  - `api/tests/integration/test_case_questions.py`: new
    `submit_life_case` creates a life v3 case, uploads the PDF, and
    submits through the normal API extraction path (fake extraction
    provider), then repins the case to the draft test guideline.
    `test_injection_is_untrusted_and_matches_clean_twin` now asserts the
    injected text was stored by extraction, both twins have the same route,
    the answer is covered, answer and citations match, and the text reaches
    the provider only in `untrusted`.
- Maker self-assessment: D5 is maker-ready. This is the maker's view, not a
  verdict.
- Verification: focused `test_case_questions.py` 8 passed; `make test-api`
  644 passed at 100% coverage. Test-only change, so web tests, web build,
  and smoke were not rerun (iteration 41: 186 web, build, smoke passed).
  No line over 80 columns.
- Open questions / risks:
  - The test was not red first: production code already handled the case;
    this iteration strengthens coverage only.
  - `test_case_questions.py` is 399 lines, at the limit; the next addition
    must split it.
  - The test activates product life v3, as
    `test_route_explanation.py` already does; shared active-product state.
  - The repin to the draft guideline uses a bound SQL update after
    submission, because submission pins only an active guideline.
- Handoff: ready-for-check

## Iteration 43 - 2026-09-29
- Story: US6 specialist brief
- Targeted criteria: D6
- Worktree: in place
- Change:
  - `api/src/underwriteflow/knowledge/brief.py` (new): pure
    `build_brief`; `None` unless route is specialist; evidence items with
    field, value, document filename, and source locator; triggered rule
    codes; passages; at most three suggested citations.
  - `knowledge/case_guidance.py`: `store_specialist_brief` selects pinned
    guideline passages whose `thresholds` contain a triggered rule code
    (JSONB containment, ordered by passage key), inserts one
    `specialist_brief` row per case cycle (status `template`,
    insert-once), and emits `specialist_brief_stored` audit.
  - `cases/evidence_persistence.py`: calls it after the route
    explanation.
  - `knowledge/guidance_router.py`: `specialist_brief` and
    `suggested_citations` returned from stored row; shared `_citation`
    helper strips `version_id`.
  - Web: `specialist-brief.tsx` (new); `guidance-panel.tsx` renders the
    brief and reports suggestions via `onSuggestions`; `case-review.tsx`
    passes them to `review-actions.tsx`, whose optional citation buttons
    append `[version:passage_key]` to the reason.
  - Tests (T064/T066/T068): unit 3, integration 1, Vitest 3.
- Maker self-assessment: D6 is maker-ready. This is the maker's view, not a
  verdict.
- Verification: new unit and integration tests failed before
  implementation (import error; no brief). Focused API 4 passed; focused
  web 7 passed. `make test-api` 648 passed at 100% target coverage;
  `make test-web` 189 passed; web build exit 0; `make smoke` exit 0.
  Live quickstart US6 probe on running stack: hazardous case routes
  specialist, brief has evidence with document and `page:1`, rule
  `hazardous_occupation_specialist`, passage and suggestion
  `g1:life-occupation-hazardous`; office twin routes expedited with no
  brief; Applicant GET 403. Probe cases removed. Changed files below 400
  lines, no line over 80 columns, `git diff --check` clean.
- Open questions / risks:
  - Passage choice uses exact threshold rule-code match, not hybrid
    retrieval (R9 says "retrieved for those rule codes"). Deterministic
    and needs no embedder; checker should confirm this reading.
  - "Override dialog" is the existing reason textarea; suggestions show
    there whenever present, not only while overriding.
  - Integration fixture needs `cover_start_date`, income record, and
    previous policy; otherwise life v3 routes needs_information. A
    submit failure before `try` leaks the case (two leaked cases were
    removed during development).
  - No staff review run yet for US6 (criterion 7).
  - Brief evidence exposes extracted values to underwriters, as the
    evidence panel already does.
- Handoff: ready-for-check

## Iteration 44 - 2026-09-29
- Story: US6 specialist brief
- Targeted criteria: D6 (repairs C043 failure 1: `_rule_passages` bypassed
  hybrid retrieval and band filters)
- Worktree: in place
- Change:
  - `api/src/underwriteflow/knowledge/case_guidance.py`:
    `_rule_passages` now calls `knowledge.retrieval.retrieve` with the
    space-joined triggered rule codes as the query and the case `age`
    and `sum_assured` facts as band filters, inside a savepoint, and
    returns the fused ranking as the brief passages with
    `version`/`version_id`/`passage_key` citations. It returns no
    passages when the embedder, pinned version, or triggered codes are
    missing, and on `ProviderError` or `SQLAlchemyError` it logs a
    sanitized warning and returns none, so guidance failure never fails
    the submission.
  - `api/src/underwriteflow/cases/evidence_persistence.py`:
    `persist_case_evidence` takes an `embedder` argument and passes it to
    `store_specialist_brief`.
  - `api/src/underwriteflow/cases/submission.py`: both
    `persist_case_evidence` calls pass `embedder=self.embedding_provider`.
  - `api/tests/integration/test_specialist_brief.py`: new
    `test_brief_passages_follow_banded_hybrid_retrieval` (written first;
    failed with `TypeError` before the fix) stores a brief through
    `store_specialist_brief` and asserts the stored passages and the
    top-three suggestions equal a direct `retrieve()` ranking for the
    rule-code query with the case facts, that the exact-match rule-code
    passage ranks first, and that more than one passage is returned (the
    superseded containment query returned one).
- Maker self-assessment: D6 appears maker-ready. This is the maker's
  view, not a verdict.
- Verification: focused US6 unit plus integration 5 passed.
  `make test-api` 649 passed, exit 0, 100% target coverage on
  `workflow/reconciliation.py`. `make test-web` 191 passed, 27 files.
  `docker compose run --rm web npm run build` exit 0. `make smoke`
  exit 0. First API-gate attempt failed 4 tests in
  `tests/integration/test_audit_enrichment.py` and
  `tests/integration/test_audit_sanitization.py` while a concurrent
  review-probe run held the shared development database; those tests
  pass alone (6 passed), and the clean rerun passed 649.
- Open questions / risks:
  - Staff review `review-20260929-163106.md` R001: no relevance floor,
    so weakly related fused passages can be shown as cited passages and
    suggestions. Needs acceptance or a later gate.
  - Staff review R003-R007 remain open suggestions (audit-event
    assertion, stored `version_id`, retrieval before the insert-once
    check, suggestions always visible, unguarded stored brief body).
- Handoff: ready-for-check

## Iteration 45 - 2026-09-29
- Story: US6 specialist brief
- Targeted criteria: D6 (repairs staff review `review-20260929-163106.md`
  R002: stale per-case guidance state)
- Worktree: in place
- Change:
  - `web/src/guidance-panel.tsx`: the fetch effect clears `guidance`,
    `message`, and the parent suggestions before each request, so a case
    switch stops rendering the previous case's brief, a failed fetch
    cannot leave a citation that is appended to another case's override
    reason, and one failure no longer pins later cases to the error
    branch.
  - `web/src/app.tsx`: `CaseReview` is keyed on `queueItem.case_id`, so
    per-case review state remounts on a case switch.
  - `web/src/guidance-panel.test.tsx`: two new tests (written first; both
    failed before the fix): a case switch with a failing fetch clears the
    stale guidance text and reports `[]` suggestions; a later case loads
    normally after an earlier failure.
- Maker self-assessment: R002 is addressed; D6 appears maker-ready. This
  is the maker's view, not a verdict.
- Verification: focused Vitest `src/guidance-panel.test.tsx` 6 passed.
  `make test-web` 191 passed (27 files). Web production build exit 0.
  `make smoke` exit 0. The API gate recorded in iteration 44 (649
  passed) predates this iteration's web-only change.
- Open questions / risks: R001 remains open. Suggestions still render
  whenever present rather than only in the override dialog (R006,
  accepted in iteration 43 as a superset of the requirement).
- Handoff: ready-for-check

## Iteration 46 - 2026-09-29
- Story: US6 specialist brief
- Targeted criteria: D6 (repairs DEBT-036 / staff review
  `review-20260929-163106.md` R004, R006, R007; D6 was checker-pass but the
  guard blocked sign-off on DEBT-036)
- Worktree: in place
- Change:
  - `web/src/review-actions.tsx`: the suggested-citation group renders only
    while `overriding` is true, so citations appear only inside the override
    dialog (R006, user-required at guard Q3).
  - `web/src/review-actions.test.tsx`: the harness now controls `overriding`;
    new failing-first tests assert the group is hidden outside the dialog and
    shown inside it; the two acceptance tests render the override state.
  - `api/src/underwriteflow/knowledge/case_guidance.py`: `_rule_passages`
    stores only `version` and `passage_key` per passage citation, dropping
    the internal `version_id` from the JSONB body and the suggestion list
    (R004).
  - `api/src/underwriteflow/knowledge/guidance_router.py`: new
    `_brief_response` validates the stored brief body and, on
    `ValidationError`, logs the error class and serves no brief instead of a
    500 (R007). Suggested citations are suppressed with the brief.
  - `api/tests/integration/test_specialist_brief.py`: the stored-brief
    helper now returns the stored citation dicts and asserts they hold
    exactly `version` and `passage_key`; new
    `test_corrupt_stored_brief_is_ignored` inserts a corrupt brief row and
    asserts `GET /reviews/{id}/guidance` answers 200 with
    `specialist_brief` null and no suggestions.
- Maker self-assessment: R004, R006, and R007 appear addressed; D6 appears
  maker-ready for a fresh checker pass. This is the maker's view, not a
  verdict.
- Verification:
  - Red-first: `review-actions.test.tsx` failed 1 of 4 before the gate (the
    `Suggested citations` group still rendered); the stored-citation
    assertion failed with `assert False`; the corrupt-brief test raised
    `ValidationError` from `guidance_router.py:216`. All three pass after.
  - Focused US6 checkpoint plus contract: 13 passed.
  - `make test-api` 650 passed, 100% target coverage, exit 0 (was 649).
  - `make test-web` 193 passed, 27 files (was 191).
  - Web production build exit 0. `make smoke` exit 0. Gates ran one at a
    time; no concurrent runs touched the shared database.
  - Scan: no changed file reaches 400 lines (`test_specialist_brief.py` 341);
    no line exceeds 80 columns; every new function has an intent comment;
    nothing staged; `git diff --check` clean.
- Open questions / risks:
  - Consequence of the literal R006 fix the user chose: `overriding` is set
    only by the needs-information branch, so a specialist-routed case (the
    only route that produces a brief) never renders the suggestion buttons.
    The brief still lists the same passages under "Guideline passages". The
    checker and human should confirm US6 scenario 2 is satisfied by the
    override dialog alone, or ask for an override mode in the confirm panel.
    Resolved by the user in session, 2026-09-29: "R006 is fine." The user
    accepts that suggestions appear only in the override dialog, so a
    specialist case shows its passages through the brief and offers no
    suggestion buttons there. The checker should not fail D6 on this point.
  - DEBT-036 stays `open` in the ledger until the checker and human verify.
    R003 (audit assertion) and R005 (retrieval before the insert-once check)
    in DEBT-035 remain acknowledged, non-blocking.
  - No browser walkthrough of the revised panel was recorded; the dev DB has
    no active life guideline.
- Handoff: ready-for-check

## Iteration 47 - 2026-09-29
- Targeted criteria: D6 (US6), repairing the C045 failure (R007).
- Worktree: in place.
- Change:
  - `api/src/underwriteflow/knowledge/guidance_router.py`: new
    `_brief_citations(brief, brief_response)` helper converts stored brief
    citations and drops items that are not objects, `None`, or a non-list
    citation column; `get_guidance` now calls it instead of mapping
    `brief.citations` directly. `_explanation_response` also ignores a
    stored explanation body that is not an object (same defect class: a
    corrupt row previously raised `AttributeError` on `body.get`).
  - `api/tests/integration/test_guidance_read_robustness.py` (new, 117
    lines): the corrupt-row tests moved out of
    `test_specialist_brief.py` (which hit 406 lines) into this file, beside
    the original `test_corrupt_stored_brief_is_ignored`, plus two new
    regressions: `test_corrupt_stored_brief_citations_are_ignored` (valid
    body, citations `["bad", {...}]` keeps only the object and answers 200)
    and `test_corrupt_stored_explanation_body_is_ignored` (body `["bad"]`
    answers 200 with an empty template explanation).
  - `api/tests/integration/test_specialist_brief.py`: corrupt-row block
    removed; now 302 lines.
- Maker self-assessment: R007 appears addressed and the two new tests
  reproduce the C045 probe inside the real app and database; D6 appears
  maker-ready for an independent checker pass. This is the maker's view, not
  a verdict.
- Verification:
  - Red-first: with the loop's working copy of `guidance_router.py` replaced
    by its HEAD revision, `pytest -k corrupt` failed
    `test_corrupt_stored_brief_citations_are_ignored` and
    `test_corrupt_stored_explanation_body_is_ignored`; the iteration 46
    brief-body test still passed. The working copy was restored and its
    sha256 matched the pre-revert backup.
  - Focused US6 unit plus integration plus the new file: 8 passed.
  - `make test-api` 652 passed, 100% target coverage, exit 0 (was 650).
  - `make test-web` 193 passed, 27 files. Web production build exit 0.
    `make smoke` exit 0. Gates ran one at a time; the `api` container was
    restarted after smoke stopped it and is up.
  - Scan: `guidance_router.py` 308 lines, `test_specialist_brief.py` 302,
    `test_guidance_read_robustness.py` 117; no line over 80 columns; every
    new function has an intent comment; nothing is staged; no secret-like
    file is present.
- Open questions / risks:
  - `git diff --check` reports `specs/008-rag-guidance/loop/verdicts.md:163:
    new blank line at EOF`. That file is the checker's; the maker did not
    edit it. The checker should drop the stray blank line.
  - Dev DB still has no active life guideline (361 draft, 3 retired) and the
    test suite keeps adding draft guideline rows (DEBT-013/022 pattern).
    Iteration 47 did not change that.
  - The `_explanation_response` body guard is slightly wider than C045's
    suggested smallest fix. It is the same defect class (corrupt stored row
    answers 500) and is covered by its own regression test.
- Handoff: ready-for-check

## Iteration 48 - 2026-09-29
- Story: US7
- Targeted criteria: D7
- Worktree: in place
- Change: Ran `/speckit.clarify` first, because the approved upload feature
  needed a spec amendment, and recorded three answers in
  `specs/008-rag-guidance/spec.md` (FR-014, FR-015, US7 scenario 2a, edge
  cases, a 2026-09-29 clarification session), `contracts/rest-api.md`,
  `plan.md`, and `tasks-us6-us9.md`. Then implemented US7 end to end.
  New: `knowledge/regulation.py` (manifest, SHA-256, clause split),
  `knowledge/regulation_upload.py` (streamed verified upload),
  `knowledge/regulation_service.py` (import, tags, shared activation),
  `knowledge/regulation_router.py`, `knowledge/regulation_view.py`
  (related clauses), `tests/fixtures/regulation.py`,
  `tests/unit/test_regulation_manifest.py`,
  `tests/integration/test_regulation_import.py`,
  `tests/integration/test_regulation_route_isolation.py`,
  `web/src/regulation-side.tsx`, `web/src/knowledge-tags.tsx` and their
  tests. Changed: `providers/extraction.py` (additive `ocr_page`),
  `knowledge/retrieval.py` (`retrieve_by_meaning`), `knowledge/pins.py`
  (pin the active regulation version, previously always null),
  `knowledge/router.py` (regulation list scope, activation dispatch),
  `app.py`, `config.py` (`regulatory_root`), `compose.yaml` (mount),
  `api/tests/conftest.py` (shared regulation fixtures),
  `api/tests/integration/test_knowledge_migration.py`,
  `api/tests/integration/test_knowledge_pinning.py`,
  `api/tests/contract/test_guidance_api.py`, and the web files
  `api-knowledge.ts`, `types-knowledge.ts`, `guidance-panel.tsx`,
  `knowledge-admin.tsx`, plus the `case-review`, `guidance-panel`, and
  `knowledge-admin` test mocks.
- Verification:
  - Red-first: unit manifest (14) and integration import (6) tests failed
    before their modules existed; the passage contract test failed 404
    before the endpoint. T070's column test cannot be red-first because
    migration 09 already created the columns; T071's migration was
    therefore withdrawn as unnecessary.
  - Focused US7 checkpoint plus migration, pinning, and guidance contract
    suites: 36 passed.
  - `make test-api` 677 passed, 100% target coverage, exit 0.
  - `make test-web` 197 passed, 29 files. Web production build exit 0.
    `make smoke` exit 0. `git check-ignore data/regulatory/manifest.yaml`
    → `.gitignore:47`.
  - Live quickstart US7 on the real nine-file corpus: import 201 in 67 s
    for version `r-eb1720874ed0` with 1144 clauses; the 38-page scanned
    `general_mc_2024.pdf` produced 27 clauses through OCR; the `.doc` was
    reported `unsupported_format`; tag accept 200, activate 200, then a
    second tag accept 409.
  - Live probe found and fixed a real defect: the shipped manifest's
    unquoted YAML dates raised `manifest_invalid`; `ManifestEntry.date`
    now accepts a YAML date and a unit test covers it.
  - Scan: no changed file reaches 400 lines; no changed line exceeds 80
    columns; every new function has an intent comment (flags are decorator
    blocks); nothing staged; no secret pattern; `git diff --check` clean.
- Maker self-assessment: D7 appears maker-ready. This is the maker's view,
  not a verdict.
- Open questions / risks:
  - Approval deviation: Q3 approved a read-only mount for `api` and
    `bootstrap`, but an approved upload must write into the manifest
    folder, so `api` mounts `./data/regulatory` read-write while
    `bootstrap` stays read-only. Needs human confirmation.
  - No staff review covers US7 yet; criterion 7 is unmet until one is
    recorded.
  - `T071` was withdrawn rather than done; the checker should confirm that
    migration 09 already provides every regulation passage column.
  - The live endpoint uses the configured embedding provider (fake
    locally); no caller passes a provider into the import path.
  - Dev DB now holds the real regulation version `r-eb1720874ed0` as
    active, with 1144 clauses, and two test drafts from earlier runs.
- Handoff: ready-for-check

## Iteration 49 - 2026-09-29
- Story: US7 repair
- Targeted criteria: D7 (checker-fail in C047)
- Worktree: in place
- Change: Repaired both C047 blockers and the three staff-review
  warnings, then fixed the review's three cheap notes.
  - C047 (1) version identity: `regulation_version` in
    `knowledge/regulation.py` now hashes the loaded clause set
    (passage key, product lines, title, body) as well as the manifest
    entries, so an upload after an earlier import creates a newer draft
    instead of silently returning the old one. Regression test
    `test_upload_after_first_import_reaches_a_version` (import, upload,
    import) proved red before the fix.
  - C047 (2) `web/src/knowledge-admin.tsx` `) : ( <ul ...` merged line
    split; a repo-wide scan of every changed non-documentation file now
    reports no line over 80 columns.
  - C047 (3) staff review `reviews/review-20260929-190000.md` recorded
    for US7: APPROVED WITH CONDITIONS, 0 blockers.
  - Staff R001: the same identity now hashes `product_lines`, with
    regression test `test_manifest_product_lines_change_creates_new_version`.
  - Staff R002: `test_routes_are_identical_with_and_without_regulation`
    runs both comparisons with `guidance_enabled=True`, so each run reads
    the knowledge tables, and it asserts the fixture's active version has
    at least one clause.
  - Staff R003: authorization refusals added for the four new endpoints
    (`test_regulation_endpoints_require_administrator` for the two
    administrator endpoints plus one anonymous probe, and
    `test_guidance_passage_rejects_other_roles` for the underwriter
    endpoint).
  - Staff R004: the administrator notice reports the returned status, not
    a hardcoded "draft". R005: an unreadable listed file is now reported
    as `unreadable` instead of failing the whole import. R006:
    meaning-only retrieval returns `topic`, so related clauses no longer
    carry an empty topic.
- Verification:
  - Focused regulation suites after the fixes: 26 passed. Contract suites
    with the new refusals: 12 passed.
  - `make test-api` 682 passed, 100% target coverage, exit 0 (was 679).
  - `make test-web` 197 passed, 29 files. Web production build exit 0.
    `make smoke` exit 0.
  - Scan of every changed non-documentation file: no line over 80
    columns, `api/src/underwriteflow/knowledge/regulation_service.py` is
    324 lines and `regulation_upload.py` 116; nothing staged;
    `git diff --check` clean.
- Maker self-assessment: D7 appears maker-ready again. This is the maker's
  view, not a verdict.
- Open questions / risks:
  - The review's R007 (the read-only `./data/regulatory` mount on
    `bootstrap` is unused, and the git-ignored manifest has no fetch
    path, so the allowlist is not reproducible from a fresh clone) and
    R008 (`write_embeddings` is unguarded, and the guidance panel issues
    one related-clause request per citation) are recorded as DEBT-043 and
    DEBT-044.
  - The reviewer's own gate run reported 679 API tests before this
    iteration's additions; the checker should rerun the checkpoint.
  - DEBT-038 (write mount on `api`) still needs human confirmation.
- Handoff: ready-for-check
