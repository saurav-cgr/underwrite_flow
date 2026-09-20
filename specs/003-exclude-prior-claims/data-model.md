# Data Model: Exclude Prior Claims from New Business

No database schema change is required. This feature changes one immutable
configuration version and tightens validation around existing entities.

## Product

- **Identity**: `motor-private-car`
- **Relationship**: Owns multiple immutable product versions.
- **Invariant**: At most one version is active.

## Product Configuration Version

- **New identity**: `motor-private-car` / `v5`
- **Initial state**: `draft`
- **Fields**:
  - `prior_claims.applies_to`: `renewal`
  - all other field definitions: inherited unchanged from `v4`
- **Routing rules**:
  - `prior_claims_standard.applies_to`: `renewal`
  - all other rules: inherited unchanged from `v4`
- **Reconciliations**:
  - `motor_ncb_match` remains renewal-only and may use `prior_claims`
  - all other checks remain unchanged
- **Validation**:
  - every item journey is a subset of supported journeys
  - each rule condition field is available on the rule journey
  - each reconciliation input, document, and parameter field is available on
    the reconciliation journey
- **State transitions**:
  - `draft` to `active`: authenticated administrator activation
  - prior active sibling to `retired`: part of the same activation
  - active versions are never edited in place

## Rulebook Version

- **Identity**: Same version label and content identity as product version
  `v5`.
- **Relationship**: Belongs to exactly one product configuration version.
- **Invariant**: Rules are created during validated import and remain
  immutable.

## Case

- **Journey**: `new_business` or `renewal`
- **Relationships**: Pinned to one product version and one matching rulebook
  version.
- **New-business invariant for `v5`**: The applicable configuration contains no
  `prior_claims` field, rule, or reconciliation dependency.
- **Renewal invariant for `v5`**: Prior claims remain available to configured
  renewal rules and checks.
- **Historical invariant**: Existing cases retain their original versions and
  behavior after `v5` activation.

## Submission

- **Application payload**: Answers keyed by configured field name.
- **Validation rule**: Every submitted key must exist in the case's
  journey-filtered configuration.
- **New-business `v5` rule**: `prior_claims` is rejected as an unsupported
  application field.
- **Persistence rule**: A rejected payload is not stored and produces no case
  or replacement audit event.

## Audit Event

- Existing configuration import and activation events record the `v5`
  identity and actor.
- Existing case events continue to record the pinned product and rulebook
  versions.
- Historical events are never updated or deleted.

## Evaluation Record

- Selected current motor new-business records use `v5` and omit prior claims.
- Historical `v1` standard-route records remain unchanged because their label
  depends on the old rule.
- Renewal records may include prior claims when their pinned version requires
  them.
- The full dataset retains 90 cases and 30 expected cases per route.
