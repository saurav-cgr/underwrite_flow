# Quickstart: Validate Journey, Authoring, and Evaluation

## Preconditions

- Use synthetic data only.
- Obtain explicit approval before applying migration 08.
- Run all commands from the repository root through Docker Compose.
- Keep Gemini and LangSmith disabled for deterministic checks.

## 0. Phase 1 Baseline Record (2026-09-19)

- `make test-api`: 376 passed; reconciliation coverage 100%.
- `make test-web`: 16 files, 141 tests passed.
- `docker compose run --rm web npm run build`: succeeded, no
  TypeScript or bundling errors.
- No blockers found before feature edits.

## 1. Static and Deterministic Suites

```bash
make test-api
make test-web
docker compose run --rm web npm run build
```

Expected:

- API and web suites pass.
- Reconciliation retains 100% statement and branch coverage.
- Production web build completes.
- No live provider or external tracing request occurs.

## 2. Migration and Legacy Compatibility

After schema approval:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current
```

Run focused migration, product, case, workflow, and API contract tests:

```bash
docker compose run --rm api pytest \
  tests/integration/test_journey_migration.py \
  tests/unit/test_products.py \
  tests/unit/test_cases.py \
  tests/unit/test_evaluation.py \
  tests/contract -q
```

Expected:

- Current revision is 08.
- Existing cases read as `new_business`.
- Legacy product files remain valid and bootstrap remains idempotent.
- A semantically unchanged legacy version retains its original hash.
- Unsupported journey and non-applicable evidence are rejected.

## 3. Applicant Journey Scenarios

Start the normal stack with the fake provider:

```bash
GENERATION_PROVIDER=fake LANGSMITH_TRACING=false +  docker compose up --build
```

Validate through the browser:

1. Select new business and confirm only eligible products appear.
2. Complete motor new business: form, supporting documents, submit.
3. Select renewal and confirm term life is unavailable.
4. Start motor renewal and verify this order:
   prior policy, renewal form, supporting evidence, submit.
5. Reload after each renewal stage and verify restored journey, answers,
   documents, pinned version, and status.
6. Attempt renewal submission without prior-policy evidence and verify refusal.
7. Confirm renewal-only checks are absent from new-business review.
8. Confirm journey appears in queue, review, audit, and completion.
9. Confirm the route as an underwriter, complete twice, and verify one handoff.

Expected behavior is defined in [REST API Contract](./contracts/rest-api.md)
and [Data Model](./data-model.md).

## 4. Administrator Builder Scenarios

As a synthetic administrator:

1. Create a blank fictional product and complete all seven builder sections.
2. Preview an invalid reference and verify precise rejection without a write.
3. Correct it, import the version, and verify draft status.
4. Confirm the draft is absent from the applicant catalogue.
5. Activate it through the separate confirmation and verify it appears.
6. Clone an active version, choose a new version, and verify the source remains
   unchanged.
7. Upload expert YAML and verify the normalized builder state.
8. Export canonical YAML and re-upload it under a new version.
9. Verify the active-version diff uses text/icons and is keyboard accessible.
10. Verify an existing case remains pinned after activating a successor.

The exact schema and diff keys are in
[Product Configuration Contract](./contracts/product-configuration.md).

## 5. Fast Offline Evaluation

```bash
docker compose run --rm api +  python -m underwriteflow.evaluation.runner
```

Expected:

- 90 cases run with the fake provider.
- Journey counts are 60 new business and 30 renewal.
- Route counts remain 30 expedited, 30 standard, and 30 specialist.
- No business database or upload is used.

## 6. Isolated End-to-End Evaluation

Render and inspect the standalone boundary:

```bash
docker compose -f compose.evaluation.yaml config
```

Confirm no published ports, named volumes, development network, live provider,
or tracing setting appears.

Run twice:

```bash
make evaluate-e2e
cp evaluation/results/e2e.json /tmp/underwriteflow-e2e-first.json
make evaluate-e2e
```

Expected after each run:

- Exit status is zero.
- `evaluation/results/e2e.json` exists.
- `passed` is true, provider is `fake`, and failures are empty.
- Case, journey, and route counts match the dataset contract.
- Representative human reviews and completions are nonzero.
- Repeated completion returns the same response.
- Dataset/config hashes, counts, metrics, and failures match across runs.
- Elapsed time may differ.

The complete result contract is in
[Evaluation Contract](./contracts/evaluation.md).

## 7. Development-Isolation Proof

While the development stack is running, record its case count and upload-file
count. Run `make evaluate-e2e`, then record both counts again.

Expected:

- Development row count is unchanged.
- Development upload-file count is unchanged.
- Development containers and named volumes remain running and untouched.
- Evaluation teardown leaves no evaluation containers.
- Only the ignored result JSON remains on the host.

## 8. Final Human-Authority Check

Search all new flows and results for prohibited final actions.

Expected:

- The system only recommends expedited, standard, or specialist review.
- Missing information remains a queue state.
- No code or UI approves, declines, binds, prices, issues, renews, or cancels.
- Every completed route has an authenticated human review and immutable audit.
