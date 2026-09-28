# Comprehension Debt & Sign-off

Record changes that still need human review. Keep acknowledged debt in the
ledger. Open blocking debt prevents loop completion.

## Open debt

| ID | Iteration | Change | Human review needed | Severity | Status |
|----|-----------|--------|---------------------|----------|--------|
| DEBT-001 | 6 | Life v3 `date_of_birth` web form | Checker verified API (422/200) and `<input type="date">` rendering in source only; no browser run of quickstart US1 web-form flow | non-blocking | acknowledged |
| DEBT-002 | 8 | Journey test restore of motor state | `set_motor_status(prior, "v1")` restores product status but not the prior active version: with motor v5 active before, v1 is active after. Pre-existing pattern (24 uses at HEAD). Decide whether to accept | non-blocking | acknowledged |
| DEBT-003 | 1-2 | `validation.py` date parsing and `not_future` | New trust-boundary validation; human should confirm strict ISO round-trip and server-local `date.today()` are intended | non-blocking | acknowledged |
| DEBT-004 | 3-5 | Life v3 config, importer entry, 30 life fixtures repinned to v3 with synthetic DOBs, built-in version count 10 to 11 | Evaluation dataset identity changed; human should confirm repinning v1/v2 fixtures to v3 is intended | non-blocking | acknowledged |
| DEBT-005 | 6-7 | Corpus parser, alignment checker, 12-section `g1.yaml`, read-only Compose mounts | Largest new logic; `undeclared_number` rule and closed topic sets decide what later stories may say; one probe escaped as `TypeError` (iteration 6 verdict) | non-blocking | acknowledged |
| DEBT-006 | 9-11 | Administrator knowledge screen and quickstart US2 | Checker ran US2 quickstart through in-process API and Vitest only; no browser run of import, preview, activate, and case pin flow | non-blocking | acknowledged |
| DEBT-007 | 9 | Migration `09_knowledge_base.py` (three tables, coalesce unique indexes) | Becomes permanent schema history once committed; human should confirm table shape and `uq_knowledge_versions_one_active` before it is frozen | non-blocking | acknowledged |
| DEBT-008 | 9-14 | `knowledge/service.py` import/activate/retire, `IntegrityError` mapping, idempotent re-activation | Checker probed races, but concurrent same-content import returns 409 while sequential re-import succeeds; human should accept or reject that asymmetry | non-blocking | acknowledged |
| DEBT-009 | 9, 11 | `pin_case_knowledge` call in `cases/submission.py` and `case_guidance_pinned` audit event | Changes every case submission path; human should confirm pin happens once at processing start and null pin is acceptable when no guideline is active | non-blocking | acknowledged |
| DEBT-010 | 9, 11 | `import_corpora` appended to Compose `bootstrap` in both stacks | Runs on every start; editing a shipped corpus without bumping `version` raises conflict and may fail bootstrap. Human should confirm fail-loud is intended | non-blocking | acknowledged |

## Sign-off log

| Date | Criterion / scope | Signed off by | Note |
|------|-------------------|---------------|------|
| 2026-09-28 | D1 (US1) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D1`. Guard questions 1-6 were not answered in session. DEBT-001 to DEBT-005 acknowledged as accepted, not resolved. |
| 2026-09-28 | D2 (US2) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D2`. Guard questions 1-5 were not answered in session. DEBT-006 to DEBT-010 acknowledged as accepted, not resolved. Checker verdict medium confidence; browser quickstart US2 not run. |
