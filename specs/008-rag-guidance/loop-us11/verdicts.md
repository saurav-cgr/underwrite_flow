# Checker Verdicts

A criterion passes only after an independent checker confirms primary
sources: tests, files, or a running flow. Maker self-assessment is not proof.

| ID | Iteration | Criterion | Method | Verdict | Confidence | Date |
|----|-----------|-----------|--------|---------|------------|------|
| C010-1 | 10 | D1 | E1 | pass | high | 2026-10-04 |
| C010-2 | 10 | D2 | E2 | fail | high | 2026-10-04 |
| C010-3 | 10 | D3 | E3 | pass | high | 2026-10-04 |
| C010-4 | 10 | D4 | E4 | pass | high | 2026-10-04 |
| C010-5 | 10 | D5 | E5 | pass | high | 2026-10-04 |
| C010-6 | 10 | D6 | E6 | fail | high | 2026-10-04 |
| C011-2 | 11 | D2 | E11-2 | pass | high | 2026-10-04 |
| C011-6 | 11 | D6 | E11-6 | fail | high | 2026-10-04 |
| C012-6 | 12 | D6 | E12-6 | pass | high | 2026-10-04 |

## C010 evidence: independent checker, iteration 10

This checker session did not produce the implementation. Checks used the
existing isolated `underwriteflow-us11-gate` Compose project. Development
volumes, private configuration, implementation, and maker records were not
edited. No live provider request was required.

- E1: Read `api/src/underwriteflow/config.py` and the configuration unit
  tests. The full unit suite passed. An independent Docker runtime probe
  passed 48 generation/embedding/override combinations, including fake
  overrides, mixed providers, fallback, blanks, and trimmed custom names.
  Setting all four legacy model environment names had no selection effect.
  Default constants occur only in `config.py` within runtime source.
- E2: The baseline unit suite passed the mocked builder tests, but an
  adversarial run with supported common model overrides failed three tests.
  `GENERATION_MODEL=checker-custom-generation` caused both default cases
  in `test_provider_model_builders.py:39` to fail. Setting
  `EMBEDDING_MODEL=checker-custom-embedding` also failed the default check
  in `test_embedding_providers.py:236`. Result: 3 failed, 19 passed, exit 1.
  `_env_file=None` does not disable process environment loading. The runtime
  correctly honors overrides; default tests incorrectly inherit them.
  Smallest correction: clear common model environment names in those tests
  or explicitly pass None when asserting automatic defaults. Preserve
  override tests and provider safeguards.
- E3: All 14 Compose contract tests passed within the integration gate.
  Read the shared YAML anchor and removed entries. Independently rendered
  base, production, smoke, and evaluation configurations through Compose.
  Whitelisted jq assertions returned true for shared common names, empty
  defaults, production modes, and fake/tracing-off acceptance overrides.
  Rendered credentials were never printed. Runtime and Compose searches
  found no remaining legacy model names or duplicate runtime defaults.
- E4: The full integration gate included the new mocked configuration
  persistence regression, `test_knowledge_embeddings.py`, and
  `test_regulation_import.py`. All passed. Inspected request counts,
  isolated synthetic identities, unchanged-import reuse, replacement
  vectors, and final `ollama:model-b` source tags for both corpus scopes.
- E5: Independent ordered baseline acceptance passed: unit exit 0 with
  469 tests; integration and Compose contract exit 0 with 197 tests;
  isolated smoke exit 0. Neither pytest gate reported skips. Acceptance
  used fake providers and tracing disabled. The unit run explicitly set
  `GEMINI_NO_TRAINING_ACKNOWLEDGED=false`. Smoke confirmed intake, review,
  completion, retry, and audit. The first smoke invocation overlapped a
  checker one-off failure, which Compose counted as an exit failure; a
  sequential rerun passed. That interference is not an implementation bug.
- E6: Task boxes and the story report exist, and file sizes, 80-column
  limits, named-function intent comments, and `git diff --check` passed.
  No files were staged; changed configuration contains no private keys.
  However, quickstart lines 182-194 omit the acknowledgement override and
  isolated project required by the report and loop memory. A Docker probe
  with an acknowledged local setting reproduced failure in
  `test_provider_contracts.py:230`: `DID NOT RAISE` ProviderError, exit 1.
  Quickstart overrides fake providers only for the one-off API, leaving
  dependency bootstrap configuration and tracing dependent on local state.
  README also lacks T118's required explanation of mixed provider choices.
  Smallest correction: document complete, command-scoped fake/tracing-off
  overrides, false acknowledgement, normalized model test settings, and
  the isolated project for each ordered gate. Add a short mixed-provider
  example without reading or changing private `.env`.

### Gate

No uncertain verdicts or new comprehension-debt items were needed. D2 and
D6 require correction; passing criteria do not close the loop. The maker
budget is exhausted at 10/10. Obtain human review and an explicit budget
decision before another maker iteration; use `/speckit-loop-status` next.
After corrections, rerun the independent checker and then the human guard.

## C011 evidence: independent checker, iteration 11

Default scope includes D2 and D6, the only maker-ready criteria. This
checker did not make the iteration's implementation or test changes.
D1, D3, D4, and D5 retain their previously recorded C010 verdicts.

- E11-2: Read the builder default assertions and explicit None inputs.
  Independently ran all unit tests in Docker with both common environment
  overrides set to checker custom values, fake providers, false training
  acknowledgement, and tracing disabled. Result: 469 passed, no skips,
  exit 0. The three C010 failures are fixed. The run used `--no-deps` on
  the existing isolated project to prevent ambient bootstrap calls.
- E11-6: The README now explains mixed providers. Quickstart now includes
  the isolated project, explicit model blanks, false acknowledgement, and
  tracing disabled for its one-off API. The report and task boxes exist;
  changed file sizes, 80-column limits, intent comments, and diff hygiene
  pass. README has 399 lines. No files are staged, and no legacy names
  remain in runtime, Compose, or current operator configuration.
  However, quickstart lines 182-203 still set fake providers through
  `docker compose run -e`, which applies only to the one-off API service.
  Its dependency bootstrap runs `knowledge.import_corpora`, constructs an
  embedder from its own Settings, and imports corpora. It does not inherit
  the run overrides. A controlled Compose render with generation and
  embeddings set to Ollama returned Ollama for both bootstrap providers;
  the project name only isolates storage. This reproduces the remaining
  C010 defect without starting a live provider or printing credentials.
  Smallest correction: put fake provider and tracing overrides in the
  Compose process environment for both pytest commands, alongside the
  project name. Retain the API's false acknowledgement and model blanks.
  The smoke override already sets fake providers on API and bootstrap.

### C011 gate

D2 passes, D6 fails. There are no uncertain verdicts or new debt items.
The checker changed only loop status and this verdict record, not source,
tests, operator documentation, or maker history. Correct D6 in a bounded
maker iteration, then rerun the independent checker before the human guard.
Budget metadata also needs reconciliation: the live contract says 30,
but configuration, purpose, and the old checkpoint still say 10. Preserve
the authorized budget rather than inferring or creating a new extension.

## C012 evidence: independent checker, iteration 12

Default scope is D6, the only maker-ready criterion. This checker did not
write the maker's documentation or implementation. Existing D1-D5 verdicts
remain in force. Verification stayed within US11; no product code changed.

- E12-6: Read the corrected US11 quickstart commands, shared Compose
  mapping, task checklist, README, configuration template, and story report.
  Both pytest commands now put overrides in the Compose process environment,
  not only the one-off API. Adversarially rendered these overrides under
  conflicting ambient Ollama providers, custom model values, acknowledged
  training, and enabled tracing. With the public configuration template,
  allowlisted assertions returned true for safe API and bootstrap settings:
  fake providers, blank models, false acknowledgement, and disabled tracing.
  Bootstrap has no tracing environment entry; Settings defaults it to false.
  No credentials were displayed and no live provider was invoked.
- Independently executed the exact documented commands, sequentially in
  the existing isolated project. Unit: 469 passed in 6.07 seconds, exit 0.
  Contract/integration: 197 passed in 50.49 seconds, exit 0. Neither gate
  reported skips. Smoke then exited 0 and confirmed intake, review,
  completion, retry, and audit. Dependency bootstrap completed successfully.
- T107-T122 are checked complete. The report records changed files, ordered
  verification, remaining risks, and the proposed commit. Current operator
  documentation uses common model names and explains mixed providers.
  Reviewed source/test diffs and intent comments. Size and column scans of
  modified and untracked hand-written files passed, as did git diff --check.
  No legacy names remain in runtime or current operator configuration.
  No files are staged; reviewed configuration contains no private keys.

### C012 gate

D6 passes with high confidence. All six criteria now have independent
passing verdicts. No uncertain criteria or new comprehension-debt items.
Only loop.md and this verdict record were changed by the checker.
Use /speckit-loop-guard for human review and explicit US11 sign-off; this
passing check does not declare done or authorize a commit or push.
Resolve the existing budget conflict during human review: the live contract
says 30, while configuration, purpose, and the old checkpoint say 10.
The checker did not change or infer budget authorization.
