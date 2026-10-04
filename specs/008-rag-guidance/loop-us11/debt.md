# Comprehension Debt & Sign-off

Unreviewed changes are debt. Acknowledge debt rather than deleting it.
Open blocking debt prevents done. Historical debt remains in ../loop/.

## Open debt

| ID | Iteration | Change | Needs human eyes | Severity | Status |
|----|-----------|--------|------------------|----------|--------|
| G01 | 1 | Prerequisites | Review A1 | low | acknowledged |
| G02 | 2-4 | Regression tests | Review A2 | medium | acknowledged |
| G03 | 5 | Model resolution | Review A3 | high | acknowledged |
| G04 | 6,9,10 | Ordered gates | Review A4 | medium | acknowledged |
| G05 | 7 | Shared Compose settings | Review A5 | high | acknowledged |
| G06 | 8,10 | Operator docs/report | Review A6 | medium | acknowledged |
| G07 | 11 | Default test isolation | Review A7 | medium | acknowledged |
| G08 | 11,12 | Acceptance commands | Review A8 | high | acknowledged |
| G09 | 11,12 | Budget discrepancy | Review A9 | high | acknowledged |

## Guard review: 2026-10-04

The sweep covers all twelve iterations because no US11 human sign-off is
recorded. Requests to run the checker or guard do not demonstrate review
of the changes. Grouped rows preserve coverage without duplicating debt.
Severity reflects the impact of accepting a change without understanding
it, not a new correctness verdict. No implementation was changed.

- A1: Iteration 1 reviewed prerequisites and preserved existing US11 work.
  Confirm the US10 checkpoint authorizes this story, not a later story.
- A2: Iterations 2-4 added resolution, builder, and persistence regressions.
  Review mocked transports, synthetic fixtures, unchanged-import request
  counts, and changed-model replacement assertions.
- A3: Iteration 5 removed four legacy model fields and introduced common
  normalized overrides and resolved provider defaults in config.py and
  the builders. Explain blank defaults, mixed selections, fake identity,
  and the required private configuration rename without exposing secrets.
- A4: Iterations 6, 9, and 10 ran ordered acceptance and recorded results.
  Review why isolated storage was used: existing development guidance
  state caused unrelated failures. Passing isolated gates does not prove
  every existing development database has the same state.
- A5: Iteration 7 shared API/bootstrap provider settings in compose.yaml.
  Explain why corpus bootstrap must receive the same embedding settings
  and why this does not enable external providers or tracing in acceptance.
- A6: Iterations 8 and 10 changed current operator instructions and added
  us11-report.md. Review legacy removal, mixed-provider guidance, risks,
  and the proposed commit. No commit or push is authorized by this report.
- A7: Iteration 11 repaired default tests by explicitly passing None.
  Explain why _env_file=None alone does not isolate process environment.
- A8: Iterations 11-12 repaired quickstart acceptance commands. Explain
  why docker compose run -e does not configure dependency bootstrap and
  why process-scoped fake settings keep both services deterministic.
- A9: Iterations 11-12 exceed the original ten-iteration checkpoint.
  The live contract says 30; purpose, configuration, and checkpoint say
  10. Existing records do not establish authorization for this discrepancy.
  The human must identify the authorized budget and decide how to record
  acceptance of iterations 11-12. Do not infer or rewrite that authority.

## Verification attention

All latest D1-D6 verdicts are independent high-confidence passes. There
are no latest uncertain verdicts or medium/low-confidence passes.
Historical D2/D6 failures were superseded by C011/C012 evidence, not
silently removed. Checker evidence includes 469 unit tests, 197 contract
and integration tests, and successful human-confirmed-flow smoke.
Human observation or understanding of that evidence is not yet recorded.
Accepting the passes without explaining A3, A5, A7, and A8 would be
cognitive surrender; automated evidence does not replace human judgment.

## Done-gate

- Independent checker passes: satisfied for all six criteria.
- No open high-severity debt: satisfied; all debt rows are acknowledged.
- Explicit human sign-off: satisfied by the user's signoff invocation.
- Phase is done. Commit, push, and the next story still require continue.

## Human review answers: 2026-10-04

- The user explained capability-specific defaults for Ollama generation
  and Gemini embeddings, embedding fallback, and fake None resolution.
  G03 is partially reviewed; the private model-key rename is unanswered.
- The user explained that run -e applies only to the one-off API, while
  bootstrap starts separately using its Compose environment. G05 and G08
  are acknowledged from that review, without recording story sign-off.
- The user confirmed review of isolated-gate evidence and development
  database limitations. G04 is acknowledged.
- The user explicitly confirmed the authorized budget is 30 and iterations
  11-12 were authorized. G09 is acknowledged. Contract purpose, checkpoint,
  and configuration were reconciled to 30 without altering maker history.
- Answer 3 repeated the Compose explanation; it did not explain why
  _env_file=None still permits process environment values. G07 stays open.
- G01, G02, and G06 also remain open pending review or explicit acceptance.
  No answer in this message constitutes US11 sign-off or commit permission.

## Sign-off log

| Date | Criterion / scope | Signed off by | Note |
|------|-------------------|---------------|------|
| 2026-10-04 | US11 D1-D6, G01-G09 | User | Explicit signoff; see S1 |

### S1: Explicit US11 acceptance

The user invoked speckit-loop-guard with singoff, interpreted as the
unambiguous spelling error signoff. This records acceptance of US11
D1-D6 and acknowledges all surfaced debt G01-G09. Earlier review answers
and the authorized thirty-iteration budget remain recorded above.
The private model-key rename and process-environment test-isolation
questions were not answered; this sign-off acknowledges that recorded
comprehension risk, not demonstrated understanding of those details.
No inability to answer was stated. No debt or checker history was deleted.
All criteria had independent high-confidence passes before closure.
No uncertain verifications remain. No implementation, maker history,
private configuration, commit, or push was changed by this guard action.
