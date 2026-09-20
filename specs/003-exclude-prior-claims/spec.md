# Feature Specification: Exclude Prior Claims from New Business

**Feature Branch**: `003-exclude-prior-claims`

**Created**: 2026-09-20

**Status**: Draft

**Input**: User description: "new application shouldnt have prior claims"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Without Prior Claims (Priority: P1)

A new-business applicant completes an application without being asked about
prior claims. Prior claims do not affect the application's completeness,
evidence checks, or recommended triage route.

**Why this priority**: A question that does not apply to new business creates
confusion and can produce an incorrect recommendation.

**Independent Test**: Complete a new-business application for each product
that defines prior-claims behavior. Confirm that no prior-claims answer is
requested and that the case can reach human review without one.

**Acceptance Scenarios**:

1. **Given** a new-business application, **When** the applicant views the
   application questions, **Then** no prior-claims question is shown.
2. **Given** a complete new-business application with no prior-claims answer,
   **When** the applicant submits it, **Then** submission succeeds without a
   missing-information finding for prior claims.
3. **Given** a submitted new-business application, **When** its recommendation
   is calculated, **Then** prior-claims rules and checks do not affect the
   recommendation.
4. **Given** a new-business case under review, **When** an underwriter views
   its answers and findings, **Then** prior claims are not presented as an
   applicant answer, missing item, or reconciliation result.

---

### User Story 2 - Preserve Renewal Claims Handling (Priority: P2)

A renewal applicant continues to provide prior-claims information wherever
the active product configuration requires it.

**Why this priority**: Removing prior claims from new business must not weaken
the existing renewal journey or its evidence checks.

**Independent Test**: Complete a renewal application whose active product
requires prior claims. Confirm that the question, validation, rules, and
checks behave as before.

**Acceptance Scenarios**:

1. **Given** a renewal whose product requires prior claims, **When** the
   applicant completes the application, **Then** the prior-claims question and
   validation remain available.
2. **Given** a renewal with prior-claims information, **When** its evidence is
   reconciled and recommendation calculated, **Then** the configured renewal
   rules and checks may use that information.

---

### User Story 3 - Keep Versioned Cases Stable (Priority: P3)

An underwriter can rely on an existing case retaining the product and rulebook
version selected when processing began, while newly started cases use the
corrected journey behavior.

**Why this priority**: Changing an in-progress case would undermine audit
reconstruction and repeatability.

**Independent Test**: Compare a case pinned before the corrected product
version with a case started afterward. Confirm that the earlier case is
unchanged and the newer case excludes prior claims from new business.

**Acceptance Scenarios**:

1. **Given** a case already pinned to an earlier product version, **When** a
   corrected version becomes active, **Then** the existing case retains its
   original questions, checks, results, and audit history.
2. **Given** a new case started after the corrected version becomes active,
   **When** new business is selected, **Then** the case uses the corrected
   behavior.

### Edge Cases

- A stale client sends a prior-claims value for a new-business application.
- A saved new-business draft is pinned to an earlier product version.
- A renewal omits prior claims when its active product requires the field.
- A new-business rule or check still refers to prior claims after the field is
  excluded.
- An evaluation example includes a prior-claims answer for new business.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: New-business applications MUST exclude prior claims from their
  applicable questions.
- **FR-002**: New-business submission MUST NOT require a prior-claims answer or
  report prior claims as missing information.
- **FR-003**: The system MUST reject a prior-claims value submitted for new
  business as inapplicable to that journey.
- **FR-004**: New-business routing rules MUST NOT evaluate prior claims.
- **FR-005**: New-business reconciliation checks MUST NOT consume, compare, or
  report prior-claims information.
- **FR-006**: Reviews, queues, progress, and audit views MUST NOT present prior
  claims as a new-business answer or finding.
- **FR-007**: Renewal applications MUST retain configured prior-claims fields,
  validation, routing rules, and reconciliation checks.
- **FR-008**: Configuration validation MUST reject any new-business rule or
  check that refers to prior claims.
- **FR-009**: New and updated synthetic evaluation cases for new business MUST
  omit prior-claims answers and expected findings.
- **FR-010**: Cases already pinned to a product and rulebook version MUST
  retain that version and its reproducible behavior.
- **FR-011**: The change MUST remain inside the existing single-tenant and
  local data boundary and MUST NOT add an external data flow.
- **FR-012**: Audit history MUST remain append-only; correction MUST occur
  through a new version rather than alteration of historical case events.
- **FR-013**: Triage output MUST remain a recommendation that requires an
  authenticated underwriter to confirm or override the final route.
- **FR-014**: All applicants, answers, documents, products, rules, and
  evaluation records used by this feature MUST be synthetic.

### Key Entities *(include if feature involves data)*

- **Journey Type**: The new-business or renewal context that determines which
  configured fields, rules, and checks apply.
- **Product Configuration Version**: The immutable definition of journey
  fields, validation, routing rules, and reconciliation checks.
- **Case**: An application pinned to one journey and one product configuration
  version when processing begins.
- **Prior-Claims Answer**: A renewal-only count or history of prior insurance
  claims when required by the active configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of supported new-business application screens and contracts
  omit the prior-claims question.
- **SC-002**: 100% of valid new-business applications submit without a
  prior-claims answer or related missing-information finding.
- **SC-003**: 100% of new-business routing and reconciliation scenarios are
  unaffected by prior-claims values.
- **SC-004**: 100% of stale new-business submissions containing prior claims
  receive a precise inapplicable-field error.
- **SC-005**: All renewal regression scenarios retain their configured
  prior-claims behavior.
- **SC-006**: Existing pinned-case scenarios retain identical questions,
  findings, recommendations, and audit reconstruction.
- **SC-007**: Every final route still requires authenticated underwriter
  confirmation.

## Assumptions

- "New application" means the existing `new_business` journey.
- "Prior claims" means the existing prior insurance claims field and the
  rules or checks that depend on it.
- Current-incident evidence and unrelated loss information are outside this
  feature.
- Prior claims remain valid for renewal only where the active product version
  requires them.
- The correction is delivered through a new immutable product configuration
  version; historical versions and case audit events are not rewritten.
- No tenant, authorization, provider, storage, or external tracing boundary
  changes are required.
- Deterministic reconciliation remains configuration-driven and excludes
  inapplicable new-business inputs.
- Human decision authority remains unchanged.
