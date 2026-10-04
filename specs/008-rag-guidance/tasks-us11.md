# Tasks: Common Provider Model Configuration (US11)

Continuation of [tasks.md](tasks.md) and [tasks-us10.md](tasks-us10.md).
Input: [plan.md](plan.md), [spec-later-stories.md](spec-later-stories.md)
US11, research R15, data-model runtime settings, and
[configuration contract](contracts/provider-configuration.md).

Paths below are repository-relative. Tests are required by constitution V.
Use Docker Compose only. Keep files below 400 lines, lines at most 80
columns, and intent comments before every named function. Preserve private
.env contents and earlier completed task checkboxes. No commit or push
until the user says continue after the story report.

## Phase 15: Setup

- [x] T107 Review US11 prerequisites in
  `specs/008-rag-guidance/plan.md` and `docs/PRD.md`, alongside
  `docs/IMPLEMENTATION_PLAN.md`; confirm the US10 verification/story gate
  is satisfied and record the starting worktree state. Do not overwrite
  user changes or implement another story.

## Phase 16: Foundational

Reuse existing Settings, provider adapters, Compose services, and tests.
No new infrastructure, migration, dependency, or authorization work.

## Phase 17: User Story 11 - Common Model Configuration (P11)

**Goal**: common generation/embedding model overrides with centralized
defaults, independent provider selection, and immediate legacy removal.

**Independent test**: default, blank, custom, mixed-provider, and legacy
removal checks pass; builders use resolved names; Compose forwards the
same provider settings to bootstrap/API; model tags and re-import behavior
are preserved; deterministic smoke passes without remote provider calls.

### Unit tests first

- [x] T108 [US11] Create `api/tests/unit/test_provider_model_config.py`.
  Isolate process environment and dotenv loading. Cover all contract
  defaults, explicit overrides, and the exact rule "Unset, empty, and
  whitespace-only mean automatic defaults." Cover surrounding whitespace,
  independent Gemini/Ollama selections, backend embedding-provider
  fallback, fake resolved models as None, and old environment names having
  no selection effect. Assert four legacy Settings fields are absent.
  Run focused tests and record the expected failures before T112.
- [x] T109 [US11] Add failing builder tests in
  `api/tests/unit/test_provider_model_builders.py`: extraction and Gemini
  guidance receive the same common generation override; selected defaults
  reach Gemini/Ollama extraction. Preserve Ollama guidance returning None,
  fake behavior, host refusal, and no-training acknowledgement refusal.
  Build adapters without live requests; record failures before T113.
- [x] T110 [US11] Update
  `api/tests/unit/test_embedding_providers.py` to use the new common
  override instead of ollama_embedding_model. Cover Gemini/Ollama defaults,
  custom models, mixed selections, and fake identity ignoring overrides.
  Keep mocked transport, redaction, width, transient error, and host tests.
  Record the focused failures before T114; split by responsibility if
  adding tests would reach 400 lines.
- [x] T111 [US11] Add configuration-to-persistence regression coverage in
  `api/tests/integration/test_provider_model_configuration.py`. Build the
  Ollama embedder through Settings with EMBEDDING_MODEL, intercept requests
  using httpx.MockTransport, and return deterministic 768-wide vectors.
  Import isolated synthetic guideline/regulation versions; assert resolved
  tags, one embedding call for unchanged re-import, and replacement after
  the common model changes. Reuse synthetic regulation fixtures; no real
  files or live requests. Author before implementation; execute at T119.

### Backend implementation

- [x] T112 [US11] Update `api/src/underwriteflow/config.py`: define named
  model default constants; add generation_model and embedding_model,
  each "str or None with default None"; trim overrides and normalize
  blanks to None. Add resolved_generation_model and
  resolved_embedding_model properties per contract, returning None for
  fake. Preserve effective embedding-provider fallback. Remove four old
  fields outright without aliases; make T108 pass.
- [x] T113 [US11] Update `api/src/underwriteflow/providers/factory.py`
  and `api/src/underwriteflow/providers/guidance.py` to consume the
  resolved common generation model. Keep fake branches, Ollama guidance
  behavior, provider guards, and metadata unchanged. Make T109 pass.
- [x] T114 [US11] Update `api/src/underwriteflow/providers/embedding.py`
  to consume the resolved common embedding model for the independently
  selected provider. Preserve fake identity, host checks, redaction,
  retries/errors, and 768-wide vectors. Make T110 pass without changing
  `api/src/underwriteflow/knowledge/embedding_writer.py` tag semantics.
- [x] T115 [US11] Run all unit tests under `api/tests/unit/` through
  Compose with fake generation/embeddings; require a successful exit and
  record results in `specs/008-rag-guidance/us11-report.md`.
  Stop on failure; only passing unit tests unlock T116-T119.

### Compose contract and documentation

- [x] T116 [US11] Update
  `api/tests/contract/test_environment_compose.py` with failing assertions
  that API/bootstrap share common model entries, old model entries are
  absent, and model-name defaults are not repeated. Preserve environment
  mode, production, evaluation, bootstrap, and fake-provider checks.
  Record expected failures before T117; use targeted rendered Compose
  checks from quickstart without printing any credentials.
- [x] T117 [US11] Update `compose.yaml` with a shared provider environment
  anchor used by API/bootstrap. Forward GENERATION_MODEL and EMBEDDING_MODEL
  with empty-string defaults; remove all four old model entries. Keep
  other settings' effective values, per-service settings, embedding fake
  default, and optional profiles unchanged. Confirm evaluation, production,
  and smoke configurations still select their intended providers.
- [x] T118 [US11] Update `.env.example` and `README.md` to show blank
  common overrides and explain automatic defaults and mixed providers.
  Remove old model names from current operator instructions; describe
  private override renaming without reading or modifying .env. Update
  `specs/008-rag-guidance/quickstart.md` US10 examples to the current common
  names, preserving US10 historical decisions and completed tasks.
- [x] T119 [US11] Run `api/tests/contract/test_environment_compose.py`
  and `api/tests/integration/` through Compose with fake providers; include
  T111 and existing guideline/regulation re-embedding tests. Require all
  checks to run without unexpected skips and pass. Record results in
  `specs/008-rag-guidance/us11-report.md`; stop on failure.
- [x] T120 [US11] Follow `specs/008-rag-guidance/quickstart.md` US11:
  run `make smoke` only after T119 passes. Record startup/import and
  human-confirmed flow results in `specs/008-rag-guidance/us11-report.md`.
  Require no live Gemini, Ollama, or LangSmith calls for acceptance.

## Phase 18: Polish and delivery

- [x] T121 Inspect the US11 diff, including `api/src/underwriteflow/`
  and `compose.yaml`, for remaining legacy runtime references, duplicate
  model defaults, secrets, file limits, line limits, and intent comments.
  Keep historical spec/task references; exclude unrelated cleanup.
  Record findings in `specs/008-rag-guidance/us11-report.md`.
- [x] T122 Complete `specs/008-rag-guidance/us11-report.md` with changed
  files, unit/integration/end-to-end evidence, remaining risks, local env
  rename requirement, and proposed commit `refactor: unify provider model
  configuration`. Stop and await continue before committing or pushing.

## Dependencies and parallel opportunities

US10 checkpoint and its continue gate -> T107 -> T108-T111 -> T112-T114
-> T115 -> T116 -> T117 -> T118 -> T119 -> T120 -> T121 -> T122.

Each failing unit test must precede its paired implementation. Integration
tests are authored early but executed only after the unit gate. The Compose
contract fails before its implementation, after the unit gate.

No parallel execution: the active feature tasks require sequential work.
T108-T111 touch separate files, but their execution remains sequential.
Parallel example: none under the current project constraints.

## Implementation strategy

Deliver US11 as one minimal story and one proposed commit. All 16 tasks
are required; there is no partial MVP that omits Compose or verification.
No frontend change, new provider capability, schema migration, dependency,
tracing activation, destructive reset, or compatibility alias is included.
