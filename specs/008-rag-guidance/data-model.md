# Data Model: RAG-Grounded Triage Guidance

All new tables arrive in additive Alembic revisions after
`08_case_journey.py`. No existing column is dropped or rewritten. Column
types are PostgreSQL; `vector(768)` comes from the pgvector extension
(research R1).

## knowledge_versions

One validated set of passages for one product, or one set of regulatory
clauses.

| Column | Type | Rules |
|--------|------|-------|
| id | uuid PK | |
| scope | varchar(32) | `guideline` or `regulation` |
| product_id | uuid FK null | required for `guideline`; null for regulation |
| version | varchar(100) | unique per (scope, product_id) |
| content_type | varchar(32) | `synthetic_guidance` or `public_regulation` |
| status | varchar(32) | `draft`, `active`, `retired` |
| content_hash | varchar(128) | SHA-256 of normalized source |
| source | jsonb | file names, manifest ids, checksums; never text |
| validation | jsonb | last validation report (counts and issue codes) |
| created_at | timestamptz | |
| activated_at | timestamptz null | |
| activated_by_user_id | uuid FK users null | |

Indexes:

- `uq_knowledge_versions_identity` unique
  `(scope, coalesce(product_id, '00000000-...'), version)`.
- `uq_knowledge_versions_one_active` unique
  `(scope, coalesce(product_id, '00000000-...'))` where `status = 'active'`.

State transitions: `draft` to `active` (validation passed, administrator
action); `active` to `retired` (another version activated or explicit
retire). A retired version never returns to active; load a new version.

## knowledge_passages

A guideline section or a regulatory clause inside one version.

| Column | Type | Rules |
|--------|------|-------|
| id | uuid PK | |
| version_id | uuid FK | knowledge_versions; no cascade delete |
| passage_key | varchar(200) | section id or clause ref; unique per version |
| product_code | varchar(100) null | null for regulation |
| product_lines | jsonb | list, for regulation (`life`, `motor`, `health`) |
| topic | varchar(100) | from a closed topic list per product |
| topic_tags | jsonb | regulation: administrator-accepted tags only |
| suggested_tags | jsonb | regulation: suggestions only, never matched |
| limits | jsonb | regulation: accepted `{field, operator, value}` list |
| thresholds | jsonb | guideline: `{rule_code, field, operator, value}` |
| age_min, age_max | integer null | inclusive; null means unbounded |
| sum_assured_min, _max | numeric null | inclusive; null means unbounded |
| title | varchar(300) | |
| body | text | display text; label is prepended in the UI |
| label | varchar(64) | synthetic or informational label, verbatim |
| source_locator | varchar(500) null | regulation: `<manifest id>#page:<n>` |
| search_vector | tsvector | generated: English over key, topic, title, body |
| embedding | vector(768) | written at load time |

Indexes: unique `(version_id, passage_key)`; GIN on `search_vector`;
HNSW `vector_cosine_ops` on `embedding`; btree on `(version_id, topic)`.

Validation at load (guideline):

- `id` matches `^[a-z]+(-[a-z0-9]+)+$` and is unique in the file.
- `topic` is in the product's topic list.
- `age_min <= age_max` and `sum_assured_min <= sum_assured_max` when both
  are set.
- Every threshold passes the alignment check (research R5) against the
  product version named in the file.
- `body` is 1 to 1,200 characters.

## case_knowledge_pins

One row per case, written once at submission. A separate table keeps
`cases` and `persistence/models.py` (395 lines) untouched.

| Column | Type | Rules |
|--------|------|-------|
| case_id | uuid PK, FK cases | |
| guideline_version_id | uuid FK knowledge_versions null | never updated |
| regulation_version_id | uuid FK knowledge_versions null | never updated |
| created_at | timestamptz | |

No row, or a null column, means no active version existed when
processing started (edge case). Resubmission keeps the first pin.

## case_guidance

Stored route explanation or specialist brief for one review cycle.

| Column | Type | Rules |
|--------|------|-------|
| id | uuid PK | |
| case_id | uuid FK cases | |
| review_cycle | integer | |
| kind | varchar(32) | `route_explanation` or `specialist_brief` |
| status | varchar(32) | `generated`, `template`, `unavailable` |
| body | jsonb | `{text, missing_items}` or `{evidence, rules, passages}` |
| citations | jsonb | list of `{version_id, version, passage_key}` |
| provider | varchar(50) null | |
| model | varchar(200) null | |
| request_hash | varchar(64) null | |
| created_at | timestamptz | |

Unique `(case_id, review_cycle, kind)`. Insert-once; a second insert for
the same key is ignored, which keeps pause and resume idempotent.

## case_questions

| Column | Type | Rules |
|--------|------|-------|
| id | uuid PK | |
| case_id | uuid FK cases | |
| asked_by_user_id | uuid FK users | underwriter only |
| question | text | 1 to 1,000 characters |
| answer | text | model answer or exactly `not covered by guidelines` |
| covered | boolean | false when the fallback phrase is returned |
| citations | jsonb | at least one entry when `covered` is true |
| provider | varchar(50) null | |
| model | varchar(200) null | |
| created_at | timestamptz | |

Every underwriter can list all rows for a case (clarification Q5).

## Audit events (existing `audit_events` table)

| Event type | Details (sanitized; no text bodies) |
|------------|-------------------------------------|
| `knowledge_version_loaded` | scope, product, version, hash, count |
| `knowledge_version_activated` | scope, product, version, previous |
| `knowledge_version_retired` | scope, product_code, version |
| `regulation_tags_accepted` | version, passage_key, tag count, limit count |
| `regulation_file_rejected` | manifest id, reason code |
| `case_guidance_pinned` | case_id, guideline and regulation version ids |
| `route_explanation_stored` | case_id, status, citation keys, request_hash |
| `citation_dropped` | case_id, output kind, passage_key |
| `case_question_answered` | case_id, question id, covered, citation keys |
| `conformance_flags_recorded` | product_code, version, flag count, rule codes |

## Serializable graph state additions (`TriageState`)

- `guidance_context: dict` with `case_id`, `product_code`, `age`,
  `sum_assured`, `guideline_version_id`, `regulation_version_id`. Ids and
  numbers only; no text, no sessions.
- `route_explanation: dict` with `status`, `text`, `missing_items`,
  `citations`, `provider`, `model`, `request_hash`.

## Configuration files (source of truth for loads)

- `knowledge-config/<product_code>/<version>.yaml`: guideline corpus.
  Format in [contracts/knowledge-corpus.md](contracts/knowledge-corpus.md).
- `evaluation/retrieval/<product_code>.yaml`: labelled questions with
  `id`, `question`, `case` (optional `age`, `sum_assured`), and
  `expected` passage keys.
- `product-config/life-individual-term-v3.yaml`: adds `date_of_birth`.
