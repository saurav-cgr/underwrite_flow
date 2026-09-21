# Quickstart: Validate Environment Baseline and Evaluation Loading

## Prerequisites

- Docker Engine with Compose support
- Repository checkout at the project root
- `.env` copied from `.env.example` only when local overrides are needed
- No real applicant, insurer, credential, or document data

All commands run through Docker Compose. No host Python or PostgreSQL is
required.

## 1. Verify the Common Development Baseline

Start the normal stack from fresh project storage according to the project's
safe reset procedure, then run:

```bash
docker compose up -d --build
curl http://localhost:8000/api/v1/environment
```

Expected:

- environment is `development`;
- evaluation loading is allowed;
- all three documented demo accounts authenticate;
- roles, permissions, and built-in product configurations exist;
- cases, submissions, documents, and recommendations are empty.

Do not use `docker compose down -v`; project volume deletion requires explicit
approval.

## 2. Load Evaluation Data Explicitly

The loader requires a real access token for a user whose current
authorization holds the `evaluation:run` permission; mint one for the
fictional demo administrator, then run the load:

```bash
export DEMO_ADMINISTRATOR_PASSWORD=underwriteflow-demo-administrator
export EVALUATION_LOADER_ACTOR_TOKEN=$(curl -s -X POST \
  http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\": \"administrator@synthetic.test\", \"password\": \"$DEMO_ADMINISTRATOR_PASSWORD\"}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
make load-evaluation-data
```

Expected output is one sanitized JSON object with:

- `expected_count: 90`;
- `verified_count: 90`;
- `complete: true`;
- a SHA-256 identity for the exact corpus.

The applicant and underwriter screens may now show the loaded synthetic cases
and derived recommendations. No case is human-confirmed or completed.

The isolated evaluation Compose stack takes the same corpus through its own
command instead, using a token scoped to that stack's own login endpoint:

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

A document loaded this way stays readable through that same running
`evaluation-api` container; a token minted against development is refused
there, and one minted against evaluation is refused by development.

## 3. Prove Idempotency

Run the same command again:

```bash
make load-evaluation-data
```

Expected:

- exit code is zero;
- `created_count` is zero;
- case and document counts do not increase;
- unrelated records and files remain unchanged;
- only one dataset completion marker exists for the hash.

## 4. Prove Retry Safety

Use the focused integration test that injects a failure after an early record,
then reruns the loader:

```bash
docker compose run --rm api \
  pytest tests/integration/test_evaluation_loader.py -q
```

Expected:

- the interrupted run has no completion marker;
- already committed exact records remain identifiable;
- retry fills only missing stages;
- the final state contains one complete 90-case dataset.

## 5. Prove Production Refusal

Render and start the production-mode override, then invoke the same loader:

```bash
docker compose -f compose.yaml -f compose.production.yaml config
docker compose -f compose.yaml -f compose.production.yaml run --rm api \
  python /app/scripts/load_evaluation_data.py
```

Expected:

- nonzero exit code;
- `error_code` is `evaluation_load_forbidden`;
- the guard runs before database or upload access;
- the common baseline remains available;
- zero evaluation business or load-audit records are written.

## 6. Run Feature Gates

```bash
docker compose run --rm api \
  pytest tests/unit/test_environment_config.py \
  tests/contract/test_environment_compose.py \
  tests/integration/test_environment_baseline.py \
  tests/integration/test_evaluation_loader.py -q
make test-api
make smoke
```

Expected:

- focused feature tests pass;
- the full deterministic API suite passes;
- the existing smoke flow still requires human confirmation;
- no live Gemini, Ollama, or LangSmith call occurs.
