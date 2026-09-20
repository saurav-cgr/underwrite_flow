  # Quickstart Validation Guide

This guide validates the completed feature. It does not authorize schema,
authentication, provider, dependency, or retention changes. Obtain the project
approval required by `AGENTS.md` before implementation or migration.

## Prerequisites

- Docker and Docker Compose
- Synthetic fixtures only
- A non-production Gemini commercial project configured for no-training use,
  or the deterministic fake provider for normal acceptance
- No real applicant, insurer, policy, medical, financial, or vehicle data

Read first:

- [Feature specification](./spec.md)
- [Implementation plan](./plan.md)
- [Data model](./data-model.md)
- [REST contract](./contracts/rest-api.md)
- [Reconciliation contract](./contracts/reconciliation.md)

## 1. Deterministic Baseline

Run all standard suites through Compose:

```bash
make test-api
make test-web
docker compose run --rm web npm run build
```

Expected:

- All default tests use deterministic fake providers.
- No test requires Gemini, Ollama, LangSmith, host Python, or host Node.
- Pure NCB, lapse, and asset reconciliation functions report 100% statement
  and branch coverage.
- No fixture contains unmarked real-world data.

## 2. Migration Validation

Run only after explicit schema/auth approval:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic current
```

Expected:

- One additive revision follows revision 06.
- `01_initial.py` is unchanged.
- Existing users retain IDs and gain exactly one user-role mapping.
- Existing role strings map to seeded Applicant, Underwriter, and
  Administrator roles without guessing.
- Duplicate user-role and role-permission mappings are rejected.
- The audit update/delete trigger still rejects mutation.

## 3. Authentication and Dynamic RBAC

Start the local application with synthetic accounts:

```bash
docker compose up --build
```

Validate the [authentication contract](./contracts/rest-api.md):

1. Log in through `POST /api/v1/auth/login`.
2. Read identity through `GET /api/v1/auth/me`.
3. Refresh once through `POST /api/v1/auth/refresh`.
4. Retry the old refresh credential.
5. Create a custom read-only role and synthetic user as an administrator.
6. Verify that the new user can read a case but cannot override it.
7. Grant `cases:override`, issue a fresh access token, and retry.
8. Disable the user and retry the same access token.

Expected:

- Access credentials are three-segment signed JWT bearer tokens.
- Claims contain `sub`, `role`, sorted `permissions`, issuer, audience, issue
  time, expiry, token type, and token ID.
- Old refresh reuse is rejected and its replacement chain is revoked.
- Role or permission changes invalidate stale claim snapshots on the next
  secured request.
- Disabled users receive no access even with an unexpired token.
- Applicant ownership and underwriter-only finalization remain enforced after
  scope checks.
- Tokens, refresh digests, passwords, and authorization headers do not appear
  in audit responses or error bodies.

## 4. Configuration Validation

Use a fictional motor configuration marked:
`SYNTHETIC - FOR DEMONSTRATION ONLY`.

The configuration must declare:

- application NCB claim;
- previous-policy NCB;
- claims count;
- engine, chassis, and registration identifiers;
- previous expiry and new start dates;
- `ncb_match`, `asset_match`, and `policy_lapse` checks.

Validate, preview, import, and activate it through the existing product
configuration routes.

Expected:

- Unknown fields, document codes, check kinds, or thresholds fail before
  activation.
- Preview changes no active configuration.
- Activation appends an audit event.
- An existing case continues using its pinned older version.

## 5. Evidence and Reconciliation

Create one synthetic case with:

- matching NCB evidence;
- one engine-number formatting variation that normalizes to a match;
- one chassis-number mismatch;
- previous expiry and new start dates that breach the configured lapse limit;
- missing claims history for a required NCB rule.

Upload documents and submit the case.

Expected ordered results:

| Check | Expected status |
| --- | --- |
| Asset engine comparison | `CLEARED` |
| Asset chassis comparison | `FLAGGED_DISCREPANCY` |
| NCB comparison | `MISSING_EVIDENCE` |
| Policy lapse | `FLAGGED_DISCREPANCY` |

Every result must include stable codes, normalized comparisons, document IDs,
source locators, and pinned rule version. Repeating the same pure reconciliation
input must produce byte-identical ordered output.

## 6. Provider Boundary

### Fake provider

Run the deterministic smoke flow:

```bash
make smoke
```

Expected: one complete synthetic workflow reaches human review, records
provider metadata, and finishes exactly once after confirmation.

### Ollama

Optional local validation:

```bash
docker compose --profile ollama up --build
```

Expected: existing Ollama adapter and shared validation contract are used;
payloads stay local; invalid JSON becomes a typed provider failure.

### Gemini

Live Gemini validation is opt-in and never deterministic acceptance.

Expected:

- Configured PII is redacted before network transmission.
- Provider/model, attempts, request/result hashes, and reported token usage are
  appended to local audit.
- Raw prompt, raw file, credentials, and prohibited PII do not appear in audit
  or traces.
- Timeout or invalid output preserves successful sibling evidence and opens a
  visible review signal.

## 7. Human Review and Audit

Open the discrepancy queue as an underwriter.

Expected:

- Flagged and missing results, confidence source, evidence links, and pinned
  versions appear in one review view.
- A user without `cases:override` cannot override.
- An override without rationale fails validation.
- A valid underwriter override appends one immutable event.
- Repeating review or completion does not create another decision or handoff.
- Original audit events cannot be updated or deleted; correction appends a
  linked superseding event.

## 8. Pilot-Scale Probe

Use synthetic documents to run ten cases concurrently, then a 100-case daily
volume sample.

Capture:

- ordinary interaction p95;
- review-ready p95;
- OCR seconds/page;
- provider latency and maximum active calls;
- PostgreSQL pool use and stored bytes/case;
- upload bytes/case;
- queue query p95.

Acceptance:

- 95% ordinary interactions complete within two seconds.
- 95% cases become review-ready within 60 seconds.
- No case exceeds three simultaneous provider branches.
- No committed case, audit event, upload, or checkpoint is lost after a
  container restart.

If the ten-case probe fails, evaluate a process-local submission semaphore
before proposing a worker, cache, queue, shard, or new service.
