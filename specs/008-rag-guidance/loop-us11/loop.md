# Loop Contract: US11 Configuration Settings

## Purpose

1. Complete and independently verify configuration tasks T107-T122 in
   ../tasks-us11.md, with human sign-off, within 30 maker iterations.

## Done-criteria

| ID | Checkable criterion | Checker verification | Status |
|----|---------------------|----------------------|--------|
| D1 | Common model resolution | Unit checks below | human-signed |
| D2 | Builders and safeguards | Mocked builder tests | human-signed |
| D3 | Shared Compose settings | Contract checks below | human-signed |
| D4 | Model tag persistence | Import regressions | human-signed |
| D5 | Ordered full acceptance | Exit codes and smoke | human-signed |
| D6 | Tasks, docs, and hygiene | Files and diff review | human-signed |

Primary sources and exact checks:

- D1: tests/unit/test_provider_model_config.py proves provider defaults,
  blank/whitespace normalization, overrides, mixed providers, backend
  fallback, fake None resolution, and legacy field/name removal. Verify
  named defaults and resolution in api/src/underwriteflow/config.py.
- D2: tests/unit/test_provider_model_builders.py and
  tests/unit/test_embedding_providers.py prove adapters receive resolved
  model values while fake identity, guards, redaction, errors, and Ollama
  guidance behavior remain unchanged. No remote requests in tests.
- D3: tests/contract/test_environment_compose.py passes. Inspect shared
  provider environment mapping in compose.yaml: common names forwarded to
  API/bootstrap with empty defaults; legacy model entries absent;
  evaluation, production, and smoke override behavior preserved.
- D4: tests/integration/test_provider_model_configuration.py and existing
  test_knowledge_embeddings.py/test_regulation_import.py pass. Resolved
  tags persist; unchanged re-import reuses embeddings; changed models
  replace vectors for synthetic guideline and regulation versions.
- D5: all api/tests/unit pass before api/tests/integration and the Compose
  contract pass; then make smoke exits 0. Use fake providers and tracing
  disabled for acceptance. Unexpected skips or absent gates fail D5.
- D6: T107-T122 in ../tasks-us11.md are complete; .env.example, README.md,
  and quickstart document current names; ../us11-report.md has evidence,
  risks, and proposed commit. Verify git diff --check, fewer than 400 lines
  per changed hand-written file, at most 80 columns, intent comments,
  no legacy runtime references/aliases, and no secrets in the diff.

All paths above are repository-relative unless prefixed ../. Test commands
run through Docker Compose using ../quickstart.md US11. The checker must
inspect primary sources and independently execute required verification;
maker assertions and checked task boxes alone cannot pass a criterion.

Statuses: pending -> maker-ready -> checker-pass | checker-fail
-> human-signed. Done requires every criterion human-signed, one independent
passing checker verdict per criterion, and no open blocking debt.

## Budget

- Max iterations: 30
- Iterations run: 12
- Per iteration: one bounded group of US11 tasks or checker-requested fixes.
- Follow task dependencies and failing-test-first requirements.
- Stop maker work at each checker handoff; never self-grade.
- At iteration 30 stop and request human review if any work remains.
- No automatic budget increase or reset.
- Isolation: none
- No parallel maker iterations or changes to other stories.

## Roles

- Maker: implements tasks through /speckit-loop-run.
- Checker: independent adversarial grader through /speckit-loop-check.
- Checker MUST use a separate agent/session from the maker; one vote.
- Human: reviews comprehension debt and signs off via speckit-loop-guard.
- Maker cannot declare done or manufacture checker verdicts/sign-off.

## Allowed tools / connectors

- Core Spec Kit skills; repository reads, searches, edits, and git diffs.
- Docker Compose, Make, pytest, and mocked httpx adapters for US11 checks.
- Separate checker agent/session for checking, never parallel making.
- No live Gemini/Ollama calls or LangSmith tracing for acceptance.
- No email, chat messaging, external connectors, or scheduled automation.

## Automation trigger

- Manual /speckit-loop-run; no scheduler is created by define.
- Active directory: specs/008-rag-guidance/loop-us11/.
- /speckit-loop-status resumes this state in fresh sessions.

## Guardrails

- Independent checker pass required before done: true
- Human sign-off required before done: true
- Comprehension debt tracked: true
- Open blocking debt blocks done: true
- One feature/story only: US11. Preserve existing changes and loop history.
- No schema, dependency, authentication, provider capability, tracing,
  reset, or broad architecture change without existing escalation approval.
- Never edit, log, return, or commit private .env or credentials.
- Synthetic fixtures only; no real regulatory download or applicant data.
- Routing, human confirmation, and backend ownership remain unchanged.
- Stop at the story checkpoint with files, evidence, risks, proposed commit.
- Wait for explicit continue before commit or push; never force-push.
- Earlier human sign-offs do not count as US11 sign-off.
- Historical non-blocking debt stays recorded in ../loop/debt.md.
  If it concretely blocks US11, reference it in this loop's debt ledger.

## State

- Phase: done
- Last updated: 2026-10-04
- Checker C010 passed D1, D3, D4, D5; failed D2 and D6.
- Checker C011 passed D2 with adversarial overrides; D6 still fails.
- Iteration 12 moves US11 Compose overrides into the process environment,
  so bootstrap and one-off API use the same deterministic settings.
- Checker C012 passed D6 after adversarial rendering and all ordered gates.
- All criteria retain independent passes and are human-signed on 2026-10-04.
- Human confirmed a 30-iteration budget and authorization of iterations
  11-12 on 2026-10-04; purpose, checkpoint, and configuration now agree.
- Explicit user sign-off acknowledges G01-G09; see debt.md S1 for scope
  and the unanswered comprehension questions accepted by that sign-off.
- D1, D3, D4, D5 retain their C010 passes; D2 C011 and D6 C012 pass.
- No open blocking debt remains. User authorized commit and push with
  continue on 2026-10-04; no later story is defined in the active tasks.
- Previous RAG loop remains closed and unchanged at ../loop/.
