# Tasks: Add README Project Tour

**Input**: Design documents from `specs/006-readme-project-tour/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/readme-project-tour.md`, and `quickstart.md`

**Tests**: No automated test task is required. This is a Markdown-only change;
the quickstart validation and final static checks provide acceptance evidence.

## Phase 1: Setup

**Purpose**: Establish exact insertion points without duplicating existing docs.

- [X] T001 Map `README.md` headings to `contracts/readme-project-tour.md`.

---

## Phase 2: Foundational

**Purpose**: Preserve the current documented safety, setup, and verification
content while preparing a concise project-tour layer.

- [X] T002 Mark project-tour insertion points in `README.md`; retain guides.

**Checkpoint**: Existing onboarding content remains the source of detailed
instructions; user-story work can proceed.

---

## Phase 3: User Story 1 - Understand the Demonstration Quickly (P1) 🎯 MVP

**Goal**: Let a reader identify the fictional, human-governed triage purpose
and main demonstrated capabilities in three minutes.

**Independent Test**: Read only the opening project tour in `README.md`; find
purpose, three routes, underwriter authority, and fictional-data restriction.

- [X] T003 [US1] Add contents and "What this demonstrates" to `README.md`.
- [X] T004 [US1] Add the capability table to `README.md`.
- [X] T005 [US1] Check `README.md` against `contracts/readme-project-tour.md`.

**Checkpoint**: User Story 1 is independently readable and demonstrable.

---

## Phase 4: User Story 2 - Follow the Case Lifecycle (P1)

**Goal**: Let a technical evaluator trace a fictional case to a
human-confirmed route and identify component boundaries.

**Independent Test**: Compare the lifecycle and responsibility text in
`README.md` against its architecture diagram without reading source code.

- [ ] T006 [US2] Add a case lifecycle beside the architecture in `README.md`.
- [ ] T007 [US2] Add component responsibilities to `README.md`.
- [ ] T008 [US2] Check `README.md` lifecycle against `docs/ARCHITECTURE.md`.

**Checkpoint**: User Story 2 explains the existing diagram in text.

---

## Phase 5: User Story 3 - Navigate the README Efficiently (P2)

**Goal**: Let readers jump from contents to all major README sections.

**Independent Test**: Open `README.md` in a Markdown viewer and select each
contents link once.

- [ ] T009 [US3] Validate each contents target and heading anchor in `README.md`
  using `quickstart.md`.

**Checkpoint**: User Story 3 provides one-selection navigation for major topics.

---

## Phase 6: Polish and Cross-Cutting Validation

**Purpose**: Prove the README stays factual, readable, and documentation-only.

- [ ] T010 Check `README.md` for real data or unsafe claims.
- [ ] T011 Run `quickstart.md` validation and `git diff --check`.

---

## Dependencies and Execution Order

- T001 → T002 → T003 through T008 → T009 → T010 → T011.
- US1 is the MVP and should complete before the lifecycle explanation.
- US2 builds on the existing diagram and can start after T002; it shares
  `README.md`, so it remains sequential.
- US3 depends on the contents list created in US1.

## Parallel Opportunities

No safe implementation parallelism: all changes target `README.md`.
After edits, separate readers may validate the project tour and architecture
text in parallel, but the final README review remains one pass.

## Implementation Strategy

1. Complete T001 and T002 without changing existing detailed guidance.
2. Deliver US1 as the smallest useful project tour; validate its four key facts.
3. Add US2's lifecycle and responsibility explanation.
4. Validate navigation, then run the final factual and whitespace checks.
