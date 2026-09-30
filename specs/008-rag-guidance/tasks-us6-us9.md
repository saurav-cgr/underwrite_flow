# Tasks (continued): RAG-Grounded Triage Guidance

Continuation of [tasks.md](tasks.md). The rules, shorthand (`API`,
`WEB`), and checkpoint gate in `tasks.md` apply here unchanged.

## Phase 8: User Story 6 - Specialist Brief (P6)

**Goal**: Deterministic brief and up to three suggested citations.
**Independent test**: hazardous-occupation fixture shows brief and
suggestions.

- [x] T064 [US6] Write failing tests in
  `tests/unit/test_specialist_brief.py`: brief lists evidence with source
  locators, triggered rule codes, and passages for those codes; no brief
  for other routes; at most three suggested citations.
- [x] T065 [US6] Implement `build_brief` in
  `src/underwriteflow/knowledge/brief.py`.
- [x] T066 [US6] Write failing test in
  `tests/integration/test_specialist_brief.py`: the fixture stores a
  `specialist_brief` row and `GET /reviews/{id}/guidance` returns it with
  `suggested_citations`.
- [x] T067 [US6] Store the brief in `knowledge/case_guidance.py` and
  return it from `knowledge/guidance_router.py`.
- [x] T068 [US6] Write failing Vitest tests in
  `web/src/specialist-brief.test.tsx` and
  `web/src/review-actions.test.tsx`: brief sections render; accepting a
  suggestion adds its citation to the override reason; ignoring is
  allowed.
- [x] T069 [US6] Implement `web/src/specialist-brief.tsx`; add
  suggestions to `web/src/review-actions.tsx`.

**Checkpoint US6**: `API pytest tests/unit/test_specialist_brief.py
tests/integration/test_specialist_brief.py -q`; `make test-api`;
`make test-web`; `make smoke`; quickstart US6.

## Phase 9: User Story 7 - Informational Regulatory Corpus (P7)

**Goal**: Checksum-verified IRDAI clauses, badged, side by side, never in
routing. **Independent test**: altered file rejected; routes identical.

**Open questions (resolved with the user 2026-09-29)**:

- Q1 Scanned PDF: `general_mc_2024.pdf` is image-only on all 38 pages
  (0 characters). Decision: reuse the existing local OCR path
  (`pdftoppm` plus `tesseract`) for pages whose `pypdf` text is empty;
  a page or document whose OCR fails is reported, not fatal.
- Q2 `.doc` file: keep `insurance_act_1938.doc` report-only; no hand
  conversion.
- Q3 Mount: add `./data/regulatory:/app/data/regulatory:ro` to the
  `api` and `bootstrap` services in `compose.yaml`. Approved.
- Q4 Upload and verify: approved for this story. `POST
  /knowledge/regulation/import` takes an optional `file` part, accepts
  it only when its SHA-256 matches a manifest entry, writes the verified
  bytes to that entry's declared file name under `data/regulatory/`,
  and rejects otherwise with 422 and a `regulation_file_rejected` audit.
  The limit is 100 MB per file. The manifest is never edited. FR-014,
  FR-015, US7 scenario 2a, and the REST contract are amended. Q3 still
  applies to folder import.
- Note: `policyholders_mc_2024.pdf` is 91 MB for 109 pages but has text;
  expect slow import, not failure.

- [x] T070 [US7] Extend `tests/integration/test_knowledge_migration.py`:
  `knowledge_passages` gains `product_lines`, `topic_tags`,
  `suggested_tags`, `limits`, `source_locator`.
- [x] T071 [US7] [NEEDS APPROVAL] Create
  `alembic/versions/13_regulation_passages.py`; map the columns.
  **Not required**: migration `09_knowledge_base.py` already created all
  five columns and the ORM maps them, so US7 adds no schema. Approved
  migration is therefore withdrawn; `test_regulation_passage_columns_present`
  locks the columns instead.
- [x] T072 [US7] Write failing tests in
  `tests/unit/test_regulation_manifest.py` using synthetic PDFs from
  `tests/fixtures/synthetic_pdf.py` and a temp manifest: checksum
  mismatch rejected, unlisted file ignored, missing file and `.doc`
  reported, clauses split at numbered headings with `<id>#page:<n>`,
  label `PUBLIC REGULATION - INFORMATIONAL`.
- [x] T073 [US7] Implement `src/underwriteflow/knowledge/regulation.py`
  (manifest read, SHA-256, `pypdf` text, clause split).
- [x] T074 [US7] Write failing tests in
  `tests/integration/test_regulation_import.py`: folder import makes a
  draft, audits `regulation_file_rejected`, fills `suggested_tags`; an
  approved upload stores the declared file name and an unlisted or
  altered upload is rejected 422 with nothing written; tag accept works
  only on drafts (409 otherwise) and audits `regulation_tags_accepted`;
  activation pins new cases.
- [x] T075 [US7] Implement `src/underwriteflow/knowledge/
  regulation_service.py`, `regulation_upload.py`, and `src/
  underwriteflow/knowledge/regulation_router.py` (`POST
  /knowledge/regulation/import` with an optional 100 MB `file` part, `PUT
  .../tags`); write verified upload bytes to the manifest's declared file
  name under `data/regulatory/`, audit `regulation_file_rejected`, and
  include both routers in `app.py`.
- [x] T076 [US7] Write test in
  `tests/integration/test_regulation_route_isolation.py`: routes for all
  evaluation fixtures are identical with and without an active regulation
  version; `workflow/` and `products/rules.py` never import
  `underwriteflow.knowledge.regulation`.
- [x] T077 [US7] Write failing contract test in
  `tests/contract/test_guidance_api.py` for `GET /reviews/{id}/guidance/
  passages/{key}`: at most three related clauses, each labelled.
- [x] T078 [US7] Implement the endpoint in `knowledge/guidance_router.py`
  using meaning-only retrieval on the pinned regulation version.
- [x] T079 [US7] Write failing Vitest tests in
  `web/src/regulation-side.test.tsx` and
  `web/src/knowledge-tags.test.tsx`.
- [x] T080 [US7] Implement `web/src/regulation-side.tsx` (mounted from
  `guidance-panel.tsx`) and `web/src/knowledge-tags.tsx` (mounted from
  `knowledge-admin.tsx`): the administrator screen offers regulation
  import (with an optional file upload) and tag acceptance on drafts.

**Checkpoint US7**: `API alembic upgrade head`; `API pytest
tests/unit/test_regulation_manifest.py
tests/integration/test_regulation_import.py
tests/integration/test_regulation_route_isolation.py -q`;
`make test-api`; `make test-web`; `make smoke`;
`git check-ignore data/regulatory/manifest.yaml`; quickstart US7.

## Phase 10: User Story 8 - Rule Conformance Preview (P8)

**Goal**: Deterministic flags and change impact; never blocks.
**Independent test**: flagged draft still activates.

- [x] T081 [US8] Write failing tests in `tests/unit/test_conformance.py`:
  flag when an accepted clause limit is violated; related clauses via
  accepted tags only; suggested tags never match; diff lists added,
  removed, changed thresholds and documents.
- [x] T082 [US8] Implement `src/underwriteflow/knowledge/conformance.py`.
- [x] T083 [US8] Write failing tests in
  `tests/integration/test_conformance_preview.py`: `POST
  /products/preview` includes `conformance` and `change_impact`;
  activation with flags succeeds and audits `conformance_flags_recorded`.
- [x] T084 [US8] Merge the keys with one call in
  `src/underwriteflow/products/router.py` preview and one audit call in
  `activate`.
- [x] T085 [US8] Write failing Vitest tests in
  `web/src/conformance-preview.test.tsx`: flags, diff, label text,
  activation button stays enabled.
- [x] T086 [US8] Implement `web/src/conformance-preview.tsx`; mount in
  `web/src/product-import.tsx` preview.

**Checkpoint US8**: `API pytest tests/unit/test_conformance.py
tests/integration/test_conformance_preview.py -q`; `make test-api`;
`make test-web`; `make smoke`; quickstart US8.

## Phase 11: User Story 9 - Motor and Health Guidelines (P9)

**Goal**: Same alignment and recall for motor and health.

- [x] T087 [US9] Write failing parametrized test in
  `tests/unit/test_product_corpus_alignment.py` for motor and health
  corpora against their newest product-config versions.
- [x] T088 [US9] Write `knowledge-config/motor-private-car/g1.yaml` and
  `knowledge-config/health-individual-family-floater/g1.yaml`.
- [x] T089 [US9] Parametrize `tests/integration/test_retrieval_recall.py`
  over all three products (fails until data exists).
- [x] T090 [US9] Write `evaluation/retrieval/motor-private-car.yaml` and
  `evaluation/retrieval/health-individual-family-floater.yaml`.

**Checkpoint US9**: `API pytest tests/unit/test_product_corpus_alignment.py
tests/integration/test_retrieval_recall.py -q`; `make test-api`;
`make smoke`; `API python /app/scripts/evaluate_retrieval.py` for motor
and health with their `g1` active and `GENERATION_PROVIDER=fake`.

## Phase 12: Polish

- [x] T091 Update `README.md` (knowledge admin, regulatory import,
  `GEMINI_EMBEDDING_MODEL`) and `docs/ARCHITECTURE.md` (retrieval flow).
- [x] T092 Run `make test-api`, `make test-web`, `WEB npm run build`,
  `make smoke`, `make evaluate-e2e`; confirm no hand-written file is 400
  lines or more and no line exceeds 80 columns.
