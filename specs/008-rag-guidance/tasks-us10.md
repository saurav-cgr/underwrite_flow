# Tasks (continued): RAG-Grounded Triage Guidance - US10

Continuation of [tasks.md](tasks.md) and
[tasks-us6-us9.md](tasks-us6-us9.md). The rules, shorthand (`API` =
`docker compose run --rm api`, `WEB`), and checkpoint gate in `tasks.md`
apply unchanged. Design: [plan.md](plan.md) US10, [research.md](research.md)
R14, `source.embedding_model` in [data-model.md](data-model.md).

**Approval gate**: US10 is a provider change (Escalation). Do not start
T093 until the user approves R14.

**Draft code**: an interrupted session left uncommitted edits in
`api/src/underwriteflow/providers/embedding.py` and
`api/tests/unit/test_embedding_providers.py`. T093-T096 reconcile them;
do not trust them as finished.

## Phase 13: User Story 10 - Local Ollama Embeddings (P10)

**Goal**: `EMBEDDING_PROVIDER=ollama` embeds configured corpora locally with
`embeddinggemma` (768 dimensions), so bootstrap no longer depends on the
Gemini quota. Imports re-embed a version after provider switches.

**Independent test**: with mocked transports only, the Ollama provider
sends the documented request and validates replies; importing a corpus
with a different `embedding_model` re-embeds it; the default suite and
`make smoke` still use the fake provider.

### Tests first (must fail before implementation)

- [x] T093 [US10] In `api/tests/unit/test_embedding_providers.py`, keep or
  write a failing test that `OllamaEmbeddingProvider("http://ollama:11434/",
  "embeddinggemma", transport=httpx.MockTransport(...))` posts to exactly
  `http://ollama:11434/api/embed` with JSON
  `{"model": "embeddinggemma", "input": [...]}` in input order, returns
  one vector per text, and raises `ProviderError` matching
  `invalid data` when the count differs or any vector is not 768 wide.
  Empty input returns `[]` without a request.
- [x] T094 [P] [US10] In the same file, add failing tests: statuses
  408, 429, 500, 503 raise `TransientProviderError`; status 400 raises
  `ProviderError`; inputs pass through `redact_personal_data` with
  `pii_redaction_terms` (reuse the Gemini redaction assertions: the name,
  `email@example.test`, and `9876543210` never reach the request body).
- [x] T095 [US10] In `test_embedding_providers.py::
  test_embedding_provider_builder`, replace the old "Ollama is not
  supported" assertion with: `Settings(_env_file=None,
  embedding_provider="ollama")` builds `OllamaEmbeddingProvider` with
  `model == "embeddinggemma"`; `ollama_embedding_model="custom"` reaches
  `provider.model`; `ollama_base_url="http://elsewhere.test:11434"`
  raises `ProviderError` matching `host`; Gemini without the no-training
  acknowledgement still raises `no-training`.
- [x] T096 [US10] In `api/tests/integration/test_knowledge_embeddings.py`,
  add failing tests using two in-test fake providers that differ only in
  `model` (e.g. subclass `FakeEmbeddingProvider` with `model =
  "fake-b"`): (a) importing the same guideline corpus twice with one
  provider calls `embed` once and sets `source["embedding_model"]` to
  `"fake:fake-embedding-768"`; (b) importing again with the second
  provider re-embeds every passage and sets
  `source["embedding_model"]` to `"fake:fake-b"`; (c) a version whose
  `source` lacks `embedding_model` is re-embedded on import. Repeat (b)
  for a regulation version through `RegulationService` (follow the
  fixtures in `tests/integration/test_regulation_import.py`).

### Implementation

- [x] T097 [US10] Add `ollama_embedding_model: str = "embeddinggemma"` to
  `Settings` in `api/src/underwriteflow/config.py`, after `ollama_model`.
- [x] T098 [US10] Finish `OllamaEmbeddingProvider` in
  `api/src/underwriteflow/providers/embedding.py`: `name = "ollama"`;
  `__init__(base_url, model, timeout_seconds=30,
  pii_redaction_terms=(), transport=None)` strips the trailing `/`;
  `embed` redacts each text, posts `{"model", "input"}` to
  `{base_url}/api/embed`, reads `embeddings`, maps timeout/network and
  transient statuses to `TransientProviderError` and everything else to
  `ProviderError` with messages that never include payloads, and
  validates count and 768 width. Update the module docstring to name
  Ollama. Keep the file below 400 lines and lines at most 80 columns.
- [x] T099 [US10] In `build_embedding_provider` (same file), the `ollama`
  branch checks `urlparse(settings.ollama_base_url).hostname` (lowercased)
  is in `provider_allowed_hosts`, else raises
  `ProviderError("Provider host is not approved")`, then returns
  `OllamaEmbeddingProvider(settings.ollama_base_url,
  settings.ollama_embedding_model, timeout_seconds=
  settings.provider_timeout_seconds, pii_redaction_terms=
  settings.pii_redaction_terms)`. Import `urlparse` from
  `urllib.parse`. Gemini branch behavior is unchanged. Run T093-T095:
  green.
- [x] T100 [US10] In `api/src/underwriteflow/knowledge/embedding_writer.py`
  add `embedding_tag(provider) -> str` returning
  `f"{provider.name}:{provider.model}"` and
  `needs_embeddings(version, passages, provider=None) -> bool` (resolves
  `provider or build_embedding_provider(get_settings())`; true when any
  `passage.embedding is None` or
  `(version.source or {}).get("embedding_model") != embedding_tag(...)`).
  `write_embeddings` loads the `KnowledgeVersion`, and after writing
  vectors sets `version.source = {**(version.source or {}),
  "embedding_model": tag}` (new dict, so SQLAlchemy sees the change).
  `source` must stay text-free: only the tag string is added.
- [x] T101 [US10] In `api/src/underwriteflow/knowledge/service.py`
  replace `if any(passage.embedding is None for passage in passages):`
  in `import_guideline` with `if needs_embeddings(existing, passages,
  self.embedding_provider):`. The file is 399 lines: the change must be
  net zero (swap the import line too); if it would reach 400, stop and
  report instead of splitting under this story.
- [x] T102 [US10] In `api/src/underwriteflow/knowledge/regulation_service.py`
  make `_needs_embeddings` call `needs_embeddings(version, passages,
  self.embedding_provider)` (load the version via the repository or pass
  `existing` from the caller). Run T096: green.
- [x] T103 [P] [US10] Configuration: add `OLLAMA_EMBEDDING_MODEL=
  embeddinggemma` under the Ollama block in `.env.example` and update the
  `EMBEDDING_PROVIDER` comment to `fake | gemini | ollama`; in
  `compose.yaml` pass `OLLAMA_EMBEDDING_MODEL:
  ${OLLAMA_EMBEDDING_MODEL:-embeddinggemma}` to both `bootstrap` and
  `api` beside `OLLAMA_MODEL`. Do not add `ollama` to `depends_on`.
- [x] T104 [P] [US10] `README.md` provider section: how to select
  `EMBEDDING_PROVIDER=ollama`, the
  `docker compose --profile ollama up -d ollama` and
  `docker compose exec ollama ollama pull embeddinggemma` order, that
  bootstrap re-embeds configured guideline corpora and Administrators
  re-import other versions after a switch, and that Ollama recall is
  reported, not gated. Each command in its own `bash` block.

**Checkpoint US10**: `API pytest tests/unit/test_embedding_providers.py
tests/integration/test_knowledge_embeddings.py
tests/integration/test_regulation_import.py -q`; `make test-api`;
`make smoke` (fake provider); then the opt-in quickstart US10 end-to-end
with local Ollama and its recall numbers recorded in the story report.
Confirm `knowledge/service.py` is still below 400 lines.

## Phase 14: Polish (US10)

- [x] T105 Run `make test-api`, `make smoke`; confirm no hand-written
  file is 400 lines or more and no line exceeds 80 columns; check staged
  files for secrets; then stop at the story gate and report.
- [x] T106 [US10] Give each fake-provider recall test import a unique
  version identity so it cannot re-embed development `g1` vectors.

## Dependencies

- T093-T096 (tests) before T097-T102. T094 is parallel with T093 after
  the import line exists. T097 before T099. T100 before T101 and T102.
- T103 and T104 touch only config and docs; parallel with T100-T102.
- US10 depends on US3 (embedding protocol, `write_embeddings`) and US7
  (`RegulationService`); both are complete.

## Parallel example

```text
After T099 is green:
  T100 -> T101, T102   (embedding_writer, then both import paths)
  T103                 (.env.example, compose.yaml)
  T104                 (README.md)
```

## Implementation strategy

Single story, single commit after the `continue` gate. MVP is T093-T099
plus T103: Ollama embeddings selectable and bootstrap free of the Gemini
quota. T100-T102 are required in the same story because without them a
provider switch silently mixes vector spaces.
