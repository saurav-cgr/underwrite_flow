---

description: "Task list for complete README operation guidance"
---

# Tasks: Complete README Operation Guidance

**Input**: Design documents from `/specs/007-readme-operation-guidance/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/readme.md`, and `quickstart.md`

**Tests**: No new automated test suite is requested. Validation tasks use the
existing Compose rendering and repository checks described by the feature.

**Scope**: Documentation-only. Update `README.md`; reuse existing Compose,
environment, provider, and architecture behavior without changing runtime
code or configuration contracts.

## Phase 1: Setup (Source-of-Truth Review)

**Purpose**: Confirm the existing operational commands and safety boundaries
before editing the README.

- [X] T001 Review `README.md`, `.env.example`, `compose.yaml`,
  `compose.evaluation.yaml`, and `compose.production.yaml` to record the
  existing mode, provider, isolation, volume, and bootstrap behavior

## Phase 2: Foundational (Documentation Constraints)

**Purpose**: Establish the shared content boundaries that all story work must
  preserve.

**⚠️ CRITICAL**: All story edits depend on these constraints.

- [X] T002 Confirm the README acceptance checklist in
  `specs/007-readme-operation-guidance/contracts/readme.md`, including
  synthetic-data-only language, no credential values, human confirmation, and
  reset scope limited to `postgres_data` and `uploads_data`

**Checkpoint**: Source-of-truth commands and documentation safety constraints
are confirmed; story work can proceed in priority order.

---

## Phase 3: User Story 1 - Start in the Intended Mode (Priority: P1) 🎯 MVP

**Goal**: Let a reader choose development, evaluation, or production mode and
copy a correct startup path with its provider, isolation, and restrictions.

**Independent Test**: A new reader can select a stated goal, copy the labeled
command from `README.md`, and explain the mode's provider and data boundary
without inspecting source code.

### Implementation for User Story 1

- [X] T003 [US1] Add a labeled environment-mode quickstart section to
  `README.md` with one copyable development command using
  `GENERATION_PROVIDER=fake`, fictional-data-only wording, and local-state
  expectations
- [X] T004 [US1] Add the isolated evaluation startup example to `README.md`
  using `compose.evaluation.yaml`, stating fake-provider use, separate state,
  synthetic evaluation scope, and expected evaluation result
- [X] T005 [US1] Add the production-mode guard example to `README.md` using
  `compose.yaml` plus `compose.production.yaml`, stating that evaluation
  loading is refused and that the setting is not a production-readiness claim

**Checkpoint**: User Story 1 is independently testable from `README.md` using
only the three documented mode paths.

---

## Phase 4: User Story 2 - Configure Gemini Deliberately (Priority: P1)

**Goal**: Let an approved Gemini user configure the existing provider safely
while preserving a credential-free fake-provider path.

**Independent Test**: A reader can find every required Gemini field and
acknowledgment in `README.md`, understand redaction and approved-project
requirements, and choose fake without a cloud credential.

### Implementation for User Story 2

- [X] T006 [US2] Add a credential-safe Gemini quickstart subsection to
  `README.md` that directs readers to `.env.example` and names
  `GENERATION_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
  `GEMINI_NO_TRAINING_ACKNOWLEDGED`, `PROVIDER_ALLOWED_HOSTS`, and
  `PII_REDACTION_TERMS`
- [X] T007 [US2] Document the approved Gemini-project, no-training
  acknowledgment, redacted synthetic task-data boundary, and safe secret
  handling in `README.md` without showing a credential value or placing one in
  command history examples
- [X] T008 [US2] Add the Gemini startup command and retain an adjacent
  no-credential `GENERATION_PROVIDER=fake` path in `README.md`, clarifying that
  normal local checks remain fictional and deterministic

**Checkpoint**: User Story 2 is independently testable by reading the Gemini
and fake-provider quickstart paths in `README.md`.

---

## Phase 5: User Story 3 - Recover a Local Demonstration (Priority: P2)

**Goal**: Let an evaluator deliberately reset only local synthetic database and
upload state, then recreate the documented empty baseline.

**Independent Test**: Before running the command, a reader can identify the
permanent deletion scope; afterward, they can restart the stack and verify
fictional accounts and product versions with no prior case, document, review,
or audit records.

### Implementation for User Story 3

- [X] T009 [US3] Add a clearly labeled local reset warning to `README.md`
  stating that the operation is irreversible and permanently removes only the
  development `postgres_data` database volume and `uploads_data` uploaded-file
  volume, and is not production recovery or retention guidance
- [X] T010 [US3] Document the reset procedure in `README.md` with the
  prerequisite stopped development stack and the narrow volume-removal
  command, explicitly avoiding `docker compose down -v`
- [X] T011 [US3] Document restart and baseline verification in `README.md`,
  including migration and product bootstrap reruns, fictional demo accounts
  and built-in product versions, and absence of prior cases, documents,
  reviews, and audit history

**Checkpoint**: User Story 3 is independently testable from the warning,
bounded command, recovery steps, and baseline checklist in `README.md`.

---

## Phase 6: User Story 4 - Trace the Governed Workflow (Priority: P2)

**Goal**: Let a technical evaluator trace the complete governed LangGraph path,
including bounded parallel work and the human resume boundary.

**Independent Test**: A reader can identify all required workflow stages and
distinguish parallel document extraction, sequential reconciliation, checkpoint
resume support, immutable audit history, and authenticated underwriter
confirmation from `README.md`.

### Implementation for User Story 4

- [X] T012 [US4] Expand the Mermaid architecture diagram in `README.md` to
  show the parent LangGraph flow through intake, bounded document fan-out,
  selected product path, deterministic reconciliation, and route
  recommendation
- [X] T013 [US4] Extend the README Mermaid flow and nearby legend to show the
  human interrupt, authenticated underwriter resume, idempotent queue
  handoff/completion, and the rule that no route completes before confirmation
- [X] T014 [US4] Add README legend text distinguishing bounded parallel work
  from sequential stages, PostgreSQL checkpoints as resume support, and
  immutable business audit events as the source of truth

**Checkpoint**: User Story 4 is independently testable by tracing one
fictional case through the README architecture section.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the completed README against the feature contract and
existing project behavior without expanding scope.

- [X] T015 Review `README.md` against
  `specs/007-readme-operation-guidance/contracts/readme.md` and all FR-001
  through FR-010 requirements, correcting omissions while preserving human
  authority and synthetic-data boundaries
- [X] T016 [P] Run `docker compose config`,
  `docker compose -f compose.evaluation.yaml config`, and
  `docker compose -f compose.yaml -f compose.production.yaml config` against
  `compose.yaml`, `compose.evaluation.yaml`, and `compose.production.yaml` to
  verify every command documented in `README.md` matches committed files
- [X] T017 Execute the existing checks from
  `specs/007-readme-operation-guidance/quickstart.md` (`make test-api`,
  `make test-web`, and `make smoke`) and
  record any documentation-relevant discrepancy without changing application
  behavior
- [X] T018 [P] Render `README.md` in a Mermaid-capable Markdown viewer and
  verify the mode examples, Gemini section, reset warning, and LangGraph
  legend remain readable and copyable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; confirm the existing source of truth.
- **Foundational (Phase 2)**: Depends on Setup; fixes shared safety and scope
  constraints before README edits.
- **User Stories (Phases 3-6)**: Depend on the Foundational phase. Because all
  implementation tasks edit `README.md`, complete them sequentially in
  priority order to avoid merge conflicts.
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Phase 2 and is the MVP increment.
- **User Story 2 (P1)**: Depends only on Phase 2; keep its fake-provider path
  consistent with User Story 1.
- **User Story 3 (P2)**: Depends only on Phase 2; its volume names must match
  the mode commands documented by User Story 1.
- **User Story 4 (P2)**: Depends only on Phase 2; its flow must preserve the
  human-authority wording used by User Stories 1-3.

### Within Each User Story

- Implement the README content tasks in listed order.
- Keep commands copied from the existing Compose and environment files.
- Validate the story at its checkpoint before proceeding to the next story.

### Parallel Opportunities

- No story implementation tasks are marked `[P]`: they all modify the same
  `README.md` and should not run concurrently.
- After the README edit is complete, the Compose rendering checks in T016 and
  the textual contract review in T015 can be performed independently.
- Mermaid rendering in T018 can run independently of the command checks once
  all README content tasks are complete.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T002 to confirm source behavior and safety boundaries.
2. Complete T003-T005 for the three actionable environment-mode paths.
3. Validate the User Story 1 checkpoint and stop for review/demo.

### Incremental Delivery

1. Add User Story 2's Gemini and fake-provider guidance.
2. Add User Story 3's bounded reset and baseline verification.
3. Add User Story 4's governed LangGraph flow and legend.
4. Run Phase 7 validation and existing checks.

### Parallel Team Strategy

Implementation remains single-owner because every story edits `README.md`.
Reviewers can parallelize T015, T016, and T018 after the final content is
present.

## Notes

- Every task includes an exact repository path.
- `[USn]` labels map directly to the four stories in `spec.md`.
- No application code, schema, dependency, provider, or destructive reset
  implementation is introduced by this feature.

---

## Phase 8: Convergence

- [X] T019 State the configured provider choice in the production startup path
  in `README.md` per FR-002 (partial)
- [X] T020 Add an explicit local `.env` reconfiguration step before the reset
  restart command in `README.md` per FR-005 (partial)
