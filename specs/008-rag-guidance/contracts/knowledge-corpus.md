# Contract: Knowledge Corpus Files

## Guideline corpus

Path: `knowledge-config/<product_code>/<version>.yaml`. Fictional content
only. Loaded by an administrator (upload or bootstrap import) as a draft
guideline version.

```yaml
# SYNTHETIC - FOR DEMONSTRATION ONLY
product_code: life-individual-term
version: g1
aligned_product_version: v3
label: SYNTHETIC - FOR DEMONSTRATION ONLY
topics: [cover-amount, occupation, health-declaration, identity, age]
sections:
  - id: life-cover-high-sum-assured
    title: High requested cover
    topic: cover-amount
    sum_assured_min: 10000001
    thresholds:
      - rule_code: high_cover_standard
        field: requested_cover
        operator: greater_than
        value: 10000000
    body: >-
      Requested cover above 10000000 goes to standard review and needs a
      synthetic income record.
  - id: life-occupation-hazardous
    title: Hazardous occupation
    topic: occupation
    thresholds:
      - rule_code: hazardous_occupation_specialist
        field: occupation_type
        operator: equals
        value: hazardous
    body: >-
      A hazardous occupation is referred to life review specialists.
```

Rules:

- `label` MUST equal `SYNTHETIC - FOR DEMONSTRATION ONLY`.
- `aligned_product_version` MUST name an existing product version; the
  alignment check runs against it. Activation additionally requires it to
  be the product's active version.
- `rule_code` MUST name a routing rule, or `document:<code>` for a
  conditional document requirement, in that product version.
- `field`, `operator`, and `value` MUST equal the rule's condition.
- Every number in `body` MUST equal a declared threshold value or one of
  the section's band bounds (research R5).
- Band keys: `age_min`, `age_max`, `sum_assured_min`, `sum_assured_max`;
  omitted means unbounded.

Alignment report (returned by validate and preview):

```json
{
  "valid": false,
  "issues": [
    {
      "code": "threshold_mismatch",
      "section_id": "life-cover-high-sum-assured",
      "stated": 5000000,
      "rule_value": 10000000,
      "rule_code": "high_cover_standard"
    }
  ]
}
```

Issue codes: `threshold_mismatch`, `unknown_rule`, `undeclared_number`,
`duplicate_section_id`, `unknown_topic`, `invalid_band`, `missing_label`,
`product_version_not_found`.

## Regulatory manifest

Path: `data/regulatory/manifest.yaml` (git-ignored, existing format).
Fields used: `id`, `file`, `title`, `issuer`, `date`, `product_lines`,
`sha256`. Files outside the manifest are never read.

Load report per file:

```json
{"id": "life_products_mc_2024", "status": "loaded", "clauses": 84}
{"id": "insurance_act_1938", "status": "skipped",
 "reason": "unsupported_format"}
{"id": "health_mc_2024", "status": "rejected",
 "reason": "checksum_mismatch"}
```

Reason codes: `checksum_mismatch`, `missing_file`, `unsupported_format`,
`no_clauses_found`.

## Retrieval evaluation set

Path: `evaluation/retrieval/<product_code>.yaml`.

```yaml
# SYNTHETIC - FOR DEMONSTRATION ONLY
product_code: life-individual-term
questions:
  - id: life-q01
    question: What review does a cover above ten million need?
    case: {sum_assured: 15000000, age: 42}
    expected: [life-cover-high-sum-assured]
```

A question counts as a hit when any `expected` key appears in the top five
results. Recall is hits divided by question count.
