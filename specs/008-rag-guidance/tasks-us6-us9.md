# Tasks (continued): RAG-Grounded Triage Guidance

Continuation of [tasks.md](tasks.md). The rules, shorthand (`API`,
`WEB`), and checkpoint gate in `tasks.md` apply here unchanged.

## Phase 8: User Story 6 - Specialist Brief (P6)

**Goal**: Deterministic brief and up to three suggested citations.
**Independent test**: hazardous-occupation fixture shows brief and
suggestions.

- [ ] T064 [US6] Write failing tests in
  `tests/unit/test_specialist_brief.py`: brief lists evidence with source
  locators, triggered rule codes, and passages for those codes; no brief
  for other routes; at most three suggested citations.
- [ ] T065 [US6] Implement `build_brief` in
  `src/underwriteflow/knowledge/brief.py`.
- [ ] T066 [US6] Write failing test in
  `tests/integration/test_specialist_brief.py`: the fixture stores a
  `specialist_brief` row and `GET /reviews/{id}/guidance` returns it with
  `suggested_citations`.
- [ ] T067 [US6] Store the brief in `knowledge/case_guidance.py` and
  return it from `knowledge/guidance_router.py`.
- [ ] T068 [US6] Write failing Vitest tests in
  `web/src/specialist-brief.test.tsx` and
  `web/src/review-actions.test.tsx`: brief sections render; accepting a
  suggestion adds its citation to the override reason; ignoring is
  allowed.
- [ ] T069 [US6] Implement `web/src/specialist-brief.tsx`; add
  suggestions to `web/src/review-actions.tsx`.

**Checkpoint US6**: `API pytest tests/unit/test_specialist_brief.py
tests/integration/test_specialist_brief.py -q`; `make test-api`;
`make test-web`; `make smoke`; quickstart US6.

## Phase 9: User Story 7 - Informational Regulatory Corpus (P7)

**Goal**: Checksum-verified IRDAI clauses, badged, side by side, never in
routing. **Independent test**: altered file rejected; routes identical.

- [ ] T070 [US7] Extend `tests/integration/test_knowledge_migration.py`:
  `knowledge_passages` gains `product_lines`, `topic_tags`,
  `suggested_tags`, `limits`, `source_locator`.
- [ ] T071 [US7] [NEEDS APPROVAL] Create
  `alembic/versions/13_regulation_passages.py`; map the columns.
- [ ] T072 [US7] Write failing tests in
  `tests/unit/test_regulation_manifest.py` using synthetic PDFs from
  `tests/fixtures/synthetic_pdf.py` and a temp manifest: checksum
  mismatch rejected, unlisted file ignored, missing file and `.doc`
  reported, clauses split at numbered headings with `<id>#page:<n>`,
  label `PUBLIC REGULATION - INFORMATIONAL`.
- [ ] T073 [US7] Implement `src/underwriteflow/knowledge/regulation.py`
  (manifest read, SHA-256, `pypdf` text, clause split).
- [ ] T074 [US7] Write failing tests in
  `tests/integration/test_regulation_import.py`: import makes a draft,
  audits `regulation_file_rejected`, fills `suggested_tags`; tag accept
  works only on drafts (409 otherwise) and audits
  `regulation_tags_accepted`; activation pins new cases.
- [ ] T075 [US7] Implement `src/underwriteflow/knowledge/
  regulation_service.py` and `src/underwriteflow/knowledge/
  regulation_router.py` (`POST /knowledge/regulation/import`, `PUT
  .../tags`); include in `app.py`.
- [ ] T076 [US7] Write test in
  `tests/integration/test_regulation_route_isolation.py`: routes for all
  evaluation fixtures are identical with and without an active regulation
  version; `workflow/` and `products/rules.py` never import
  `underwriteflow.knowledge.regulation`.
- [ ] T077 [US7] Write failing contract test in
  `tests/contract/test_guidance_api.py` for `GET /reviews/{id}/guidance/
  passages/{key}`: at most three related clauses, each labelled.
- [ ] T078 [US7] Implement the endpoint in `knowledge/guidance_router.py`
  using meaning-only retrieval on the pinned regulation version.
- [ ] T079 [US7] Write failing Vitest tests in
  `web/src/regulation-side.test.tsx` and
  `web/src/knowledge-tags.test.tsx`.
- [ ] T080 [US7] Implement `web/src/regulation-side.tsx` (mounted from
  `guidance-panel.tsx`) and `web/src/knowledge-tags.tsx` (mounted from
  `knowledge-admin.tsx`).

**Checkpoint US7**: `API alembic upgrade head`; `API pytest
tests/unit/test_regulation_manifest.py
tests/integration/test_regulation_import.py
tests/integration/test_regulation_route_isolation.py -q`;
`make test-api`; `make test-web`; `make smoke`;
`git check-ignore data/regulatory/manifest.yaml`; quickstart US7.

## Phase 10: User Story 8 - Rule Conformance Preview (P8)

**Goal**: Deterministic flags and change impact; never blocks.
**Independent test**: flagged draft still activates.

- [ ] T081 [US8] Write failing tests in `tests/unit/test_conformance.py`:
  flag when an accepted clause limit is violated; related clauses via
  accepted tags only; suggested tags never match; diff lists added,
  removed, changed thresholds and documents.
- [ ] T082 [US8] Implement `src/underwriteflow/knowledge/conformance.py`.
- [ ] T083 [US8] Write failing tests in
  `tests/integration/test_conformance_preview.py`: `POST
  /products/preview` includes `conformance` and `change_impact`;
  activation with flags succeeds and audits `conformance_flags_recorded`.
- [ ] T084 [US8] Merge the keys with one call in
  `src/underwriteflow/products/router.py` preview and one audit call in
  `activate`.
- [ ] T085 [US8] Write failing Vitest tests in
  `web/src/conformance-preview.test.tsx`: flags, diff, label text,
  activation button stays enabled.
- [ ] T086 [US8] Implement `web/src/conformance-preview.tsx`; mount in
  `web/src/product-import.tsx` preview.

**Checkpoint US8**: `API pytest tests/unit/test_conformance.py
tests/integration/test_conformance_preview.py -q`; `make test-api`;
`make test-web`; `make smoke`; quickstart US8.

## Phase 11: User Story 9 - Motor and Health Guidelines (P9)

**Goal**: Same alignment and recall for motor and health.

- [ ] T087 [US9] Write failing parametrized test in
  `tests/unit/test_product_corpus_alignment.py` for motor and health
  corpora against their newest product-config versions.
- [ ] T088 [US9] Write `knowledge-config/motor-private-car/g1.yaml` and
  `knowledge-config/health-individual-family-floater/g1.yaml`.
- [ ] T089 [US9] Parametrize `tests/integration/test_retrieval_recall.py`
  over all three products (fails until data exists).
- [ ] T090 [US9] Write `evaluation/retrieval/motor-private-car.yaml` and
  `evaluation/retrieval/health-individual-family-floater.yaml`.

**Checkpoint US9**: `API pytest tests/unit/test_product_corpus_alignment.py
tests/integration/test_retrieval_recall.py -q`; `make test-api`;
`make smoke`; `API python /app/scripts/evaluate_retrieval.py` for motor
and health with their `g1` active and `GENERATION_PROVIDER=fake`.

## Phase 12: Polish

- [ ] T091 Update `README.md` (knowledge admin, regulatory import,
  `GEMINI_EMBEDDING_MODEL`) and `docs/ARCHITECTURE.md` (retrieval flow).
- [ ] T092 Run `make test-api`, `make test-web`, `WEB npm run build`,
  `make smoke`, `make evaluate-e2e`; confirm no hand-written file is 400
  lines or more and no line exceeds 80 columns.
