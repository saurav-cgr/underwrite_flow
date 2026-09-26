# Implementation Plan: Add README Project Tour

**Branch**: `006-readme-project-tour` | **Date**: 2026-09-21 |
**Spec**: [spec.md](spec.md)

## Summary

Extend the existing README with a small project-tour layer inspired by the
supplied Decision Memory Assistant README: linked navigation, a clear statement
of what UnderwriteFlow demonstrates, a capability table, case lifecycle, and
component responsibilities. Reuse the current quickstart, role checks,
architecture diagram, and deeper links. This is a README-only change.

## Technical Context

**Language/Version**: Markdown rendered by repository viewers

**Primary Dependencies**: Existing README headings and linked documents

**Storage**: Repository Markdown only

**Testing**: Link checks, Markdown review, and `git diff --check`

**Target Platform**: GitHub and local Markdown viewers

**Project Type**: Documentation update for an existing web application

**Performance Goals**: Reader identifies purpose, safety boundary, and project
tour within three minutes

**Constraints**: No binaries, dependencies, credentials, real data, behavior,
schema, authorization, or provider changes. Preserve existing documentation.

**Scale/Scope**: One README update: compact navigation, three short overview
sections or tables, one lifecycle explanation, and expanded architecture text.

## Constitution Check

*GATE: Passed before research; re-checked after design.*

- **Tenant and authorization — Pass**: The documentation preserves the
  existing role and authenticated-underwriter boundary.
- **Data and provider boundary — Pass**: It reinforces fictional data, local
  evidence handling, and approved provider boundaries without adding a path.
- **Configuration and reconciliation — Pass**: It describes existing version
  pinning and deterministic reconciliation only.
- **Audit and human authority — Pass**: It retains immutable audit language.
  Human confirmation remains the final control point.
- **Reuse — Pass**: It changes only `README.md` and links existing guides.

### Post-Design Re-check

The design adds documentation only. It introduces no provider, data,
authorization, schema, audit, or insurance-decision behavior. All gates pass.

## Project Structure

### Documentation

```text
specs/006-readme-project-tour/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── readme-project-tour.md
```

### Change Surface

```text
README.md
docs/
├── ARCHITECTURE.md
├── DEMO.md
├── PRD.md
└── RELEASE_READINESS.md
```

**Structure Decision**: Edit `README.md` only. Existing documents remain the
source for detailed instructions; the project tour links to them.

## Phase 0: Research Decisions

See [research.md](research.md). No clarification remains.

## Phase 1: Documentation Design

- Place a compact contents list after the opening purpose and boundary.
- Add a "What this demonstrates" paragraph and capability table before setup.
- Add a short lifecycle beside the existing architecture overview and a
  responsibility table for interface, workflow, storage, provider, and eval.
- Reuse safety wording and deeper links already verified for this README.
- Keep all wording factual and explicitly exclude automated insurance actions,
  production-readiness claims, compliance claims, and real data.
- Validate internal links, heading anchors, line width, and Markdown structure.

## Complexity Tracking

No constitution violation or exceptional complexity requires justification.
