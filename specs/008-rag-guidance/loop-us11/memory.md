# Loop Memory

Keep durable conventions, decisions, and dead ends short.

- [M-001] Scope is tasks-us11.md T107-T122 only. One story and sequential
  work; every required gate must pass. (definition, 2026-10-04)
- [M-002] Common model names only. Keep credentials and URLs specific to
  their providers; remove legacy model names without aliases.
  (definition, 2026-10-04)
- [M-003] Blank means backend default. Generation and embedding selection
  are independent; fake identity and model tags stay unchanged.
  Contract: ../contracts/provider-configuration.md.
  (definition, 2026-10-04)
- [M-004] User explicitly requested a fresh loop with max 10 iterations.
  Project loop config now points to loop-us11 with max_iterations 10;
  earlier loop files/counters/verdicts/sign-offs stay unchanged.
  (definition, 2026-10-04)
- [M-005] Isolation none, independent/adversarial checker, one vote,
  human sign-off and debt blocking come from loop-config.yml. No
  SPECKIT_LOOP overrides were present at definition.
  (definition, 2026-10-04)
- [M-006] US10 is human-signed in the previous loop. Verify its story
  gate evidence under T107; do not redo or overwrite completed stories.
  (definition, 2026-10-04)
- [M-007] T107 confirmed US10 commit `65c6c2e`, D10 human sign-off, and
  checker iteration 68 pass. Existing US11 specification files are
  uncommitted and preserved. (iteration 1, 2026-10-04)
- [M-008] T108 focused test fails 12 times before T112: common model fields
  and resolved properties are absent, while legacy fields remain present.
  (iteration 2, 2026-10-04)
- [M-009] T109 confirms only common generation override fails before T113;
  provider defaults, fake identity, Ollama guidance, and guards already hold.
  (iteration 3, 2026-10-04)
- [M-010] T110 red coverage isolates common embedding-model wiring; T111
  uses mocked Ollama responses and verifies both import scopes. (iteration 4,
  2026-10-04)
- [M-011] Common models resolve in Settings; builders read resolved values.
  Fake branches return before any resolved model reaches an adapter.
  (iteration 5, 2026-10-04)
- [M-012] Full unit gate needs command-scoped
  `GEMINI_NO_TRAINING_ACKNOWLEDGED=false` when private local `.env` enables
  it; 469 unit tests then pass. (iteration 6, 2026-10-04)
- [M-013] API and bootstrap share provider settings through a Compose anchor;
  model defaults stay only in `config.py`. (iteration 7, 2026-10-04)
- [M-014] Use the isolated `underwriteflow-us11-gate` Compose project for
  deterministic integration and smoke checks; it preserves development data.
  (iterations 9-10, 2026-10-04)
- [M-015] Default builder tests must pass explicit None for common models;
  `_env_file=None` still reads process environment. (iteration 11,
  2026-10-04)
- [M-016] Compose `run -e` affects only its one-off service. Put acceptance
  overrides in the process environment to configure bootstrap too.
  (iteration 12, 2026-10-04)
