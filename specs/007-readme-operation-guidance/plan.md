# Implementation Plan: Complete README Operation Guidance

**Branch**: `007-readme-operation-guidance` | **Date**: 2026-09-21 | **Spec**:
[spec.md](spec.md)

**Input**: Feature specification from
`/specs/007-readme-operation-guidance/spec.md`

## Summary

Expand README onboarding with current, copyable environment-mode startup
examples, deliberate Gemini setup, a narrowly scoped local reset procedure,
and a more explicit LangGraph flow diagram. Reuse the existing Compose files,
`.env.example`, provider boundary, and Mermaid diagram; no runtime behavior or
configuration contract changes.

## Technical Context

**Language/Version**: Markdown; existing Docker Compose and environment files

**Primary Dependencies**: Existing Docker Compose, Mermaid, and Gemini adapter

**Storage**: Existing local PostgreSQL and upload volumes; no schema changes

**Testing**: README review, Compose configuration rendering, existing checks

**Target Platform**: Local Docker Compose demonstration

**Project Type**: Documentation-only change in a local web application

**Performance Goals**: Readers identify a correct mode and start path in five
minutes or less

**Constraints**: Synthetic data only; no credential values; no new provider,
schema, dependency, or destructive reset mechanism; no production claim

**Scale/Scope**: `README.md` and, only if an existing documentation check needs
an adjacent update, its focused documentation test; no application code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status before Phase 0: PASS**

- Tenant and data boundary: the README will say that only local fictional data
  is valid and that Gemini receives approved, redacted task data.
- Provider boundary: examples reuse the existing fake and Gemini providers;
  they add neither a provider nor a direct model call.
- Configuration and reconciliation: the diagram retains product-version
  pinning and deterministic reconciliation as owned system behavior.
- Audit and checkpoints: the diagram labels checkpoints as resume support and
  audit events as the business history.
- Human authority: the diagram preserves the required authenticated
  underwriter interrupt and resume before completion.
- Reset safety: reset guidance names only the local database and upload
  volumes. It must not use `docker compose down -v` or imply recovery of data
  that needs retention.

**Status after Phase 1: PASS** — the design adds documentation only and keeps
all constitutional boundaries above explicit.

## Project Structure

### Documentation (this feature)

```text
specs/007-readme-operation-guidance/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Documentation concepts
├── quickstart.md        # Validation guide
├── contracts/readme.md  # README content contract
└── tasks.md             # Created later by speckit-tasks
```

### Source Code (repository root)

```text
README.md                       # Mode, provider, reset, and flow guidance
.env.example                    # Existing configuration source of truth
compose.yaml                    # Existing development configuration
compose.evaluation.yaml         # Existing isolated evaluation configuration
compose.production.yaml         # Existing production-mode guard
docs/ARCHITECTURE.md             # Existing detailed architecture reference
specs/004-environment-data-seeding/quickstart.md
                                # Existing evaluation command reference
```

**Structure Decision**: Update only `README.md`. It links to existing detailed
guides rather than duplicating their operational content.
