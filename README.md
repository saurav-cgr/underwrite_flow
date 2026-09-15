# UnderwriteFlow

Human-governed triage for fictional motor, life, and health applications.
The local MVP uses FastAPI, LangGraph, React, PostgreSQL, and Docker Compose.

UnderwriteFlow recommends a work queue route. An authenticated underwriter
must confirm or override every final route. It never approves, declines,
binds, prices, issues, renews, or cancels insurance.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. PostgreSQL listens on port `5433`.
The Compose bootstrap applies migrations and imports the three product files.
The migration provisions fictional Applicant, Underwriter, and Administrator
accounts. Their synthetic passwords are used by the API test fixtures.

Run the deterministic checks with:

```bash
make test-api
make test-web
make smoke
```

## Provider boundary

The default generation provider is Gemini, but normal tests and the smoke
flow use the deterministic fake provider. Ollama is available through the
`ollama` Compose profile. Uploaded files remain in the local upload volume.
They are untrusted content and are never treated as model instructions.

LangSmith tracing is disabled by default. To opt in for synthetic evaluation,
set `LANGSMITH_TRACING=true`, provide a local evaluation key, and use the
APAC endpoint in `.env.example`. Trace payloads are redacted and tracing
failures never change application behavior.

## Documentation

- [Product requirements](docs/PRD.md)
- [Finalized MVP decisions](docs/PRD_FINALIZED_DECISIONS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Demo guide](docs/DEMO.md)
- [Synthetic evaluation set](evaluation/cases.json)
- [UI prototype](designs/underwriteflow-ui/index.html)

All applicants, documents, organizations, product rules, and evaluation cases
are synthetic and intended only for demonstration.
