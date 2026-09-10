# UnderwriteFlow PRD — Finalized MVP Decisions

This document forms part of [the UnderwriteFlow PRD](./PRD.md).

## 20. Finalized MVP decisions

### 20.1 Products and jurisdiction

UnderwriteFlow will demonstrate three insurance workflows for India:

- Comprehensive insurance for privately owned cars.
- Individual term life insurance.
- Individual and family-floater hospitalization insurance.

Commercial and fleet vehicles, two-wheelers, investment-linked or savings life products, group insurance, travel insurance, critical-illness-only products, and government schemes are outside the MVP. The implementation will use fictional demonstration rules and must not present them as real Indian underwriting or regulatory requirements.

### 20.2 Application information and documents

All products will collect common applicant, contact, coverage, policy-history, claim-history, declaration, consent, and audit information. Each workflow will add only the fields relevant to that product:

- **Motor:** vehicle, ownership, usage, modification, finance, previous-policy, claim, and inspection information.
- **Life:** identity, nominee, requested coverage, occupation, income, existing coverage, health, and lifestyle information.
- **Health:** covered-member, relationship, requested coverage, existing policy, continuity, claim, medical-history, hospitalization, treatment, and lifestyle information.

The system will distinguish minimum intake information from conditional evidence. Supporting evidence may include synthetic identity and address records, vehicle registration and prior-policy records, income evidence, medical reports, discharge summaries, prescriptions, examination results, and vehicle photographs. Not every document is mandatory for every case.

Every extracted value will retain its source, page or location when available, extraction method, confidence, conflict status, and human-verification state. Unreadable, missing, conflicting, irrelevant, or suspicious documents will be surfaced without guessing or making fraud accusations.

Applicant documents belong to a single case and are uploaded through the application Documents step. Insurance product definitions and product-reference documents are shared configuration and are managed separately through `Administration > Product Configuration`.

The repository will provide three initial structured configuration files:

- `product-config/motor-private-car.yaml`
- `product-config/life-individual-term.yaml`
- `product-config/health-individual-family-floater.yaml`

Setup will validate and import these fictional configurations into PostgreSQL. The original reference documents will use the synthetic upload volume, while PostgreSQL stores their metadata and content hashes.

### 20.3 Triage-routing rules

The workflow will use a hybrid routing system:

- Deterministic, versioned rules control product scope, required information, mandatory referrals, and routing constraints.
- AI extracts and summarizes evidence and may suggest evidence-backed observations.
- The most cautious applicable route takes precedence.
- A human underwriter confirms or overrides every final route.

Route precedence is:

1. Unsupported or manual intake.
2. Additional information required.
3. Specialist review.
4. Standard review.
5. Expedited review.

Actual medical, financial, age, vehicle-value, coverage, and claim thresholds are not invented by the AI. The MVP will use a clearly labeled fictional, versioned rulebook.

### 20.4 Roles and queues

The MVP will implement three roles:

- **Applicant:** creates applications, uploads documents, and responds to information requests.
- **Underwriter:** reviews all three products, inspects evidence, requests information, and confirms or overrides recommendations.
- **Administrator:** manages demonstration configuration and users, monitors failures, and inspects audit history and metrics.

The MVP will use four queues:

- New.
- Needs Information.
- Underwriter Review.
- Completed.

Product, route, priority, and specialist needs will be represented with filters and labels. Medical, financial, motor-inspection, and senior-review indicators will not require separate user roles in the MVP.

### 20.5 Intake and downstream systems

The built-in applicant web form will be the primary intake channel. A documented API will provide a secondary synthetic-data intake channel and demonstrate how a future insurer, broker, or mobile application could integrate.

Human-confirmed cases will remain in UnderwriteFlow's Completed queue. An optional mock webhook may emit a minimal, non-sensitive triage-completion event after human confirmation. No real insurer, hospital, government, or policy-administration integration is included.

### 20.6 Evaluation data and review process

Evaluation will use 90 fully synthetic applications: 30 each for motor, life, and health, balanced across expedited, standard, and specialist routes. Documents will use fictional identities and organizations and will be visibly marked `SYNTHETIC - FOR DEMONSTRATION ONLY`.

The dataset will contain 60 development cases and 30 holdout cases. Every case will have a reference answer derived from the fictional, versioned rulebook. Results must describe these as reference labels, not genuine expert underwriting decisions.

Evaluation will measure route agreement, specialist recall, evidence accuracy, conflict detection, missing-information detection, unsupported material claims, and workflow reliability. It will also cover unclear documents, extraction failures, retries, resumability, duplicate prevention, and prompt-injection content embedded in documents.

### 20.7 Runtime, performance, retention, and recovery

UnderwriteFlow will be a local-first Docker Compose application modeled on the Decision Assistant project. Its initial services will be:

- PostgreSQL/pgvector 16 database.
- Python 3.12 FastAPI and LangGraph API.
- Node 24 web application.
- Optional Ollama service enabled through a Compose profile.

The configuration will use health checks, dependency ordering, environment variables, separate API and web Dockerfiles, persistent volumes, an isolated-network override, and an AI-independent smoke-test override. PostgreSQL will persist application records, audit events, and LangGraph checkpoints. Synthetic uploads will use a Docker volume. A separate worker, Redis, object storage, Kubernetes, and cloud infrastructure are deferred until justified.

MVP targets are:

| Area | Target |
| --- | --- |
| Normal page or API response | 95% within 2 seconds |
| Review-ready processing | 95% within 60 seconds |
| Daily applications | 100 |
| Simultaneous processing | 10 applications |
| Simultaneous users | 20 |
| Documents per application | 10 |
| Maximum document size | 10 MB |
| Maximum document pages | 50 per application |
| Completed-case retention | 90 days |
| Temporary-file retention | 24 hours |

The MVP has no contractual availability target. It must recover safely from container restarts without losing committed cases, documents, checkpoints, or audit events. Demonstration data will be synthetic; deployment and external-provider processing locations must be documented rather than making an unverified data-residency claim.

### 20.8 AI and document-processing providers

Gemini will be the default hosted generation provider, matching the Decision Assistant environment-driven configuration. Ollama with a configurable local model will be available as an optional Docker Compose profile. Provider and model names, timeouts, retry counts, and credentials will be runtime configuration rather than application constants.

Digital PDFs will use local text extraction. Scanned PDFs, JPEGs, and PNGs will use local OCR before model analysis. The MVP will not add a commercial document-processing provider. Low-confidence extraction will be presented for human review instead of being guessed.

Model responses must conform to validated JSON schemas and cite source evidence for material observations. Deterministic rules remain authoritative when a model suggestion conflicts with a mandatory rule. Models will not receive permission to change routing rules, complete cases, send webhooks, or modify records directly.

Embeddings and retrieval are deferred because the fictional rulebook can be represented as versioned structured configuration. PostgreSQL/pgvector remains available for a later evidence-retrieval capability if a demonstrated need emerges.

## 21. Release approach

1. Validate the workflow with synthetic cases.
2. Run offline evaluation using the synthetic development and holdout cases.
3. Conduct a shadow-mode trial in which recommendations do not affect live queues.
4. Review quality, security, privacy, fairness, and override findings.
5. Begin a limited pilot with mandatory human confirmation and active monitoring.
6. Expand scope only after the pilot's acceptance thresholds and governance reviews are satisfied.
