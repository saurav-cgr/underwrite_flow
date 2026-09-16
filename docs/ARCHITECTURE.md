# UnderwriteFlow architecture

```mermaid
flowchart LR
    Applicant --> Web[React web]
    Underwriter --> Web
    Administrator --> Web
    Web --> API[FastAPI modular monolith]
    API --> DB[(PostgreSQL :5433)]
    API --> Uploads[(Local upload volume)]
    API --> Parent[Parent LangGraph]
    Parent --> Evidence[Bounded document fan-out]
    Parent --> Product[One selected product subgraph]
    Product --> Triage[Deterministic triage]
    Triage --> Human[Underwriter interrupt]
    Human --> Queue[Queue and completion]
    API -. optional redacted traces .-> LangSmith[LangSmith APAC]
```

## Ownership boundaries

- PostgreSQL is the business source of truth for cases, versions, reviews,
  queues, completion records, and immutable audit events.
- LangGraph checkpoints make processing resumable. They do not replace audit
  events or determine authorization.
- Backend Python owns product rules, workflow state, persistence, provider
  behavior, and authorization.
- React owns presentation, interaction state, accessibility, and typed API
  consumption. It does not reproduce underwriting rules.
- Gemini and Ollama are provider adapters. The fake provider owns normal tests
  and deterministic smoke checks.

## Trust boundary

Uploaded documents are untrusted data. Extraction receives a separate trusted
system instruction and a serialized document payload. Stored audit and trace
views contain metadata and evidence locators, not credentials or raw files.

## Routing precedence

Deterministic rules outrank model suggestions. The applied order is
unsupported/manual, needs information, specialist, standard, expedited. Only
`expedited`, `standard`, and `specialist` are final routes; `manual` and
`needs_information` are review states, and a manual recommendation resolves to
the most cautious final route once an underwriter decides.

Normal intake cannot produce an unsupported product. A case is pinned to a
version that was validated when it was imported, and the case carries no
independent product code, so the pinned configuration always describes a
supported product. The `unsupported_product` state the triage graph reads as
tier one is set when the pinned version's stored configuration can no longer be
read. That routes the case to manual review with the reason recorded as a
validation, instead of failing the request. Any future intake path that accepts
a product the rulebook does not cover must set the same state.

## Governance boundary

The workflow produces only `expedited`, `standard`, or `specialist` triage
recommendations. It pauses before final routing. Only an authenticated
underwriter can confirm or override that recommendation.
