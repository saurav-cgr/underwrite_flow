# Quickstart: Validate RAG-Grounded Guidance

Run everything from the repository root through Docker Compose. Default
checks use `GENERATION_PROVIDER=fake` and the fake embedder; no network
access is needed. Contracts: [rest-api.md](contracts/rest-api.md),
[knowledge-corpus.md](contracts/knowledge-corpus.md). Tables:
[data-model.md](data-model.md).

## Prerequisites

- Stack builds: `docker compose build api web`.
- Migrations apply: `docker compose run --rm api alembic upgrade head`,
  then `alembic current` shows the newest knowledge revision.
- Development data reset (only when the date-of-birth field lands): use the
  README section "Reset local demonstration". It removes only
  `postgres_data` and `uploads_data`. Never use `docker compose down -v`.

## Gate order per story

1. Unit: `docker compose run --rm api pytest tests/unit -q`
2. Integration: `docker compose run --rm api pytest tests/integration -q`
3. Web: `docker compose run --rm web npm test -- --run`
4. End-to-end for every story, because each one crosses components
   (configuration, API, database, workflow, provider, or web): `make
   smoke`, then the story scenario below against the running stack.

A failing gate stops the next gate.

## Story scenarios

### US1: Life corpus alignment

- Run `pytest tests/unit/test_knowledge_alignment.py -q`.
- Expect: the shipped `knowledge-config/life-individual-term/g1.yaml`
  passes; the seeded mismatch fixture fails with `threshold_mismatch`
  naming the section, stated value, and rule value.
- Expect: `product-config/life-individual-term-v3.yaml` rejects a future
  `date_of_birth`.
- End-to-end: activate life v3, submit a life case with a past date of
  birth through the web form, and confirm a future date is refused.

### US2: Versioned knowledge store

- Sign in as Administrator. Import `g1`, preview it, activate it.
- Start a life case. Import and activate `g2`. Start a second case.
- Expect: case one pins `g1`, case two pins `g2`; the audit trail shows
  both `knowledge_version_activated` events; Underwriter and Applicant
  calls to `/knowledge/*` return 403.

### US3: Retrieval quality

- Run `pytest tests/integration/test_retrieval_recall.py -q`.
- Expect: top-five recall at least 0.90 on 30 life questions; no result
  from a non-pinned version; exact rule-code queries rank their section in
  the top five.
- End-to-end: with the stack up and `g1` active, run
  `docker compose run --rm api python /app/scripts/evaluate_retrieval.py`
  (fake provider): recall at least 0.90 through the running database.
- Optional live check (never gates acceptance): the same script with
  `GENERATION_PROVIDER=gemini` and an approved key.

### US4: Route explanation

- Submit one fictional life case per route plus one needs-information case.
- Open each as Underwriter.
- Expect: at most 120 words, at least one citation, synthetic label;
  missing items listed with reasons; route unchanged versus a run with
  guidance disabled.
- Restart the API (`docker compose restart api`) and reopen: text and
  citations are identical.
- Timing, API: `pytest tests/integration/test_guidance_latency.py -q`
  shows the stored explanation returned in under 3 seconds.
- Timing, screen (SC-008): `make test-e2e` runs
  `web/e2e/guidance-timing.spec.ts` in the Playwright container: 5 cases,
  each from click to visible explanation under 3 seconds. Record the five
  printed times in the story report.

### US5: Underwriter Q&A

- Ask a covered question, an uncovered question, and a question on the
  prompt-injection fixture case.
- Expect: citation on the covered answer; exactly
  `not covered by guidelines` on the uncovered one; the injected
  instruction is ignored and the route is unchanged; each exchange is
  audited; Administrator and Applicant get 403.

### US6: Specialist brief

- Submit the hazardous-occupation fixture. Open it as Underwriter.
- Expect: brief with evidence sources, `hazardous_occupation_specialist`,
  and cited passages; override dialog suggests up to three citations.

### US7: Regulatory corpus

- Place manifest files in `data/regulatory/` (git-ignored).
- Administrator imports regulation, reviews and accepts tags, activates.
- Expect: altered or unlisted files are rejected; the `.doc` file is
  skipped as `unsupported_format`; clauses show
  `PUBLIC REGULATION - INFORMATIONAL` beside guideline sections.
- Run `pytest tests/integration/test_regulation_route_isolation.py -q`:
  routes are identical with and without the regulation version.
- Check `git status`: no regulatory text is tracked.

### US8: Conformance preview

- Preview a fictional rules draft that violates an accepted clause limit.
- Expect: the flag and the change-impact diff appear; activation succeeds;
  a `conformance_flags_recorded` audit event exists.

### US9: Motor and health

- Run the US1 and US3 checks, including the end-to-end retrieval
  script, for `motor-private-car` and
  `health-individual-family-floater`:

  ```bash
  docker compose run --rm api python /app/scripts/evaluate_retrieval.py \
    motor-private-car
  docker compose run --rm api python /app/scripts/evaluate_retrieval.py \
    health-individual-family-floater
  ```

- Expect: alignment passes and recall is at least 0.90 per product.
