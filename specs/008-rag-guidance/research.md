# Research: RAG-Grounded Triage Guidance

Phase 0 decisions. Each entry states the decision, why, and what was
rejected. Items marked **Approval** need explicit user sign-off under the
constitution's Escalation rule before the story that uses them starts.

## R1. Vector storage

- **Decision**: Use the `vector` extension already shipped in the
  `pgvector/pgvector:pg16` image. Enable it with
  `CREATE EXTENSION IF NOT EXISTS vector` in a new additive Alembic
  revision (US3). Map the column with a small SQLAlchemy `UserDefinedType` in
  `persistence/vector.py` instead of adding the `pgvector` Python package.
- **Rationale**: No new service, no new container, and no new Python
  dependency. PostgreSQL stays the single source of truth. The
  architecture decision in `docs/PRD_FINALIZED_DECISIONS.md` already names
  pgvector as the path for later retrieval.
- **Alternatives**: `pgvector` Python package (small, but a new dependency
  for about 20 lines of type code); Chroma/FAISS/Qdrant (new service or
  in-process index outside PostgreSQL, rejected by the monolith rule).
- **Approval**: schema migration (`10_knowledge_retrieval.py`).

## R2. Embedding provider

- **Decision**: Add an `EmbeddingProvider` protocol beside the existing
  `ExtractionProvider`. Gemini adapter calls `embedContent` /
  `batchEmbedContents` on the already-approved host
  `generativelanguage.googleapis.com` with `gemini-embedding-001` and
  `outputDimensionality: 768`. A deterministic `FakeEmbeddingProvider`
  hashes normalized word unigrams and bigrams into 768 dimensions and
  L2-normalizes. Ollama is not extended in this feature. *Amended
  2026-10-03 by R14: Ollama embeddings become an opt-in local option.*
- **Rationale**: Reuses `httpx`, the host allowlist, redaction, timeout, and
  retry settings. The fake gives stable, content-sensitive vectors, so
  default tests and SC-002 run without network access.
- **Alternatives**: local `sentence-transformers` (large image, new heavy
  dependency); Ollama embeddings (optional profile only, cannot be the
  default).
- **Approval**: provider change (new Gemini endpoint and model setting
  `GEMINI_EMBEDDING_MODEL`).

## R3. Hybrid retrieval and ranking

- **Decision**: Two SQL queries on the pinned version, fused in Python with
  Reciprocal Rank Fusion (`k = 60`):
  1. meaning: cosine distance `embedding <=> :query_vector`, top 20;
  2. exact wording: `ts_rank_cd(search_vector, websearch_to_tsquery(
     'english', :query))`, top 20, where `search_vector` is a generated
     `tsvector` column over identifier, topic, and body.
  Filters applied in both queries: `version_id`, product, and band
  overlap. Ties sort by passage key, so ordering is stable.
- **Rationale**: Built-in PostgreSQL features only. RRF needs no score
  calibration. Exact rule codes such as `high_cover_standard` rank through
  full-text search even when embeddings miss them (US3 scenario 2).
- **Alternatives**: vector-only (misses exact codes); a cross-encoder
  re-ranker (new model and dependency, no measured need).

## R4. Band filtering and age

- **Decision**: Each passage stores inclusive numeric ranges
  `age_min/age_max` and `sum_assured_min/sum_assured_max`; `NULL` means
  unbounded ("all"). A case filters with
  `(age_min IS NULL OR age_min <= :age) AND (age_max IS NULL OR
  age_max >= :age)`, and the same for sum assured. Age is whole years
  between `date_of_birth` and the submission date, computed in backend
  code. A case value that is absent skips that filter.
- **Rationale**: Ranges compare with plain SQL and bound parameters.
  Skipping an absent value keeps motor and health, which have no age or
  sum-assured field, working with the same query.
- **Alternatives**: label strings such as `"18-40"` (needs parsing, easy to
  mistype).

## R5. Guideline corpus format and alignment check

- **Decision**: One YAML file per product and version under
  `knowledge-config/<product_code>/<version>.yaml`, mounted read-only like
  `product-config/`. Each section declares `id`, `topic`, band ranges,
  `body`, and a `thresholds` list of `{rule_code, field, operator, value}`.
  The alignment check is a pure function:
  1. every declared threshold must match a condition in the named product
     version (routing rule or conditional document), same field, operator,
     and value;
  2. every number in `body` must equal a declared threshold value or an
     allowed band bound, so an undeclared number also fails.
- **Rationale**: Structured thresholds make the check exact. The
  number scan catches prose drift that a structured list alone would miss.
- **Alternatives**: Markdown with front matter (thresholds harder to
  validate); model-based comparison (non-deterministic).

## R6. Regulatory ingestion

- **Decision**: A command reads `data/regulatory/manifest.yaml`, verifies
  each file's SHA-256 against the manifest, extracts PDF text with the
  existing `pypdf`, and splits clauses at numbered headings with one
  regular expression. Unsupported formats (for example the `.doc` Act) and
  missing files are skipped and reported. Clauses load into a draft
  regulation version; nothing is written to git.
- **Rationale**: Existing dependency only. Checksum first means an altered
  file never reaches the database (SC-009).
- **Alternatives**: OCR for all files (slow, unnecessary for digital
  PDFs); `.doc` conversion tooling (new dependency, one file).

## R7. Route explanation generation

- **Decision**: New triage node `explain_route` runs after
  `recommend_triage_route` and before `human_review`. It reads the pinned
  version through an injected read-only retriever, calls
  `GuidanceProvider.explain`, validates the JSON (`text` at most 120 words,
  `citations` a subset of the retrieved passage keys), and returns the
  result into graph state. On provider failure it returns the fixed
  template; on retrieval failure it returns status `unavailable`.
  `persist_case_evidence` stores the result once per case and review
  cycle.
- **Rationale**: Graph state stays serializable. The node runs before the
  interrupt, so resume replays only `human_review` and the stored text is
  reused (SC-005). Route is computed before this node and never read back
  from it (FR-009).
- **Alternatives**: generating on page open (unstable text, extra latency).

## R8. Underwriter Q&A

- **Decision**: Synchronous endpoint guarded by the existing
  `require_underwriter()` dependency. Retrieval runs first. If no passage
  passes the minimum fused score, the answer is exactly "not covered by
  guidelines" with no model call. Otherwise the provider receives the
  question, retrieved passages, and case facts in a JSON user message
  labelled untrusted; the system instruction forbids following content
  instructions. An answer whose citations are empty or outside the
  retrieved set becomes the fallback phrase. Every exchange is stored and
  audited; audit details keep ids and hashes, never question text.
- **Rationale**: `require_underwriter()` already refuses administrators and
  applicants, so no RBAC change is needed. Q&A has no write path to routes.
- **Alternatives**: new `guidance:ask` permission (authorization change,
  not needed).

## R9. Specialist brief and suggested citations

- **Decision**: Deterministic assembly, no model call: evidence with
  source locators, triggered rule codes, and the top passages retrieved
  for those rule codes. The override dialog shows the top three passage
  citations for the triggered rules.
- **Rationale**: All content already exists; generation adds risk and
  cost without new information.

## R10. Conformance preview

- **Decision**: Regulatory clauses carry administrator-accepted
  `topic_tags` and optional structured `limits`
  `{field, operator, value}`. Retrieval may suggest tags in the
  regulation preview; only accepted tags are stored. The rules preview
  flags a rule when an accepted clause limit on the same field is violated
  by the rule's threshold, and lists topic-matched clauses as related.
  The change-impact summary is a structural diff of routing rules and
  conditional documents against the active version.
- **Rationale**: Matches clarification Q3; fully deterministic and
  testable.

## R11. Date of birth

- **Decision**: New `product-config/life-individual-term-v3.yaml` adds a
  required `date_of_birth` date field with `validation: {not_future: true}`.
  `validate_field_value` gains ISO-date parsing and the `not_future`
  check. No routing rule uses age. Development data is reset with a
  targeted database reset, never `docker compose down -v`.
- **Rationale**: Case payloads are JSONB and forms render from
  configuration, so no business-table migration is needed for the field.

## R12. Evaluation

- **Decision**: `evaluation/retrieval/life-individual-term.yaml` holds
  30 synthetic questions with expected section ids. A pytest integration
  test asserts top-five recall of at least 0.9 with the fake embedder.
  `scripts/evaluate_retrieval.py` runs the same set against the running
  stack: with the fake provider it is the end-to-end gate; with Gemini
  it reports live recall and never gates. US9 adds motor and health.
- **Rationale**: Deterministic gate per constitution Principle V.
- **Risk**: The fake embedder is lexical. Questions must share vocabulary
  with their sections; paraphrase-heavy questions are measured only in
  the opt-in live run.

## R13. Screen timing check

- **Decision**: `@playwright/test` (exact pin) runs
  `web/e2e/guidance-timing.spec.ts` in the official Playwright container,
  Compose profile `e2e`, via `make test-e2e`. Approved by the user on
  2026-09-28.
- **Rationale**: SC-008 is measured from click to visible text in a real
  browser. The container keeps the Docker-only rule and needs no host
  browser or Node.
- **Alternatives**: manual DevTools timing (not repeatable); Vitest with
  jsdom (no real rendering or network timing).

## R14. Local Ollama embeddings (added 2026-10-03)

- **Problem**: Gemini `batchEmbedContents` returns HTTP 429 under the
  project quota. `write_embeddings` has no retry, and `bootstrap` runs
  `import_corpora` on every start, so one 429 fails bootstrap and the API
  never starts.
- **Decision**: Add `OllamaEmbeddingProvider` in `providers/embedding.py`,
  selected by `EMBEDDING_PROVIDER=ollama`. It calls
  `POST {OLLAMA_BASE_URL}/api/embed` with `{"model", "input": [texts]}`
  and reads `embeddings`. New setting `OLLAMA_EMBEDDING_MODEL`, default
  `embeddinggemma`. Fake stays the default and the test provider; Gemini
  stays available.
- **Rationale**: `embeddinggemma` outputs 768 dimensions natively, so the
  `vector(768)` column and HNSW index stay unchanged: no migration. Text
  stays on the machine, so there is no quota. Reuses `httpx`, the
  existing `ollama` Compose profile and volume, `OLLAMA_BASE_URL`, the
  host allowlist (`ollama` is already listed), timeout, and the
  transient/permanent error split. No new package.
- **Safeguards kept**: base URL host must be in `PROVIDER_ALLOWED_HOSTS`;
  inputs pass through `redact_personal_data` like Gemini; vectors are
  rejected unless count and 768 width match; errors never echo payloads.
- **Vector-space switch**: vectors from fake, Gemini, and Ollama are not
  comparable. `write_embeddings` records
  `embedding_model` (`"<provider>:<model>"`) in the version's `source`
  JSON; guideline and regulation imports re-embed when any embedding is
  `NULL` or the recorded value differs from the current provider. Bootstrap
  automatically re-imports configured guideline YAMLs only. After a switch,
  Administrators must re-import API-managed guideline versions and the
  regulation manifest through their existing import endpoints. No schema
  change: `source` already holds non-text provenance.
- **Alternatives**:
  1. Retry with backoff on Gemini 429 — still quota-bound, slows every
     bootstrap; can be added later, independent of this change.
  2. Smaller Gemini batches — does not lift a per-minute quota.
  3. `sentence-transformers` in the API image — new heavy dependency.
  4. Manual reset (`SET embedding = NULL`) on switch — easy to forget,
     silent wrong results; rejected for the recorded-model check.
- **Known ceiling**: `embeddinggemma` recommends task prefixes
  (`task: search result | query:` / `title: none | text:`). The
  `EmbeddingProvider.embed(texts)` contract has no query/document flag, so
  prefixes are not sent. Add a `kind` argument if live recall falls short.
- **Startup dependency**: with `EMBEDDING_PROVIDER=ollama`, bootstrap needs
  the `ollama` service running and the model pulled. Not added as a hard
  `depends_on` because the profile is optional; quickstart documents the
  order.
- **Approval**: provider change (Escalation). Requested by the user on
  2026-10-03; confirm before implementation.
