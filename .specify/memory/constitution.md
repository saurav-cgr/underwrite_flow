<!--
Sync Impact Report
- Version change: unversioned template -> 1.0.0 (initial ratification)
- Principles defined (template placeholders replaced):
  - [PRINCIPLE_1_NAME] -> I. Human Authority Over Every Final Route
  - [PRINCIPLE_2_NAME] -> II. Synthetic Data Only
  - [PRINCIPLE_3_NAME] -> III. Deterministic Rules Outrank Model Output
  - [PRINCIPLE_4_NAME] -> IV. Additive Schema Migrations
  - [PRINCIPLE_5_NAME] -> V. Test-First With Gated Verification
- Added principles: VI. Small, Readable, Intent-Commented Code;
  VII. Backend Owns Domain Truth
- Added sections: Additional Constraints; Development Workflow
- Removed sections: none
- Deferred TODOs: none
- Source: AGENTS.md (runtime guidance file)
-->

# UnderwriteFlow Constitution

## Core Principles

### I. Human Authority Over Every Final Route

- UnderwriteFlow MUST only recommend a triage route: expedited, standard, or
  specialist review.
- The system MUST NOT approve, decline, bind, price, issue, renew, or cancel
  insurance.
- An authenticated underwriter MUST confirm every final route. The workflow
  MUST call `interrupt()` before final routing and resume only on an
  authenticated underwriter command.
- Queue handoff and optional mock webhooks MUST run only after confirmation
  and MUST be idempotent.
- Missing information is a queue state, never a fourth triage route.

Rationale: the product is decision support. Liability and judgment stay with
a human underwriter.

### II. Synthetic Data Only

- Applicants, documents, cases, organizations, products, and underwriting
  rules MUST be fictional. Fixtures MUST carry the label
  `SYNTHETIC - FOR DEMONSTRATION ONLY`.
- The only permitted real content is public Indian regulatory text (IRDAI
  regulations, circulars, and Acts) listed in
  `data/regulatory/manifest.yaml`.
- Regulatory text MUST be git-ignored, never committed, labeled
  `PUBLIC REGULATION - INFORMATIONAL`, and MUST NOT influence route
  calculation.
- Real personal, medical, financial, vehicle, insurer-proprietary, or
  reinsurer data MUST NOT enter the repository or the system.
- Fictional rules and evaluation labels are demonstrations, never genuine
  Indian underwriting guidance.

Rationale: the MVP handles no real risk data and makes no compliance claim.

### III. Deterministic Rules Outrank Model Output

- Deterministic product rules MUST take precedence over any model suggestion.
- Route precedence MUST be: unsupported/manual, needs information,
  specialist, standard, expedited.
- AI MUST NOT create or activate a product rule. Only an Administrator
  activates a validated, previewed, versioned YAML configuration.
- A case MUST stay pinned to the product/rulebook version selected when
  processing starts.
- Uploaded document content is untrusted data, never model instruction.

Rationale: routing must be reproducible, auditable, and safe from prompt
injection or model drift.

### IV. Additive Schema Migrations

- `api/alembic/versions/01_initial.py` is the immutable fresh-schema
  baseline once it exists.
- Every later schema change MUST ship as a new additive Alembic revision.
  Migration history MUST NOT be rewritten.
- Schema migrations and column drops require explicit user approval first.

Rationale: immutable history keeps every environment reproducible and
upgradeable.

### V. Test-First With Gated Verification (NON-NEGOTIABLE)

- A focused failing test MUST precede each behavior change. Implementation
  is the minimum code that makes the test pass.
- Verification gates run in order: unit, then integration, then end-to-end.
  A failing gate blocks the next gate. End-to-end is required whenever a
  change crosses components.
- A feature is complete only when every required gate passes. Written code
  alone is not completion.
- The default suite MUST mock external providers. Live Gemini, Ollama, and
  LangSmith checks are opt-in and never count as acceptance.
- Coverage MUST include authorization, evidence provenance, routing
  precedence, human interrupts, resume after restart, idempotent
  finalization, checkpoint/audit separation, and product-version pinning.

Rationale: triage correctness is only credible when proven by deterministic
tests at each layer.

### VI. Small, Readable, Intent-Commented Code

- Every hand-written file MUST stay below 400 lines. Split along a clear
  responsibility boundary before the limit. Generated files, lockfiles, and
  immutable migration snapshots are exempt; any other exception needs a
  stated justification first.
- Every hand-written line MUST be 80 characters or fewer.
- A short intent comment MUST immediately precede every hand-written named
  function or method, in Python and TypeScript/React. The comment states
  purpose, not syntax. Tests may use a Given/When/Then comment.
- Named handlers are preferred over complex inline callbacks.

Rationale: small files and explicit intent keep review fast and reduce
misreading.

### VII. Backend Owns Domain Truth

- Backend Python owns domain rules, workflow state, persistence, provider
  behavior, evaluation, authorization decisions, and audit logic.
- React owns presentation, interaction state, accessibility, and typed API
  consumption. React MUST NOT become a second source of underwriting truth.
- PostgreSQL is the business source of truth. LangGraph checkpoints support
  resume/replay and never replace immutable audit events.

Rationale: one source of truth prevents divergent routing logic between
layers.

## Additional Constraints

- Secrets: never commit `.env`, backups, API keys, credentials, or tokens.
  `.env.example` is the only configuration template. Never log or return
  `GEMINI_API_KEY` or `LANGSMITH_API_KEY`.
- SQL: use SQLAlchemy expressions or bound parameters. Never interpolate
  user-controlled values into SQL.
- Architecture: one FastAPI modular monolith and one web application, run
  through Docker Compose. No microservices, Redis, Celery, Kafka, GraphQL,
  Kubernetes, or object storage for the MVP.
- Tracing: LangSmith is development/evaluation-only, disabled by default,
  synthetic-data-only, and redacted.
- Reset safety: never run `docker compose down -v` without an explicit user
  request that acknowledges deletion of all project volumes.
- Escalation: ask before schema migrations, new dependencies, authentication
  or authorization changes, provider changes, enabling external tracing,
  destructive resets, column drops, or broad architecture rewrites.

## Development Workflow

- Follow the active `specs/NNN-*/tasks.md` on the `rag-implementation`
  branch, one story at a time. Never combine stories or pre-build a later
  story.
- At the end of each story, stop and report changed files, verification
  results, remaining risks, and the proposed commit.
- Commit, push, and start the next story only after the user says
  `continue`.
- Check staged files for secrets before every commit. Never force-push.
  Preserve user changes and unrelated files.
- Do not refactor unrelated features while implementing the current one.

## Governance

- This constitution supersedes conflicting practice. `AGENTS.md` is the
  runtime guidance file and MUST stay consistent with this document.
- Amendments require a written change, user approval, and an updated Sync
  Impact Report. Amendments that affect existing code include a migration
  plan.
- Versioning follows semantic versioning: MAJOR for removed or redefined
  principles, MINOR for added principles or materially expanded guidance,
  PATCH for clarifications and wording.
- Every spec, plan, task list, and review MUST check compliance with these
  principles. Any justified deviation is recorded in the plan's complexity
  tracking.

**Version**: 1.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
