# README Update Validation Guide

## Prerequisites

- Work from repository root.
- Docker Compose is available.
- Keep all examples fictional.

## 1. Verify documented facts

Check every README statement against its source before editing:

- Product and safety claims: `docs/PRD.md` and
  `docs/PRD_FINALIZED_DECISIONS.md`.
- Architecture and invariants: `docs/ARCHITECTURE.md`.
- Role journeys: `docs/DEMO.md`.
- Commands: `Makefile` and Compose files.
- Demo accounts: `web/src/entry.tsx`.

## 2. Verify local quickstart

Create local environment file, set `GENERATION_PROVIDER=fake`, then start the
application with the documented Compose command. Confirm web interface opens
and all three fictional roles appear at sign-in.

## 3. Verify role journeys

1. Applicant: start new business or renewal, supply requested synthetic
   evidence, and submit case.
2. Underwriter: open submitted case, inspect evidence, then confirm or override
   route with required rationale.
3. Administrator: inspect versioned product configuration and run documented
   synthetic evaluation path.

Confirm no step says system makes final insurance decision.

## 4. Verify automated checks

Run each README command from repository root:

```bash
make test-api
make test-web
make smoke
make evaluate-e2e
```

Each command must match its README description and return a successful status.

## 5. Verify rendered README

- Render README in a Markdown-capable viewer.
- Confirm Mermaid diagram renders and labels remain readable.
- Confirm all local document links resolve.
- Confirm code blocks wrap safely and no credential is presented as real.
- Run `git diff --check`.
