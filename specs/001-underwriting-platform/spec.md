# Feature Specification: Governed Underwriting Platform

<!-- ROUTE=direct | WRITE_READY=1 | READ_READY=0 | EXISTING=0 |
PLANNED_DISPATCH=0 | LEAD=specification | REASON=single_artifact |
DETAIL=One coupled feature spec is cheaper to draft and validate directly. -->

**Feature Branch**: `not-created`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Build a single-tenant underwriting platform with
JWT authentication, dynamic RBAC, configurable schemas and rulebooks, existing
Gemini and Ollama extraction, deterministic evidence reconciliation, an
underwriter queue, and immutable audit history."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administer Secure Access (Priority: P1)

An administrator creates users, defines roles from granular permissions, and
assigns those roles so each person can access only authorized operations.
Users authenticate, refresh their session, and inspect their own identity and
permissions through the published authentication operations.

**Why this priority**: No case, configuration, or review action is safe until
identity and authorization are enforced consistently.

**Independent Test**: Create two custom roles with different scopes, assign
them to separate users, authenticate both users, and prove that each protected
operation allows or denies access according to effective permissions.

**Acceptance Scenarios**:

1. **Given** an active user with valid credentials, **When** the user logs in,
   **Then** the user receives bearer session credentials and can retrieve their
   identity and effective permissions.
2. **Given** a valid refresh credential, **When** the user refreshes the
   session, **Then** a new valid session is issued without another login.
3. **Given** a user without `users:manage`, **When** the user attempts a user or
   role administration action, **Then** access is denied and audited.
4. **Given** an administrator changes a user's role, **When** the user next
   performs a protected action, **Then** the current configured permissions are
   enforced.

---

### User Story 2 - Configure Extraction and Rules (Priority: P1)

An administrator defines and versions document schemas and underwriting
rulebooks for the deployment, previews validation results, and explicitly
activates a valid version without changing application code.

**Why this priority**: Extraction and reconciliation cannot be trustworthy
unless their expected fields and rules are explicit, validated, and pinned.

**Independent Test**: Import one valid schema and rulebook, reject one invalid
configuration, activate the valid version, and verify that a new case pins to
it while an existing case retains its earlier version.

**Acceptance Scenarios**:

1. **Given** a valid YAML or JSON configuration, **When** an authorized
   administrator previews it, **Then** validation shows its document mappings,
   NCB tiers, age thresholds, and renewal rules without activating it.
2. **Given** a validated configuration, **When** the administrator activates
   it, **Then** new processing uses that immutable version and records the
   activation in audit history.
3. **Given** a case pinned to an older configuration, **When** a newer version
   becomes active, **Then** the case continues using its pinned version.

---

### User Story 3 - Extract and Reconcile Evidence (Priority: P1)

An authorized case user submits synthetic PDF or image documents. The platform
extracts schema-defined fields through the existing configured provider,
compares evidence across documents, and produces deterministic discrepancy
verdicts with source references.

**Why this priority**: Evidence extraction and reconciliation provide the core
underwriting triage value.

**Independent Test**: Submit a synthetic application, policy schedule,
registration certificate, and claims history containing known matches,
conflicts, and omissions; verify the expected verdicts and provenance.

**Acceptance Scenarios**:

1. **Given** documents containing matching NCB and asset identifiers, **When**
   processing completes, **Then** their checks return `CLEARED` with evidence
   references.
2. **Given** conflicting NCB, engine, chassis, or registration values, **When**
   processing completes, **Then** each conflict returns
   `FLAGGED_DISCREPANCY` with both source values and the applied rule.
3. **Given** a required document or field is absent, **When** reconciliation
   runs, **Then** the affected check returns `MISSING_EVIDENCE` rather than
   guessing a value.
4. **Given** a previous policy expiry and new policy start date, **When** the
   lapse check runs, **Then** its verdict is derived from the pinned renewal
   rule and those source dates.
5. **Given** the same normalized evidence and pinned rules, **When** checks run
   repeatedly, **Then** verdict values, reasons, and ordering are identical.

---

### User Story 4 - Review and Override a Case (Priority: P1)

An underwriter views flagged discrepancies, missing evidence, confidence
indicators, and provenance in one queue. An authorized underwriter confirms a
route or overrides the recommendation only after entering a rationale.

**Why this priority**: The platform may recommend triage but human authority
must control every final route.

**Independent Test**: Open a flagged case, inspect all evidence links, attempt
an override without permission and without rationale, then complete it with
both requirements satisfied.

**Acceptance Scenarios**:

1. **Given** a processed case, **When** an underwriter opens it, **Then** the
   view shows discrepancies, missing evidence, confidence indicators, source
   evidence, and pinned configuration versions.
2. **Given** a user without `cases:override`, **When** the user attempts an
   override, **Then** the action is denied and no case decision changes.
3. **Given** an authorized underwriter supplies no rationale, **When** an
   override is submitted, **Then** validation rejects it.
4. **Given** an authorized underwriter supplies a rationale, **When** the
   override is submitted, **Then** the final route changes once and the action
   is appended to audit history.

---

### User Story 5 - Inspect Audit History (Priority: P2)

An authorized reviewer inspects an append-only chronology of authentication,
configuration, provider, rule, and human actions for a case without exposing
raw sensitive prompt content.

**Why this priority**: Reviewers need evidence that every automated and human
decision can be reconstructed after processing.

**Independent Test**: Process and override one synthetic case, then verify that
the timeline contains each expected actor, configuration version, hash, token
count, verdict, and rationale and cannot be edited or deleted.

**Acceptance Scenarios**:

1. **Given** a completed extraction, **When** audit history is viewed, **Then**
   it shows provider and model identity, input and output token counts, payload
   hashes, and extraction schema version without raw PII.
2. **Given** a manual override, **When** audit history is viewed, **Then** it
   shows the authenticated user, prior recommendation, final route, rationale,
   and referenced evidence.
3. **Given** an existing audit event, **When** a correction is required,
   **Then** a superseding event is appended and the original remains unchanged.

### Edge Cases

- A user is disabled after a session is issued.
- A refresh credential is expired, malformed, or replayed after replacement.
- A role is changed while the affected user has an active session.
- A configuration is valid YAML or JSON but violates its semantic rules.
- Two administrators try to activate different versions concurrently.
- A document is encrypted, corrupt, unsupported, duplicated, or partly blank.
- Local parsing succeeds but the selected provider times out or returns output
  that does not match the active extraction schema.
- Gemini redaction removes a value required by an extraction schema.
- Ollama is selected but its local service or configured model is unavailable.
- Asset identifiers differ only by whitespace, punctuation, or letter case.
- Policy dates are missing, invalid, equal, or cross a leap day.
- Conflicting documents have equal confidence or no reliable precedence.
- A provider does not report token counts for an invocation.
- An underwriter submits the same finalization command more than once.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each deployment MUST serve one insurer and MUST NOT expose a path
  to another tenant or shared global case state.
- **FR-002**: The platform MUST provide login, session refresh, and current-user
  operations at `POST /auth/login`, `POST /auth/refresh`, and `GET /auth/me`.
- **FR-003**: Protected operations MUST accept sessions only as signed JWT
  bearer credentials in the `Authorization` header.
- **FR-004**: Authentication MUST reject invalid, expired, incorrectly issued,
  incorrectly targeted, or disabled-user sessions.
- **FR-005**: Administrators MUST be able to create and disable users, create
  custom roles, select granular permission scopes, and assign roles to users.
- **FR-006**: The permission catalogue MUST include `cases:read`,
  `cases:override`, `users:manage`, and `schemas:edit`.
- **FR-007**: Every protected operation MUST enforce its required scopes using
  the authenticated user's current effective permissions.
- **FR-008**: Authentication failures, authorization denials, user changes,
  role changes, and permission changes MUST append audit events.
- **FR-009**: Administrators with `schemas:edit` MUST be able to import,
  validate, preview, version, and activate YAML or JSON schemas and rulebooks.
- **FR-010**: Configuration MUST define expected document types and fields,
  document mappings, NCB tier progression, product-specific age thresholds,
  policy renewal rules, and evidence requirements without insurer-specific
  application code.
- **FR-011**: Every case MUST retain the exact schema and rulebook versions
  selected when its processing begins.
- **FR-012**: Document parsing MUST accept supported synthetic PDFs and images,
  extract local text or image content, and report unsupported or unreadable
  input without silently discarding it.
- **FR-013**: Provider extraction MUST reuse the existing Gemini and Ollama
  provider contract, with Gemini as default and Ollama as optional local mode.
- **FR-014**: Gemini-bound payloads MUST be redacted locally for Aadhaar, PAN,
  contact details, and configured PII before transmission.
- **FR-015**: Provider output MUST be validated against the active extraction
  schema; invalid or unexpected fields MUST produce a visible provider failure.
- **FR-016**: Provider failures MUST preserve successful sibling document
  results and place affected checks into a visible review state.
- **FR-017**: Reconciliation MUST compare NCB claims, engine numbers, chassis
  numbers, registration numbers, previous policy expiry, and new policy start.
- **FR-018**: Every reconciliation check MUST return exactly one of `CLEARED`,
  `FLAGGED_DISCREPANCY`, or `MISSING_EVIDENCE`.
- **FR-019**: Every verdict MUST include a stable check identifier, explanation,
  source evidence references, normalized compared values, and rule version.
- **FR-020**: Reconciliation MUST produce identical ordered verdicts for
  identical normalized evidence and rule versions, without external side
  effects.
- **FR-021**: Missing evidence MUST remain a queue state and MUST NOT become a
  fourth final triage route.
- **FR-022**: The review queue MUST show flagged discrepancies, missing
  evidence, confidence indicators, source provenance, and current status.
- **FR-023**: Confidence indicators MUST identify their source and MUST NOT
  determine a final route without deterministic rules and human confirmation.
- **FR-024**: Only users with `cases:override` MAY override a recommendation,
  and every override MUST include a non-empty rationale.
- **FR-025**: Every final route MUST be confirmed or overridden by an
  authenticated underwriter before queue handoff or finalization.
- **FR-026**: Finalization and queue handoff MUST be idempotent.
- **FR-027**: Audit events MUST be append-only and MUST record authenticated
  user identity, action, timestamp, case or configuration identity, prior and
  resulting states, and relevant schema and rulebook versions.
- **FR-028**: Each provider audit event MUST record provider and model identity,
  reported input and output token counts, and hashes of exact prompt and
  completion payloads without recording prohibited raw PII.
- **FR-029**: If a provider supplies no token count, audit history MUST record
  that the count was unavailable rather than fabricate one.
- **FR-030**: Every automated rule outcome and human decision MUST be linked to
  its evidence, rule version, actor, and rationale.
- **FR-031**: Audit events MUST NOT be updated or deleted; corrections MUST
  append a superseding event linked to the original.
- **FR-032**: All fixtures, documents, users, insurers, products, and rules used
  by the MVP MUST be synthetic and marked for demonstration only.
- **FR-033**: Existing project-owned services, contracts, schemas, components,
  and tests MUST be reused or minimally extended when they satisfy the need.

### Key Entities

- **User**: Authenticated person with status, assigned roles, and audit
  identity.
- **Role**: Administrator-defined name and set of permission scopes.
- **Permission**: Granular authorization scope enforced on protected actions.
- **Session**: Short-lived bearer access and refresh credentials linked to a
  user and their current authorization state.
- **Configuration Version**: Immutable validated schema and rulebook bundle with
  activation state and audit provenance.
- **Case**: Synthetic underwriting submission pinned to one product,
  configuration version, workflow state, and human reviewer.
- **Document**: Synthetic uploaded file with type, local extraction status, and
  evidence references.
- **Extracted Evidence**: Schema-validated field value with source location,
  confidence metadata, provider identity, and configuration version.
- **Reconciliation Verdict**: Deterministic check result, compared values,
  evidence references, explanation, and rule version.
- **Review Decision**: Human confirmation or override with rationale and actor.
- **Audit Event**: Immutable chronological record linked to an actor, action,
  case or configuration, payload hashes, versions, and prior event when needed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of protected operations reject absent, invalid, expired, or
  insufficiently authorized sessions without changing business data.
- **SC-002**: An administrator can create a user, define a custom role, assign
  its scopes, and verify access in under five minutes.
- **SC-003**: 100% of cases retain one immutable schema and rulebook version for
  their complete processing lifecycle.
- **SC-004**: Every supported document produces validated evidence or a visible
  actionable failure; no document branch disappears silently.
- **SC-005**: Repeating reconciliation with identical inputs produces identical
  verdict values, explanations, and ordering in 100% of test runs.
- **SC-006**: 100% of discrepancy and missing-evidence verdicts identify source
  evidence and the exact rule version used.
- **SC-007**: Underwriters can identify all flagged and missing evidence for a
  processed case from one review view within two minutes.
- **SC-008**: 100% of accepted overrides contain an authorized user identity,
  mandatory rationale, prior recommendation, and immutable audit event.
- **SC-009**: 100% of provider invocations record payload hashes and actual
  token counts or an explicit unavailable marker without raw PII exposure.
- **SC-010**: No automated path approves, declines, binds, prices, issues,
  renews, or cancels insurance without authenticated human confirmation.
- **SC-011**: Pure NCB, lapse, and asset checks achieve 100% statement and
  branch coverage and pass deterministic repeatability checks.

## Assumptions

- This specification covers one self-hosted deployment for one fictional
  insurer; multi-tenant hosting and cross-insurer analytics are out of scope.
- Only synthetic demonstration data is permitted during the MVP.
- Existing case intake, provider contracts, local extraction, workflow,
  checkpoint, queue, and audit capabilities are reused before new code is added.
- Gemini remains the default external provider under approved no-training terms;
  Ollama remains an optional local provider and deterministic fakes own tests.
- Configuration applies to motor first while retaining generic support for term
  life, health, and later configured products.
- Confidence indicators assist review but do not replace deterministic rules or
  human judgment.
- Password recovery, enterprise single sign-on, and multi-factor authentication
  are outside this feature unless specified separately.
- Data retention and deletion policy remain governed outside this feature; this
  feature does not introduce automatic audit-event deletion.
