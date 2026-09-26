# Contract: Journey-Specific Prior Claims

All routes retain existing authentication and permission requirements. Examples
contain synthetic values only.

## Product Catalogue

### New business

`GET /api/v1/products/catalog?journey=new_business`

For active motor version `v5`:

- response status is `200`;
- `prior_claims` is absent from `fields`;
- renewal-only documents remain absent;
- routing rules and reconciliations remain undisclosed.

### Renewal

`GET /api/v1/products/catalog?journey=renewal`

For active motor version `v5`, `prior_claims` remains in `fields` with its
configured validation.

## Case Creation

### Accepted new-business payload

`POST /api/v1/cases`

```json
{
  "product_code": "motor-private-car",
  "idempotency_key": "synthetic-new-business-001",
  "journey": "new_business",
  "payload": {
    "vehicle_age": 4,
    "vehicle_use": "personal"
  },
  "document_codes": []
}
```

The response is the existing case contract and identifies product version
`v5` after administrator activation.

### Rejected stale new-business payload

The same request with `"prior_claims": 0` returns status `422`:

```json
{
  "detail": "Unsupported application field: prior_claims"
}
```

No case, submission, or audit event is created.

## Application Replacement

`PUT /api/v1/cases/{case_id}/application`

- A mutable `v5` new-business case rejects `prior_claims` with status `422`
  and the same safe detail.
- The existing stored submission remains unchanged after rejection.
- A valid replacement without `prior_claims` uses the existing success
  response.

## Submission and Review

For a valid `v5` new-business case:

- submission does not report `prior_claims` as missing;
- extraction does not request it;
- routing does not evaluate `prior_claims_standard`;
- reconciliation does not consume it;
- `GET /api/v1/cases/{case_id}/configuration` omits it;
- `POST /api/v1/reviews/{case_id}/start` omits it from submitted facts,
  evidence, missing information, and reconciliation results.

## Renewal Compatibility

A `v5` renewal request may include:

```json
{
  "prior_claims": 0,
  "claimed_ncb_percent": 20
}
```

The prior-claims field, standard-routing rule, and NCB reconciliation remain
available as defined by the pinned renewal configuration. Existing document
and completeness requirements remain unchanged.

## Configuration Validation

Product validation returns `422` before import when a rule, reconciliation
input, document source, or reconciliation parameter field applies to a journey
where its referenced field or document is unavailable.

## Versioning

- `v5` import creates a draft and its existing audit event.
- Activation requires the existing authenticated administrator operation.
- Cases created before activation remain pinned to their original product and
  rulebook versions.
