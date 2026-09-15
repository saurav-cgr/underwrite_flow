# Main-Branch Remediation Plan

**Sources:** `docs/PRD.md`, `docs/PRD_FINALIZED_DECISIONS.md`, and the
whole-branch review completed on 15 September 2026.

**Status:** Planned; implementation not started.

## Goal

Remediate all P0–P3 review findings through sequential, test-first steps.
Each step remains uncommitted until its report is reviewed and the user says
`continue`. Only then is it committed and the next step started.

The upload boundary will validate content and page count without adding
malware scanning or quarantine. This is an accepted exception, not evidence
of full PRD or pilot readiness.

## Delivery rules

1. Implement exactly one remediation step at a time.
2. Start behavior changes with a focused failing regression test.
3. Run focused Docker-based checks and `git diff --check`.
4. Stop and report files, verification, risks, and the proposed commit.
5. Wait for explicit `continue` before committing and starting the next step.
6. Request separate approval for schema or provider changes.
7. Preserve unrelated changes and the untracked `output/` directory.

## Remediation steps

### R1: Add persistence and concurrency safeguards

Create one additive migration. Do not change `01_initial.py`.

- Add `documents.document_code`. Keep it nullable for legacy rows but require
  it through the API for every new upload.
- Add `cases.review_cycle` for safe needs-information resubmission.
- Add review-cycle and specialist-label metadata to reviews.
- Add storage metadata to product reference documents.
- Replace global case idempotency with applicant-scoped idempotency.
- Add a partial unique index permitting one active version per product.

Approval: obtain explicit schema-migration approval before implementation.

### R2: Repair intake and uploaded-document handling

- Require a valid `document_code` and calculate missing requirements by code,
  never by the number of uploaded files.
- Detect supported content from bytes, reject MIME or extension mismatches,
  and calculate PDF or image page counts on the server.
- Permit document changes for `new` and `needs_information` cases.
- Commit document deletion before removing its file. Retain recoverable
  orphan cleanup if filesystem deletion fails.
- Remove PostgreSQL's public host port from default Compose configuration.
  Add only an explicitly enabled localhost override if development needs it.
- Replace claims that all data stays local with accurate Gemini disclosure.

No scanner or quarantine is included in this step.

### R3: Connect submission to the evidence workflow

- Add applicant `POST /cases/{case_id}/submit`.
- Validate document requirements before workflow processing.
- Invoke local extraction and the bounded evidence graph with no more than
  three concurrent document branches.
- Persist extracted fields, provenance, confidence, conflicts, validations,
  branch failures, and the recommendation.
- Accept provider output only for requested field names. Treat unknown names
  as typed branch failures.
- Execute only the selected product subgraph and preserve deterministic route
  precedence.
- Reconcile database state with the checkpoint idempotently so commit failure
  cannot leave an invisible paused workflow.
- Keep `thread_id` stable and use `review_cycle` as checkpoint namespace.

Approval: obtain explicit provider-change approval before implementation.

### R4: Complete the human-review journey

- Keep `POST /reviews/{case_id}/start` as the idempotent underwriter entry
  point, but return the persisted pending review instead of starting work.
- Return the case summary, evidence and locators, conflicts, missing facts,
  extraction failures, recommendation reasons, and specialist labels.
- Require evidence acknowledgement before a decision.
- Trim reasons and reject whitespace-only text, same-route overrides, and
  incomplete specialist selections.
- Resolve manual recommendations to one of `expedited`, `standard`, or
  `specialist`; never persist `manual` as the final route.
- Make review and completion retryable. Keep reviewed cases awaiting handoff
  visible with a retry action.
- Show the human-selected route and specialist label in completed queues and
  handoff payloads.

### R5: Implement needs-information recovery

- Add applicant `POST /cases/{case_id}/resubmit`.
- Validate updated documents, increment `review_cycle`, record an audit event,
  and run a new checkpoint namespace under the stable workflow thread.
- Add applicant-scoped `GET /cases` listing.
- Restore the latest eligible case after refresh, sign-out, or navigation
  instead of relying on React memory.

### R6: Harden product configuration

- Compile and validate every routing condition before import or activation.
- Reject unsupported operators, malformed paths, and unknown field names.
- Serialize activation and rely on the database index to prevent concurrent
  active versions.
- Add Administrator-only upload, list, and delete APIs for versioned product
  reference documents, with storage, hashes, and audit metadata.
- Allow references to inform extraction, but never create or activate rules.
- Await history refreshes, bind previews to the current YAML hash, clear stale
  previews after edits, and show active-version metadata in the admin UI.

### R7: Make audit and evaluation trustworthy

- Record product and rulebook IDs and hashes, document IDs and hashes,
  evidence provenance, validations, recommendation output, human decisions,
  specialist destination, and handoff in append-only audit events.
- Keep audit details sanitized; exclude secrets and full document contents.
- Run evaluation fixtures through the real evidence and routing pipeline.
- Calculate all metrics from produced outputs rather than copied labels.
- Add negative controls proving that changed outputs reduce relevant metrics.

### R8: Finish frontend correctness and accessibility

- Parse the backend `{error: {message, ...}}` envelope consistently.
- Add recovery states for failed completion, interrupted processing, and stale
  sessions.
- Replace invalid ARIA list or table structures with semantic markup or
  complete ownership structures.
- Verify keyboard use, focus, labels, dialogs, status announcements, and
  non-color cues for all three roles.

### R9: Run release acceptance

- Run all API unit, integration, and contract tests.
- Run web tests and the production build.
- Verify migration upgrade and current revision against an existing database.
- Run the deterministic smoke path and browser-based role journeys.
- Inspect staged files for secrets and synthetic-data compliance.
- Record the upload-security exception in the final readiness report.

## Public contract changes

- Document upload requires multipart `document_code`; client `page_count` is
  no longer trusted.
- `GET /cases` lists the authenticated applicant's cases.
- `POST /cases/{id}/submit` starts processing.
- `POST /cases/{id}/resubmit` starts a new review cycle.
- `ReviewStartResponse` gains typed summary, evidence, conflict, failure,
  missing-information, and specialist-option fields.
- `ReviewCommand` gains `specialist_label`; final routes remain limited to the
  three PRD routes.
- Queue items expose recommendation and final human route separately.
- Product reference-document APIs require the Administrator role.
- The web client adopts the backend's nested error envelope.

The bundled web client and API may change together. No external API consumer
is currently documented, so a compatibility layer is not required.

## Verification scenarios

- Spoofed, corrupt, oversized, or mislabelled uploads; computed page counts;
  document codes; failed file deletion; applicant-scoped idempotency.
- Bounded extraction, stable joins, sibling failure isolation, selected
  subgraph execution, provider field filtering, and restart recovery.
- Needs-information cycles, whitespace reasons, manual recommendations,
  same-route overrides, specialist labels, duplicate reviews, and handoff
  retry.
- Concurrent activation and invalid rule import at service and database
  boundaries.
- Evaluation negative controls and audit reconstruction.
- Reload recovery, nested API errors, keyboard operation, focus, labels,
  dialogs, status semantics, and non-color state cues.

## Assumptions and release boundary

- All findings from the main-branch review are included.
- Existing helpers, provider protocols, graph code, and UI components will be
  extended before introducing new abstractions or dependencies.
- Malware scanning and quarantine are excluded by user choice. The product
  must not be called fully PRD-ready or pilot-ready until this is resolved.
- Authentication roles and human decision authority remain unchanged.
- The immutable migration baseline and synthetic-data boundary remain intact.
