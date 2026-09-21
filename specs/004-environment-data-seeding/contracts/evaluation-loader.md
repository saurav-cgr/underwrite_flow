# Evaluation Data Loader Contract

## Purpose

Load the authoritative synthetic evaluation corpus into development or
evaluation business storage only when an operator explicitly requests it.
Production must refuse the operation before any database or file write.

## Environment Status

A read-only unauthenticated status response exposes only safe mode data:

```json
{
  "environment": "development",
  "evaluation_loading_allowed": true
}
```

Rules:

- `environment` is `development`, `evaluation`, or `production`.
- `evaluation_loading_allowed` is false only for production.
- No database URL, credential, provider key, token, or filesystem path appears.
- Unsupported configured modes prevent startup rather than appearing here.

## Operator Command

Primary local command:

```bash
make load-evaluation-data
```

Underlying Compose command:

```bash
docker compose run --rm api \
  python /app/scripts/load_evaluation_data.py
```

The command accepts no production data path or mode override. Tests may inject
a smaller dataset through function parameters; the operator command always
uses the mounted authoritative corpus.

## Preconditions

Before its first write, the loader must verify:

- environment mode permits loading;
- the full dataset parses and passes the existing 90-case distribution rules;
- every record carries the exact synthetic demonstration label;
- every source case ID is unique;
- every product, product version, rulebook, and journey exists;
- the default applicant identity exists and is active;
- the loader actor identity carries a real access token
  (`EVALUATION_LOADER_ACTOR_TOKEN`), re-verified exactly like a protected API
  request, whose current database authorization holds the `evaluation:run`
  permission; a bare email or environment-supplied name is never accepted as
  proof of identity;
- upload storage and checkpoint configuration are local;
- external tracing is not enabled for the load;
- the deterministic fake provider is selected for workflow execution.

Any failed precondition returns nonzero and writes no business or audit row.

## Record Mapping

For each source record, in stable order:

1. Build the reserved idempotency key from dataset SHA-256 and source case ID.
2. Find or create the case through the existing case service, pinned to the
   exact product and rulebook versions from the record.
3. Verify journey and application payload against the source record.
4. Generate each synthetic document with the existing renderer.
5. Skip an exact existing document by code and content hash; upload a missing
   document through the existing storage and case service.
6. If the case is new, submit it through the existing workflow with the fake
   provider.
7. If it was already processed, verify its persisted result instead of
   resubmitting or resetting it.
8. Compare derived route, missing-data, and conflict results with reference
   labels.
9. Append one bounded `evaluation_record_loaded` event after verification,
   recording the resolved loader actor and the pinned product and rulebook
   version identities.

The loader never confirms, overrides, completes, or hands off a case.

## Retry Contract

- The same dataset and source case always resolve to the same idempotency key.
- Re-running a complete load creates zero duplicate cases and documents.
- Exact cases, documents, workflow results, and audit markers are reused.
- Missing stages resume in place.
- Unrelated rows and upload files are untouched.
- A reserved identity with mismatched version, journey, payload, document hash,
  or result fails with `evaluation_record_collision`.
- The dataset completion marker is appended once, only after full verification.

## Production Contract

When environment mode is production:

- exit before database or upload-storage construction;
- write no case, submission, document, workflow, checkpoint, or audit record;
- leave the common baseline unchanged;
- return the stable error code `evaluation_load_forbidden`.

Removing the script or corpus from an image is defense in depth, not the
authoritative guard.

## Output

Success writes one JSON object to standard output and exits zero:

```json
{
  "environment": "development",
  "dataset_sha256": "sha256",
  "expected_count": 90,
  "created_count": 90,
  "resumed_count": 0,
  "verified_count": 90,
  "complete": true
}
```

An exact second run reports `created_count: 0` and remains complete.

Failure writes one sanitized JSON object and exits nonzero:

```json
{
  "environment": "production",
  "complete": false,
  "error_code": "evaluation_load_forbidden"
}
```

Optional failure fields are limited to dataset hash, source case ID, and stage.
Output never includes credentials, tokens, database URLs, application payloads,
document text, provider prompts, or hidden workflow state.

A rejected corpus preflight reports `evaluation_load_preflight_failed` with
the failing case ID and stage. Any other unexpected failure reports the
generic `evaluation_load_failed` with no further detail. Both are caught at
the CLI boundary: no traceback or exception detail ever reaches standard
output or standard error.

## Compose Modes

| Compose configuration | Mode | Automatic load | Explicit load |
| --- | --- | --- | --- |
| `compose.yaml` | development | Never | Allowed |
| `compose.evaluation.yaml` | evaluation | Never | Allowed |
| `compose.yaml` + `compose.production.yaml` | production | Never | Refused |

The production override is an environment-selection contract only. It is not a
claim of production readiness or compliance.
