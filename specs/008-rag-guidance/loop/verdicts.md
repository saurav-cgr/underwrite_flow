# Checker Verdicts

A criterion passes only after the independent checker verifies primary
sources. Record each story's checkpoint, shared gate, and staff review.

| ID | Iteration | Criterion | Method | Verdict | Confidence | Date |
|----|-----------|-----------|--------|---------|------------|------|
| D1 | 2 | US1: Phase 3, T001, shared gate | tasks.md checkboxes; ls of T004-T011 artifacts; `pytest tests/unit/test_date_field.py` (3 pass) and same test vs HEAD validator (2 fail, red-first confirmed); date edge probes; `make test-api` (561 pass, 100% cov); line/size scan of changed files | fail | high | 2026-09-28 |
| D1 | 4 | US1: Phase 3, T001, shared gate | tasks.md: T006-T011 unchecked, `knowledge-config/` absent; focused `test_date_field.py` + `test_life_v3_config.py` (4 pass); `make test-api` (17 fail, 545 pass): `test_reference_baseline_is_perfect` missing_precision 0.3158, `test_baseline_imports_every_built_in_product_version` 11 != 10, evaluation loader/collision tests fail after life fixtures repinned v1 to v3 | fail | high | 2026-09-28 |
| D1 | 6 | US1: Phase 3, T001, shared gate | tasks.md T001-T011 checked; checkpoint command as written exits 4 (`file or directory not found: tests/unit/test_life_corpus_alignment.py`, test lives in `tests/integration/`); same tests at actual paths 20 pass; `make test-api` 578 pass 100% cov; `make test-web` 173 pass; web build ok; `make smoke` exit 0; changed files <400 lines, <=80 cols, intent comments present; 17 adversarial corpus probes (1 escaped as `TypeError`, non-blocking); API e2e with life v3 active: future, `01/01/1990`, `1990-1-1` DOB give 422, past DOB gives 200 pinned v3; nothing staged; staff review `review-20260928-061300.md` covers T001-T011 | fail | high | 2026-09-28 |
| D1 | 8 | US1: Phase 3, T001, shared gate | tasks.md T001-T011 checked, checkpoint paths match repo; checkpoint 19 + 1 pass; `make test-api` 578 pass 100% cov; `make test-web` 173 pass; web build ok; `make smoke` exit 0; changed files <400 lines, new long lines only in markdown tables (compose.yaml 3 long lines pre-existing); intent comments present; nothing staged, no secret-like untracked files; isolation probe: motor v5 active then journey tests pass (6); staff review `review-20260928-124500.md` APPROVED, 0 blockers; web form renders `type="date"` (source); browser e2e not run (DEBT-001); red-first proven only for T002/T004 | pass | medium | 2026-09-28 |
| D2 | 11 | US2: Phase 4 and shared gate | tasks.md T012-T024 checked; `alembic upgrade head`/`current` = `09_knowledge_base (head)`; checkpoint 8 pass (+ `test_import_corpora.py`); `make test-api` 588 pass 100% cov; `make test-web` 176 pass; web build ok; `make smoke` exit 0; changed files <400 lines, new lines <=80 cols (compose.yaml 3 long lines pre-existing); new functions have intent comments; nothing staged; staff review `review-20260928-141546.md` APPROVED WITH CONDITIONS (R001 read locks open); 23 adversarial API/service probes: 403/401 on all 6 endpoints for Underwriter/Applicant/anon, preview limit 101 gives 422, malformed YAML gives 422, misaligned activation gives 422, identity conflict 409, idempotent re-import. FAILED: 4 concurrent activations of different drafts raise raw `IntegrityError` (`uq_knowledge_versions_one_active`) from autoflush in `audit.latest_event_id` outside the `commit` try, so API returns 500 not 409 (T016 requires conflict mapping); 4 concurrent same-identity imports raise raw `IntegrityError` too; re-activating the active version appends a second `knowledge_version_activated` event. DB constraints kept exactly one active version. Quickstart US2 checked through in-process API, not browser | fail | high | 2026-09-28 |
| D2 | 14 | US2: Phase 4 and shared gate | tasks.md T012-T024 checked; `alembic upgrade head`/`current` = `09_knowledge_base (head)`; checkpoint files plus `test_import_corpora.py` and `test_knowledge_service.py` 11 pass; `make test-api` 591 pass 100% cov; `make test-web` 177 pass; web build ok; `make smoke` exit 0; changed files <400 lines, only long lines are 3 pre-existing in compose.yaml; intent comments present (flagged defs are multi-line decorators); nothing staged, no secret-like content or files; staff review `review-20260928-170504.md` APPROVED, 0 blockers. Adversarial probe (separate session, service level, 5 rounds): 4 concurrent activations of different drafts give 1 `ok` + 3 `KnowledgeConflictError`, exactly 1 active row, exactly 1 `knowledge_version_activated` event per winner; 4 concurrent same-content imports and 4 concurrent same-identity/different-content imports give 1 `ok` + 3 conflicts, no raw `IntegrityError`; API re-activate of active version twice gives 200/200 with 1 audit event; bad UUID 422, missing version activate/retire 404, scope `regulation` 422, YAML list 422, YAML alias 422. Read paths use `find` (no `FOR UPDATE`); preview uses SQL `COUNT` plus `OFFSET/LIMIT`. Notes (non-blocking): concurrent same-content import returns 409 not idempotent success; nav added in `components.tsx`/`app.tsx`, not `admin.tsx` as T024 names; passages order by `passage_key` string, not file order; preview reads version twice. Browser quickstart US2 not run (DEBT-006) | pass | medium | 2026-09-28 |
| D3 | 17 | US3: Phase 5 and shared gate | tasks.md T025-T039 checked; `alembic upgrade head`/`current` = `10_knowledge_retrieval (head)`; checkpoint unit 12 pass, integration (retrieval, recall, migration, embeddings) 6 pass; `make test-api` 608 pass 100% cov; `make test-web` 177 pass; web build ok; `make smoke` exit 0; `evaluate_retrieval.py` with g1 activated and fake provider recall 1.000 (30/30), exit 0; DB shows `vector(768)` and `hnsw (embedding vector_cosine_ops)`; 12/12 g1 passages embedded; nothing staged; files <400 lines, <=80 cols (except 30 flow-style lines in `evaluation/retrieval/life-individual-term.yaml`, data file); staff review `review-20260928-181000.md` APPROVED. Probes passed: SQL/tsquery/LIKE metacharacters, unicode, and empty queries bound safely; limit 0/51 rejected; unknown version gives `[]`; age 30/70 band filters correct; absent fact keeps all bands; leap-day and day-before-birthday ages correct. FAILED: (1) criterion 5, nested named functions without intent comments: `run` in `tests/integration/test_retrieval.py:33`, `test_retrieval_recall.py:23`, `test_knowledge_embeddings.py:39`, and `handler` in `tests/unit/test_embedding_providers.py:44`. Committed precedent comments nested helpers (`test_evaluation_e2e.py:48`), and staff R002 blocked the same defect in `vector.py`. (2) criterion 2, T036 names "absent fact skips its filter", but `test_retrieval.py` has no such assertion; T025 names `vector(768)` and `vector_cosine_ops`, but the migration test checks only `udt_name = vector` and index names. Both hold in the DB (checker probe), but the named tests do not lock them. Red-first not verifiable (all new files untracked). Notes: the recall gate passes 30/30 with random query vectors (lexical path alone clears it, DEBT-011); bootstrap now fails when `GENERATION_PROVIDER=gemini` without acknowledgement (DEBT-012); integration tests leave test versions active in the dev DB (DEBT-013) | fail | high | 2026-09-28 |
| D3 | 18 | US3: Phase 5 and shared gate | Separate session. tasks.md T025-T039 checked; `alembic upgrade head`/`current` = `10_knowledge_retrieval (head)`; checkpoint unit (+`test_import_corpora.py`) 13 pass, integration (retrieval, recall, migration, embeddings) 6 pass; `make test-api` 608 pass 100% cov; `make test-web` 177 pass; web build ok; `make smoke` exit 0; `evaluate_retrieval.py` with g1 active and `GENERATION_PROVIDER=fake` recall 1.000 (30/30), exit 0. Prior failures fixed: nested `run`/`handler` helpers now have intent comments; `test_retrieval.py:66-75` asserts absent age keeps the 18-40 band passage; migration test asserts `vector(768)` and `vector_cosine_ops`. Mutation probe: patched `_band_filters` to drop banded passages when age absent, test failed (mutant killed). Scan of modified/untracked non-markdown files: none >=400 lines, none >80 cols, every `def` preceded by comment or decorator; nothing staged; 0 secret-pattern hits; `.env.example` adds only `GEMINI_EMBEDDING_MODEL`. Staff review `review-20260928-185248.md` APPROVED, 0 blockers. Notes (non-blocking): T025 GIN type not asserted by test (DB shows `USING gin (search_vector)`); unused imports `case_facts`/`KnowledgeVersion` in `test_retrieval.py`, `case_facts` in `test_retrieval_recall.py`; checker mutation run retired dev `g1` permanently (DEBT-013 escalated). Red-first not verifiable (files untracked) | pass | medium | 2026-09-28 |
| D3 | 20 | US3: Phase 5 and shared gate (repairs DEBT-012, DEBT-013, review R001-R002) | Separate session. US3 checkpoint plus repair tests (embedding providers, import corpora, case facts, rank fusion, vector type, Compose contract, retrieval, recall, migration, embeddings) 33 pass; `make test-api` 608 pass 100% cov; `make test-web` 177 pass; web build ok; `make smoke` exit 0; bootstrap container exits 0 with default local env. Provider: `EMBEDDING_PROVIDER` defaults to `fake` in `compose.yaml` (api and bootstrap), smoke, evaluation, and `.env.example`; bootstrap and API receive the same embedding settings; `ollama` (explicit or via generation fallback) raises `ProviderError`, test matches "Ollama"; Gemini path keeps acknowledgement and host checks. DEBT-013 probe: snapshot of `knowledge_versions` status before and after running retrieval, recall, and embedding tests shows no status change and no activation; only 3 new `draft` rows added (test drafts are never cleaned up, non-blocking). Web preview renders identifier, topic, age band, sum-assured band, and label (FR-001); Vitest asserts each. Scan: no changed file >=400 lines; only long lines are pre-existing (`.env.example:8`, `compose.yaml:34,67,73`), no new added line >80 cols; intent comments present; nothing staged. Staff review `review-20260928-192923.md` APPROVED, 0 findings. Notes: `retrieval.py` query-side provider is injected by caller (no US3 API caller yet, parity enforced only for bootstrap/import); dev DB currently has no active life guideline (`g1` draft) | pass | high | 2026-09-28 |
| D4 | 30 | US4: Phase 6 and shared gate | Separate session. tasks.md T040-T055 checked; `alembic upgrade head`/`current` = `11_case_guidance (head)`; checkpoint unit + integration + contract 16 pass; `make test-api` 625 pass 100% cov; `make test-web` 180 pass; web build ok; `make smoke` exit 0; `docker compose restart api` ok; `make test-e2e` exit 0, times 499, 426, 472, 431, 340 ms. Scan: no changed file >=400 lines, no new line >80 cols. Staff review `review-20260928-221135.md` APPROVED WITH CONDITIONS (R001 npm audit, R002 no post-resume read). FAILED: (1) FR-019 regression, probe: with `GENERATION_PROVIDER=ollama`, `POST /cases/{id}/submit` returns 500 because `build_guidance_provider` raises `ProviderError` in `cases/router.py:291` (not caught, no global handler); stubbing both guidance builders gives 200 `needs_information`, so US4 breaks every Ollama submission. (2) T046 names SC-003 test "routes for all 90 cases in `/app/evaluation/cases.json` identical with guidance enabled and disabled"; no test loads `cases.json` or compares enabled/disabled routes. (3) T054: E2E asserts only `role=status` "Explanation unavailable."; DB check shows all 5 E2E cases route `needs_information` with no `case_guidance` row (motor has no guideline), so no per-route coverage and SC-008 never times a stored explanation. (4) T048: contract "route unchanged after the call" compares `submitted` route with itself (tautology), no re-read after GET. (5) criterion 5: nested `fake_retrieve` at `tests/unit/test_explain_node.py:254` lacks intent comment. Notes (non-blocking): `web/test-results/` untracked and not git-ignored (commit risk); `web-e2e` mounts `./web` without node_modules volume, so `npm ci` rewrites host `web/node_modules`; E2E leaves motor v5 active; panel omits missing-item citations; `submission.py` lost blank lines around `__init__`; retrieval DB error inside shared session may abort the transaction before persistence (only mocked in tests). Red-first not verifiable (files untracked) | fail | high | 2026-09-28 |
| D4 | 31 | US4: Phase 6 and shared gate (repairs iteration 30 failures) | Separate session. tasks.md T040-T055 checked; `alembic upgrade head`/`current` = `11_case_guidance (head)`; checkpoint unit + integration + contract 18 pass; `make test-api` 627 pass 100% cov; `make test-web` 180 pass; web build ok; `make smoke` exit 0; `docker compose restart api` healthy; `make test-e2e` exit 0, times 462, 432, 463, 454, 473 ms. Scan: no changed file >=400 lines; new long lines only in lockfile and markdown; every `def` has intent comment; nothing staged. Prior failures fixed: (1) Ollama probe with `generation_provider=ollama`, `embedding_provider=fake` gives submit 200; (3) DB shows the 5 E2E cases route expedited, standard, specialist, needs_information, expedited, each with a stored `generated` `route_explanation` row; (4) contract reads review before and after GET; (5) nested comment present. FAILED: (2) T046/SC-003 test is vacuous. `evaluate_cases(guidance_enabled=True)` computes the route before calling `explain_route`, discards its return, and uses a stub explainer, not `RouteExplainer` with pins as T046 names. Mutation probe: `explain_route` returning `recommendation.route = "specialist"` leaves `test_guidance_keeps_all_reference_routes_unchanged` passing (other graph tests catch it). Staff review not rerun after iteration 31 (latest `review-20260928-221135.md`). Notes (non-blocking): with `embedding_provider` unset and `generation_provider=ollama`, submit still returns 500 because `build_embedding_provider` raises; Compose and `.env.example` default `EMBEDDING_PROVIDER=fake`, so shipped stack is unaffected; test-only stub explainer lives in production `evaluation/runner.py`; `web/test-results/` still not git-ignored; `npm audit` produced no output in checker session (not settled) | fail | high | 2026-09-29 |
| D4 | 33 | US4: Phase 6 and shared gate (repairs iterations 31-33) | Separate session. tasks.md T040-T055 checked; `alembic current` = `11_case_guidance (head)`; checkpoint unit + integration + contract 18 pass; `make test-api` 627 pass 100% cov; `make test-web` 180 pass (24 files); web build ok; `make smoke` exit 0; `docker compose restart api` healthy; `make test-e2e` exit 0, times 337, 315, 313, 378, 338 ms. Scan: no changed file >=400 lines, no new line >80 cols, every Python `def` and TS named function has intent comment; nothing staged. Prior failure fixed: T046/SC-003 now runs `build_triage_graph` with real `RouteExplainer` and reads route from graph output; mutation probe (`explain_route` rewrites `recommendation.route` to `specialist`) fails the test (mutant killed). Dev DB has life `g1` active, so 30 life cases exercise the explainer. `web/test-results/` now git-ignored; `@playwright/test` 1.63.0 matches E2E image tag. FAILED: escalation gate. Iteration 33 bumped `vitest` 3.2.7 to 5.0.2 (major) in `web/package.json`; T053 approved only `@playwright/test`; no approval recorded in tasks.md or loop files; latest staff review `review-20260929-101500.md` APPROVED WITH CONDITIONS flags it (R001). AGENTS.md requires asking before dependency changes. Notes (non-blocking, staff R002-R005 open): `explainer.py:55` `except Exception` around `retrieve` returns `unavailable` with no log; no transient retry before template fallback (plan.md accepts timeout fallback); `web-e2e` bind-mounts `./web` and `npm ci` rewrites host `web/node_modules`; `submission.py` blank lines removed. SC-003 test passes vacuously if no guideline is active (no assertion that any explanation was produced) | fail | high | 2026-09-29 |
| D4 | 35 | US4: Phase 6 and shared gate (repairs iterations 34-35) | Separate session. Prior failure fixed on paper: tasks.md T053 now records 2026-09-29 approval of `vitest` 3.2.7 to 5.0.2 (maker states user approved in session; checker cannot see that session, human to confirm). `explainer.py` catch narrowed to `(ProviderError, SQLAlchemyError)` with sanitized log; SC-003 test asserts at least one generated/template explanation. FAILED: (1) FR-019/transaction abort, probe: temporary test patched `retrieve` to run `SELECT 1/0` on the shared submission session; explainer catches the `DBAPIError` and returns `unavailable`, but the PostgreSQL transaction stays aborted and the next write (`INSERT INTO validations`) raises `InFailedSQLTransactionError`, so `POST /cases/{id}/submit` fails. Catching `SQLAlchemyError` without a savepoint converts a guidance failure into a submission failure. (2) SC-003 test is order-dependent, probe: with the active life guideline set to draft, `pytest -k all_reference_routes` alone fails `assert any(...)`. It passes in the full suite only because `test_submission_graph_persists_guidance_before_restart` activates a test guideline (`guidance-<hex>`) and never restores the prior one; bootstrap imports shipped `g1` as draft, so a fresh stack has no active guideline. Dev DB now has `guidance-2be040c811` active, not shipped `g1` (activation side effect, DEBT-013 pattern). (3) criterion 4: `api/src/underwriteflow/cases/submission.py` is 400 lines after iteration 34 restored blank lines; limit is fewer than 400. Not rerun (fail already established): full `make test-api`, web, build, smoke, E2E. Probe files removed; probe case removed; prior active guideline restored | fail | high | 2026-09-29 |
| D4 | 36 | US4: Phase 6 and shared gate (repairs iteration 35 failures) | Separate session. `make test-api` 628 pass 100% cov. Fixed: (1) savepoint, end-to-end probe (temporary test patching `retrieve` to run `SELECT 1/0` on the submission session) now gives submit 200 `underwriter_review` and GET guidance 200 `unavailable`; probe removed. (3) `submission.py` 390 lines, `case_facts.py` 58, `test_route_explanation.py` 333. FAILED: (2) `active_guideline` fixture restore fails silently, so tests still leave the dev DB changed. Probe: active life guideline before `make test-api` `guidance-6f65793db4`, after `guidance-98e0b670d7`; running `test_route_explanation.py` alone changed it again to `guidance-6709a10a39`. Cause: activating the fixture's version retires the prior one, and the fixture's restore `POST .../{prior}/activate` returns 422 `retired version cannot be active` (probe reproduced); the response is not checked. Each run leaves a new test guideline active and the prior one permanently retired (retired is terminal). Shipped `g1` is `draft` in dev DB, so the demo stack has no shipped guideline active. Maker claim "leaves the dev DB unchanged" is false. Not rerun (fail established): web tests, build, smoke, E2E (no web or Compose change since iteration 33 pass of those gates). Vitest 5.0.2 approval still human-stated only | fail | high | 2026-09-29 |
| D4 | 37 | US4: Phase 6 and shared gate (repairs iteration 36 failure) | Separate session. tasks.md T040-T055 checked; `alembic current` = `11_case_guidance (head)`; checkpoint unit + integration + contract 19 pass; `make test-api` 628 pass 100% cov; `make test-web` 180 pass; web build ok; `make smoke` exit 0; `docker compose restart api` ok; `make test-e2e` exit 0, times 494, 345, 339, 346, 173 ms. Scan: no changed file >=400 lines, no new line >80 cols, every Python `def` and TS named function has intent comment; nothing staged; no secret-pattern hits. Prior failure fixed: active knowledge snapshot identical before and after `make test-api` (`g1` active); SC-003 uses a draft guideline id and asserts active id unchanged. Probe: with no active guideline at start, `test_route_explanation.py` leaves shipped `g1` active, because session fixture `restore_life_guideline_status` falls back to `g1` when prior is None; raw SQL status writes bypass audit and `activated_at` (opened DEBT-022). Vitest 5.0.2 approval confirmed by user in checker session. FAILED: criterion 7. Latest staff review `review-20260929-101500.md` predates iterations 34-37, which changed `explainer.py` (savepoint, narrowed catch), `submission.py`, `case_facts.py`, `evaluation/runner.py`, and `tests/conftest.py`; no staff review covers the current code. Its warnings R003 (`web-e2e` bind-mounts `./web`, `npm ci` rewrites host `node_modules`, still present in `compose.yaml`) and R004 (no transient retry before template) are neither fixed nor accepted by the user | fail | high | 2026-09-29 |
| D4 | 38 | US4: Phase 6 and shared gate (repairs R003, R004, DEBT-022) | Separate session. Fixed: R004, `RouteExplainer` retries only `TransientProviderError` up to `provider_retry_count` (wired from `settings.provider_retry_count` via `submission.py`), unit test `test_transient_provider_error_retries_before_template` present. FAILED: (1) R003 not fixed, made worse. `web-e2e` (Playwright noble, glibc) now mounts the same `web_node_modules` volume as `web` (`node:24-alpine`, musl). `npm ci` in `web-e2e` replaces `@rollup/rollup-linux-arm64-musl` with `-gnu`. Probe: `make test-e2e` exits 1, `web-1` crashes `Cannot find module '@rollup/rollup-linux-arm64-musl'`; afterwards `make test-web` and `npm run build` fail with the same error. Checker restored the volume with `npm ci` in the `web` service. (2) `make test-api` exits non-zero, reproduced twice: 629 pass, 1 error, session fixture `restore_life_guideline_status` teardown `assert restored_by_id == prior_by_id` fails with `{}`. Cause: committed `test_journey_migration.py` runs `alembic downgrade 07` on the live DB, dropping knowledge tables and every life guideline row; the snapshot ids no longer exist. Dev DB after run: 14 test-era life guideline rows, all `draft`, shipped `g1` draft, no active guideline. (3) criterion 7: no staff review after `review-20260929-101500.md`; iterations 34-38 unreviewed. Not rerun (fail established): smoke, line scan | fail | high | 2026-09-29 |
| D4 | 39 | US4: Phase 6 and shared gate (repairs iteration 38 failures, R001 of `review-20260929-111953.md`) | Separate session. tasks.md T040-T055 checked; `alembic current` = `11_case_guidance (head)`; checkpoint unit + integration + contract + journey migration 21 pass; `make test-api` 629 pass, exit 0; `make test-e2e` (canonical, with build) exit 0, times 331, 311, 304, 325, 337 ms; then `make test-web` 180 pass and web build ok (R003 probe: E2E no longer corrupts `web_node_modules`; `web-e2e` uses own `web_e2e_node_modules` volume); `make smoke` exit 0; api restarted healthy. Fixed: (1) journey migration runs `alembic downgrade 07` only in disposable `underwriteflow_journey_migration`; probe: `knowledge_versions` snapshot before and after `make test-api` shows no status or `activated_at` change on any existing row (only 5 new test `draft` rows added), active life guideline unchanged, disposable DB absent after run. (2) Staff review `review-20260929-111953.md` APPROVED WITH CONDITIONS postdates every code change; its only warning R001 (rerun canonical `make test-e2e`) now satisfied by this run. Scan: no changed file >=400 lines (`submission.py` 391); only long lines pre-existing `compose.yaml:34,67,73`; every Python `def` and TS named function has intent comment; nothing staged; 0 secret-pattern hits. Notes (non-blocking): test runs still add draft knowledge rows, some with `activated_at` set (DEBT-013/022 pattern); Makefile coverage report lists only `reconciliation.py`; red-first not verifiable (files untracked) | pass | high | 2026-09-29 |
| D5 | 40 | US5: Phase 7 and shared gate | Separate checker session. T056-T063 checked; `alembic upgrade head` and `alembic current` reach `12_case_questions (head)`; focused migration, provider, integration, and contract suite 25 pass; focused Q&A Vitest 5 pass. Changed hand-written files are below 400 lines and have no lines over 80 columns; intent comments present; nothing staged; no committed secret assignment found. FAILED: (1) adversarial no-pin probe with `generation_provider=gemini`, fake embeddings, and no Gemini acknowledgement: `POST /reviews/{case_id}/questions` returns 500 `internal_error`, not 201 with exact fallback. `post_question` eagerly calls `build_guidance_provider` before `ask_question` can detect the missing pin and skip the provider, violating T058's no-hit/no-provider-call outcome and FR-019. Temporary probe removed. (2) criterion 7: latest staff review `review-20260929-111953.md` predates iteration 40; no staff review covers US5. (3) source inspection: valid citations make `covered=true` even if provider text equals the exact fallback phrase, conflicting with the data-model outcome invariant. Not rerun after failure established: full API/web/build/smoke gates or live quickstart. | fail | high | 2026-09-29 |
| D5 | 41 | US5: Phase 7 and shared gate (iteration 40 failure repairs) | Separate checker session. Human confirmed migration 12. `alembic upgrade head` and `current` reach `12_case_questions (head)`; focused API suite 27 pass; focused web suite 9 pass; `make test-api` 644 pass at 100% target coverage; `make test-web` 186 pass; web build and `make smoke` exit 0. Live API quickstart: covered answer 201 with one citation; uncovered answer 201 with exact fallback; history 200; Administrator POST and Applicant GET 403; answer audits present. Prior failures fixed: unusable provider settings return 201 fallback; cited exact fallback becomes uncovered; R002 web error branch mounts Q&A. Scan: changed hand-written files below 400 lines and at most 80 columns; intent comments present; nothing staged; no committed secret assignment found. Staff review `review-20260929-134127.md` is recorded; checker verified its post-review R002 repair. FAILED: T058 and the US5 independent test require an injection fixture document. `tests/fixtures/injection.py` inserts an `extracted_fields` row directly and creates no document or extraction path. Maker and staff review both confirm live PDF extraction drops the injected `document_note`; therefore the test cannot prove an uploaded document instruction reaches the provider only as untrusted data. | fail | high | 2026-09-29 |
| D5 | 42 | US5 gate | C042 evidence below | pass | high | 2026-09-29 |
| D6 | 43 | US6 gate | C043 evidence below | fail | high | 2026-09-29 |
| D6 | 45 | US6 gate (repairs C043, review R002) | C044 evidence below | pass | high | 2026-09-29 |
| D6 | 46 | US6 gate (repairs DEBT-036: R004, R006, R007) | C045 evidence below | fail | high | 2026-09-29 |
| D6 | 47 | US6 gate (repairs C045, R007) | C046 evidence below | pass | high | 2026-09-29 |

## C042 evidence

- Separate checker session. T056-T063 remain checked. Human migration approval
  remains recorded.
- `alembic upgrade head` and `alembic current` reached
  `12_case_questions (head)`.
- Unit provider suite: 7 passed. Phase integration and contract checkpoint:
  15 passed. Focused web Q&A and guidance suites: 9 passed.
- `make test-api`: 644 passed with 100% target coverage. `make test-web`:
  186 passed. Web production build and `make smoke` exited 0.
- T058 failure fixed. Source and test execution prove two real synthetic PDFs
  use upload, local PDF reading, fake extraction, persistence, and submission.
  Extracted `holder_name` contains the injected text. Injected and clean twins
  keep equal routes, answers, and citations. The guidance provider request
  contains the text only under `untrusted`.
- Live HTTP probe against the running stack passed: injected and clean routes
  matched; covered answers matched with one citation; uncovered answer was the
  exact fallback; Applicant and Administrator received 403; history held both
  exchanges. Synthetic probe cases were removed.
- Adversarial source check found no route write path in Q&A. The test checks
  the trusted request fields exclude the injection, not only output equality.
- Changed implementation and test files remain below 400 lines and at most
  80 columns. Named functions have intent comments. `git diff --check` passed.
  Nothing is staged. Staff review `review-20260929-134127.md` covers US5;
  iteration 42 resolves its R001 test-quality warning. No new implementation
  followed it.

## C043 evidence

- Separate checker session. T064-T069 are checked.
- Focused unit tests: 3 passed. Focused integration test: 1 passed. Full unit
  suite: 418 passed. Full integration suite: 162 passed.
- `make test-api`: 648 passed with 100% target coverage. `make test-web`:
  189 passed. Web production build and `make smoke` exited 0.
- Live HTTP probe against the running stack passed. Hazardous occupation
  produced a specialist brief with sourced evidence, triggered rule, passage,
  and one suggestion. Office occupation produced no brief or suggestions.
  Applicant guidance access returned 403. Synthetic probe cases were removed.
- Changed implementation and test files remain below 400 lines and at most
  80 columns. Named functions have intent comments. `git diff --check` passed.
  Nothing is staged; no secret-like file is present.
- FAILED: R9 requires top passages retrieved for triggered rule codes. FR-007
  requires hybrid semantic and exact-wording retrieval with matching bands.
  `_rule_passages` bypasses `knowledge.retrieval.retrieve`, ignores case bands,
  and orders exact threshold matches by passage key. Suggestions are therefore
  not the required top hybrid-retrieval results.
- FAILED: shared criterion 7 requires a recorded staff review. Latest review
  is `review-20260929-134127.md` for US5 and predates iteration 43. Maker also
  records that no US6 staff review has run.
- Red-first history is not independently verifiable because new tests remain
  untracked. No comprehension debt opened because D6 has definite failures.

## C044 evidence

- Separate checker session. T064-T069 are checked. Staff review
  `review-20260929-163106.md` covers US6 (iteration 44). Iteration 45
  repairs its R002 warning; no later implementation followed.
- Focused US6 unit plus integration: 5 passed.
- `make test-api`: 649 passed, 100% target coverage, exit 0.
  `make test-web`: 191 passed, 27 files. Web production build exit 0.
  `make smoke` exit 0. Gates ran one after another, with no concurrent
  use of the shared database.
- C043 failure 1 fixed: `_rule_passages` calls `retrieve` with the rule
  code query and the case `age` and `sum_assured` facts. A temporary
  mutation probe monkeypatched `retrieve` two ways: facts dropped, and
  results reordered by passage key. The regression test
  `test_brief_passages_follow_banded_hybrid_retrieval` failed for both
  mutants. The probe file was removed.
- C043 failure 2 fixed: a US6 staff review is recorded (see above).
- Iteration 45 mutation probe: a copy of `guidance-panel.tsx` without the
  three state resets fails both new tests. The unchanged file passes all
  6 tests. The probe files were removed.
- Wiring probe: a temporary Vitest test rendered `CaseReview` with a
  mocked brief. It found the `Specialist brief` heading. Clicking
  `Use citation g1: life-occ` appended `[g1:life-occ]` to the reason
  field. The probe file was removed. No permanent test covers this
  wiring (DEBT-034).
- Live HTTP quickstart US6 against the running stack (fake providers):
  - With no active life guideline (current dev DB state), the hazardous
    case routes to specialist. The brief lists 21 sourced evidence items
    and `hazardous_occupation_specialist`, with no passages and no
    suggestions. The office twin routes expedited with no brief.
    Applicant `GET /guidance` returns 403.
  - With a probe guideline imported and activated, the brief pins that
    guideline. Passages are `life-occupation-hazardous`,
    `life-age-eighteen-to-forty`, `life-cover-up-to-standard-limit`,
    `life-health-declaration-complete`, `life-health-statement-required`.
    Suggestions are the first three. The response contains no
    `version_id` or `storage_key`. A second fetch is identical.
  - Probe cases were removed. Guideline statuses were restored to the
    snapshot, and the restore was checked.
- Observation: the dev DB has no active life guideline (278 draft, 3
  retired). The cause is not established. The quickstart shows passages
  only after an Administrator activates a guideline.
- Changed and new implementation and test files are below 400 lines and
  at most 80 columns. Every named function has an intent comment.
  `git diff --check` passed. Nothing is staged; no secret-like file is
  present. Loop ledger files keep the existing exception.
- Red-first history for T064-T068 is not independently verifiable
  because the tests are untracked. The mutation probes substitute for it.
- R001 (no relevance floor) remains open. Passages 4 and 5 in the live
  probe are weak matches for the hazardous rule. Opened as DEBT-033.

## C045 evidence

- Separate checker session; this session did not produce iteration 46.
  T064-T069 are checked. Iteration 46 invalidates C044, so every gate
  was rerun.
- Focused US6 unit plus integration: 6 passed.
- `make test-api`: 650 passed, 100% target coverage, exit 0.
  `make test-web`: 193 passed, 27 files. Web production build exit 0.
  `make smoke` exit 0. Gates ran one after another. Smoke stops the
  `api` container; the checker restarted it.
- R006 verified: a temporary mutation that dropped `overriding &&` from
  the suggestion group made `hides stored suggestions outside the
  override dialog` fail (1 of 4). The original file was restored and
  compared byte for byte. User accepted in session that a specialist
  case shows no suggestion buttons ("R006 is fine").
- R004 verified: `_rule_passages` stores only `version` and
  `passage_key`; the integration helper asserts exactly those keys.
- R007 incomplete (fail): `_brief_response` guards only the stored
  `body`. `get_guidance` still maps `brief.citations` with `_citation`
  and no `isinstance(item, dict)` filter, unlike `_explanation_response`.
  A temporary integration probe stored a valid body `{"rules": []}` with
  `citations=["bad"]`. `GET /reviews/{id}/guidance` answered 500
  `internal_error`. The probe file was removed. Smallest fix: filter
  non-dict items (as `_explanation_response` does), or build the
  suggestion list inside the guarded path, plus one regression test.
- Scan: changed and new files are below 400 lines and at most 80
  columns. Every named function has an intent comment. Nothing is
  staged. `git diff --check` clean.

## C046 evidence

- Separate checker session; this session did not produce iteration 47.
  T064-T069 are checked. The C045 checker pass on R004 and R006 still
  holds; iteration 47 changed only the guidance read path and tests.
- Focused US6 unit, integration, and `test_guidance_read_robustness.py`:
  8 passed.
- `make test-api`: 652 passed, 100% target coverage, exit 0.
  `make test-web`: 193 passed. Web production build exit 0. `make smoke`
  exit 0. Gates ran one after another; the checker restarted `api` after
  smoke stopped it.
- R007 verified on the brief path: a temporary probe stored five corrupt
  brief shapes (body `None`; citations `5`; citations `{"a": 1}`; a
  passage whose citation is a string; body `"text"` with a nested
  version object). `GET /reviews/{id}/guidance` answered 200 for all
  five. The probe file was removed.
- Out of D6 scope, recorded as DEBT-037: the same probe found three
  corrupt route-explanation shapes that still answer 500
  (`missing_items: 5`; a missing item with `citations: 5`; row
  `citations: 5`). This is US4 read-path code signed off under D4.
- Scan: changed and new files are below 400 lines and at most 80
  columns. Every named function has an intent comment. Nothing is
  staged. The checker removed its own stray blank line at the end of
  this file, which `git diff --check` reported.
