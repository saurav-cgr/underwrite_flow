# Release Readiness Report

**Scope:** `main` at the R9 acceptance run, 15 September 2026. The body below
is the record of that run; the amendment that follows supersedes its counts.
**Branch state at R9:** 38 commits ahead of `origin/main`, since pushed.
**Verdict:** Remediation steps R1–R9 complete. The MVP is demonstrable
end to end on synthetic data. It is **not** pilot-ready or PRD-complete.

## Amendment, 16 September 2026

The twelve-finding code-review remediation landed after this report. The
verdict above is unchanged. Current measurements:

| Requirement | Result |
| --- | --- |
| API tests | 178 passed |
| API contract tests | Satisfied — 9 of those, in `api/tests/contract/` |
| Web tests | 97 passed across 13 files |
| Production web build | Passed; 247.84 kB JS, 27.07 kB CSS |
| Migrations | 6 revisions, linear; `alembic current` at `e5f6a7b8c9d0` |
| Branch state | 30 commits ahead of `origin/main`, unpushed |

Resolved or reduced since this report:

- **Limitation 2** — closed. The HTTP error handler replaced every router
  message with one generic sentence, so an underwriter overriding to the
  already-recommended route saw "Request could not be completed" instead of the
  actionable reason the router had already written. Every `detail` in the
  codebase was audited first: all are hand-written literals or
  application-owned error messages, with no exception text, file path, SQL, or
  user data. A 4xx detail is now served to the client while 5xx stays generic,
  pinned by a unit test covering both branches. Framework validation errors
  stay generic on purpose: that payload can echo submitted input values.
- **Limitation 3** — reduced. `jsdom` and `@testing-library/react` are
  installed, and DOM tests now cover intake, the evidence pack, the review
  decision, reference documents, the admin product configuration, import, and
  evaluation panels, and the shared confirm dialog. Applicant tracking, the
  audit workspace, and sign-in still have no DOM coverage.
- **Limitation 6** — reduced. The contract suite removes every row it creates,
  verified by comparing row counts before and after a run. Other integration
  suites still mutate the shared development database.
- **Limitation 6, second pass** — the applicant catalogue was left empty again
  after a run, because twenty-two sites across seven integration modules ended
  with `set_motor_status("draft")` rather than restoring the status they
  found. A session-scoped fixture in `api/tests/conftest.py` now returns
  product activation to whatever the run found it as, and three tests that
  read the ambient status (the bootstrap import, the catalogue on first
  intake, and the inactive-catalogue pin) assert the state they set up
  instead. The suite was run twice, once with all three products active and
  once with all three draft: 178 passed in both cases, and the status was
  unchanged afterwards in both.
- **A web test raced its own second fetch.**
  `web/src/product-configuration.test.tsx` read the `Activate` buttons with a
  synchronous query after awaiting only the product list, so it failed
  whenever the version history arrived late — observed once in three
  consecutive runs of the same commit. It now awaits the buttons themselves
  and passed three consecutive runs.
- **Two documents with the same filename were indistinguishable.** The
  evidence and conflict rows named only the file, so a case with two
  `synthetic.pdf` uploads showed identical labels — the same condition that
  produced a duplicate React key during remediation. A document is now
  suffixed with the first eight characters of its id when another document
  shares its name (`synthetic.pdf #df591137`), and unique names stay as they
  are.
- **Conflict rows named a field but not the disagreement.** Each conflict
  carried `field_name`, `source_locator`, and `conflict_status` only, so an
  underwriter reading "vehicle_age — conflict" had to hunt the evidence list
  for the two values. A conflict now carries `value` and `document_id`, the
  contract suite pins both keys, and the panel shows each value with the
  document and locator it came from.
- **Limitation 9** — closed. Product activation, applicant document removal,
  and reference document removal each used the native `window.confirm`, which
  is unstyled, blocking, and outside the design system. All three now use one
  `ConfirmDialog` built on the design system's modal tokens, with a labelled
  `role="dialog"`, `aria-modal`, Escape to cancel, Tab held inside the dialog,
  and focus returned to the control that opened it. Covered by DOM tests and a
  browser check of both the cancel and confirm paths.
- **Limitation 10** — reduced. `api/tests/contract/` and `api/tests/fixtures/`
  now exist, and every suite imports the shared fixture package instead of
  inserting a path for itself. Product-state helpers are shared by every
  module, but seven integration modules still carry a local `login` copy.
  `sample_data/` still does not exist.
- **Limitation 11** — partly closed. Every line added during remediation is
  within the 80-column limit, and `web/src` has none. The pre-existing debt is
  larger than this report states: 137 lines across `api/src`, of which 12 are
  the two files named in the list below.
- **Limitation 8** — closed. The review screen reported missing *document
  codes* and missing *requested fields* under one heading, so a case returned
  for information said only "No requested document is outstanding" and hid why
  it was routed there. The panel now labels both lists and names every missing
  field, covered by a DOM test and checked in the browser against a live
  `needs_information` case.
- **Limitation 13** — closed.
  `api/tests/integration/test_checkpoint_audit_separation.py` runs one review
  across two application instances, so the second instance resumes a
  checkpoint that only PostgreSQL holds, and proves that a repeated resume
  returns the first decision without rewriting or duplicating a single audit
  row. Both tests were confirmed to fail when the checkpointer is not durable
  and when the duplicate-resume guard is removed.

Defects found during remediation and closed:

- **The applicant readiness meter counted files, not satisfied requirements.**
  A replacement upload for a code that was already received made the screen
  read "3 of 2 requested documents received" with `aria-valuenow` 150 against
  `aria-valuemax` 100. It now counts each requested code once, covered by a
  regression test in `web/src/documents.test.tsx`.
- **A recorded decision named its route twice.** A request for information
  rendered "needs information · needs information", because the banner joined
  the status with a route that was the same string. The route is now omitted
  when it matches the status, so `confirmed · specialist` is unchanged.
- **Two intake paths assumed a readable configuration**, previously listed
  below as limitation 15. `create_case` and `add_document` validated the
  stored configuration without catching `ValidationError`, so a corrupted
  product version escaped as an unhandled error. Both now read it through one
  guarded helper and return the sanitized 422 the rest of intake uses.
- **The review-start fallback dropped `factors`**, previously listed below as
  limitation 14. A case whose persisted summary was empty served a
  recommendation object without the `factors` key that `case-review.tsx`
  reads. The served shape is now identical on every path.

New limitations recorded since this report, ordered with the list below:

14. **`web/src/product-configuration.tsx` is at 396 of the 400-line cap.** The
    next change to that screen must split it, along the validate and import
    panel boundary.

## Accepted exception: upload security

The upload boundary validates file type, size, and page count, and treats all
submitted content as untrusted data rather than model instruction. It does
**not** scan for malware and does **not** quarantine suspect files.

This is an accepted exception recorded at the request of the remediation plan,
not evidence of full PRD or pilot readiness. Any deployment that accepts
uploads from real users must add malware scanning and quarantine first.

## Verification results

| Requirement | Result |
| --- | --- |
| API unit and integration tests | 133 passed |
| API contract tests | Not satisfied |
| Web tests | 18 passed |
| Production web build | Passed |
| Migration upgrade and current | At `head` |
| Migration history integrity | Linear, unmodified |
| Deterministic smoke path | Passed |
| Browser role journeys | Passed, all roles |
| Staged-file secret scan | Clean |
| Synthetic-data compliance | Clean |

Detail behind the summary:

- **API unit and integration tests** — 133 passed, 0 failed, 133 collected.
- **API contract tests** — not satisfied. No `api/tests/contract/` directory
  exists, although `AGENTS.md` and the implementation plan both name one.
  Provider contract coverage lives in `api/tests/unit/test_providers.py`.
- **Web tests** — 18 passed across 2 files.
- **Production web build** — passed; 236 kB JS and 26 kB CSS (72 kB and
  5.8 kB gzipped).
- **Migration upgrade and current** — `alembic current` reports
  `d4e5f6a7b8c9 (head)`, and `alembic upgrade head` against the populated
  development database is a no-op.
- **Migration history integrity** — 5 revisions in a linear chain. No
  migration file has ever been modified after it was committed.
- **Deterministic smoke path** — passed: intake, review, completion, retry,
  audit.
- **Browser role journeys** — passed for all three roles; see below.
- **Staged-file secret scan** — no credentials in tracked files. `.env` is
  gitignored and untracked; only `.env.example` ships.
- **Synthetic-data compliance** — every fixture carries the synthetic marker,
  and all email addresses use reserved `.test` domains.

## Browser role journeys

**Applicant.** Signed in, created a motor application from the pinned product
configuration, uploaded two synthetic PDFs to 100% completion, submitted, and
reached `underwriter_review` with product and rulebook pinned to v1.

**Underwriter.** Opened the submitted case from the queue, then exercised the
human-authority boundary:

- override without acknowledging the evidence → refused client-side
- override with a too-short reason → refused client-side
- override to the already-recommended route → refused by the API (422)
- override to `standard` with a reason → decision recorded, handoff executed

The queue then showed the case as `completed` with the recommended route
(`specialist`) and the final human route (`standard`) displayed separately.

**Administrator.** Ran the reference evaluation (90 cases, 12 metrics),
inspected product configuration, and reconstructed the case from its audit
trail.

## Audit trail reconstruction

The case above produced five append-only events, each sufficient to
reconstruct the decision without reading raw application payloads:

| Event | Recorded facts |
| --- | --- |
| `case_created` | product and rulebook identity |
| `document_uploaded` | document hash and size |
| `case_submitted` | recommendation and evidence |
| `underwriter_reviewed` | decision against recommendation |
| `case_completed` | route, handoff, idempotency |

In full, the recorded facts are:

- **`case_created`** — product code, product and rulebook version IDs, both
  versions, and both content hashes.
- **`document_uploaded` (twice)** — document ID, content hash, byte size, and
  document code.
- **`case_submitted`** — recommendation, conflicts, missing fields, evidence
  provenance, validations, risk signals, document hashes, and the pinned
  version identity.
- **`underwriter_reviewed`** — action, recommended route, selected route,
  reason, review ID, and review cycle.
- **`case_completed`** — route, handoff ID, destination, idempotency key, and
  reviewed-at timestamp.

Details are sanitized by one builder: secret-shaped keys are dropped at any
depth, every string is truncated at 200 characters, and collections and
nesting are bounded. A negative-control suite proves the metrics and the
sanitizer respond to change rather than passing vacuously.

## Known limitations

Ordered by the risk each poses to a real deployment.

1. **Uploads are not scanned for malware.** See the accepted exception above.
2. **Closed.** The API served one generic sentence for every router 4xx, so an
   underwriter overriding to the already-recommended route could not read why
   it failed. A 4xx detail is now served while 5xx stays generic; see the
   amendment above.
3. **Reduced.** DOM coverage now exists for intake, the evidence pack, the
   review decision, reference documents, and the admin product, import,
   evaluation, and confirm-dialog screens. Applicant tracking, the audit
   workspace, and sign-in still have none.
4. **Evaluation runs synchronously on the event loop.** `POST /evaluation/run`
   executes the full 90-case pipeline (~500 ms CPU) inline. Acceptable
   locally; needs caching or a worker before real use.
5. **Product and rulebook content hashes are identical by construction.**
   `products/service.py` passes one hash to both records, so the rulebook hash
   provides no independent verification today.
6. **Product status is no longer clobbered; rows still are.** Integration
   tests no longer leave the applicant catalogue empty, and no test reads the
   ambient product status any more. Suites other than the contract one still
   create cases, documents, reviews, and audit rows in the shared development
   database.
7. **`alembic check` is unsafe to follow.** It reports drift confined to the
   four LangGraph checkpoint tables, which are managed outside the ORM
   metadata. Acting on its suggestion would drop `checkpoints`,
   `checkpoint_blobs`, `checkpoint_writes`, and `checkpoint_migrations`.
8. **Closed.** The review screen separates missing documents from missing
   fields and names every missing field; see the amendment above.
9. **Closed.** Activation and the two removal actions use the shared
   `ConfirmDialog`; no `window.confirm` remains in `web/src`.
10. **Reduced.** `api/tests/contract/` and `api/tests/fixtures/` now exist and
    every suite imports the shared fixture package instead of inserting a path
    for itself. Seven integration modules still carry a local `login` copy,
    and `sample_data/` still does not exist.
11. **Line-length debt.** Twelve pre-existing backend lines exceed 80 columns
    in `nodes.py` and `queues/router.py`. Every line added during remediation
    stays within the limit.
12. **Rotate local provider keys.** The untracked `.env` holds
    `GEMINI_API_KEY` and `LANGSMITH_API_KEY`. If either was ever displayed or
    shared during development, rotate it.
13. **Closed.** `api/tests/integration/test_checkpoint_audit_separation.py`
    resumes one review across two application instances and proves a repeated
    resume cannot rewrite audit history; see the amendment above.

## What is genuinely trustworthy

- Every routing decision is traced to a pinned product and rulebook version,
  and no rule can be created or activated by a model.
- Missing information is a queue state, never a fourth triage route.
- Routing precedence is deterministic-first and covered by tests, including
  `test_triage_graph_applies_route_precedence_before_review` and
  `test_triage_graph_honors_internal_rule_routes`.
- Human confirmation is mandatory, idempotent, and occurs before any queue
  handoff or webhook.
- Audit events are append-only by construction: `AuditRepository.append` only
  inserts, and no code path updates or deletes an `AuditEvent`.
- No real personal, medical, financial, vehicle, or insurer data is present
  anywhere in the repository.

## Amendment, 18 September 2026 — governed platform acceptance run

**Branch state:** `phase2`, one commit ahead of `origin/phase2`, with this
phase's changes uncommitted when the run below was taken.
**Verdict:** unchanged. The governed platform is demonstrable end to end on
synthetic data. It is **not** pilot-ready or PRD-complete.

| Requirement | Result |
| --- | --- |
| API tests | 343 passed, 0 failed |
| API contract tests | Satisfied — 25 of those, across 5 files |
| Web tests | 141 passed across 16 files |
| Production web build | Passed; 267.33 kB JS (80.43 kB gzip) |
| Migrations | Single head `07`; linear from `<base>` through 8 |
| Migration upgrade and current | At `head`, no pending upgrade |
| Deterministic smoke path | Passed |
| Ten-case synthetic load probe | Passed; 10 cases, 2 of 3 branches |
| Staged-file secret scan | Clean |
| Synthetic-data compliance | Clean |
| Line-length rule | 506 pre-existing over-80 lines, 0 added here |
| File-size rule | 3 pre-existing files at or over 400 lines |

### Quickstart scenario results

| # | Scenario | Result |
| --- | --- | --- |
| 1 | Deterministic baseline | Passed, coverage unmeasured |
| 2 | Migration validation | Passed |
| 3 | Authentication and dynamic RBAC | Passed as automated equivalent |
| 4 | Configuration validation | Partial — check set differs |
| 5 | Evidence and reconciliation | Partial — check set differs |
| 6 | Provider boundary | Fake passed, Ollama and Gemini not run |
| 7 | Human review and audit | Passed |
| 8 | Pilot-scale probe | Partial — ten-case bound only |

Detail behind the table:

- **Scenario 1** — `make test-api` 343 passed, `make test-web` 141 passed, and
  the production build is clean. Every default test used the fake provider and
  no test needed host Python, Node, Ollama, Gemini, or LangSmith. Neither
  `coverage` nor `pytest-cov` is installed, so the quickstart's "100% statement
  and branch coverage" target for the pure reconciliation functions is
  **unverified**. The behaviour it would measure is covered by
  `api/tests/unit/test_reconciliation.py`, which exercises all three kinds, all
  three statuses, missing inputs, normalization, leap-day handling, and
  ordering.
- **Scenario 2** — one head, `07`, linear from `<base>` through eight
  revisions; `01_initial.py` is unchanged. The append-only trigger now has a
  delete test next to its update test in
  `api/tests/integration/test_persistence.py`.
- **Scenario 3** — executed as the automated equivalent of the eight listed
  steps, across `api/tests/contract/test_auth_rbac_contract.py`,
  `api/tests/integration/test_dynamic_authorization.py`, and
  `api/tests/integration/test_user_role_management.py`. The browser journey was
  not re-run by hand in this pass.
- **Scenarios 4 and 5** — **divergence.** The shipped motor configuration
  declares two checks: `motor_ncb_match` (`ncb_match`) and
  `motor_renewal_lapse` (`policy_lapse`). The quickstart names a third,
  `asset_match`, over engine, chassis, and registration identifiers, and its
  expected-results table lists an asset engine row and an asset chassis row.
  The `asset_match` kind is implemented, validated at activation, and covered
  by `api/tests/unit/test_reconciliation.py` and by the synthetic version in
  `api/tests/integration/test_product_activation.py`, but no shipped demo
  product activates it. The quickstart text, not the code, is out of date.
- **Scenario 6** — `make smoke` passed. Ollama and live Gemini were not run:
  both are opt-in and neither is deterministic acceptance. The audit
  enrichment this scenario expects — provider, model, attempts, request and
  result hashes, and token usage or the unavailable marker — is now recorded
  and asserted by `api/tests/integration/test_audit_enrichment.py`.
- **Scenario 7** — passed across `test_review_contract.py`,
  `test_review_workflow.py`, `test_flagged_override.py`, and
  `test_audit_enrichment.py`, including the scope denial, the missing-rationale
  rejection, exactly-once completion, and supersession links.
- **Scenario 8** — a bounded ten-case probe was added
  (`scripts/pilot_load_probe.py`, `make probe`). It processed ten synthetic
  motor cases with the fake provider, kept every case at two provider calls
  against the three-branch bound, and reported `expedited` for all ten. The
  100-case daily sample, OCR seconds per page, provider latency and maximum
  concurrent calls, PostgreSQL pool use, stored and uploaded bytes per case,
  and queue-query p95 are **not measured**. The probe is a bounded local check,
  not a load generator, and those figures need a benchmark harness that does
  not exist. Resume after restart is covered separately by
  `test_checkpoint_audit_separation.py` and `test_workflow_checkpoint.py`.

### New findings

15. **The quickstart's reconciliation scenarios outrun the shipped demo
    configuration.** See scenarios 4 and 5. Either the quickstart or the motor
    configuration must change, and changing configuration needs approval.
16. **Branch coverage for the reconciliation module is unverified** because no
    coverage tool is installed. Adding one is a new test dependency and needs
    approval.
17. **Three files remain at or over the 400-line cap**, all predating this
    work: `web/src/access-admin.tsx` (465),
    `api/tests/unit/test_triage_workflow.py` (452), and
    `web/src/review.css` (447). `api/src/underwriteflow/cases/submission.py`
    crossed the cap during this work and was split to 351 lines, with local
    document reading moved to
    `api/src/underwriteflow/cases/local_reading.py`.
    `web/src/product-configuration.tsx`, recorded at 396, is unchanged.
18. **Line-length debt is larger than previously recorded.** 506 lines exceed
    80 columns across hand-written tracked files, including `docs/PRD.md` (99)
    and `docs/IMPLEMENTATION_PLAN.md` (90). No line added by this work exceeds
    the limit.
19. **The pilot probe reuses ten deterministic cases.** A repeated run measures
    idempotent re-processing rather than fresh throughput, by design.

## Amendment, 20 September 2026

`make evaluate-e2e` deterministic; dev state unchanged. New flows carry no
automated approve/decline/bind/price/issue/renew/cancel action.
