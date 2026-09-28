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

## Sign-off log

| Date | Criterion / scope | Signed off by | Note |
|------|-------------------|---------------|------|
| 2026-09-28 | D1 (US1) | saurav-cgr | Sign-off given via `/speckit.loop.guard signoff D1`. Guard questions 1-6 were not answered in session. DEBT-001 to DEBT-005 acknowledged as accepted, not resolved. |
