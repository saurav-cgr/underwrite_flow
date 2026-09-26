# REST API Contract

All paths are under `/api/v1`. Existing bearer authentication, permission
checks, request IDs, and sanitized error envelopes remain unchanged.

## Product Catalogue

### `GET /products/catalog`

Optional query:

```text
journey_type=new_business|renewal
```

- Omitted journey defaults to `new_business`.
- A supplied journey returns only active versions supporting it.
- The backend applies the filter even if the browser also filters.

Response item additions:

```json
{
  "product_code": "motor-private-car",
  "version": "v4",
  "supported_journeys": ["new_business", "renewal"],
  "fields": [],
  "documents": []
}
```

The returned fields and documents are filtered for the selected journey.

Errors:

- `422`: unknown journey.
- `403`: caller lacks case-write permission.

## Case Creation

### `POST /cases`

```json
{
  "product_code": "motor-private-car",
  "journey_type": "renewal",
  "idempotency_key": "synthetic-key",
  "payload": {},
  "document_codes": []
}
```

Compatibility:

- `journey_type` defaults to `new_business`.
- `payload` defaults to an empty object.
- `document_codes` remains accepted for legacy clients but is not trusted for
  evidence completeness.

Behavior:

- Pins the active product and rulebook versions and immutable journey.
- Rejects unsupported product/journey combinations.
- Validates any supplied field keys and values, but allows omitted required
  fields until submission.
- Remains idempotent per applicant and idempotency key.

Response:

```json
{
  "id": "uuid",
  "product_code": "motor-private-car",
  "product_version": "v4",
  "rulebook_version": "v4",
  "journey_type": "renewal",
  "status": "new"
}
```

Errors:

- `403`: caller lacks permission.
- `422`: product, journey, field key, or supplied value is invalid.

## Application Replacement

### `PUT /cases/{case_id}/application`

```json
{
  "payload": {
    "vehicle_age": 4,
    "claimed_ncb_percent": 20
  }
}
```

Behavior:

- Complete replacement, never merge.
- Only the applicant owner may update.
- Allowed only for `new` or `needs_information`.
- Validates supplied journey-applicable fields and values.
- Allows required fields to remain missing until submission.
- Preserves case journey and pinned versions.
- Appends `application_updated` with keys/counts only, never values.

Response:

```json
{
  "case_id": "uuid",
  "journey_type": "renewal",
  "payload": {
    "vehicle_age": 4,
    "claimed_ncb_percent": 20
  }
}
```

Errors:

- `403`: caller is not the owner or lacks permission.
- `404`: case not found.
- `409`: case is no longer mutable.
- `422`: key or supplied value is invalid.

## Pinned Case Configuration

### `GET /cases/{case_id}/configuration`

Response additions:

```json
{
  "case_id": "uuid",
  "journey_type": "renewal",
  "application": {},
  "fields": [],
  "documents": [
    {
      "code": "previous_policy",
      "stage": "prior_policy",
      "required": true
    }
  ]
}
```

Fields and documents are filtered for the immutable case journey. The
`application` object enables reload recovery without another endpoint.

## Document Upload and Submission

Existing document endpoints remain.

- Upload rejects a document code outside the case journey.
- Submit/resubmit validates required fields from the current stored
  application and required documents from actual document rows.
- Missing required prior-policy evidence returns `422`.
- Unreadable uploaded evidence follows current processing-failure and
  needs-information behavior.

## Staff and Handoff Views

Add `journey_type` to:

- queue items;
- review-start and review-decision responses;
- completion responses;
- handoff payloads;
- relevant case audit-event details.

Add optional `journey_type` filtering to `GET /queues`. Omission preserves
the current all-journey response.

Human review, override rationale, specialist labels, and repeated completion
semantics do not change.

## Administrator Configuration Read

### `GET /products/{code}/versions/{version}/configuration`

Permission: existing product-configuration read permission.

```json
{
  "product_code": "motor-private-car",
  "version": "v4",
  "lifecycle_status": "draft",
  "content_hash": "sha256",
  "configuration": {}
}
```

The nested configuration is validated and normalized through the current
product schema.

Errors:

- `403`: caller lacks read permission.
- `404`: product version not found.
- `409`: stored configuration no longer validates.

## Administrator Canonical Export

### `GET /products/{code}/versions/{version}/export`

Permission: existing product-configuration read permission.

Response:

- Status `200`.
- Content type `application/yaml`.
- Attachment filename derived only from sanitized product code and version.
- Body is canonical YAML from the validated normalized configuration.
- Field ordering follows the product schema; output is safe-loadable and
  imports to the same semantic configuration.

Errors match configuration read.

## Existing Product Write Operations

No new builder write endpoint is added.

- `POST /products/validate`, `/preview`, and `/import` continue accepting
  `{"yaml_text": "..." }`.
- The text may contain YAML or JSON, as supported today.
- Preview adds `configuration`, containing the normalized configuration.
- Existing preview counts and reconciliation summary remain for compatibility.
- Import always persists an immutable draft.
- Existing activation remains a separate confirmed action.
