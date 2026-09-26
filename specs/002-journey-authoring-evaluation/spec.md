# Feature Specification: Journey, Product Authoring, and Evaluation

**Feature Branch**: `phase2`

**Feature Key**: `002-journey-authoring-evaluation`

**Created**: 2026-09-18

**Status**: Draft

**Input**: Close the new-business and renewal journey gap, let
administrators create products without hand-editing configuration, and add an
isolated production-shaped evaluation environment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the Correct Insurance Journey (Priority: P1)

An applicant chooses new business or renewal before choosing an eligible
product. The application, evidence requirements, checks, and review context
then match that journey. A renewal applicant supplies an existing policy as
untrusted evidence before completing renewal-specific questions.

**Why this priority**: New business and renewal have materially different
evidence and validation needs. Treating them as one flow can omit renewal
evidence or apply the wrong checks.

**Independent Test**: Complete one new-business case and one renewal case for
the same supported product. Confirm that each receives only its configured
fields, documents, rules, and checks, and that reviewers can identify the
journey throughout review and completion.

**Acceptance Scenarios**:

1. **Given** a product supporting both journeys, **When** an applicant selects
   new business, **Then** only new-business requirements and checks apply.
2. **Given** the same product, **When** an applicant selects renewal, **Then**
   the existing policy is requested before renewal-specific questions.
3. **Given** a product that does not support renewal, **When** an applicant
   selects renewal, **Then** that product is unavailable for selection.
4. **Given** a renewal missing required existing-policy evidence, **When** the
   applicant attempts submission, **Then** submission is blocked and the case
   remains mutable.
5. **Given** unreadable or conflicting policy evidence, **When** the case is
   processed, **Then** the current cautious evidence and routing behavior is
   used without treating the policy as trusted system data.

---

### User Story 2 - Author a Product Without Editing YAML (Priority: P2)

An administrator creates a product or a new product version through a guided
builder. They may start blank, clone an immutable version, or upload an expert
configuration. They preview validation and differences, save an immutable
draft, and activate it through a separate confirmed action.

**Why this priority**: The platform can already import configurations, but a
nontechnical administrator cannot discover or safely use that capability.

**Independent Test**: Build a new product from a blank configuration, save it
as a draft, correct a validation error, activate it, and confirm that it then
appears in the applicant catalogue while existing cases remain pinned.

**Acceptance Scenarios**:

1. **Given** an administrator, **When** they choose Create product, **Then** a
   guided builder covers identity, journeys, fields, documents, routing,
   reconciliations, specialist labels, preview, and change review.
2. **Given** an active version, **When** an administrator chooses Create
   version, **Then** an editable draft clone is created and the active version
   remains unchanged.
3. **Given** a valid uploaded configuration, **When** it is imported, **Then**
   it becomes a draft and does not affect applicants until activated.
4. **Given** an unknown field, document, rule, source, operator, or specialist
   label reference, **When** the draft is validated, **Then** save or
   activation is rejected with a precise error.
5. **Given** a valid draft, **When** activation is confirmed, **Then** new
   cases may use it and cases already started retain their pinned version.
6. **Given** any saved version, **When** an administrator exports it, **Then**
   the result is a canonical expert-editable configuration.

---

### User Story 3 - Evaluate Without Touching Development Data (Priority: P3)

A maintainer runs fast deterministic evaluation during development and a
separate production-shaped evaluation before release. The second evaluation
uses public product behavior, begins with empty isolated storage, exercises
selected human-review paths, and leaves development data and files unchanged.

**Why this priority**: Fast evaluation catches routing regressions, but it does
not prove persistence, authorization, checkpoint, audit, queue, or completion
behavior. Both layers are required for credible pilot evidence.

**Independent Test**: Record development row and file counts, run the isolated
90-case evaluation twice, and confirm unchanged development state, fresh
evaluation state, identical deterministic metrics, and complete result files.

**Acceptance Scenarios**:

1. **Given** the reference dataset, **When** fast evaluation runs, **Then** all
   90 cases are scored without using business storage.
2. **Given** a clean isolated environment, **When** end-to-end evaluation
   runs, **Then** it authenticates synthetic users and exercises the public
   case, evidence, recommendation, review, queue, audit, and completion flows.
3. **Given** an earlier evaluation run, **When** evaluation runs again, **Then**
   it starts empty and produces the same fake-provider aggregate metrics.
4. **Given** any evaluation result, **When** it is saved, **Then** it identifies
   the dataset, product configurations, provider, totals, failures, metrics,
   and elapsed time without writing to development storage.
5. **Given** a failed threshold or scenario, **When** evaluation ends, **Then**
   automation receives a failure and the failing cases are identifiable.

### Edge Cases

- An old product configuration has no journey metadata.
- An old case has no stored journey before migration.
- A product supports renewal but its required prior-policy document is absent.
- A draft changes its product code or version to one already present.
- A cloned draft refers to an item removed elsewhere in the configuration.
- Activation is attempted while validation errors remain.
- Two administrators try to activate sibling versions concurrently.
- Evaluation is interrupted and later rerun.
- An evaluation case expects a product version that is not in its manifest.
- An isolated evaluation tries to reach development storage or credentials.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST distinguish `new_business` and `renewal` as
  first-class case journeys.
- **FR-002**: Existing cases and configurations without journey metadata MUST
  retain new-business behavior.
- **FR-003**: Products MUST declare supported journeys, and unsupported
  product-journey combinations MUST be unavailable to applicants.
- **FR-004**: Product fields, document requirements, routing rules, and
  reconciliation checks MUST be configurable by journey.
- **FR-005**: Renewal journeys MUST support a prior-policy evidence stage
  before the renewal application stage.
- **FR-006**: Prior-policy uploads MUST remain applicant-supplied evidence and
  MUST NOT be treated as authoritative policy-system records.
- **FR-007**: Applicants MUST be able to save and replace application answers
  while they own a mutable draft case.
- **FR-008**: Journey identity MUST remain visible in case, queue, review,
  audit, handoff, and evaluation records.
- **FR-009**: Private-car motor and individual/family-floater health MUST
  support both journeys; individual term life MUST support new business only.
- **FR-010**: Final routing MUST remain a recommendation requiring an
  authenticated underwriter's confirmation.
- **FR-011**: Administrators MUST be able to start product authoring from a
  blank configuration, an immutable-version clone, or an uploaded expert
  configuration.
- **FR-012**: The guided builder MUST cover product identity, journeys,
  applicant fields, validation, documents, stages, routing rules,
  reconciliations, specialist labels, normalized preview, and version diff.
- **FR-013**: Guided authoring and expert import MUST produce the same validated
  product configuration and MUST NOT introduce another rule model.
- **FR-014**: Client-side checks MAY improve feedback, but authoritative
  validation MUST reject invalid cross-references and unsupported operations.
- **FR-015**: Every import or builder save MUST create an immutable draft.
- **FR-016**: Activation MUST be a separate confirmed administrator action;
  artificial intelligence MUST NOT create or activate rules.
- **FR-017**: Active versions MUST NOT be editable; administrators MUST clone
  them to create a successor.
- **FR-018**: Activating a version MUST affect only cases created afterward;
  existing cases MUST retain their pinned product and rulebook versions.
- **FR-019**: Administrators MUST be able to retrieve and canonically export
  any product version configuration they are authorized to view.
- **FR-020**: Fast evaluation MUST remain deterministic, in memory, and based
  on a fake provider.
- **FR-021**: The 90-case dataset MUST contain 15 motor new-business, 15 motor
  renewal, 15 health new-business, 15 health renewal, and 30 life
  new-business cases.
- **FR-022**: The dataset MUST contain 30 expected expedited, 30 expected
  standard, and 30 expected specialist recommendations.
- **FR-023**: Each evaluation case MUST identify its journey and exact product
  configuration version.
- **FR-024**: End-to-end evaluation MUST use isolated ephemeral storage,
  synthetic identities, synthetic documents, deterministic providers, and
  disabled external tracing.
- **FR-025**: End-to-end evaluation MUST exercise public user behavior for
  authentication, activation, intake, evidence, submission, recommendations,
  selected review and completion, queues, checkpoints, audit, and idempotency.
- **FR-026**: Evaluation MUST share no database, uploads, network exposure,
  credentials, or persistent storage with development.
- **FR-027**: A saved evaluation result MUST include dataset and configuration
  identities, case totals, aggregate metrics, failures, provider identity,
  and elapsed time.
- **FR-028**: Evaluation failures MUST be machine-detectable and MUST NOT write
  results or business records to development storage.
- **FR-029**: All applicants, documents, users, products, rules, and evaluation
  records introduced by this feature MUST be clearly synthetic.

### Key Entities

- **Journey Type**: The new-business or renewal context selected for a case.
- **Case**: An applicant-owned application pinned to one journey and immutable
  product and rulebook versions once processing begins.
- **Product Configuration**: The single validated definition of journeys,
  fields, documents, rules, reconciliations, and specialist labels.
- **Product Version**: An immutable draft or active configuration version.
- **Document Requirement**: Evidence type, journey applicability, requirement
  status, and intake stage.
- **Evaluation Case**: A synthetic expected outcome pinned to one journey and
  product configuration version.
- **Evaluation Run**: An isolated execution with inputs, metrics, failures,
  provider identity, timing, and integrity hashes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All supported new-business and renewal scenarios complete with
  only their configured fields, documents, rules, and checks.
- **SC-002**: All unsupported product-journey selections are prevented before
  an applicant starts an application.
- **SC-003**: An administrator can create, validate, save, and activate a new
  synthetic product without editing expert configuration text.
- **SC-004**: Every invalid configuration reference is rejected before
  activation with an error that identifies the failing item.
- **SC-005**: Existing cases retain the same pinned configuration and result
  after another product version is activated.
- **SC-006**: Fast evaluation scores all 90 reference cases and preserves the
  required product, journey, and recommendation distribution.
- **SC-007**: Two consecutive isolated fake-provider runs produce identical
  aggregate metrics from fresh state.
- **SC-008**: Isolated evaluation changes zero development database rows and
  zero development upload files.
- **SC-009**: The isolated run proves at least one human confirmation and one
  repeated completion request without duplicate finalization.
- **SC-010**: All final recommendations still require authenticated human
  confirmation; zero cases are approved, declined, bound, priced, issued,
  renewed, or cancelled automatically.

## Assumptions

- Renewal means renewal with the same fictional insurer; portability and
  external policy administration are outside this feature.
- Existing-policy documents are untrusted evidence supplied by applicants.
- Private-car motor and health support both journeys; term life supports only
  new business until a later configuration defines renewal or revival.
- Product authoring keeps expert import and export alongside the guided path.
- The administrator interface retains fast evaluation only; isolated
  end-to-end evaluation is run by maintainers and automation.
- No policy issuance, payment, binding, pricing, cancellation, real insurer
  integration, or real applicant data is included.
- No new runtime dependency is required.
