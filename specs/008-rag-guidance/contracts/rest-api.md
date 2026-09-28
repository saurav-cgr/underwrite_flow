# REST API Contract: RAG-Grounded Guidance

Base path `/api/v1`. Security, token claims, and the error envelope follow
`specs/001-underwriting-platform/contracts/rest-api.md`. Every response
that carries passage text also carries the passage `label`.

## Guards

| Guard | Existing dependency | Who passes |
|-------|--------------------|------------|
| admin-config | `require_permission(PRODUCT_CONFIG_WRITE)` | administrator |
| admin-read | `require_permission(PRODUCT_CONFIG_READ)` | administrator |
| underwriter | `require_underwriter()` | underwriter role only |

No new permission scope is introduced.

## Knowledge versions (US2, US7)

### POST `/knowledge/validate` (admin-config)

Body: `{"scope": "guideline", "yaml": "<corpus text>"}`.
Response 200: alignment report (see
[knowledge-corpus.md](knowledge-corpus.md)). Nothing is stored.

### POST `/knowledge/import` (admin-config)

Body: `{"scope": "guideline", "yaml": "<corpus text>"}`. Creates a draft
version. 201 `{"id", "scope", "product_code", "version", "status":
"draft", "passage_count", "validation"}`. 409 when the version identity
exists with different content. 422 when the file cannot be parsed.

### POST `/knowledge/regulation/import` (admin-config)

Body: none. Reads the manifest, verifies checksums, loads a draft
regulation version. 201 `{"id", "version", "files": [<load report>]}`.

### GET `/knowledge/versions?scope=&product_code=` (admin-read)

List of `{"id", "scope", "product_code", "version", "status",
"content_type", "passage_count", "activated_at"}`, newest first.

### GET `/knowledge/versions/{id}/preview` (admin-read)

`{"version": {...}, "validation": {...}, "passages": [{"passage_key",
"title", "topic", "bands", "label", "body", "thresholds",
"topic_tags", "suggested_tags", "limits"}]}`. Paged with `?offset=&limit=`
(limit at most 100).

### PUT `/knowledge/versions/{id}/passages/{passage_key}/tags` (admin-config)

Regulation drafts only. Body `{"topic_tags": ["cover-amount"],
"limits": [{"field": "requested_cover", "operator": "greater_than",
"value": 0}]}`. 409 when the version is not a draft.

### POST `/knowledge/versions/{id}/activate` (admin-config)

Re-runs validation. 200 with the activated version; the previous active
version for the same scope and product becomes `retired`. 422 with the
validation report when validation fails. 409 on a lost activation race.

### POST `/knowledge/versions/{id}/retire` (admin-config)

200 with the retired version.

## Case guidance (US4, US6, US7)

### GET `/reviews/{case_id}/guidance` (underwriter)

```json
{
  "pinned": {"guideline_version": "g1", "regulation_version": "r1"},
  "route_explanation": {
    "status": "generated",
    "text": "Standard review: requested cover is above the threshold.",
    "missing_items": [
      {"item": "income_record", "reason": "Cover above threshold",
       "citations": [{"version": "g1",
         "passage_key": "life-cover-high-sum-assured"}]}
    ],
    "citations": [{"version": "g1",
      "passage_key": "life-cover-high-sum-assured"}],
    "label": "SYNTHETIC - FOR DEMONSTRATION ONLY"
  },
  "specialist_brief": null,
  "suggested_citations": []
}
```

`status` is `generated`, `template`, or `unavailable`. `specialist_brief`
is present only for specialist-routed cases; `suggested_citations` holds
at most three entries. This endpoint never changes the recommendation.

### GET `/reviews/{case_id}/guidance/passages/{passage_key}` (underwriter)

Returns one pinned passage and, for guideline passages, related regulatory
clauses from the pinned regulation version:
`{"passage": {...}, "related_regulation": [{..., "label":
"PUBLIC REGULATION - INFORMATIONAL"}]}` (at most three).

## Underwriter Q&A (US5)

### POST `/reviews/{case_id}/questions` (underwriter)

Body `{"question": "<1-1000 chars>"}`. 201:

```json
{
  "id": "uuid",
  "question": "Does a hazardous occupation need a specialist?",
  "answer": "Yes. Hazardous occupations are referred to life review.",
  "covered": true,
  "citations": [{"version": "g1",
    "passage_key": "life-occupation-hazardous"}],
  "asked_by": "Synthetic Underwriter",
  "created_at": "2026-09-28T10:00:00Z"
}
```

When uncovered: `"answer": "not covered by guidelines"`, `"covered":
false`, `"citations": []`. 403 for applicants and administrators. 404 for
an unknown case.

### GET `/reviews/{case_id}/questions` (underwriter)

Full history for the case, oldest first, all underwriters (clarification
Q5).

## Conformance preview (US8)

### POST `/products/preview` (existing, admin-config)

Response gains two keys; activation is never blocked by them:

```json
{
  "conformance": {
    "regulation_version": "r1",
    "flags": [
      {"rule_code": "high_cover_standard", "field": "requested_cover",
       "rule_value": 10000000, "clause": {"passage_key": "4.2",
       "limit": {"operator": "greater_than", "value": 0}},
       "label": "PUBLIC REGULATION - INFORMATIONAL"}
    ],
    "related": [{"rule_code": "...", "passage_keys": ["..."]}]
  },
  "change_impact": {
    "against_version": "v2",
    "added_rules": [], "removed_rules": [],
    "changed_thresholds": [{"rule_code": "high_cover_standard",
      "from": 10000000, "to": 5000000}],
    "changed_documents": []
  }
}
```

`POST /products/{code}/activate` (existing) records a
`conformance_flags_recorded` audit event when flags exist and proceeds.
