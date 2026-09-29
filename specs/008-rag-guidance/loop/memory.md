# Loop Memory

Keep short decisions and dead ends across sessions. Do not restate the
contract or copy full logs here.

<!-- - [M-001] <decision> (iteration <n>, <date>) -->

- [M-001] User approved T005 [NEEDS APPROVAL]: add
  `product-config/life-individual-term-v3.yaml`, synthetic
  `date_of_birth` in life `evaluation/cases.json` payloads, and reset dev
  data via README "Reset local demonstration" (never `down -v`).
  Given in checker session. (iteration 2, 2026-09-28)
- [M-002] Life v3 evaluation fixtures must carry synthetic `date_of_birth`
  evidence in `identity_record`; otherwise baseline marks complete cases as
  missing information. (iteration 5, 2026-09-28)
- [M-003] Corpus parsing uses closed product topic sets; alignment rejects
  every body number not declared by a threshold or band. (iteration 6,
  2026-09-28)
- [M-004] T010 stays under integration because it reads mounted knowledge
  files; checkpoint paths must match repository paths. (iteration 7,
  2026-09-28)
- [M-005] Journey contract tests must select motor v1 before draft creation;
  active product state is shared across tests. (iteration 8, 2026-09-28)
- [M-006] Repository migration 08 uses revision id `08`; US2 migration chains
  from that id and keeps knowledge pins FK-safe in test cleanup. (iteration 9,
  2026-09-28)
- [M-007] Evaluation-document recovery now has isolated unit coverage for
  present-but-corrupt files; unconditional hashing remains accepted at current
  corpus scale. (iteration 10, 2026-09-28)
- [M-008] US2 review coverage must exercise bootstrap import, every knowledge
  endpoint, public submission pinning, and activation audit metadata; pin
  audit timestamps use database defaults. (iteration 11, 2026-09-28)
- [M-009] Knowledge imports map identity races to domain conflicts; activation
  flushes sibling retirement before target activation and repeats are no-ops.
  (iteration 12, 2026-09-28)
- [M-010] Knowledge validation aligns to the named product version; activation
  alone requires that version to be active. Read previews use unlocked SQL
  pagination with administrator page controls. (iteration 13, 2026-09-28)
- [M-011] Knowledge summaries use SQL passage counts; preview pages never load
  all passage bodies for metadata. (iteration 14, 2026-09-28)
- [M-012] Retrieval uses fake embeddings for bootstrap and backfills missing
  embeddings on idempotent imports; Gemini remains opt-in. (iteration 15)
- [M-013] Bootstrap now builds the configured embedding provider; smoke and
  evaluation explicitly select fake embeddings. (iteration 16)
- [M-014] Bootstrap mirrors API Gemini embedding settings; deterministic
  Compose overrides set fake provider explicitly. (iteration 17)
- [M-015] US3 repair tests now assert absent-fact filtering, vector width, and
  cosine index operator class; nested helpers carry intent comments.
  (iteration 18)
- [M-016] Corpus embedding provider is explicit; local Compose selects fake,
  while approved Gemini selection remains opt-in and guarded. Retrieval tests
  avoid activation side effects. (iteration 19)
- [M-017] Knowledge preview renders stable key, topic, age band, and
  sum-assured band; Ollama embeddings fail explicitly until an adapter exists.
  (iteration 20)
- [M-018] Provider adapters preserve citations; pinned explainer validation
  owns filtering, audit, and complete missing-item coverage. (iteration 30)
- [M-019] Unsupported Ollama guidance disables explanation only; submission
  still runs deterministic triage. (iteration 31)
- [M-020] Evaluation guidance uses active guideline IDs and the real
  RouteExplainer through the triage graph; graph output owns route comparison.
  (iteration 32)
- [M-021] Playwright package and E2E image stay on matching 1.63.0 versions;
  generated test results stay ignored. (iteration 33)
- [M-022] Vitest 5.0.2 major bump approved by user 2026-09-29 and recorded
  under T053. (iteration 34)
- [M-023] Explainer retrieval catches only ProviderError and SQLAlchemyError,
  logs class and case id; SC-003 test requires a produced explanation.
  (iteration 35)
- [M-024] Explainer retrieval runs in a savepoint; integration tests that
  need an active guideline use the `active_guideline` fixture, which
  restores prior state. `submission.py` must stay under 400 lines.
  (iteration 36)
- [M-025] SC-003 passes a draft guideline directly to evaluation; submission
  fixture retires its temporary active version, then restores prior status by
  bound SQL because retired versions cannot be reactivated. (iteration 37)
- [M-026] API test-session teardown restores the prior life guideline, falling
  back to shipped `g1` if another test deletes the captured version.
  (iteration 37)
- [M-027] Life-guideline test teardown restores the exact pre-run status and
  `activated_at` snapshot, including no active guideline; E2E uses the
  `web_node_modules` volume. (iteration 38)
- [M-028] Destructive migration tests use a disposable database; E2E and web
  services use separate native-dependency volumes. (iteration 39)
- [M-029] User approved T057 migration `12_case_questions` on 2026-09-29.
  Q&A relevance gate: fused score > 1/61 (vector and lexical agree); case
  text reaches providers only in `GuidanceRequest.untrusted`. (iteration 40)
- [M-030] Q&A endpoints build providers through `_optional`; unusable
  provider settings store the fallback (201), never 500. Cited fallback
  text is not covered. (iteration 41)
- [M-031] Q&A injection coverage uploads a life v3 identity PDF with the
  instruction in `holder_name` and submits through normal extraction; never
  seed `extracted_fields` directly for T058. (iteration 42)
- [M-032] (superseded by M-033) US6 brief passages first came from pinned
  guideline thresholds whose `rule_code` matches a triggered rule (JSONB
  containment), not retrieval. Life v3 specialist fixtures need
  `cover_start_date`, income record, and previous policy to avoid
  needs_information. (iteration 43)
- [M-033] US6 brief passages come from `knowledge.retrieval.retrieve` with
  the triggered rule codes as the query and the case age and sum-assured
  facts as band filters, inside a savepoint. The submission service passes
  its embedding provider through `persist_case_evidence`; retrieval failure
  degrades to no passages, never a failed submission. (iteration 44,
  2026-09-29)
- [M-034] Per-case underwriter state must reset on a case switch: the
  guidance effect clears guidance, message, and suggestions, and
  `CaseReview` is keyed on the case id. (iteration 45, 2026-09-29)
- [M-035] Do not run two Compose test runs against the shared development
  database at once: a concurrent run made
  `tests/integration/test_audit_enrichment.py` and
  `tests/integration/test_audit_sanitization.py` fail on active product
  version state. Both pass alone and in the clean full run. (iteration 44,
  2026-09-29)
- [M-036] Override suggestions render only while `overriding` is true, and
  that flag is set only by the needs-information branch, so specialist
  briefs never show suggestion buttons. Stored brief citations keep only
  `version` and `passage_key`; a corrupt stored brief body degrades to no
  brief. (iteration 46, 2026-09-29)
- [M-037] User accepted the R006 consequence, 2026-09-29 ("R006 is fine"):
  a specialist case shows its passages in the brief and no suggestion
  buttons. R006 is closed by acceptance; do not reopen it on the D6
  recheck. (iteration 46, 2026-09-29)
- [M-038] Every stored guidance row must be read defensively: brief
  citations map through a filter that keeps only objects, and an
  explanation body that is not an object is treated as empty. Corrupt-row
  regressions live in
  `api/tests/integration/test_guidance_read_robustness.py`, which exists so
  `test_specialist_brief.py` stays under 400 lines. (iteration 47,
  2026-09-29)
- [M-039] US7 needs no migration: migration `09_knowledge_base.py` already
  creates `product_lines`, `topic_tags`, `suggested_tags`, `limits`, and
  `source_locator` on `knowledge_passages`. The planned
  `13_regulation_passages.py` is withdrawn; a migration test locks the
  columns instead. (iteration 48, 2026-09-29)
- [M-040] The regulation manifest must accept an unquoted YAML date; the
  shipped `manifest.yaml` uses date scalars, not strings, and typing the
  field as `str` makes every real import answer 422 `manifest_invalid`.
  (iteration 48, 2026-09-29)
- [M-041] Regulation uploads are verified by streaming to a `.part` file
  while hashing, then `os.replace` onto the manifest's declared file name;
  a refusal commits its own `regulation_file_rejected` audit before the
  request fails, because a raising handler would otherwise lose it.
  (iteration 48, 2026-09-29)
- [M-042] Regulation activation is a shared, product-less scope, so it
  runs through `RegulationService.activate` dispatched by scope in
  `knowledge/router.py`; `pin_case_knowledge` pins the active regulation
  version for every product. The pinning test reads the active regulation
  instead of asserting null. (iteration 48, 2026-09-29)
- [M-043] A regulation clause body is capped at 6000 characters and its
  key is `<manifest id>#<heading number>` with a
  `<id>#page:<n>` source locator; a repeated heading number stays body
  text so keys never collide. (iteration 48, 2026-09-29)
- [M-044] A regulation version is identified by the manifest entries
  plus every loaded clause (key, product lines, title, body). Identity
  must cover everything the draft stores, or a later upload or a
  manifest edit silently returns the older draft while the report
  claims the file loaded. (iteration 49, 2026-09-29)
- [M-045] A tag-only accept must keep stored limits: the request omits
  `limits` and the service only overwrites them when the key is
  present. (iteration 49, 2026-09-29)
- [M-046] Route isolation is only meaningful when both comparison runs
  have guidance enabled, because `evaluate_cases(guidance_enabled=
  False)` never opens the knowledge tables. Manifest file names must
  be plain names; an unreadable listed file is reported, never fatal.
  (iteration 49, 2026-09-29)
