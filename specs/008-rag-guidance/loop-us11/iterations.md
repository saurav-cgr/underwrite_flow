# Maker Iterations

Append-only. One record per /speckit-loop-run iteration. The maker never
marks the loop done; it records work and criteria ready for the checker.

<!-- Record format:
## Iteration n - date
- Targeted criteria: D-ids
- Tasks: T-ids
- Change: result and file pointers
- Verification: failing-test proof and subsequent command/exit evidence
- Maker self-assessment: criteria believed ready
- Open questions / risks: items for checker or human review
- Handoff: ready-for-check
-->

## Iteration 1 - 2026-10-04
- Targeted criteria: D1-D6 prerequisite only
- Tasks: T107
- Worktree: in place
- Change: Reviewed `docs/PRD.md`, `docs/IMPLEMENTATION_PLAN.md`, and
  `plan.md`; confirmed US10 T093-T106 checked, prior D10 human-signed,
  checker iteration 68 passed, and US10 commit `65c6c2e` exists. Recorded
  current worktree as existing US11 specification and loop files only.
- Verification: `git status --short`, `git log --oneline -8`, task checkbox
  scan, and prior loop verdict/sign-off sources.
- Maker self-assessment: T107 is complete. D1-D6 remain pending; this is
  maker assessment, not a verdict.
- Open questions / risks: Existing uncommitted files define US11 and must
  remain preserved. No implementation or provider behavior changed.
- Handoff: ready-for-check

## Iteration 2 - 2026-10-04
- Targeted criteria: D1
- Tasks: T108
- Worktree: in place
- Change: Added isolated Settings resolution tests in
  `api/tests/unit/test_provider_model_config.py:1` for defaults, blank and
  whitespace values, overrides, mixed providers, fallback, fake, and legacy
  field removal.
- Verification: Focused Compose run failed as expected before T112: 12
  failures for missing common fields/properties and present legacy fields.
- Maker self-assessment: T108 is complete. D1 remains pending until T112
  and the unit gate pass; this is maker assessment, not a verdict.
- Open questions / risks: Tests avoid dotenv and clear all model environment
  variables. No production code changed.
- Handoff: ready-for-check

## Iteration 3 - 2026-10-04
- Targeted criteria: D2
- Tasks: T109
- Worktree: in place
- Change: Added mocked-free construction tests in
  `api/tests/unit/test_provider_model_builders.py:1` for resolved defaults,
  one common Gemini override, fake identity, Ollama guidance, and guards.
- Verification: Focused Compose run had one expected failure before T113:
  Gemini extraction kept `gemini-3.1-flash-lite` instead of `shared-model`.
  Five unrelated behavior checks passed.
- Maker self-assessment: T109 is complete. D2 remains pending until T113
  and its paired embedding coverage pass; this is maker assessment, not a
  verdict.
- Open questions / risks: No remote requests occurred. Existing provider
  safeguards are asserted directly.
- Handoff: ready-for-check

## Iteration 4 - 2026-10-04
- Targeted criteria: D2, D4
- Tasks: T110-T111
- Worktree: in place
- Change: Updated embedding builder tests in
  `api/tests/unit/test_embedding_providers.py:208`; added mocked Ollama
  import persistence coverage in
  `api/tests/integration/test_provider_model_configuration.py:1`.
- Verification: T110 focused Compose run failed as expected before T114:
  Ollama and Gemini builders ignored common `embedding_model`. T111 is
  authored for T119 and uses only MockTransport.
- Maker self-assessment: T110-T111 are complete. D2 and D4 remain pending;
  this is maker assessment, not a verdict.
- Open questions / risks: T111 expects two first imports and no unchanged
  re-import calls; checker should inspect its request-count assumption.
- Handoff: ready-for-check

## Iteration 5 - 2026-10-04
- Targeted criteria: D1, D2
- Tasks: T112-T114
- Worktree: in place
- Change: Replaced four model settings with normalized common overrides and
  resolved properties in `api/src/underwriteflow/config.py:16`; updated
  extraction, guidance, and embedding builders to consume them.
- Verification: The three focused unit modules pass: 34 tests. No remote
  provider request is made.
- Maker self-assessment: T112-T114 are complete. D1-D2 remain pending until
  the full unit gate; this is maker assessment, not a verdict.
- Open questions / risks: Builders receive resolved values after a non-fake
  branch check; checker should confirm this remains type-safe.
- Handoff: ready-for-check

## Iteration 6 - 2026-10-04
- Targeted criteria: D1, D2, D5
- Tasks: T115
- Worktree: in place
- Change: No source change; ran the ordered unit gate.
- Verification: `pytest tests/unit -q` first exposed local acknowledgement
  state in one legacy guard test. With fake providers and
  `GEMINI_NO_TRAINING_ACKNOWLEDGED=false`, 469 tests passed.
- Maker self-assessment: T115 is complete. D1-D2 and D5 remain pending;
  this is maker assessment, not a verdict.
- Open questions / risks: Acceptance commands need the explicit false
  acknowledgement override when local `.env` sets it true.
- Handoff: ready-for-check

## Iteration 7 - 2026-10-04
- Targeted criteria: D3
- Tasks: T116-T117
- Worktree: in place
- Change: Updated Compose contract coverage and added the shared
  `x-provider-environment` anchor in `compose.yaml:3` for API/bootstrap.
  Common overrides are blank by default; legacy model names are absent.
- Verification: Contract test failed before T117 for missing
  `GENERATION_MODEL`; after T117, all 14 Compose contract tests passed.
- Maker self-assessment: T116-T117 are complete. D3 remains pending until
  the full integration gate; this is maker assessment, not a verdict.
- Open questions / risks: Compose test reads source YAML, not rendered
  credentials. Evaluation and production overrides remain covered by tests.
- Handoff: ready-for-check

## Iteration 8 - 2026-10-04
- Targeted criteria: D6
- Tasks: T118
- Worktree: in place
- Change: Updated `.env.example`, `README.md`, and US10 quickstart examples
  to use blank common model overrides and explain private local renaming.
- Verification: Legacy current operator names are absent from these files.
- Maker self-assessment: T118 is complete. D6 remains pending until final
  hygiene and report; this is maker assessment, not a verdict.
- Open questions / risks: Historical task/spec references stay untouched.
- Handoff: ready-for-check

## Iteration 9 - 2026-10-04
- Targeted criteria: D3, D4, D5
- Tasks: T119
- Worktree: in place
- Change: Ran the Compose contract and integration gate in a clean isolated
  `underwriteflow-us11-gate` project after local development state exposed
  two unrelated failures.
- Verification: Isolated gate passed 197 tests with fake providers and
  tracing disabled. T111 passed with MockTransport. No unexpected skips.
- Maker self-assessment: T119 is complete. D3-D5 remain pending until smoke
  and final hygiene; this is maker assessment, not a verdict.
- Open questions / risks: Local development DB has active motor guidance
  state; it is preserved and documented in `us11-report.md`.
- Handoff: ready-for-check

## Iteration 10 - 2026-10-04
- Targeted criteria: D1-D6
- Tasks: T120-T122
- Worktree: in place
- Change: Ran isolated smoke; inspected current runtime names, sizes, lines,
  comments, staged names, and diff hygiene; added `us11-report.md`.
- Verification: Isolated `make smoke` passed. Focused post-hygiene tests: 35
  passed. No legacy runtime names, staged files, over-limit lines, or files.
- Maker self-assessment: D1-D6 are maker-ready. This is maker assessment,
  not a checker verdict.
- Open questions / risks: Full local integration is state-sensitive; clean
  isolated Compose passes and no user data or volume was reset.
- Handoff: ready-for-check

## Iteration 11 - 2026-10-04
- Targeted criteria: D2, D6 (checker C010 failures)
- Tasks: regression repair and acceptance-document correction
- Worktree: in place
- Change: Default builder tests explicitly set common model inputs to None;
  US11 quickstart now uses isolated, command-scoped fake/tracing-off gates;
  README gives an Ollama-generation/Gemini-embedding example.
- Verification: Adversarial unit gate with both common model overrides: 469
  passed. Isolated contract/integration gate: 197 passed. Isolated smoke
  passed.
- Maker self-assessment: D2 and D6 are maker-ready after C010 repair. This
  is maker assessment, not a checker verdict.
- Open questions / risks: Existing local development data remains untouched.
  Recheck must independently verify C010 findings and command reproducibility.
- Handoff: ready-for-check

## Iteration 12 - 2026-10-04
- Targeted criteria: D6 (checker C011 failure)
- Tasks: acceptance-document correction
- Worktree: in place
- Change: Moved quickstart provider, model, acknowledgement, and tracing
  overrides into the Compose process environment, shared by bootstrap/API.
- Verification: Exact quickstart unit gate: 469 passed. Exact integration
  gate: 197 passed. Isolated smoke passed.
- Maker self-assessment: D6 is maker-ready after C011 repair. This is maker
  assessment, not a checker verdict.
- Open questions / risks: Budget metadata conflict remains for human review;
  no budget value was changed by this iteration.
- Handoff: ready-for-check
