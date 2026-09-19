# Research: Journey, Product Authoring, and Evaluation

## Decision 1: Store Journey on the Case

**Decision**: Add `new_business | renewal` to each case through additive
migration 08. Backfill and default existing rows to `new_business`.

**Rationale**: Journey affects intake, evidence, rules, review, audit, and
evaluation. Persisting it once prevents later inference from mutable answers.

**Alternatives considered**:

- Infer journey from fields or documents: ambiguous and not auditable.
- Store journey only in submission JSON: weak integrity and awkward queries.
- Separate renewal workflow tables: duplicates the existing case lifecycle.

## Decision 2: Extend and Filter the Existing Product Contract

**Decision**: Add journey metadata to the existing strict product schema.
Omitted metadata defaults to new-business-only. One shared pure helper filters
fields, documents, rules, and reconciliations for a case journey before current
validation and workflow logic runs.

**Rationale**: This preserves the one configuration and one rules engine
invariants. Existing stored configurations remain readable.

**Alternatives considered**:

- Separate renewal configuration files: risks drift between two products.
- Journey-specific workflow graphs: duplicates routing and reconciliation.
- Hardcoded family behavior: violates insurer-neutral configuration.

## Decision 3: Separate Draft Saving from Submission Validation

**Decision**: Case creation and application replacement accept incomplete
drafts but validate supplied keys and values. Submit and resubmit enforce all
journey-applicable fields and actual uploaded documents.

**Rationale**: Renewal must exist before prior-policy upload. Current creation
requires a complete form, while submission already has access to real document
rows.

**Alternatives considered**:

- Keep complete validation at creation: cannot support policy-first renewal.
- Trust client-declared document codes: does not prove evidence was uploaded.
- Add a second draft entity: unnecessary persistence and lifecycle.

## Decision 4: Preserve Immutable Product Versions

**Decision**: Add new motor and health configuration versions supporting both
journeys. Keep life new-business-only. Never rewrite existing version files or
repin existing cases.

**Rationale**: Product and rulebook identity is already immutable and case
pinning already works.

**Alternatives considered**:

- Edit existing version files: changes historical version meaning.
- Store journey rules outside the product version: breaks reproducibility.

## Decision 5: Compare Legacy Imports Semantically

**Decision**: If an existing product/version hash differs during re-import,
normalize both stored and incoming configurations through the current schema.
Return the existing version when normalized payloads match, retaining its
original content hash.

**Rationale**: New schema defaults otherwise enrich old configurations and
falsely make an unchanged legacy version appear different.

**Alternatives considered**:

- Rewrite existing hashes or payloads: mutates immutable version identity.
- Reject every legacy re-import: breaks idempotent bootstrap.
- Exclude all defaults globally: risks unrelated hash changes.

## Decision 6: Reuse Import as the Builder Write Path

**Decision**: Maintain one browser-side configuration object. Blank, clone,
and upload all hydrate that shape. Preview and import send its JSON text through
the existing `yaml_text` request; the backend loader already accepts JSON and
YAML.

**Rationale**: The current backend schema, cross-reference validation, draft
import, and activation lifecycle already provide the required authority.

**Alternatives considered**:

- Add a builder-specific write model or endpoint: duplicates the contract.
- Add mutable server-side drafts: adds schema and recovery semantics.
- Add a frontend YAML parser: unnecessary dependency and validation drift.

## Decision 7: Keep Diff and Incomplete Drafts in the Browser

**Decision**: Browser state may be incomplete until preview/import. Diff the
normalized candidate against a retrieved active version by stable identifiers:
field keys, document/rule/reconciliation codes, labels, and scalar properties.

**Rationale**: Diff is presentation, not a business rule. Backend validation
still controls persistence and activation.

**Alternatives considered**:

- Backend diff service: adds duplicate presentation policy.
- Autosave incomplete server drafts: conflicts with immutable imported drafts.

## Decision 8: Add Read and Canonical Export Only

**Decision**: Add administrator endpoints to retrieve a validated normalized
configuration and export canonical YAML. Use the existing repository,
permission, Pydantic schema, and PyYAML dependency.

**Rationale**: Clone and upload hydration need readable configuration. Export
must remain backend-owned to avoid another serializer.

**Alternatives considered**:

- Read configuration from history summaries: insufficient detail.
- Generate YAML in the browser: adds a dependency and canonicalization drift.

## Decision 9: Retain Two Evaluation Layers

**Decision**: Keep current in-memory fake-provider evaluation for fast metrics.
Add an HTTP-only runner for production-shaped behavior.

**Rationale**: The fast runner is useful but bypasses auth, persistence,
checkpoints, queues, audit, and idempotent completion.

**Alternatives considered**:

- Replace fast evaluation with end-to-end evaluation: slows routine feedback.
- Let the admin UI orchestrate evaluation infrastructure: wrong trust boundary.
- Query evaluation storage directly: weakens public-contract proof.

## Decision 10: Use a Standalone Ephemeral Compose Stack

**Decision**: Create an independent four-service stack: database, bootstrap,
API, and runner. Database data and uploads use tmpfs; no ports or named volumes
are exposed. Only the result directory is host-mounted.

**Rationale**: The base stack publishes ports and uses persistent development
volumes, so an overlay cannot prove isolation.

**Alternatives considered**:

- Overlay the development Compose file: can inherit ports, credentials, and
  volumes.
- Give the runner Docker or database access: unnecessary privilege.
- Use `down -v`: prohibited and unnecessary with tmpfs.

## Decision 11: Pin Evaluation Inputs and Stable Outputs

**Decision**: Every record names journey and exact product version. Use motor
v4, health v3, and life v1 for the revised reference set. The runner writes one
atomic JSON result with hashes, counts, metrics, failures, provider, and time.

**Rationale**: Selecting the earliest file is implicit and breaks
reproducibility after version additions. Hashes prove exactly what was tested.

**Alternatives considered**:

- Select active or earliest versions at runtime: depends on ambient state.
- Persist evaluation results in the business database: violates isolation.
- Compare elapsed time for determinism: runtime duration is observational.

## Decision 12: Exercise a Bounded Human-Review Subset

**Decision**: Process all 90 cases through recommendation. Review and complete
the first eligible case for each product, journey, and expected route
combination; invoke completion twice and require identical results.

**Rationale**: This proves human authority, checkpoint resume, queue handoff,
audit, and idempotency without duplicating the same costly action 90 times.

**Alternatives considered**:

- Complete all 90 cases: cost without additional contract coverage.
- Skip review: fails to prove the platform's central human boundary.
