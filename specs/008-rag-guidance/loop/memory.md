# Loop Memory

Keep short decisions and dead ends across sessions. Do not restate the
contract or copy full logs here.

<!-- - [M-001] <decision> (iteration <n>, <date>) -->

- [M-001] User approved T005 [NEEDS APPROVAL]: add
  `product-config/life-individual-term-v3.yaml`, synthetic
  `date_of_birth` in life `evaluation/cases.json` payloads, and reset dev
  data via README "Reset local demonstration" (never `down -v`).
  Given in checker session. (iteration 2, 2026-09-28)
- [M-002] Life v3 evaluation fixtures must carry synthetic `date_of_birth`
  evidence in `identity_record`; otherwise baseline marks complete cases as
  missing information. (iteration 5, 2026-09-28)
- [M-003] Corpus parsing uses closed product topic sets; alignment rejects
  every body number not declared by a threshold or band. (iteration 6,
  2026-09-28)
- [M-004] T010 stays under integration because it reads mounted knowledge
  files; checkpoint paths must match repository paths. (iteration 7,
  2026-09-28)
- [M-005] Journey contract tests must select motor v1 before draft creation;
  active product state is shared across tests. (iteration 8, 2026-09-28)
- [M-006] Repository migration 08 uses revision id `08`; US2 migration chains
  from that id and keeps knowledge pins FK-safe in test cleanup. (iteration 9,
  2026-09-28)
- [M-007] Evaluation-document recovery now has isolated unit coverage for
  present-but-corrupt files; unconditional hashing remains accepted at current
  corpus scale. (iteration 10, 2026-09-28)
- [M-008] US2 review coverage must exercise bootstrap import, every knowledge
  endpoint, public submission pinning, and activation audit metadata; pin
  audit timestamps use database defaults. (iteration 11, 2026-09-28)
- [M-009] Knowledge imports map identity races to domain conflicts; activation
  flushes sibling retirement before target activation and repeats are no-ops.
  (iteration 12, 2026-09-28)
- [M-010] Knowledge validation aligns to the named product version; activation
  alone requires that version to be active. Read previews use unlocked SQL
  pagination with administrator page controls. (iteration 13, 2026-09-28)
- [M-011] Knowledge summaries use SQL passage counts; preview pages never load
  all passage bodies for metadata. (iteration 14, 2026-09-28)
- [M-012] Retrieval uses fake embeddings for bootstrap and backfills missing
  embeddings on idempotent imports; Gemini remains opt-in. (iteration 15)
- [M-013] Bootstrap now builds the configured embedding provider; smoke and
  evaluation explicitly select fake embeddings. (iteration 16)
- [M-014] Bootstrap mirrors API Gemini embedding settings; deterministic
  Compose overrides set fake provider explicitly. (iteration 17)
- [M-015] US3 repair tests now assert absent-fact filtering, vector width, and
  cosine index operator class; nested helpers carry intent comments.
  (iteration 18)
- [M-016] Corpus embedding provider is explicit; local Compose selects fake,
  while approved Gemini selection remains opt-in and guarded. Retrieval tests
  avoid activation side effects. (iteration 19)
- [M-017] Knowledge preview renders stable key, topic, age band, and
  sum-assured band; Ollama embeddings fail explicitly until an adapter exists.
  (iteration 20)
