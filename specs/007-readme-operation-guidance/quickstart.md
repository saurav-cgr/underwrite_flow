# Quickstart: Validate README Operation Guidance

## Prerequisites

- Docker Engine with Compose support
- A checkout containing the existing `.env.example` and Compose files
- Fictional demonstration data only

Do not use or paste real credentials in commands, shell history, or the README.

## 1. Verify documented mode paths

Confirm the examples correspond to the committed Compose configuration:

```bash
docker compose config
docker compose -f compose.evaluation.yaml config
docker compose -f compose.yaml -f compose.production.yaml config
```

Expected: development is the default, the evaluation stack is isolated and
uses the fake provider, and the production override selects production mode.

## 2. Review Gemini and fake-provider guidance

Read the Gemini quickstart next to the fake-provider quickstart. Confirm that
it points to `.env.example`, names the required acknowledgement, and displays
no credential value. Confirm that the fake path remains usable without a cloud
credential.

## 3. Verify reset guidance without executing it

Confirm the README warns that reset is irreversible, limits its scope to the
development database and upload volumes, does not use `docker compose down -v`,
and explains the baseline recreated by bootstrap. Destructive reset execution
is a separate, deliberate operator action.

## 4. Verify the workflow visual

Render the README in a Markdown viewer that supports Mermaid. Confirm the flow
shows bounded parallel document work, one selected product path, sequential
reconciliation, recommendation, human interrupt, authenticated resume, and
idempotent completion. Confirm its legend distinguishes checkpoints from the
immutable audit trail.

## 5. Run existing regression checks

```bash
make test-api
make test-web
make smoke
```

Expected: all deterministic checks pass without a live Gemini, Ollama, or
LangSmith call, and the smoke flow still requires underwriter confirmation.
