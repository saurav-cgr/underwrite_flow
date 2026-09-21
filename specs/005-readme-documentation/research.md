# Research: Improve Project README

## Existing documentation

### Decision: Make README an onboarding guide, not a second reference manual.

**Rationale**: `docs/ARCHITECTURE.md`, `docs/DEMO.md`, and the feature
quickstarts already contain detailed explanation. README needs discoverable
entry points and links.

**Alternatives considered**: Copy all existing documentation into README.
Rejected because it creates drift and makes first-time reading harder.

## Architecture visual

### Decision: Use one Mermaid flowchart and short invariant list.

**Rationale**: Existing architecture documentation uses Mermaid, which keeps
the README visual editable, reviewable, and renderer-friendly without assets.

**Alternatives considered**: Screenshot or design image. Rejected because it
adds an asset to maintain and cannot be searched or copied easily.

## Local demonstration

### Decision: Recommend `GENERATION_PROVIDER=fake` for quickstart.

**Rationale**: Fake provider is deterministic and avoids a cloud credential.
It is already used by normal tests, smoke checks, and evaluation.

**Alternatives considered**: Make Gemini default demonstration path. Rejected
because it needs provider configuration and is not deterministic.

## Role guidance

### Decision: Link three short role checks to detailed demo guide.

**Rationale**: Reader needs one clear applicant, underwriter, and administrator
flow. `docs/DEMO.md` remains detailed source for presentation steps.

**Alternatives considered**: One generic end-to-end flow. Rejected because it
hides authorization and human-decision boundaries.

## Verification guidance

### Decision: Document existing Make targets with prerequisites and outcomes.

**Rationale**: These commands are canonical and cover API, web, smoke, and
isolated evaluation. README must not invent scripts.

**Alternatives considered**: Add a new one-command verification script.
Rejected because it expands scope and current targets already cover need.

## Environment guidance

### Decision: Summarize modes in README and link detailed loader instructions.

**Rationale**: Readers need to know normal startup does not seed cases and
production blocks evaluation loading. Full token commands belong in quickstart.

**Alternatives considered**: Keep current long loader walkthrough in README.
Rejected because it obscures setup and role testing.
