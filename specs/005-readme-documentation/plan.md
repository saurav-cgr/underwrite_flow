# Implementation Plan: Improve Project README

**Branch**: `phase2` | **Date**: 2026-09-21 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`specs/005-readme-documentation/spec.md`

## Summary

Restructure the existing README as an onboarding guide. Add concise product and
safety context, a role-based demo, test commands with expected results, an
expanded Mermaid architecture diagram, environment guidance, troubleshooting,
and links to deeper references. Reuse verified repository commands and facts;
do not change application behavior or duplicate long-form documents.

## Technical Context

**Language/Version**: Markdown, rendered by repository viewers

**Primary Dependencies**: Existing Docker Compose commands and existing docs

**Storage**: Repository Markdown files only

**Testing**: Markdown review, command verification, `git diff --check`

**Target Platform**: GitHub and local Markdown viewers

**Project Type**: Documentation-only update for a web application

**Performance Goals**: New reader finds product purpose and core demo in five
minutes or less

**Constraints**: No new dependencies, binaries, screenshots, data, credentials,
or product behavior. Keep README focused; link detailed content instead.

**Scale/Scope**: One README rewrite, one architecture diagram, three role
journeys, four automated commands, and short troubleshooting guidance

## Constitution Check

*GATE: Passed before research; re-checked after design.*

- **Tenant isolation and authorization — Pass**: Documentation describes the
  existing single-deployment model and scope-based roles only.
- **Provider and data boundary — Pass**: README states fake-provider local
  verification, redaction boundary, and no real data without adding a path.
- **Schema and reconciliation — Pass**: It describes versioned configuration
  and deterministic evidence checks as existing safeguards.
- **Audit and version pinning — Pass**: It explains immutable audit events and
  pinned versions without changing data or database structure.
- **Human authority — Pass**: It prominently states recommendation-only
  behavior and mandatory underwriter confirmation.
- **Synthetic data — Pass**: Every demonstration path remains fictional.
- **Reuse — Pass**: Plan reuses `README.md`, `docs/ARCHITECTURE.md`,
  `docs/DEMO.md`, `.env.example`, and existing Make targets.

### Post-Design Re-check

Design adds documentation only. No provider, schema, authorization, external
data, or decision boundary changes. All gates remain passed.

## Project Structure

### Documentation (this feature)

```text
specs/005-readme-documentation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── readme-content.md
└── tasks.md
```

### Source Code (repository root)
```text
README.md
docs/
├── ARCHITECTURE.md
├── DEMO.md
├── PRD.md
├── PRD_FINALIZED_DECISIONS.md
└── RELEASE_READINESS.md
.env.example
Makefile
compose*.yaml
```

**Structure Decision**: Change `README.md` only. Link existing detailed docs;
do not duplicate or edit their content in this feature.

## Phase 0: Research Decisions

See [research.md](research.md). No clarification remains.

## Phase 1: Documentation Design

- Keep opening safety statement, then add a concise feature map and role table.
- Add a Mermaid diagram adapted from `docs/ARCHITECTURE.md`, plus six short
  invariants: untrusted uploads, pinned configuration, deterministic rules,
  immutable audit, provider boundary, and human final decision.
- Add no-credential local quickstart using `GENERATION_PROVIDER=fake`.
- Add fictional account table and role-based manual checks. Use only verified
  email and password values already shipped in `web/src/entry.tsx`.
- Add automated check table for `make test-api`, `make test-web`, `make smoke`,
  and `make evaluate-e2e`, with prerequisites and observable pass criteria.
- Compress existing environment-loader detail into a summary and link to the
  evaluation quickstart; preserve the production-load refusal warning.
- Add short troubleshooting and known-limits sections, then a curated reference
  list.
- Validate all commands against current Make and Compose definitions, render
  Mermaid in a Markdown-capable viewer, review claims against source docs, and
  run `git diff --check`.

## Complexity Tracking

No constitution violation or exceptional complexity required.
