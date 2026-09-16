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
| API unit and integration tests | 163 passed |
| API contract tests | Satisfied — 8 passed in `api/tests/contract/` |
| Web tests | 66 passed across 9 files |
| Production web build | Passed; 245 kB JS, 27 kB CSS |
| Migrations | 6 revisions, linear; `alembic current` at `e5f6a7b8c9d0` |
| Branch state | 14 commits ahead of `origin/main`, unpushed |

Resolved or reduced since this report:

- **Limitation 3** — reduced. `jsdom` and `@testing-library/react` are
  installed, and DOM tests now cover intake, the evidence pack, and reference
  documents. Applicant tracking, admin product configuration, and sign-in still
  have no DOM coverage.
- **Limitation 6** — reduced. The contract suite removes every row it creates,
  verified by comparing row counts before and after a run. Other integration
  suites still mutate the shared development database.
- **Limitation 10** — reduced. `api/tests/contract/` now exists.
  `sample_data/` and `api/tests/fixtures/` do not; the contract suite reaches
  the integration fixture builders through an explicit path insertion.
- **Limitation 11** — partly closed. Every line added during remediation is
  within the 80-column limit, and `web/src` has none. The pre-existing debt is
  larger than this report states: 138 lines across `api/src`, of which 12 are
  the two files named in the list below.

Defects found by the browser journeys and closed:

- **The applicant readiness meter counted files, not satisfied requirements.**
  A replacement upload for a code that was already received made the screen
  read "3 of 2 requested documents received" with `aria-valuenow` 150 against
  `aria-valuemax` 100. It now counts each requested code once, covered by a
  regression test in `web/src/documents.test.tsx`.
- **A recorded decision named its route twice.** A request for information
  rendered "needs information · needs information", because the banner joined
  the status with a route that was the same string. The route is now omitted
  when it matches the status, so `confirmed · specialist` is unchanged.

New limitations recorded since this report, ordered with the list below:

14. **A review-start fallback drops `factors`.** `reviews/router.py` serves
    `summary.get("recommendation", {"route": recommendation.route})`, so a case
    whose persisted summary is missing returns a recommendation object without
    the `factors` key that `case-review.tsx` reads. The contract suite pins the
    normal path only.
15. **Two intake paths assume a readable configuration.** `cases/service.py`
    calls `ProductConfiguration.model_validate` in `create_case` and
    `add_document` without catching `ValidationError`, so a corrupted pinned
    version raises an unhandled error instead of the 409 or review hand-off the
    review endpoints now produce.
16. **`web/src/product-configuration.tsx` is at 396 of the 400-line cap.** The
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
2. **The API discards router error messages.** `http_error_handler` replaces
   every `HTTPException.detail` with "Request could not be completed". A user
   overriding to the already-recommended route sees that generic text instead
   of the actionable reason the router already wrote. Reversing this requires
   auditing every `detail=` string for safety first.
3. **No automated frontend regression coverage.** `@testing-library/react` and
   `jsdom` are not installed, so no screen behaviour is locked in by a test.
   New logic was deliberately placed in pure helpers (`ui-state.ts`,
   `api.ts`) so it is unit-tested, but screen wiring is verified only by
   browser probing.
4. **Evaluation runs synchronously on the event loop.** `POST /evaluation/run`
   executes the full 90-case pipeline (~500 ms CPU) inline. Acceptable
   locally; needs caching or a worker before real use.
5. **Product and rulebook content hashes are identical by construction.**
   `products/service.py` passes one hash to both records, so the rulebook hash
   provides no independent verification today.
6. **Integration tests mutate the shared development database.** A test that
   toggles product status left the applicant catalog empty during this run and
   had to be reactivated by hand.
7. **`alembic check` is unsafe to follow.** It reports drift confined to the
   four LangGraph checkpoint tables, which are managed outside the ORM
   metadata. Acting on its suggestion would drop `checkpoints`,
   `checkpoint_blobs`, `checkpoint_writes`, and `checkpoint_migrations`.
8. **`ReviewStartResponse.missing_information` is ambiguous.** It carries
   missing *document codes*, while field-level gaps live at
   `summary.missing_information`. An underwriter on a `needs_information` case
   therefore sees an empty missing list.
9. **Product activation uses native `window.confirm`.** Accessible but
   unstyled, blocking, and outside the design system.
10. **Planned structure is partially absent.** `sample_data/`,
    `api/tests/contract/`, and `api/tests/fixtures/` are named in `AGENTS.md`
    but do not exist. Provider contract coverage lives in
    `api/tests/unit/test_providers.py` instead.
11. **Line-length debt.** Twelve pre-existing backend lines exceed 80 columns
    in `nodes.py` and `queues/router.py`. Every line added during remediation
    stays within the limit.
12. **Rotate local provider keys.** The untracked `.env` holds
    `GEMINI_API_KEY` and `LANGSMITH_API_KEY`. If either was ever displayed or
    shared during development, rotate it.
13. **Checkpoint/audit separation is not directly tested.** Resume is covered
    by `test_review_endpoint_resumes_checkpoint_and_records_decision`, but
    that resumes within one process. No test proves that replay cannot
    rewrite audit history, and no test simulates a restart mid-review.
    AGENTS.md lists checkpoint/audit separation and resume after restart as
    required coverage, so this is a gap rather than a verified property.

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
