# Comprehension Debt & Sign-off

Record changes that still need human review. Keep acknowledged debt in the
ledger. Open blocking debt prevents loop completion.

## Open debt

| ID | Iteration | Change | Human review needed | Severity | Status |
|----|-----------|--------|---------------------|----------|--------|
| DEBT-001 | 6 | Life v3 `date_of_birth` web form | Checker verified API (422/200) and `<input type="date">` rendering in source only; no browser run of quickstart US1 web-form flow | non-blocking | acknowledged |
| DEBT-002 | 8 | Journey test restore of motor state | `set_motor_status(prior, "v1")` restores product status but not the prior active version: with motor v5 active before, v1 is active after. Pre-existing pattern (24 uses at HEAD). Decide whether to accept | non-blocking | acknowledged |
| DEBT-003 | 1-2 | `validation.py` date parsing and `not_future` | New trust-boundary validation; human should confirm strict ISO round-trip and server-local `date.today()` are intended | non-blocking | acknowledged |
| DEBT-004 | 3-5 | Life v3 config, importer entry, 30 life fixtures repinned to v3 with synthetic DOBs, built-in version count 10 to 11 | Evaluation dataset identity changed; human should confirm repinning v1/v2 fixtures to v3 is intended | non-blocking | acknowledged |
| DEBT-005 | 6-7 | Corpus parser, alignment checker, 12-section `g1.yaml`, read-only Compose mounts | Largest new logic; `undeclared_number` rule and closed topic sets decide what later stories may say; one probe escaped as `TypeError` (iteration 6 verdict) | non-blocking | acknowledged |
| DEBT-006 | 9-11 | Administrator knowledge screen and quickstart US2 | Checker ran US2 quickstart through in-process API and Vitest only; no browser run of import, preview, activate, and case pin flow | non-blocking | acknowledged |
| DEBT-007 | 9 | Migration `09_knowledge_base.py` (three tables, coalesce unique indexes) | Becomes permanent schema history once committed; human should confirm table shape and `uq_knowledge_versions_one_active` before it is frozen | non-blocking | acknowledged |
| DEBT-008 | 9-14 | `knowledge/service.py` import/activate/retire, `IntegrityError` mapping, idempotent re-activation | Checker probed races, but concurrent same-content import returns 409 while sequential re-import succeeds; human should accept or reject that asymmetry | non-blocking | acknowledged |
| DEBT-009 | 9, 11 | `pin_case_knowledge` call in `cases/submission.py` and `case_guidance_pinned` audit event | Changes every case submission path; human should confirm pin happens once at processing start and null pin is acceptable when no guideline is active | non-blocking | acknowledged |
| DEBT-010 | 9, 11 | `import_corpora` appended to Compose `bootstrap` in both stacks | Runs on every start; editing a shipped corpus without bumping `version` raises conflict and may fail bootstrap. Human should confirm fail-loud is intended | non-blocking | acknowledged |
| DEBT-011 | 15-17 | 30-question retrieval recall gate | Gate scores 30/30 even with random query vectors, and 11/30 with a nonsense query; lexical ranking alone clears 0.9, so the gate never exercises vector quality. Gemini recall is report-only. Human should accept that vector retrieval is ungated | non-blocking | acknowledged |
| DEBT-012 | 16-17 | `build_embedding_provider` in bootstrap `import_corpora` | Bootstrap now receives explicit `EMBEDDING_PROVIDER`; local Compose and `.env.example` select fake, while approved Gemini requires explicit embedding selection and existing safeguards. Checker iteration 20 verified defaults and Ollama rejection | non-blocking | acknowledged |
| DEBT-013 | 15 | `test_retrieval.py` and other knowledge integration tests | Retrieval tests no longer activate test versions; recall selects shipped `g1` by identity, so these tests do not retire the active development guideline. Lifecycle and pinning tests retain intentional activation coverage. Checker iteration 20 confirmed no status change; each run still leaves new draft rows in the dev DB | non-blocking | acknowledged |
| DEBT-014 | 15 | `retrieve` always fills top-k by vector distance | Nonsense or empty queries still return 5 passages, so "no retrieval hit" (US4 template, US5 `not covered by guidelines`) cannot occur without a relevance threshold. US4/US5 design must decide | non-blocking | acknowledged |
| DEBT-015 | 15 | Migration `10_knowledge_retrieval.py` (pgvector extension, generated `search_vector`, HNSW) | Becomes frozen schema history on commit; `downgrade` drops the `vector` extension. Human should confirm before freezing. User accepted freezing as-is (guard Q1, 2026-09-28) | non-blocking | acknowledged |
| DEBT-016 | 15 | `knowledge/retrieval.py` hybrid RRF and `knowledge/case_facts.py` age/band derivation | Core retrieval logic (lexical plus vector fusion, band filters, age from date of birth) is checker-probed only; human should be able to explain fusion constants and absent-fact behavior before US4 builds on it | non-blocking | acknowledged |
| DEBT-017 | 15-19 | `GeminiEmbeddingProvider` sends `GEMINI_API_KEY` as URL query parameter | Same pattern as `providers/gemini.py:88`. Raised `ProviderError` text is generic, but the chained `httpx` exception string includes the request URL with the key if a traceback is logged. Human should decide whether to move the key to the `x-goog-api-key` header. User chose header; both providers now send `x-goog-api-key`, red-first tests in `test_providers.py` and `test_embedding_providers.py` | non-blocking | resolved |
| DEBT-018 | 15 | `KnowledgeService.import_guideline` now embeds passages inside the import transaction and backfills missing embeddings on idempotent re-import | With Gemini selected, a provider outage fails bootstrap import; human should accept fail-loud versus import-then-backfill | non-blocking | acknowledged |
| DEBT-019 | 20 | Administrator preview renders identifier, topic, age band, sum-assured band | Verified by Vitest only; no browser run of the preview screen | non-blocking | acknowledged |

## Sign-off log

| Date | Criterion / scope | Signed off by | Note |
|------|-------------------|---------------|------|
| 2026-09-28 | D1 (US1) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D1`. Guard questions 1-6 were not answered in session. DEBT-001 to DEBT-005 acknowledged as accepted, not resolved. |
| 2026-09-28 | D2 (US2) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D2`. Guard questions 1-5 were not answered in session. DEBT-006 to DEBT-010 acknowledged as accepted, not resolved. Checker verdict medium confidence; browser quickstart US2 not run. |
| 2026-09-28 | D3 (US3) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D3`. User reported guard questions answered; answers not recorded except Q1 (migration 10 accepted frozen) and Q4 (API key moved to `x-goog-api-key` header, DEBT-017 resolved). DEBT-011 to DEBT-016, DEBT-018, DEBT-019 acknowledged as accepted, not resolved. Checker iteration 20 verdict high confidence; no browser run of preview. |
