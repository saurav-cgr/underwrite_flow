# Evaluation Contract

## Fast Offline Layer

The existing administrator-triggered and command-line evaluation remains
process-local.

- Provider is always the deterministic fake.
- Business database, uploads, auth, checkpoints, queues, and audit are unused.
- Each record selects its exact `configuration_version`.
- Product configuration is filtered by `journey_type` before evaluation.
- Existing split and metric response fields remain compatible.
- The administrator UI never starts containers or databases.

## Dataset Contract

Each record adds:

```json
{
  "case_id": "synthetic-motor-001",
  "product_code": "motor-private-car",
  "configuration_version": "v4",
  "journey_type": "renewal"
}
```

Preflight rejects the dataset before case execution unless:

- it contains exactly 90 uniquely identified synthetic cases;
- motor and health each contain 15 new and 15 renewal cases;
- life contains 30 new-business cases and no renewal cases;
- expected routes total 30 expedited, 30 standard, and 30 specialist;
- every version exists in the mounted configuration manifest;
- every product/version supports the named journey.

## Standalone Compose Boundary

`compose.evaluation.yaml` is standalone, not an overlay.

Required services:

| Service | Responsibility |
| --- | --- |
| `evaluation-db` | PostgreSQL on tmpfs |
| `evaluation-bootstrap` | migrations and product import |
| `evaluation-api` | API with fake provider |
| `evaluation-runner` | public-HTTP evaluation |

Isolation invariants:

- Compose project name is `underwriteflow-evaluation`.
- No service publishes a host port.
- No named volume is declared.
- Database storage and API uploads are tmpfs.
- Only `evaluation/results` is writable on the host.
- Product configuration, dataset, and scripts are read-only mounts.
- Runner has no database URL, Docker socket, or development credential.
- API uses evaluation-only database, session, refresh, issuer, and audience
  values.
- Provider is `fake`, retry count is zero, tracing is false, and Gemini and
  LangSmith keys are empty.
- Services share only the stack's internal default network.

## Runner Flow

1. Validate the complete dataset and configuration manifest.
2. Authenticate fictional administrator, applicant, and underwriter roles.
3. Activate every exact version required by the dataset.
4. Confirm active version and content hash through product history.
5. For each record in stable order:
   - create the journey-specific case;
   - replace application answers;
   - generate and upload valid synthetic PDFs from existing document lines;
   - submit;
   - read the public result and compare expected route and evidence outcomes.
6. Select the first reviewable case for each product, journey, and expected
   route combination.
7. Start review, confirm the recommendation, complete twice, and require equal
   completion responses.
8. Verify representative queue states and required audit event types.
9. Compute existing aggregate metrics and write the result atomically.

Needs-information cases are asserted as such and are not forced through human
confirmation or completion.

## Result Artifact

Path:

```text
evaluation/results/e2e.json
```

Schema:

```json
{
  "schema_version": 1,
  "passed": true,
  "provider": "fake",
  "dataset_sha256": "sha256",
  "configurations": {
    "motor-private-car": {
      "version": "v4",
      "content_hash": "sha256"
    }
  },
  "case_count": 90,
  "journey_counts": {
    "new_business": 60,
    "renewal": 30
  },
  "route_counts": {
    "expedited": 30,
    "standard": 30,
    "specialist": 30
  },
  "metrics": {},
  "reviewed_count": 0,
  "completed_count": 0,
  "failures": [],
  "elapsed_seconds": 0.0
}
```

Failure item:

```json
{
  "case_id": "synthetic-motor-001",
  "stage": "submit",
  "code": "unexpected_route"
}
```

Rules:

- Failures sort by case ID, stage, then code.
- Success and failure both produce a result when the runner can write.
- Any preflight, HTTP, invariant, or expected-outcome failure exits nonzero.
- Dataset/config hashes, counts, metrics, and failure ordering are
  deterministic.
- Elapsed time is observational and excluded from equality checks.
- No token, credential, database URL, raw document, applicant payload, or
  hidden workflow state is written.

## Operator and CI Command

```bash
make evaluate-e2e
```

The target:

1. removes stale containers with `down --remove-orphans`;
2. runs the standalone stack with runner exit-code propagation;
3. tears down without `-v`;
4. leaves only the ignored JSON artifact.

CI invokes the same target and uploads the result with an always-run artifact
step.
