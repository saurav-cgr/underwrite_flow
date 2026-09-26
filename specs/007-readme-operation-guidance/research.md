# Research: Complete README Operation Guidance

## Environment-mode examples

**Decision**: Document the existing development, evaluation, and production
settings as three labeled paths, with development using the fake provider by
default in the example.

**Rationale**: `.env.example` defines all three values. The isolated evaluation
stack already fixes evaluation mode and the fake provider. The production
override selects production mode and prevents evaluation loading; it does not
make a readiness claim.

**Alternatives considered**: Add new mode scripts or change defaults. Rejected:
the existing Compose configuration already provides the needed behavior.

## Gemini setup

**Decision**: Add a credential-safe quickstart subsection that identifies the
existing provider selection, API-key field, model field, approved-host list,
redaction terms, and no-training acknowledgment. Keep the fake-provider path
adjacent.

**Rationale**: The existing settings validate these fields, and the provider
factory rejects Gemini without the acknowledgment and approved host.

**Alternatives considered**: Put a key in a command example or introduce a
second setup file. Rejected: both increase secret-exposure risk without helping
the local demonstration.

## Local reset

**Decision**: Document a bounded local reset that stops the development stack,
removes only the Compose database and upload volumes, then starts the stack to
rerun bootstrap.

**Rationale**: `postgres_data` contains the database and `uploads_data` holds
local documents. Deleting both restores the documented empty baseline after
bootstrap while preserving unrelated Compose volumes such as node modules and
Ollama data.

**Alternatives considered**: `docker compose down -v`, a new reset script, or
database-only deletion. Rejected: the first is too broad, the second is
unnecessary, and the third leaves uploaded documents behind.

## LangGraph diagram

**Decision**: Expand the existing README Mermaid diagram and its adjacent case
lifecycle explanation rather than introduce another visual.

**Rationale**: The current diagram already presents the major system boundary.
Adding bounded document fan-out, selected subgraph, reconciliation, human
interrupt, authenticated resume, and completion makes the governing sequence
visible in one place.

**Alternatives considered**: A binary diagram or a source-code-level graph.
Rejected: Mermaid renders in repository viewers and remains concise enough for
onboarding.
