# Research: Exclude Prior Claims from New Business

## Decision 1: Deliver an additive motor product version

**Decision**: Add `motor-private-car` version `v5`, copied from `v4`, with the
`prior_claims` field and its standard-routing rule limited to `renewal`.
Keep the NCB reconciliation renewal-only. Import `v5` as a draft.

**Rationale**: Cases pin immutable product and rulebook versions. A new version
changes only cases started after an administrator activates it and preserves
historical reconstruction.

**Alternatives considered**:

- Editing `v4` was rejected because it would rewrite an immutable version.
- Removing prior claims from renewal was rejected because renewal behavior is
  explicitly preserved.
- Hardcoding `prior_claims` in workflow code was rejected because product and
  journey behavior is configuration-owned.

## Decision 2: Reject stale values at the shared intake boundary

**Decision**: Make draft validation reject every payload key that is absent
from the journey-filtered field set. Return a safe field-specific 422 error for
case creation and application replacement.

**Rationale**: The existing validator checks known field values but silently
accepts unknown or journey-inapplicable keys. One generic subset check closes
the trust-boundary gap for all products and both create and update paths.

**Alternatives considered**:

- Silently dropping `prior_claims` was rejected because the client would not
  know its submission was altered.
- Adding endpoint-specific checks was rejected because create, update, and
  submit all converge on shared validation.
- Rejecting only the literal `prior_claims` key was rejected as duplicated
  product knowledge.

## Decision 3: Validate all journey-dependent reconciliation references

**Decision**: Extend the generic journey validator so a reconciliation
parameter field, including an NCB claim-count field, must be available on each
journey where the reconciliation applies.

**Rationale**: Rule condition fields, reconciliation application inputs, and
document sources are already checked by journey. Parameter field references
are the remaining path that could bypass configuration validation.

**Alternatives considered**:

- Relying only on the corrected `v5` file was rejected because a later import
  could be internally inconsistent.
- Runtime skipping was rejected because invalid configuration should fail
  before import or activation.

## Decision 4: Filter review configuration by the pinned case journey

**Decision**: Apply the existing pure journey filter when the review endpoint
loads a readable pinned configuration.

**Rationale**: Catalogue, intake, submission, rules, and reconciliation already
use the filtered configuration. Review currently loads the full version, which
can expose renewal-only labels or requirements on a new-business case.

**Alternatives considered**:

- Hiding only `prior_claims` in the review response was rejected as another
  source of journey truth.
- Filtering in the web client was rejected because backend review contracts
  must be authoritative.

## Decision 5: Cover `v5` without inventing a routing rule

**Decision**: Move the motor new-business evaluation records whose routes do
not depend on prior claims to `v5`, then remove prior claims from their payload
and document text. Keep claim-driven standard records pinned to historical
`v1`. Update the smoke path to activate `v5` and omit prior claims.

**Rationale**: This adds current-version evaluation coverage while preserving
the required 30/30/30 route distribution. The remaining `v1` records are
explicit historical-version cases, not examples of the current product.

**Alternatives considered**:

- Repointing all motor new-business records to `v5` was rejected because five
  standard labels depend only on the retired prior-claims rule.
- Changing the required route balance was rejected because feature 002 fixes
  the corpus at 30 cases per route.
- Inventing a replacement standard-routing rule was rejected as unsupported
  underwriting behavior.

## Decision 6: Reuse existing interfaces and dependencies

**Decision**: Keep the existing catalogue, case, configuration, review, audit,
and activation interfaces. Add no database migration, package, or frontend
state model.

**Rationale**: Journey-filtered fields already drive the application form, and
product import already creates immutable draft versions and audit events.

**Alternatives considered**:

- A dedicated claims endpoint or feature flag was rejected as unnecessary.
- A schema column marking renewal-only claims was rejected because
  `applies_to` already models the requirement.
