# Feature Specification: Add README Project Tour

**Feature Branch**: `phase2`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Add README sections inspired by the supplied
Decision Memory Assistant README."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand the Demonstration Quickly (Priority: P1)

A reader can see what UnderwriteFlow demonstrates, its main capabilities, and
its safety boundary without reading the full README.

**Why this priority**: A concise project tour makes the existing detailed
setup and verification guidance easier to approach.

**Independent Test**: A new reader identifies the product purpose, supported
triage routes, human decision boundary, and synthetic-data-only restriction in
three minutes.

**Acceptance Scenarios**:

1. **Given** a reader at the README, **When** they scan its opening and project
   tour, **Then** they can explain that the application recommends work queues,
   rather than making insurance decisions.
2. **Given** a reader comparing the project with the supplied reference,
   **When** they view the capability summary, **Then** they can find an
   UnderwriteFlow-specific description of each implemented capability.

---

### User Story 2 - Follow the Case Lifecycle (Priority: P1)

A technical evaluator can understand how an application moves from fictional
intake through evidence review to an underwriter-confirmed route.

**Why this priority**: The current architecture diagram is useful, but a short
plain-language lifecycle makes the control points easier to understand.

**Independent Test**: An evaluator traces one case from applicant submission
to completion and identifies deterministic reconciliation, version pinning,
audit history, and the required underwriter confirmation.

**Acceptance Scenarios**:

1. **Given** a reader viewing the project tour, **When** they follow the
   lifecycle, **Then** they can identify the sequence from evidence intake to
   human confirmation.
2. **Given** a reader considering an extension, **When** they read the
   boundary notes, **Then** they know that product configuration and approved
   provider adapters are extension paths, not automated finalization paths.

---

### User Story 3 - Navigate the README Efficiently (Priority: P2)

A reader can jump between the overview, setup, role verification, architecture,
evaluation, limits, and troubleshooting sections.

**Why this priority**: The README has grown into a complete onboarding guide;
clear navigation keeps it skimmable.

**Independent Test**: A reader locates any listed major section from a compact
table of contents in one selection.

**Acceptance Scenarios**:

1. **Given** a long README, **When** a reader selects an item in its contents,
   **Then** they reach the corresponding section.

### Edge Cases

- A reader expects a capability table to describe production or compliance
  readiness.
- A reader mistakes a generated recommendation for an insurance approval,
  decline, price, issuance, renewal, or cancellation.
- A reader attempts to use non-fictional documents or applicant data.
- A README viewer does not render the existing architecture diagram.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST include a compact, linked table of contents for its
  major onboarding and reference sections.
- **FR-002**: README MUST include a plain-language "What this demonstrates"
  section that describes the fictional, human-governed triage purpose.
- **FR-003**: README MUST include a capability table covering intake journeys,
  product versioning, reconciliation, route recommendation, human review and
  audit, and synthetic evaluation.
- **FR-004**: README MUST include a short case-lifecycle explanation adjacent
  to the architecture overview, from intake through human confirmation.
- **FR-005**: README MUST include a component-responsibility summary that
  separates interface, business workflow, storage, provider boundary, and
  isolated evaluation responsibilities.
- **FR-006**: README MUST retain and reinforce that only authenticated
  underwriters confirm or override routes, and that no automated insurance
  decision is made.
- **FR-007**: README MUST retain the fictional-data-only restriction and avoid
  adding real people, insurers, products, rules, credentials, or claims.
- **FR-008**: README MUST direct readers to existing detailed guides rather
  than duplicating setup, testing, evaluation, or architecture instructions.
- **FR-009**: README MUST describe known limitations and trade-offs factually,
  without production-readiness or compliance claims.

### Key Entities

- **Project tour**: A short orientation layer that precedes detailed README
  instructions.
- **Capability summary**: A scannable mapping from user-facing capability to
  its demonstrated behavior and boundary.
- **Case lifecycle**: The plain-language path from fictional intake to human
  route confirmation.
- **Component responsibility summary**: A concise map of the system's major
  responsibilities and controlled data boundaries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new reader identifies product purpose, human authority, and
  synthetic-data limits within three minutes.
- **SC-002**: Every capability in the project tour maps to an existing README
  section or linked deeper guide.
- **SC-003**: A technical reader can trace the case lifecycle and identify all
  five responsibility areas without inspecting source code.
- **SC-004**: All major README sections are reachable from the contents in one
  selection in a Markdown renderer.
- **SC-005**: The added content contains no production-readiness, compliance,
  or automated-insurance-decision claim.

## Assumptions

- The supplied Decision Memory Assistant README is inspiration for structure
  and readability only; wording and product claims remain UnderwriteFlow's.
- The current README remains the canonical onboarding document, so new material
  augments rather than replaces existing quickstart and verification content.
- Existing Mermaid architecture remains the primary visual; this feature adds
  concise explanation instead of another diagram.
- This is a documentation-only change. It changes no application behavior,
  dependencies, authorization, provider configuration, or data schema.
