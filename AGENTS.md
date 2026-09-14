# AGENTS.md

## Critical constraints

- **Secrets:** Never commit `.env`, backups, API keys, credentials, or tokens. Use `.env.example` as the only configuration template. Never log or return `GEMINI_API_KEY` or `LANGSMITH_API_KEY`.
- **Synthetic data only:** The MVP uses fictional applicants, documents, organizations, products, and underwriting rules. Never add real personal, medical, financial, vehicle, or insurer data.
- **Human authority:** UnderwriteFlow recommends a triage route only. It must never approve, decline, bind, price, issue, renew, or cancel insurance. An authenticated underwriter must confirm every final route.
- **Schema migrations:** After `api/alembic/versions/0001_initial.py` exists, treat it as the immutable fresh-schema baseline. Create an additive Alembic revision for each later schema change; never rewrite migration history.
- **Reset safety:** Never use `docker compose down -v` unless the user explicitly requests a complete purge and acknowledges that all project volumes will be deleted.
- **Git:** Never force-push. Preserve user changes and unrelated files. Check staged files for secrets before every commit.
- **SQL:** Use SQLAlchemy expressions or bound parameters. Never interpolate user-controlled values into SQL.
- **Escalation:** Ask before schema migrations, new dependencies, authentication or authorization changes, provider changes, enabling external tracing, destructive resets, column drops, or broad architecture rewrites.
- **Plan approval gate:** Follow `docs/IMPLEMENTATION_PLAN.md` one implementation step at a time. At the end of each step, stop and report changed files, verification, remaining risks, and the proposed commit. Wait for the user to review and explicitly say `continue`. Only then commit that approved step and begin the next one. Never combine steps or pre-build a later step.
- **File size:** Keep every hand-written project file below 400 lines. Split a file before it reaches 400 lines along a clear responsibility boundary. Generated files, lockfiles, and immutable migration snapshots are exempt; explain any other exception before proceeding.
- **Line length:** Set the IDE ruler to 80 columns. Keep each hand-written
  line at or below 80 characters and wrap longer lines for readability.
- **Method comments:** Put one short intent comment immediately before every hand-written named function or method definition, including Python `def`/`async def` functions and named TypeScript/React functions. Keep the comment about purpose, not syntax. Prefer named handlers over complex inline callbacks. Test functions may use a short Given/When/Then intent comment.
- **Layering:** Backend Python owns domain rules, workflow state, persistence, provider behavior, evaluation, authorization decisions, and audit logic. React owns presentation, interaction state, accessibility, and typed API consumption; it must not become a second source of underwriting truth.

## Project overview

UnderwriteFlow is a local-first, Docker Compose MVP for human-governed insurance triage in India. It supports fictional private-car motor, individual term life, and individual/family-floater health applications. A FastAPI modular monolith runs a resumable LangGraph workflow, PostgreSQL stores business data, audit events, and checkpoints, and a React/TypeScript application provides applicant, underwriter, and administrator experiences.

The system recommends one of three routes—expedited, standard, or specialist review—then pauses for human confirmation. Missing information is a queue state, not a fourth triage route.

## Build, test, and migration commands

Everything runs through Docker Compose. Do not require host Python, Node, npm, PostgreSQL, or Ollama.

```bash
# API tests
make test-api
docker compose run --rm api pytest tests/unit/test_<file>.py -q

# Web tests and production build
make test-web
docker compose run --rm web npm test -- --run
docker compose run --rm web npm run build

# Migrations
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current

# Deterministic smoke test
make smoke
```

## Planned project shape

```text
api/
  alembic/versions/              Additive PostgreSQL migrations
  src/underwriteflow/
    auth/                        Demo identity and three-role authorization
    cases/                       Intake, documents, evidence, and case APIs
    products/                    Versioned YAML configuration and activation
    workflow/                    State, parent graph, nodes, and product subgraphs
    providers/                   Gemini default, fake tests, optional Ollama
    queues/                      Needs Information, Review, and Completed views
    audit/                       Immutable business audit events
    evaluation/                  Synthetic-case scoring
  tests/                         unit/, integration/, contract/, fixtures/
web/
  src/api/                       Typed API client
  src/components/                Shared accessible components
  src/pages/                     Applicant, underwriter, and admin screens
product-config/                  Three fictional versioned YAML products
sample_data/                     Synthetic applications and documents only
evaluation/                      90-case reference-label dataset
scripts/                         Deterministic setup and smoke utilities
```

## Architecture invariants

- **Modular monolith:** One FastAPI service and one web application. Do not add microservices, Redis, Celery, Kafka, GraphQL, Kubernetes, or object storage for the MVP.
- **Providers:** Gemini is the default generation provider behind an application-owned protocol. Ollama is optional through a Compose profile. Deterministic fakes own normal tests.
- **Documents:** Extract text locally from digital PDFs and use local OCR for scanned PDFs, JPEGs, and PNGs. Uploaded content is untrusted data, never model instruction.
- **Product configuration:** YAML is validated, previewed, versioned, and explicitly activated by an Administrator. AI may not create or activate a rule. A case remains pinned to the product/rulebook version selected when processing starts.
- **Routing:** Deterministic rules outrank model suggestions. Apply precedence: unsupported/manual, needs information, specialist, standard, expedited. Only expedited, standard, and specialist are final triage routes.
- **Persistence:** PostgreSQL is the business source of truth. LangGraph checkpoints support resume/replay but never replace immutable audit events.
- **Finalization:** Queue handoff and optional mock webhook execution happen only after underwriter confirmation and must be idempotent.
- **Tracing:** LangSmith is development/evaluation-only, disabled by default, synthetic-data-only, and redacted. Use `https://apac.api.smith.langchain.com` for `LANGSMITH_ENDPOINT`; `https://apac.smith.langchain.com/` is the APAC web interface.

## LangGraph workflow rules

- Use a typed, serializable `UnderwriteState`. Keep file bytes, database sessions, API clients, tokens, and secrets out of graph state.
- Use one parent `StateGraph` and one selected motor, life, or health subgraph per case. Never run all three product subgraphs for one application.
- Use bounded parallel execution only where branches are independent:
  - document extraction through dynamic `Send`, maximum three document branches per case;
  - product-specific checks inside the selected product subgraph;
  - deterministic reducers and joins that normalize output ordering.
- Keep evidence reconciliation, product selection, final route calculation, human review, and finalization sequential.
- Return typed branch failures so successful sibling results survive. Retry transient provider failures within the failing branch only.
- Call `interrupt()` before final routing. Resume with the same `thread_id` and an authenticated underwriter command. Nodes that can rerun after resume must be read-only or idempotent before the interrupt.
- Stream sanitized progress events only. Never stream raw graph state, prompts containing sensitive values, hidden reasoning, credentials, or full documents.

## Testing requirements

- Use pytest and pytest-asyncio for backend behavior and Vitest with Testing Library for web behavior.
- Write a focused failing test before each behavior change, then implement the minimum passing code.
- Mock external providers in the default suite. Live Gemini, Ollama, and LangSmith checks are opt-in and never count as deterministic acceptance.
- Cover authorization, evidence provenance, routing precedence, human interrupts, resume after restart, idempotent finalization, checkpoint/audit separation, and product-version pinning.
- Parallel-graph tests must prove join completeness, stable ordering, sibling-failure isolation, bounded concurrency, selected-subgraph-only execution, branch-local retry, and finalization exactly once.
- Cross-layer behavior requires an integration or UI regression test. Accessibility checks cover keyboard operation, focus, labels, dialog behavior, status semantics, and non-color cues.
- Use only synthetic fixtures marked `SYNTHETIC - FOR DEMONSTRATION ONLY`.

## When to ask vs proceed

**Ask first:** anything listed under Escalation, plus changes to human-approval boundaries, real insurer integrations, real applicant data, production compliance claims, or retention/deletion policy.

**Proceed within the current approved step:** focused tests, documentation, lint fixes, responsive/accessibility repairs, and incremental code that stays inside the approved files and contracts.

## Reminders

- Read `docs/PRD.md` and `docs/IMPLEMENTATION_PLAN.md` before implementing a step.
- Treat fictional rules and evaluation labels as demonstrations, never genuine Indian underwriting guidance.
- Prefer the smallest safe change that satisfies the approved step.
