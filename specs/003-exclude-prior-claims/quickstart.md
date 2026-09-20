# Quickstart: Exclude Prior Claims from New Business

## Prerequisites

- Docker Compose is available.
- The repository uses synthetic local settings.
- Product version `v5` has been imported as a draft.

## 1. Validate configuration and shared guards

```bash
docker compose run --rm api pytest \
  tests/unit/test_cases.py \
  tests/unit/test_journey_configuration.py \
  tests/unit/test_evaluation.py -q
```

Expected:

- a journey-inapplicable application field is rejected;
- an inapplicable reconciliation parameter field is rejected;
- valid renewal-only prior-claims configuration passes;
- current `v5` evaluation records omit prior claims and route balance remains.

## 2. Validate the user journeys

```bash
docker compose run --rm api pytest \
  tests/integration/test_journey_workflow.py \
  tests/contract/test_review_contract.py -q
```

Expected:

- an administrator can activate motor version `v5`;
- new-business catalogue and case configuration omit prior claims;
- stale new-business payloads return a precise 422 response;
- valid new-business submission and review contain no prior-claims result;
- renewal continues to accept and use prior claims;
- a case pinned to an earlier version remains unchanged.

## 3. Run regression gates

```bash
make test-api
make test-web
docker compose run --rm web npm run build
make smoke
```

Expected: all deterministic checks pass with no live provider or tracing.

## 4. Manual acceptance

1. Start the local application through the normal Compose flow.
2. Sign in as the synthetic administrator.
3. Inspect and explicitly activate motor version `v5`.
4. Sign in as the synthetic applicant and choose motor new business.
5. Confirm that prior claims are absent, complete the remaining fields, and
   submit synthetic documents.
6. Sign in as the synthetic underwriter and confirm that no prior-claims fact,
   missing item, rule result, or reconciliation result appears.
7. Start a motor renewal and confirm that prior claims remains available.
8. Confirm that every final route still requires underwriter action.

## 5. Safety checks

```bash
git diff --check
rg -n '.{81}' \
  product-config/motor-private-car-v5.yaml \
  api/src/underwriteflow/cases \
  api/src/underwriteflow/products \
  api/src/underwriteflow/reviews \
  api/tests
```

Expected: no whitespace errors, no new overlength hand-written lines, no
schema migration, and no secret or real applicant data.
