# Research: Add README Project Tour

## Reference structure

### Decision: Adapt structure, not language or claims.

**Rationale**: The supplied Decision Memory Assistant README is a useful
example of a skimmable orientation: contents, overview, capability table,
architecture, lifecycle, limits, and troubleshooting. UnderwriteFlow must keep
its own fictional-data and human-authority boundaries.

**Alternatives considered**: Copy the reference sections or wording. Rejected
because the products, data handling, and safety claims differ.

## Navigation

### Decision: Add a compact linked contents list.

**Rationale**: The existing README now has enough onboarding material that a
reader benefits from direct paths to setup, verification, architecture, and
limits.

**Alternatives considered**: Add a standalone documentation index. Rejected
because README navigation is already sufficient and avoids another file.

## Capability summary

### Decision: Use one concise behavior-and-boundary table.

**Rationale**: A table makes implemented features scannable while avoiding a
second long-form architecture or setup guide.

**Alternatives considered**: Add a technology-stack table. Rejected because
the README already names the stack and users need demonstrated behavior first.

## Architecture explanation

### Decision: Keep the current Mermaid diagram and add lifecycle plus roles.

**Rationale**: The diagram is the maintained visual source. A short textual
path and responsibility summary make it useful in viewers with limited Mermaid
support.

**Alternatives considered**: Add another diagram or screenshot. Rejected
because it duplicates the visual and adds maintenance work.
