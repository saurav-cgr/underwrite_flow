# UnderwriteFlow

Local, human-governed triage demonstration for fictional motor, life, and
health applications. It turns application details and evidence into an
evidence-backed work-queue recommendation for human review.

The local MVP uses FastAPI, LangGraph, React, PostgreSQL, and Docker Compose.

UnderwriteFlow recommends a work queue route. An authenticated underwriter
must confirm or override every final route. It never approves, declines,
binds, prices, issues, renews, or cancels insurance.

## Implemented features

- **Journey-aware intake**: Applicants choose new business or renewal before
  product selection; renewal can require prior-policy evidence.
- **Versioned product authoring**: Administrators validate, preview, compare,
  activate, and export fictional product rulebooks. Existing cases stay pinned.
- **Evidence reconciliation**: Configured checks identify cleared, conflicting,
  or missing evidence with document provenance.
- **Human review and audit**: Deterministic rules recommend a route; an
  underwriter confirms it. Immutable audit events preserve decision history.
- **Safe evaluation**: Development and evaluation can load synthetic data on
  demand. Isolated 90-case evaluation never shares development state.

### Journeys and product authoring

Applicants choose new business or renewal before selecting a product; a
renewal requires its prior-policy document before the rest of the form.
Administrators author, preview, and version product rulebooks (fields,
documents, routing rules, reconciliation checks) through the builder, then
explicitly activate one version per product. A case stays pinned to the
version and journey selected when it started.

`make evaluate-e2e` runs the full 90-case synthetic evaluation set against an
isolated, tmpfs-only Compose stack with no published ports and no shared
state with the development database or upload volume.

### Provider boundary

The default generation provider is Gemini, so extracted document content and
application facts are sent to the Gemini API unless the fake provider is
selected. Set `GENERATION_PROVIDER=fake` to keep synthetic data on this
machine. Ollama is available through the `ollama` Compose profile.

Uploads are validated from their bytes, and file metadata is stored in the
local upload volume. Uploaded content is untrusted and is never treated as
model instructions.

LangSmith tracing is disabled by default. To opt in for synthetic evaluation,
set `LANGSMITH_TRACING=true`, provide a local evaluation key, and use the
APAC endpoint in `.env.example`. Trace payloads are redacted and tracing
failures never change application behavior.

## Quickstart: local fake provider

Use the deterministic fake provider for a no-credential local demonstration.
It keeps synthetic application and document content on this machine.

```bash
cp .env.example .env
# Edit .env: set GENERATION_PROVIDER=fake
docker compose up --build
```

Open `http://localhost:5173`. PostgreSQL is reachable only on the Compose
network by default. To use host database tools, opt in explicitly:

```bash
# Default: no published database port
# Opt in to a localhost-only port for host tools
docker compose -f compose.yaml -f compose.localhost.yaml up --build
```

The Compose bootstrap applies migrations and imports the three product files.
The migration provisions fictional Applicant, Underwriter, and Administrator
accounts.

### Fictional demo accounts

These credentials are public demonstration values. Never use them outside a
local synthetic environment.

- Applicant: `applicant@synthetic.test`
  `underwriteflow-demo-applicant`
- Underwriter: `underwriter@synthetic.test`
  `underwriteflow-demo-underwriter`
- Administrator: `administrator@synthetic.test`
  `underwriteflow-demo-administrator`

Run the deterministic checks with:

```bash
make test-api
make test-web
make smoke
make evaluate-e2e
```

## Environments and evaluation data

Every environment starts from the same common baseline: the current schema,
the authorization catalogue, the three fictional demo accounts, and every
built-in product configuration version. The baseline contains no case,
submission, document, or recommendation. Starting the stack twice changes
nothing and duplicates nothing.

`ENVIRONMENT_MODE` selects `development`, `evaluation`, or `production`.
Development is the local default; `compose.evaluation.yaml` and
`compose.production.yaml` set the other two explicitly. An unsupported value
prevents startup. The selected mode is readable without a credential:

```bash
curl http://localhost:8000/api/v1/environment
```

No startup path ever loads evaluation data. One explicit operator command
loads the 90-case synthetic corpus into development or evaluation. It
requires a real access token for a user whose current authorization holds
the `evaluation:run` permission (the fictional demo administrator, by
default); a bare email or environment-supplied name is never accepted as
identity:

```bash
export DEMO_ADMINISTRATOR_PASSWORD=underwriteflow-demo-administrator
export EVALUATION_LOADER_ACTOR_TOKEN=$(curl -s -X POST \
  http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\": \"administrator@synthetic.test\", \"password\": \"$DEMO_ADMINISTRATOR_PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
make load-evaluation-data
```

The command verifies the whole corpus before its first write, identifies the
dataset by SHA-256, reserves each case under a stable dataset-derived key,
and runs the workflow with the deterministic fake provider only. Running it
again creates nothing new, resumes any interrupted record in place, and never
overwrites a record that no longer matches its source. It never confirms,
overrides, completes, or hands off a case: an authenticated underwriter still
decides every final route.

A second command loads the same corpus into the isolated evaluation Compose
stack instead of development. Its token must come from that stack's own
login endpoint, since the isolated stack publishes no host port:

```bash
docker compose -f compose.evaluation.yaml up -d --build evaluation-api
export EVALUATION_LOADER_ACTOR_TOKEN=$(
  docker compose -f compose.evaluation.yaml exec -T evaluation-api \
    python -c "
import json, urllib.request
body = json.dumps({'email': 'administrator@synthetic.test',
                    'password': 'underwriteflow-demo-administrator'})
request = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/login',
    data=body.encode(),
    headers={'Content-Type': 'application/json'},
)
print(json.load(urllib.request.urlopen(request))['access_token'])
")
make load-evaluation-data-eval
```

That token's issuer, audience, and signing secret are scoped to the
evaluation stack, so a development-stack token is refused there and an
evaluation-stack token is refused by development. Loaded documents stay
readable through that same running `evaluation-api` container afterward.

In production mode the same command refuses before it opens the database or
the upload volume, writes nothing, and exits non-zero with the stable code
`evaluation_load_forbidden`:

```bash
docker compose -f compose.yaml -f compose.production.yaml run --rm api \
  python /app/scripts/load_evaluation_data.py
```

The production override selects an environment mode. It is not a claim of
production readiness, security hardening, or compliance. Every applicant,
document, product rule, and evaluation case this project loads is synthetic
and exists only for demonstration.

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
