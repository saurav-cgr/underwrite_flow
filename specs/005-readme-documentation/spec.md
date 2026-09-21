# Feature Specification: Improve Project README

**Feature Branch**: `phase2`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Plan how the README should be updated based on
the implemented Phase 2 features, user testing, and architecture overview."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand Product Purpose and Boundaries (Priority: P1)

A prospective user can quickly understand what UnderwriteFlow does, who uses
it, and what it does not claim to do before attempting setup.

**Why this priority**: Clear purpose and safety limits prevent users from
mistaking a fictional triage demonstration for a production insurance system.

**Independent Test**: A new reader can identify supported journeys, the three
roles, human final-decision requirement, and synthetic-data-only boundary in
five minutes or less.

**Acceptance Scenarios**:

1. **Given** a new reader, **When** they read the opening sections, **Then**
   they can describe the product's recommendation-only role and limits.
2. **Given** a reader considering adoption, **When** they view the feature
   overview, **Then** they can find journeys, product versioning, evidence,
   review, audit, and evaluation capabilities.

---

### User Story 2 - Run and Verify Core Journeys (Priority: P1)

A local evaluator can set up the application, sign in with fictional accounts,
and verify each role's most important workflow without consulting source code.

**Why this priority**: The README must turn a successful startup into a
repeatable, observable demonstration.

**Independent Test**: A new evaluator completes one new-business or renewal
case, records a human decision, and runs documented automated checks.

**Acceptance Scenarios**:

1. **Given** a local checkout, **When** an evaluator follows quickstart,
   **Then** they can start the application and sign in using documented demo
   identities.
2. **Given** an applicant case, **When** an evaluator follows a role guide,
   **Then** they can submit evidence and observe its recommendation.
3. **Given** a submitted case, **When** an underwriter follows the guide,
   **Then** they can inspect evidence and confirm or override a route.
4. **Given** an administrator, **When** they follow the guide, **Then** they
   can inspect product versions and safely run a synthetic evaluation.

---

### User Story 3 - Understand System Shape and Safe Extension Points
  (Priority: P2)

A technical evaluator can use one architecture overview to understand data
flow, component responsibilities, human controls, and supported customization
boundaries.

**Why this priority**: A concise visual model helps readers assess the project
without searching through implementation details.

**Independent Test**: A technical evaluator can trace a case from intake to
human completion and identify where configuration, evidence, workflow, audit,
and evaluation fit.

**Acceptance Scenarios**:

1. **Given** a reader viewing the architecture overview, **When** they trace
   a case, **Then** they can identify user roles, application interface,
   business workflow, stored records, and controlled provider boundary.
2. **Given** a reader planning customization, **When** they read extension
   guidance, **Then** they can identify approved configuration and provider
   paths without assuming automated insurance decisions are allowed.

### Edge Cases

- A reader has no cloud-provider credential and needs a local demonstration.
- A reader mistakes development or evaluation setup for production readiness.
- A reader tries to use real applicant, insurer, or underwriting data.
- A documented command fails because containers are not healthy or an expected
  test service is not running.
- A user starts a renewal case but omits required prior-policy evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST state that UnderwriteFlow is a fictional,
  human-governed insurance triage demonstration.
- **FR-002**: README MUST state that it recommends a route only and requires
  an authenticated underwriter to make every final route decision.
- **FR-003**: README MUST summarize implemented journeys, product authoring,
  evidence reconciliation, review, audit, environment modes, and evaluation.
- **FR-004**: README MUST document role-specific manual verification for
  applicant, underwriter, and administrator users.
- **FR-005**: README MUST document concise setup, automated verification, and
  expected outcomes for core checks.
- **FR-006**: README MUST include an architecture diagram and accompanying
  explanation of component roles, data boundaries, version pinning, immutable
  audit, and human control.
- **FR-007**: README MUST distinguish development, evaluation, and production
  modes without claiming production readiness or compliance certification.
- **FR-008**: README MUST document only fictional accounts, data, products,
  and rules; it MUST reject real data use.
- **FR-009**: README MUST include troubleshooting for common startup, sign-in,
  evaluation-load, and testing failures.
- **FR-010**: README MUST link to deeper project documents instead of
  duplicating detailed operational or architectural material.

### Key Entities

- **README reader**: Prospective user, evaluator, contributor, or technical
  reviewer seeking product and operation guidance.
- **Role journey**: Manual verification path for an applicant, underwriter, or
  administrator.
- **Architecture overview**: Diagram and short explanation of responsibility,
  data flow, safety controls, and approved extension boundaries.
- **Verification guide**: Documented automated and manual checks with expected
  observable results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new reader identifies product purpose, human authority, and
  synthetic-data limits within five minutes.
- **SC-002**: A local evaluator completes one documented role journey without
  source-code inspection.
- **SC-003**: All listed automated checks have a command, prerequisite, and
  expected outcome in the README.
- **SC-004**: A technical evaluator can explain a case's end-to-end flow from
  the architecture overview without reading another document.
- **SC-005**: README contains no claim that the project is production-ready,
  compliant, or able to make a final insurance decision.

## Assumptions

- README remains an onboarding and navigation document; detailed reference
  material stays in existing linked documentation.
- Existing fictional demo accounts and synthetic fixtures remain the only
  examples used.
- The architecture diagram uses readable text-based Markdown so it renders in
  repository viewers without a separate binary asset.
- Setup stays Docker Compose-based and uses existing project commands.
- This feature changes documentation only; it does not change product behavior,
  dependencies, permissions, schemas, or provider configuration.
