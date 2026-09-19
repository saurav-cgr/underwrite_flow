# Product Configuration Contract

This extends the existing strict configuration. Unknown keys remain rejected.
Existing field, condition, routing, reconciliation, and specialist-label rules
remain authoritative.

## Journey Fields

```yaml
supported_journeys: [new_business, renewal]

fields:
  - key: claimed_ncb_percent
    applies_to: [renewal]

documents:
  - code: previous_policy
    requirement: optional
    applies_to: [renewal]
    required_for: [renewal]
    stage: prior_policy

routing_rules:
  - code: vehicle_age_review
    applies_to: [new_business, renewal]

reconciliations:
  - code: motor_ncb_match
    applies_to: [renewal]
```

Allowed journeys:

```text
new_business
renewal
```

Allowed document stages:

```text
prior_policy
supporting
```

## Defaults and Compatibility

| Location | Omitted value |
| --- | --- |
| Product `supported_journeys` | `[new_business]` |
| Item `applies_to` | `[new_business]` |
| Document `required_for` | null; use legacy requirement semantics |
| Document `stage` | `supporting` |

An old configuration therefore retains exactly its new-business behavior.

## Requirement Semantics

- Items outside `applies_to` are invisible and cannot execute.
- A field marked `required` is required on each applicable journey.
- With document `required_for: null`, current `requirement` and
  `condition` semantics apply on each applicable journey.
- With an explicit `required_for` list, only listed journeys can require the
  document. An empty list makes it optional.
- A conditional document is required only when the journey is listed and its
  existing condition matches.
- A `not_applicable` document cannot list a required journey.

## Cross-Reference Validation

Validation rejects:

- empty or duplicate journey lists;
- an item journey not declared by the product;
- `required_for` outside document `applies_to`;
- a renewal-supporting product without required prior-policy evidence;
- prior-policy evidence that does not apply to renewal;
- a rule condition referencing a field unavailable on that rule's journey;
- a reconciliation application input unavailable on the check's journey;
- a reconciliation document source unavailable on the check's journey;
- existing unknown identifiers, unsupported operators, reconciliation kinds,
  content types, parameters, or specialist labels.

## Built-In Versions

### Motor v4

- Supports new business and renewal.
- Shared vehicle and identity inputs apply to both.
- Prior-policy evidence, NCB claim, NCB comparison, and lapse checks apply only
  to renewal.
- Existing deterministic routes are preserved unless a renewal-only check
  produces a more cautious result.

### Health v3

- Supports new business and renewal.
- Shared member and health inputs apply to both.
- Prior-policy evidence and lapse-related inputs/checks apply only to renewal.
- Existing deterministic routes are preserved.

### Life v1

- Remains new-business-only through defaults.
- Renewal or revival is out of scope.

No prior configuration file is modified.

## Normalization and Identity

The normalized form is the current schema's JSON-compatible object with stable
field ordering and absent optional nulls handled consistently.

- Hash new versions from normalized content.
- If a legacy stored hash differs, compare normalized stored and incoming
  content before reporting a conflict.
- Semantic equality returns the existing version and preserves its stored hash.
- Semantic difference for the same product/version remains a conflict.
- Retrieval, preview, browser diff, export, and import use the same normalized
  shape.

## Builder Contract

One browser object mirrors this contract.

- Blank starts with required scalar properties and empty item lists.
- Clone loads a normalized saved version, forces lifecycle status to draft,
  and requires a new version identity.
- Upload posts YAML to preview, then hydrates from normalized configuration.
- Builder JSON is stringified into the existing `yaml_text` request field.
- Local validation covers required controls, primitive types, and duplicate
  identifiers only.
- Backend validation owns all cross-references and executable-rule boundaries.
- Imported drafts are immutable. Correction requires another version.
- AI cannot create, modify, or activate rules.

## Browser Diff

Compare candidate to active normalized configuration:

- scalar properties and supported journeys by property;
- fields by `key`;
- documents, rules, and reconciliations by `code`;
- specialist labels by value;
- stable order separately from content.

Display added, removed, changed, and reordered items with text and icons, never
color alone. A product without an active version displays `new product`
instead of a diff.
