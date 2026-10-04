# Specification: Later RAG Stories

Continuation of [spec.md](spec.md); requirements remain there.

### User Story 6 - Specialist Brief (Priority: P6)

A case routed to specialist review receives a brief. The brief lists the
evidence with its sources, the triggered rules, and the relevant guideline
passages. When the underwriter overrides a route, the override dialog
suggests citations for the reason.

**Why this priority**: It shortens specialist review but is useful only
after explanations exist.

**Independent Test**: Process a fictional hazardous-occupation life case.
Confirm the brief contents and suggested citations in the override dialog.

**Acceptance Scenarios**:

1. **Given** a specialist-routed case, **When** the specialist opens it,
   **Then** the brief shows evidence with source document references,
   triggered rule codes, and cited guideline passages.
2. **Given** the override dialog, **When** it opens, **Then** it suggests
   up to three citations the underwriter may accept or ignore.
3. **Given** a case not routed to specialist review, **Then** no brief is
   produced.

### User Story 7 - Informational Regulatory Corpus (Priority: P7)

The system loads public IRDAI clauses only from documents in the approved
regulatory manifest, after verifying each file's checksum. Each clause is
badged `PUBLIC REGULATION - INFORMATIONAL`. Reviewers see clauses side by
side with guideline sections on the same topic. Clauses never affect route
calculation.

**Why this priority**: Context is helpful, but it has no effect on routes.

**Independent Test**: Load the manifest documents, alter one file, and
confirm that file is rejected. Process cases with and without the
regulatory corpus and confirm identical routes.

**Acceptance Scenarios**:

1. **Given** a manifest document whose checksum matches, **When** loading
   runs, **Then** its clauses load with document, clause reference, and
   the informational badge.
2. **Given** a file whose checksum differs, or a file absent from the
   manifest, **When** loading runs, **Then** that file is rejected and
   reported.
2a. **Given** an administrator who uploads a document equal to an
   unlisted file, **When** the upload runs, **Then** it is rejected,
   audited `regulation_file_rejected`, and no bytes are written.
3. **Given** a guideline section, **When** a reviewer views it, **Then**
   the most related clauses from the pinned regulatory version, found by
   meaning, appear beside it.
4. **Given** the same case set, **When** processed with and without the
   regulatory corpus, **Then** every route is identical.

### User Story 8 - Rule Conformance Preview (Priority: P8)

When an administrator previews a product-rules version, the preview lists
rules that may conflict with active regulatory clauses and summarizes the
change impact against the active version. The information never blocks
activation.

**Why this priority**: It helps administrators but is informational only.

**Independent Test**: Preview a fictional rules version with a known
potential conflict. Confirm the flag, the impact summary, and that
activation still succeeds.

**Acceptance Scenarios**:

1. **Given** a draft rules version, **When** the administrator previews it,
   **Then** the preview lists possible conflicts with cited clauses, found
   only by threshold and topic-tag matching, never by model judgment.
2. **Given** a draft and an active version, **When** previewed, **Then** a
   summary shows added, removed, and changed rules and thresholds.
3. **Given** flagged conflicts, **When** the administrator activates the
   draft, **Then** activation proceeds and the flags are audited.

### User Story 9 - Motor and Health Guidelines (Priority: P9)

The guideline corpus and its alignment check extend to private-car motor
and individual/family-floater health, aligned with their active product
rules. The evaluation set extends to cover both products.

**Why this priority**: Life proves the pattern; the other products follow.

**Independent Test**: Run the alignment check and the retrieval evaluation
for motor and health.

**Acceptance Scenarios**:

1. **Given** motor and health corpora, **When** the alignment check runs,
   **Then** every stated threshold matches the respective active rules.
2. **Given** motor and health evaluation questions, **When** retrieval
   runs, **Then** top-five recall meets the life target per product.

### User Story 11 - Common Model Configuration (Priority: P11)

A developer configures generation and embedding models with common names
and gets the correct defaults for each independently selected provider.

**Independent test**: deterministic settings, mocked provider builders,
Compose contracts, persistence regression tests, and smoke all pass.

**Acceptance scenarios**:

1. Unset, empty, or whitespace-only common model values resolve to the
   selected provider's defaults in the configuration contract.
2. Explicit common model overrides reach extraction, guidance, and
   embedding adapters; surrounding whitespace is removed.
3. Gemini generation and Ollama embeddings can be selected independently.
   An unspecified backend embedding provider retains its existing fallback
   to the generation provider. Compose retains its fake embedding default.
4. The four old provider-specific model variables and Settings fields are
   removed without aliases. Existing private overrides require renaming.
5. API and bootstrap receive matching provider settings; model defaults
   are defined once in backend configuration rather than Compose.
6. Fake providers, security checks, tracing defaults, routes, and stored
   provider/model metadata retain their existing behavior.
7. A resolved embedding model change still triggers re-embedding; an
   unchanged model reuses embeddings for guideline and regulation imports.

**Requirements**:

- **FR-020**: Expose GENERATION_MODEL and EMBEDDING_MODEL as optional
  model overrides. Apply the default and normalization rules above.
- **FR-021**: Remove GEMINI_MODEL, OLLAMA_MODEL,
  GEMINI_EMBEDDING_MODEL, and OLLAMA_EMBEDDING_MODEL without fallbacks.
- **FR-022**: Keep provider credentials, URLs, safety configuration, and
  selection separate. Do not change provider capabilities or defaults.
- **SC-010**: Every deterministic US11 gate passes with no live calls.

**Scope**: provider configuration only; no migration, dependency, auth,
tracing activation, database reset, or frontend behavior change.
