---

description: "Tasks for improving project README"
---

# Tasks: Improve Project README

**Input**: Design documents from `specs/005-readme-documentation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/readme-content.md, quickstart.md

**Tests**: No automated test task. This documentation-only feature uses the
manual validation steps in quickstart.md.

**Organization**: Tasks follow user stories. All content changes target one
file, so implement sequentially to avoid edit conflicts.

## Phase 1: Setup

**Purpose**: Verify facts before changing onboarding documentation.

- [X] T001 Verify commands, fictional accounts, and safety claims for
  `README.md` against `Makefile`, `web/src/entry.tsx`, and `.env.example`.

---

## Phase 2: Foundational

**Purpose**: Establish required README structure and source links.

- [X] T002 Restructure `README.md` to contract order in
  `specs/005-readme-documentation/contracts/readme-content.md`.

**Checkpoint**: README skeleton preserves human authority, synthetic-data, and
production-readiness limits before story content begins.

---

## Phase 3: User Story 1 - Product Purpose and Boundaries (Priority: P1)

**Goal**: Reader understands product purpose, implemented features, and limits.

**Independent Test**: Reader identifies roles, journeys, recommendation-only
behavior, final human authority, and synthetic-data-only limit in five minutes.

- [X] T003 [US1] Add product purpose and recommendation-only boundary to
  `README.md` using `docs/PRD.md` and `docs/PRD_FINALIZED_DECISIONS.md`.
- [X] T004 [US1] Add implemented feature map to `README.md` for journeys,
  authoring, reconciliation, review, audit, environments, and evaluation.

**Checkpoint**: User Story 1 is independently readable and does not claim
production readiness, compliance, or final insurance decisions.

---

## Phase 4: User Story 2 - Run and Verify Core Journeys (Priority: P1)

**Goal**: Local evaluator starts fake-provider demo and verifies every role.

**Independent Test**: Evaluator completes one role journey and runs documented
checks without source-code inspection.

- [X] T005 [US2] Add fake-provider quickstart and fictional account table to
  `README.md`; use only values verified in `web/src/entry.tsx`.
- [X] T006 [US2] Add applicant, underwriter, and administrator manual checks
  to `README.md`, linking detail to `docs/DEMO.md`.
- [X] T007 [US2] Add `make test-api`, `make test-web`, `make smoke`, and
  `make evaluate-e2e` guidance to `README.md` from `Makefile`.

**Checkpoint**: User Story 2 documents setup, expected role outcomes, and
automated verification without adding a new script.

---

## Phase 5: User Story 3 - Architecture and Extension Boundaries (Priority: P2)

**Goal**: Technical evaluator traces case flow and safe customization points.

**Independent Test**: Evaluator traces intake through human completion and
identifies configuration, evidence, workflow, audit, and evaluation locations.

- [X] T008 [US3] Add Mermaid architecture diagram to `README.md`, adapted from
  `docs/ARCHITECTURE.md` and meeting `contracts/readme-content.md`.
- [X] T009 [US3] Add architecture invariants and extension boundaries to
  `README.md`, including pinned versions, redaction, audit, and human control.
- [X] T010 [US3] Add environment and evaluation summary to `README.md`, linking
  detailed loading instructions and preserving production refusal warning.

**Checkpoint**: User Story 3 shows end-to-end ownership and no provider or
model is presented as final decision authority.

---

## Phase 6: Polish and Cross-Cutting Validation

**Purpose**: Make README discoverable, accurate, readable, and safe.

- [X] T011 Add troubleshooting, known limits, and curated reference links to
  `README.md` using `docs/ARCHITECTURE.md`, `docs/DEMO.md`, and feature docs.
- [ ] T012 Run every scenario in
  `specs/005-readme-documentation/quickstart.md` against `README.md`.
- [ ] T013 Check line length, Markdown links, Mermaid rendering, and diff
  whitespace for `README.md` with `git diff --check`.

---

## Dependencies and Execution Order

- Phase 1 precedes Phase 2 because all README claims need verification.
- Phase 2 precedes user stories because it creates the required section order.
- User Story 1 provides opening context for User Stories 2 and 3.
- User Stories 2 and 3 can be drafted separately, but both edit `README.md`.
- Phase 6 follows all story content.

## Parallel Opportunities

No safe parallel file edits: every implementation task changes `README.md`.

Parallel research is possible before T002:

```text
Task: "Verify README commands against Makefile and Compose files."
Task: "Verify README role claims against docs/DEMO.md and web/src/entry.tsx."
Task: "Verify README safety claims against docs/ARCHITECTURE.md and PRD."
```

## Implementation Strategy

### MVP First

1. Complete T001-T004.
2. Review product boundaries and feature map.
3. Stop for approval before adding the broader onboarding material.

### Incremental Delivery

1. Add purpose and safety context.
2. Add runnable role and automated verification guidance.
3. Add architecture, environment, troubleshooting, and references.
4. Complete quickstart validation and formatting checks.
