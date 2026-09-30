# Loop Contract

## Purpose

1. Complete and verify all nine RAG guidance user stories, one story at a
   time, with independent checking and human sign-off at every checkpoint.

## Done-criteria

| ID | Story | Checkable criterion | Status |
|----|-------|---------------------|--------|
| D1 | US1 | Phase 3, T001, and shared gate pass | human-signed |
| D2 | US2 | Phase 4 and shared gate pass | human-signed |
| D3 | US3 | Phase 5 and shared gate pass | human-signed |
| D4 | US4 | Phase 6 and shared gate pass | human-signed |
| D5 | US5 | Phase 7 and shared gate pass | human-signed |
| D6 | US6 | Phase 8 and shared gate pass | human-signed |
| D7 | US7 | Phase 9 and shared gate pass | human-signed |
| D8 | US8 | Phase 10 and shared gate pass | human-signed |
| D9 | US9 | Phases 11-12 and shared gate pass | pending |

For every story, the checker verifies all items below against primary
sources. No story passes on maker self-assessment alone.

1. Every task in that story's phase is checked in `tasks.md` or
   `tasks-us6-us9.md`. US1 includes setup T001. US9 includes polish T091-T092.
2. Story tests named in the phase exist, fail before implementation where
   required, and pass. Run the story's full checkpoint, including its
   quickstart and any migration, evaluation, or end-to-end checks.
3. `make test-api`, `make test-web`, the web build, and `make smoke` each
   exit 0 for that story. Web build command:
   `docker compose run --rm web npm run build`.
4. Every hand-written project file has fewer than 400 lines. Every
   hand-written line has at most 80 columns. Generated files, lockfiles,
   and immutable migration snapshots retain the AGENTS.md exceptions.
5. Every hand-written named function or method has a preceding short intent
   comment, including named test functions.
6. Inspect staged file names and staged content before any commit. No
   `.env`, backup, API key, credential, or token may be staged. Never print
   secret values.
7. Checker records a verdict, staff review is recorded, and the human signs
   off on that story before the next story starts.

Statuses: pending, maker-ready, checker-pass, checker-fail, human-signed.
Loop closes only when D1-D9 are human-signed, all required checker verdicts
pass, and no blocking debt remains.

## Budget

- Max iterations: 100
- Iterations run: 53
- Per iteration: exactly one story, the lowest numbered story not yet
  human-signed. Stop at that story's checkpoint.
- Isolation: none

## Roles

- Maker: Codex/Copilot. Produces one story in `/speckit.loop.run`.
- Checker: Claude/Copilot in a separate session. Independently grades the
  story, records verdicts, and alone makes commits.
- Staff review: Codex/Copilot, distinct from the checker verdict.
- Maker and checker must not share the same session.

## Allowed tools / connectors

- Core Spec Kit workflow and repository tools only.
- Docker Compose, Make, pytest, Vitest, Playwright, and git for the phase
  checks. No live providers or external tracing for deterministic gates.

## Automation trigger

- Manual `/speckit.loop.run`, one story per invocation.

## Guardrails

- Human sign-off required before done: true
- Comprehension debt tracked: true
- Open blocking debt blocks done: true
- Honor every `[NEEDS APPROVAL]` task and AGENTS.md escalation gate.
- At each checkpoint report changed files, verification, remaining risks,
  and proposed commit. Wait for the user's `continue` before checker commit,
  push, or work on the next story. No force-push.
- Preserve unrelated changes. Never use `docker compose down -v` without
  explicit purge authorization.

## State

- Phase: checked. D8 human-signed 2026-09-30 (see `debt.md` sign-off log);
  DEBT-051 open, non-blocking, deferred.
- Loop not done: D1-D8 human-signed, D9 pending.
  Next: checker commit and push of US8 after the user's `continue`, then
  `/speckit.loop.run` for US9.
- Last updated: 2026-09-30
