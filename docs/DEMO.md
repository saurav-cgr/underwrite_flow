# UnderwriteFlow demo guide

This flow is designed for a three-to-five-minute portfolio demonstration.
Use only the fictional accounts and data already in the repository.

## 1. Start the stack

```bash
cp .env.example .env
docker compose up --build
```

The bootstrap container applies the fresh-schema migration, provisions the
three demo roles, and imports the motor, life, and health configurations.

Before opening the applicant catalog, sign in as the fictional Administrator
and activate `motor-private-car` version `v1` through the product activation
API using that session's bearer token. Bootstrap imports configurations as
drafts; Administrator activation is required before applicants can see them.

## 2. Show the applicant journey

1. Open `http://localhost:5173` and choose Applicant.
2. Select the fictional private-car motor product.
3. Enter a young vehicle age, personal use, and zero fictional prior claims.
4. Upload synthetic PDF or image documents for identity and vehicle records.
5. Submit and show the case tracking state.

## 3. Show configured reconciliation

1. Open the case review screen for the submitted case.
2. Show the configured checks resolved from the pinned version, each with its
   `CLEARED`, `FLAGGED_DISCREPANCY`, or `MISSING_EVIDENCE` status as text
   rather than colour alone.
3. Show the provenance for each comparison: the application value, the
   document value, the document id, and the page locator.
4. Upload a synthetic document that disagrees, resubmit, and show the flagged
   discrepancy turn into a specialist signal.

## 4. Show governed review

1. Open a second browser window and choose Underwriter.
2. Open the new case from the review queue and read its evidence checks.
3. Confirm the recommendation, or override it with a reason.
4. Show that an override without a reason, or without permission, is refused.
5. Complete the case and show the completed queue state.

## 5. Show oversight and evaluation

1. Choose Administrator and open the audit workspace.
2. Search for the case UUID and inspect immutable event history.
3. Show the provider line per document: provider, model, attempts, token usage
   or the unavailable marker, and the recorded hashes.
4. Show that a later cycle links back to the event it supersedes.
5. Show the synthetic evaluation metrics and the 30-case holdout split.
6. Run `make smoke` for the deterministic end-to-end flow, and `make probe`
   for the bounded ten-case synthetic load probe.

## Demo boundaries

The recommendation is triage only. The application does not approve, decline,
bind, price, issue, renew, or cancel insurance, and an underwriter confirms
every final route. The product files, uploaded documents, and evaluation cases
are fictional demonstration data.

Known limits for this demonstration:

- Local-first and single-node: one API, one web app, one PostgreSQL instance,
  and one upload volume, with no broker, scheduler, or object storage.
- Normal verification uses only the deterministic fake provider, so Gemini and
  Ollama latency, cost, and quota behavior are not exercised here.
- One role per user, one active version per product, and one recommendation per
  case; multi-role assignment and version rollback are out of scope.
- Demonstration-scale document handling, with upload and page bounds set as
  configuration constants rather than tuned production limits.
- Tracing is off by default and development-only when enabled. No retention or
  deletion policy is implemented beyond the append-only audit guarantee; the
  development reset procedure deletes project volumes.
- The probe reports local synthetic timings. It is a bounded smoke-level probe,
  not a performance or capacity benchmark.
