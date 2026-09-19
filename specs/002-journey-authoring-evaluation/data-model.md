# Data Model: Journey, Product Authoring, and Evaluation

## Relationship Overview

```text
Product 1---* ProductVersion 1---* RulebookVersion
                              |
                              *---* Case 1---1 Submission
                                      |  |
                                      |  *---* Document
                                      |  *---* AuditEvent
                                      |  *---* Review
                                      |  0..1 Handoff
                                      |
                                      + journey_type

EvaluationDataset 1---90 EvaluationCase
EvaluationRun 1---1 ResultArtifact
```

Evaluation entities are files and runtime records, not business-database
tables.

## Persisted Entity Changes

### Case

Purpose: applicant-owned application pinned to one product, rulebook, and
journey.

| Field | Type | Rules |
| --- | --- | --- |
| `journey_type` | string | `new_business` or `renewal`; non-null |

Migration rules:

- Add in revision 08 after `07_dynamic_rbac.py`.
- Use server default `new_business` and backfill every existing row.
- Add a database check constraint for the two values.
- Keep the default so legacy insert fixtures remain compatible.
- Downgrade removes the check constraint, then the column.
- Never modify `01_initial.py` or earlier revisions.

Identity and lifecycle rules:

- Journey is set at case creation and never changes.
- Product and rulebook versions remain pinned.
- Journey changes require a new case.
- Journey is not a final insurance action or route.

### Submission

No column changes.

The existing `payload.application` object remains the current draft answer
set. Application replacement updates that object transactionally while
preserving unrelated submission metadata.

Rules:

- Exactly one submission is used for one case.
- Replacement is allowed only for the owning applicant while case status is
  `new` or `needs_information`.
- Replacement is complete, not a merge.
- Stored answers may be incomplete before submission.
- Unknown or non-applicable fields and invalid supplied values are rejected.
- Required fields are enforced on submit/resubmit.
- Legacy `payload.document_codes` may remain readable but is never trusted
  for evidence completeness.

### Document

No column changes.

The document code resolves through the case's pinned product configuration and
journey.

Rules:

- Upload accepts only journey-applicable document codes.
- Actual document rows determine submission completeness.
- A prior-policy document is still untrusted applicant evidence.
- Current count, type, size, and mutability limits remain.

### Product and ProductVersion

No column changes.

The existing JSON configuration gains journey metadata. Product code and family
remain stable identity; title, scope, and description remain versioned content.
Lifecycle status remains authoritative on `ProductVersion.status`, not the
legacy status value inside configuration JSON.

Import rules:

- Every builder or expert import creates an immutable draft version.
- A same product/version and same semantic configuration is idempotent.
- A same product/version with different semantic content is rejected.
- Adding schema defaults does not rewrite an existing payload or content hash.
- Activation remains serialized, audited, and prospective.

## Embedded Product Configuration

### JourneyType

```text
new_business | renewal
```

### ProductConfiguration

New field:

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `supported_journeys` | journey list | `[new_business]` | unique, non-empty |

Every declared journey must be supported. Motor v4 and health v3 support both;
life v1 and legacy configurations support new business only.

### ProductField

New field:

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `applies_to` | journey list | `[new_business]` | non-empty supported subset |

A required field is required only on journeys in `applies_to`.

### ProductDocument

New fields:

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `applies_to` | journey list | `[new_business]` | non-empty supported subset |
| `required_for` | journey list or null | null | subset of `applies_to` |
| `stage` | enum | `supporting` | `prior_policy` or `supporting` |

Effective requirement:

1. Outside `applies_to`: document is hidden and rejected if uploaded.
2. When `required_for` is null: preserve existing `requirement` and
   conditional behavior for every applicable journey.
3. When `required_for` is present: only listed journeys may require the
   document; conditional documents also require their condition to match.
4. An empty `required_for` makes the applicable document optional.

Validation:

- A renewal-supporting product has at least one `prior_policy` document whose
  `required_for` contains `renewal`.
- A prior-policy document applies to renewal.
- `not_applicable` documents cannot declare required journeys.

### RoutingRule and ReconciliationCheck

New field on each:

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `applies_to` | journey list | `[new_business]` | non-empty supported subset |

References must resolve for every applicable journey:

- Rule conditions reference journey-applicable fields.
- Reconciliation application inputs reference journey-applicable fields.
- Reconciliation document sources reference journey-applicable documents.
- Existing kind, parameter, source-count, operator, and label checks remain.

## Journey-Filtered Configuration

One pure operation accepts a validated pinned configuration and journey, then
returns the same configuration shape containing only applicable fields,
documents, rules, and reconciliations.

Properties:

- Input configuration is not mutated.
- Stable source ordering is retained.
- Unsupported journey is rejected.
- Repeated filtering produces equivalent output.
- Existing validation, extraction, reconciliation, and routing consume the
  filtered configuration.

## State Transitions

### Case

```text
new
  -> underwriter_review
  -> needs_information -> underwriter_review
  -> confirmed | overridden
  -> completed
```

Journey does not add a case status. Draft application and document changes are
allowed only in `new` and `needs_information`.

### Product Version

```text
browser draft (not persisted)
  -> imported draft (immutable)
  -> active
  -> retired
```

An imported draft cannot be edited. Corrections clone to a new version.

## Evaluation File Entities

### EvaluationCase

Required identity fields:

| Field | Type | Rules |
| --- | --- | --- |
| `case_id` | string | unique, stable, synthetic |
| `product_code` | string | known fictional product |
| `configuration_version` | string | exact imported version |
| `journey_type` | journey | supported by the named version |
| `split` | enum | `development` or `holdout` |

Existing workflow input, synthetic document lines, and expected outcome remain.

Dataset invariants:

- Exactly 90 records.
- Motor: 15 new business and 15 renewal.
- Health: 15 new business and 15 renewal.
- Life: 30 new business.
- Expected routes: 30 expedited, 30 standard, 30 specialist.
- Every record uses motor v4, health v3, or life v1 as applicable.

### EvaluationResult

Written to `evaluation/results/e2e.json`.

| Field | Type | Rules |
| --- | --- | --- |
| `schema_version` | integer | starts at 1 |
| `passed` | boolean | false for any failed invariant |
| `provider` | string | exactly `fake` |
| `dataset_sha256` | string | lowercase SHA-256 |
| `configurations` | object | version and content hash per product |
| `case_count` | integer | exactly 90 |
| `journey_counts` | object | deterministic counts |
| `route_counts` | object | deterministic counts |
| `metrics` | object | existing aggregate metric names and values |
| `reviewed_count` | integer | representative reviews completed |
| `completed_count` | integer | idempotent handoffs completed |
| `failures` | array | stable `case_id, stage, code` ordering |
| `elapsed_seconds` | number | observational, non-deterministic |

The result excludes credentials, tokens, database URLs, applicant payloads,
raw documents, and hidden workflow state.
