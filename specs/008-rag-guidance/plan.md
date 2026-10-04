# Implementation Plan: RAG-Grounded Triage Guidance

**Branch**: `rag-implementation` | **Date**: 2026-09-28 (amended
2026-10-03, US10) |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-rag-guidance/spec.md`

## Summary

Add fictional, versioned guideline corpora and an informational IRDAI
corpus to the existing FastAPI/LangGraph monolith. Passages live in
PostgreSQL with a pgvector embedding and a generated full-text column;
retrieval fuses both with Reciprocal Rank Fusion, filtered to the case's
pinned version and bands. A new read-only triage node writes a cited route
explanation before the human interrupt. Underwriters get stored Q&A and a
deterministic specialist brief. Administrators load, preview, and activate
knowledge versions like product rules, and see deterministic conformance
flags in the rules preview. Routing code and route precedence are not
touched.

**Amendment 2026-10-03 (US10)**: Gemini embeddings hit HTTP 429 and fail
bootstrap. Add an opt-in local `OllamaEmbeddingProvider` using
`embeddinggemma` (768 dimensions, no migration) and re-embed a version
automatically when the recorded embedding model differs (research R14).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript 5.9 / React 19 (web)

**Primary Dependencies**: FastAPI 0.116, LangGraph 0.6.7, SQLAlchemy 2.0
async + asyncpg, httpx, pypdf, PyYAML (existing). No new Python
package (research R1, R2). One new npm dev dependency, `@playwright/test`,
approved 2026-09-28 for the SC-008 screen timing check (research R13).

**Storage**: PostgreSQL 16 in `pgvector/pgvector:pg16` (already the image);
`vector` extension enabled by migration; `tsvector` generated column.

**Testing**: pytest + pytest-asyncio; Vitest + Testing Library;
Playwright in its own Compose container (`e2e` profile). Fake
generation and fake embedding providers in the default suite. Ollama
embedding tests use `httpx.MockTransport`; live Ollama is opt-in.

**Target Platform**: Docker Compose on a developer machine.

**Project Type**: Web application (`api/` + `web/`).

**Performance Goals**: explanation visible within 3 s of opening a paused
case (stored, no generation on open); Q&A answer within 10 s with Gemini;
retrieval query under 300 ms for 500 passages.

**Constraints**: files below 400 lines, lines at most 80 characters;
graph state stays serializable; no text bodies in audit details;
regulatory text never committed.

**Scale/Scope**: 3 products, about 40 sections each; regulation about
1,000 clauses; 30 evaluation questions per product.

## Constitution Check

*Gate before Phase 0 and re-checked after Phase 1.*

- **I. Human authority**: Pass. The explanation node sits before
  `human_review`; the route is computed earlier and never read back (R7).
  Q&A and briefs have no write path to routes.
- **II. Synthetic data only**: Pass. Corpora carry the synthetic label;
  regulatory files stay git-ignored, load only by checksum, and are
  excluded from routing (R6, US7 isolation test).
- **III. Deterministic rules outrank models**: Pass.
  `recommend_triage_route` is unchanged; conformance flags (R10) and the
  alignment check (R5) are deterministic.
- **IV. Additive migrations**: Pass, needs approval. New revisions start
  at `09_knowledge_base.py`; 01-08 are untouched.
- **V. Test-first, gated**: Pass. Each story writes failing tests first;
  quickstart lists unit, integration, web, and e2e gates. Live model
  checks are opt-in only.
- **VI. Small readable code**: Pass. New code lives in new modules.
  `persistence/models.py` (395 lines), `cases/router.py` (392), and
  `reviews/router.py` (336) are not extended; pins use a separate table.
- **VII. Backend owns truth**: Pass. Retrieval, citations, alignment,
  conformance, and age computation are backend only.
- **Escalation**: Needs approval for the schema migration (R1), the
  provider changes (R2, Gemini embeddings; R14, Ollama embeddings), and
  the product-config change (R11). `@playwright/test` is approved (R13).
  No RBAC change.

Post-design re-check: unchanged. No violation needs Complexity Tracking.

## Approvals needed before the story that uses them

1. **US1**: new `life-individual-term-v3.yaml` with `date_of_birth` and
   the `not_future` date validation; development data reset per README.
2. **US2**: Alembic `09_knowledge_base.py` (tables, indexes).
3. **US3**: Alembic `10_knowledge_retrieval.py` (`vector` extension,
   embedding and full-text columns); Gemini embedding endpoint and
   `GEMINI_EMBEDDING_MODEL` setting.
4. **US4**: Alembic `11_case_guidance.py`; Gemini guidance adapter.
   `@playwright/test` dev dependency: approved 2026-09-28.
5. **US5**: Alembic `12_case_questions.py`.
6. **US7**: no migration. Migration `09_knowledge_base.py` already created
   `product_lines`, `topic_tags`, `suggested_tags`, `limits`, and
   `source_locator` on `knowledge_passages`, so the planned
   `13_regulation_passages.py` was withdrawn (2026-09-29).
7. **US10**: Ollama embedding provider and `OLLAMA_EMBEDDING_MODEL`
   setting (R14). No migration, no new dependency.

## Story delivery map

One story at a time; each ends with the report-and-`continue` gate.

- **US1**: `knowledge/corpus.py` (parse, validate) and
  `knowledge/alignment.py`; `knowledge-config/life-individual-term/g1.yaml`;
  life v3 config; date `not_future` in `cases/validation.py`. Web: none.
  Tests first: alignment pass and fail, number scan, stable ids, future
  date of birth.
- **US2**: migration 09; `persistence/knowledge_models.py`;
  `knowledge/repository.py`; `knowledge/service.py` (import, activate,
  retire, pin); `knowledge/router.py`; pin at submission. Web: admin
  knowledge page. Tests first: one active per product, admin only, pin
  stability, audit.
- **US3**: `providers/embedding.py` (protocol, fake, Gemini);
  `persistence/vector.py`; `knowledge/retrieval.py`;
  `evaluation/retrieval/life-individual-term.yaml`. Web: none. Tests
  first: recall at least 0.9, version and band filters, exact-code
  ranking.
- **US4**: `providers/guidance.py`; `workflow/explain.py` node and one
  triage edge; `knowledge/case_guidance.py`; `GET /reviews/{id}/guidance`
  in `knowledge/guidance_router.py`. Web: explanation panel. Tests first:
  route unchanged, stable after restart, fallback states.
- **US5**: `knowledge/questions.py` and endpoints; injection fixture.
  Web: Q&A panel with history. Tests first: citation or fallback,
  injection, audit, 403.
- **US6**: `knowledge/brief.py`; suggested citations. Web: brief panel
  and override-dialog suggestions.
- **US7**: `knowledge/regulation.py` (manifest, checksum, clause split);
  `regulation_upload.py`, `regulation_service.py`, `regulation_router.py`
  (verified upload, tags, shared activation), `regulation_view.py` (related
  clauses). Web: side-by-side view, tag review.
  Tests first: checksum, skip, route isolation.
- **US8**: `knowledge/conformance.py`; preview keys; activation audit.
  Web: preview flags and diff. Tests first: flags never block.
- **US9**: motor and health corpora and evaluation files. Tests:
  alignment and recall per product.
- **US10**: `providers/embedding.py` (`OllamaEmbeddingProvider`, builder
  branch); `config.py` (`ollama_embedding_model`);
  `knowledge/embedding_writer.py` (record `embedding_model`, shared
  `needs_embeddings` predicate); `knowledge/service.py` and
  `knowledge/regulation_service.py` call the predicate; `.env.example`,
  `compose.yaml` (pass `OLLAMA_EMBEDDING_MODEL` to `bootstrap` and `api`),
  README provider section. Web: none. Tests first: request shape and
  `/api/embed` URL, 768-width and count validation, transient 429/503
  mapping, host allowlist refusal, redaction, builder selection,
  re-embed on model change and no re-embed when unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/008-rag-guidance/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rest-api.md
│   └── knowledge-corpus.md
├── tasks.md            # US1-US5
├── tasks-us6-us9.md    # US6-US9 and polish
└── tasks-us10.md       # US10 Ollama embeddings
```

### Source Code (repository root)

```text
api/
  alembic/versions/09_knowledge_base.py      # later stories add 10+
  src/underwriteflow/
    knowledge/                               # new module
      corpus.py          alignment.py        repository.py
      service.py         router.py           retrieval.py
      case_guidance.py   guidance_router.py  questions.py
      brief.py           regulation.py       conformance.py
      import_corpora.py                      # bootstrap import
    persistence/knowledge_models.py          # new tables, shared Base
    persistence/vector.py                    # vector column type
    providers/embedding.py                   # protocol, fake, Gemini,
                                             # Ollama (US10)
    providers/guidance.py                    # explain/answer, fake, Gemini
    workflow/explain.py                      # explain_route node
    workflow/triage.py                       # one node + edge added
    cases/validation.py                      # date not_future
  tests/unit/  tests/integration/  tests/contract/
knowledge-config/<product_code>/<version>.yaml
evaluation/retrieval/<product_code>.yaml
product-config/life-individual-term-v3.yaml
web/src/
  api-knowledge.ts          knowledge-admin.tsx
  guidance-panel.tsx        guidance-questions.tsx
  specialist-brief.tsx      conformance-preview.tsx
  ../e2e/guidance-timing.spec.ts   # Playwright, SC-008
web/playwright.config.ts
```

**Structure Decision**: Keep the modular monolith. All new backend code
lives in one `knowledge/` package plus two provider modules and one
workflow node. Existing large files receive only wiring lines (router
include, graph edge, preview keys). Compose mounts `knowledge-config/`
read-only into `bootstrap` and `api`, like `product-config/`.

## Risks

- Fake-embedder recall depends on shared vocabulary between questions and
  sections (R12); live recall is reported, not gated.
- Gemini embedding quotas can slow corpus loads; loads batch at most 100
  passages per call and retry transient failures.
- US10: with `EMBEDDING_PROVIDER=ollama`, bootstrap fails until the
  `ollama` profile is up and `embeddinggemma` is pulled; quickstart
  documents the order. Bootstrap re-embeds configured guideline corpora;
  Administrators re-import API-managed versions and the regulation manifest
  after a provider switch.
- US10: no query/document task prefixes for `embeddinggemma`; live recall
  is reported, not gated (R14 ceiling).
- The explanation node adds provider latency before the interrupt; a
  timeout falls back to the template so submission never blocks.
- `products/router.py` is 314 lines; conformance keys are computed in
  `knowledge/conformance.py` and merged with a single call.

## Complexity Tracking

No constitution violations.

## US11 amendment: Common provider model configuration (2026-10-04)

Specification: [later stories](spec-later-stories.md), US11. Contract:
[provider configuration](contracts/provider-configuration.md).

Use existing Python 3.12 and Pydantic Settings; no dependencies or schema
changes. Centralize model defaults and resolution in config.py. Replace
provider-specific model fields with two optional common model overrides
and resolved properties. Update extraction, guidance, and embedding
builders. Share provider environment entries in Compose with an anchor;
forward model overrides without repeating model defaults. Update the env
example and README. Keep fake identity, provider safeguards, capabilities,
metadata, re-embedding, routes, and human confirmation unchanged.

Research R15 selects immediate removal of legacy names, as requested for
active development. No compatibility layer or private .env edits.

Constitution re-check: I-III and VII unchanged; IV needs no migration;
V requires ordered unit/integration/end-to-end gates; VI requires all
changed files below 400 lines and at most 80 columns. The oversized spec
was split into a linked continuation before adding US11. No new approval
requirement is introduced; the requested configuration rename is in scope.

Delivery: [tasks-us11.md](tasks-us11.md), T107 onward, one story only.
Stop after verification and report; commit/push require continue.
