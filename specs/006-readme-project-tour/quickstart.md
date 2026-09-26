# Quickstart Validation: README Project Tour

## Prerequisites

- A Markdown viewer that supports links; GitHub preview is sufficient.
- Repository checkout at the README project-tour change.

## Validate navigation

1. Open `README.md` in a Markdown preview.
2. Select every contents item.
3. Confirm each item reaches its named section.

**Expected result**: No contents link is broken or ambiguous.

## Validate the project tour

1. Read the opening, overview, capability table, and lifecycle only.
2. Identify the three routes and who makes the final route decision.
3. Identify the fictional-data-only limitation.

**Expected result**: The reader can explain purpose, safety, and the case path
without source-code inspection.

## Validate architecture explanation

1. Compare lifecycle stages with the Mermaid diagram.
2. Compare the responsibility summary with
   [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).
3. Confirm interface, workflow, storage, provider, and evaluation areas appear.

**Expected result**: The text explains the same boundaries as the diagram.

## Final checks

```bash
git diff --check
```

**Expected result**: The documentation diff has no whitespace errors. Review
the README for real data, credentials, production claims, and assertions that
automated routing is a final insurance decision.
