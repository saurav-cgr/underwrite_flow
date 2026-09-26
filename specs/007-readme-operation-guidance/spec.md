# Feature Specification: Complete README Operation Guidance

**Feature Branch**: `007-readme-operation-guidance`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Show examples for each ENVIRONMENT_MODE; add
Gemini configuration and startup to quickstart; document a local database
reset and reconfiguration; and expand the architecture diagram with the
LangGraph flow."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start in the Intended Mode (Priority: P1)

A local evaluator can select development, evaluation, or production mode and
run the corresponding documented startup command without guessing which mode
is appropriate.

**Why this priority**: The current README names the modes but does not make
their startup choices immediately actionable.

**Independent Test**: A new reader can choose a stated goal, copy its command,
and identify its data-isolation and provider expectations from the README.

**Acceptance Scenarios**:

1. **Given** a reader who wants a normal local demonstration, **When** they
   follow the development example, **Then** they can start it with the fake
   provider and fictional data only.
2. **Given** a reader who wants to run synthetic evaluation, **When** they
   follow the evaluation example, **Then** they can identify its isolated
   state and expected result.
3. **Given** a reader who needs to validate configuration behavior, **When**
   they read the production-mode example, **Then** they understand it is a
   guarded setting and not a production-readiness claim.

---

### User Story 2 - Configure Gemini Deliberately (Priority: P1)

A local evaluator who has an approved Gemini project can configure Gemini and
start the application, while a reader without credentials can continue using
the fake provider.

**Why this priority**: Clear provider setup prevents accidental credential
exposure and makes the credential-free path easy to retain.

**Independent Test**: A reader can find all required configuration fields,
the acknowledgment required before external model use, and the safe
no-credential alternative without source-code inspection.

**Acceptance Scenarios**:

1. **Given** a reader with an approved Gemini project, **When** they follow
   the quickstart, **Then** they can configure the documented fields without
   placing a credential in the README or a command history example.
2. **Given** a reader without Gemini credentials, **When** they read the same
   section, **Then** they can select the deterministic fake provider instead.

---

### User Story 3 - Recover a Local Demonstration (Priority: P2)

A local evaluator can deliberately erase the local synthetic database and
recreate the documented baseline when they need to reconfigure from scratch.

**Why this priority**: Reset guidance is useful only when it is explicit about
irreversible data loss and restores a predictable fictional baseline.

**Independent Test**: A reader can identify the reset's exact scope, confirm
that it permanently removes local data, run the documented recovery path, and
verify the recreated baseline.

**Acceptance Scenarios**:

1. **Given** a local stack containing only fictional data, **When** a reader
   follows the reset instructions, **Then** they receive a prominent warning
   before the destructive command and can reconfigure the environment.
2. **Given** a completed reset, **When** the reader starts the stack, **Then**
   the documented schema, fictional accounts, and built-in product versions
   are restored, without prior cases, documents, reviews, or audit history.

---

### User Story 4 - Trace the Governed Workflow (Priority: P2)

A technical evaluator can trace the selected LangGraph path from intake to
underwriter-confirmed completion using the README architecture diagram.

**Why this priority**: The diagram currently identifies LangGraph but hides
the ordered processing and the human interrupt that protects final routing.

**Independent Test**: A reader can identify the parent workflow, bounded
document work, selected product path, reconciliation, recommendation, human
interrupt, resume, and idempotent completion from the diagram and nearby
legend.

**Acceptance Scenarios**:

1. **Given** a reader viewing the architecture diagram, **When** they trace
   a fictional case, **Then** they can distinguish parallel document work
   from sequential reconciliation and review.
2. **Given** a paused recommendation, **When** the reader follows the flow,
   **Then** they can identify where an authenticated underwriter resumes it
   and why no route completes before that action.

### Edge Cases

- A reader attempts a reset against data they need to retain.
- A reader selects evaluation mode but expects it to share development state.
- A reader supplies a Gemini credential but omits the documented required
  acknowledgement or approved-project condition.
- A reader misreads production mode as an assertion of production readiness.
- A provider, migration, or bootstrap step fails after a reset.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST provide one copyable, labeled startup example for
  each `ENVIRONMENT_MODE` value: development, evaluation, and production.
- **FR-002**: Each mode example MUST state its intended use, provider choice,
  isolation behavior, and any restriction on evaluation loading or startup.
- **FR-003**: README quickstart MUST document the Gemini configuration fields,
  approved-project/no-training acknowledgment, safe credential handling, and
  startup command without exposing a credential value.
- **FR-004**: README MUST retain a clearly visible fake-provider path that
  needs no cloud credential and uses fictional data only.
- **FR-005**: README MUST provide a clearly labeled local database-reset and
  reconfiguration procedure, including the exact destructive scope, a warning
  that data is permanently removed, prerequisite stack state, restart steps,
  and baseline verification.
- **FR-006**: Reset guidance MUST limit itself to an intentional local,
  synthetic demonstration reset and MUST not imply it is a recovery or
  retention procedure for production data.
- **FR-007**: README architecture diagram MUST show the parent LangGraph flow:
  intake, bounded document extraction, selected product path, deterministic
  reconciliation, recommendation, human interrupt, authenticated resume, and
  idempotent handoff/completion.
- **FR-008**: The diagram or adjacent legend MUST distinguish parallel work
  from sequential stages and identify PostgreSQL checkpoints as resumability
  support rather than the business audit source of truth.
- **FR-009**: The added guidance MUST preserve human authority: no automated
  approval, decline, binding, pricing, issuing, renewal, or cancellation.
- **FR-010**: The added examples MUST use only synthetic accounts, documents,
  organizations, products, and rules, and MUST not expose credentials.

### Key Entities

- **Environment mode**: A named local operating context with documented
  purpose, provider choice, isolation, and restrictions.
- **Gemini configuration**: The approved external-provider setup required for
  redacted synthetic task data.
- **Local reset**: A deliberate destructive operation that recreates the
  fictional baseline and removes prior local state.
- **LangGraph flow**: The governed case-processing path, including its human
  pause and resume boundary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new reader can select and start the appropriate documented
  environment mode in under five minutes without source-code inspection.
- **SC-002**: A reader can configure Gemini or select the credential-free fake
  provider using only the quickstart and no credential is displayed there.
- **SC-003**: A reader can identify the local reset's permanent deletion scope
  and restored baseline before executing it.
- **SC-004**: A technical evaluator can trace all eight listed workflow stages
  and the human-resume boundary from the README architecture section.
- **SC-005**: The updated README makes no production-readiness, compliance, or
  automated-insurance-decision claim.

## Assumptions

- This is a documentation-only follow-up to the existing README work and does
  not change behavior, dependencies, credentials, schemas, or providers.
- Existing Docker Compose commands, environment names, and bootstrap behavior
  remain the source of truth for the examples.
- The reset procedure applies only to the local demonstration database and
  its explicitly named related local state; its wording will warn readers to
  back up anything they intend to retain before proceeding.
- The existing text-based architecture diagram remains the visual format and
  is expanded rather than replaced with a binary asset.
