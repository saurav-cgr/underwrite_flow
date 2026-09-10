# UnderwriteFlow Product Requirements Document

**Product title:** UnderwriteFlow: Human-Governed Insurance Triage with LangGraph

**Status:** Draft v0.1

**Date:** 10 September 2026

**Primary audience:** Product, engineering, underwriting, compliance, and operations

## 1. Product summary

UnderwriteFlow is an AI-assisted workflow for triaging insurance applications while keeping licensed or authorized underwriters in control. It uses a LangGraph workflow to ingest an application, validate and enrich its data, identify risk signals, recommend a triage route, and assemble an evidence-backed case summary for human review.

The system does not make binding coverage decisions, issue policies, set final prices, or deny applicants. Its role is to organize information, surface uncertainty, and help underwriters reach decisions more consistently and efficiently.

## 2. Problem

Insurance applications often arrive with incomplete, inconsistent, or unstructured information. Underwriters spend significant time checking documents, reconciling fields, identifying missing evidence, and deciding which cases need specialist attention before they can assess the underlying risk.

Current approaches create four recurring problems:

- Routine submissions consume expert time that could be spent on complex cases.
- Important inconsistencies or missing evidence can be overlooked during manual review.
- Triage decisions vary across reviewers and are difficult to audit.
- AI automation can introduce unacceptable risk if recommendations are opaque or treated as final decisions.

UnderwriteFlow addresses the operational problem without removing human accountability.

## 3. Product vision

Create a transparent, auditable triage layer that helps underwriters understand each submission quickly, focus on the cases that need judgment, and retain full authority over every consequential decision.

## 4. Goals

The MVP should:

1. Convert an insurance application and its supporting documents into a normalized case record.
2. Detect missing, conflicting, or low-confidence information.
3. Produce an evidence-linked summary of the application and relevant risk signals.
4. Recommend one of three triage routes: standard review, expedited review, or specialist review.
5. Require a human underwriter to confirm or override the recommendation.
6. Record the workflow state, model outputs, evidence, human actions, and final triage outcome in an audit trail.
7. Make uncertainty and system limitations visible at the point of review.

## 5. Non-goals

The MVP will not:

- Approve, decline, bind, renew, cancel, or price a policy autonomously.
- Replace underwriting guidelines, actuarial models, or an insurer's system of record.
- Contact an applicant, broker, or third party without explicit human action.
- Infer or use protected characteristics, or proxies for them, to recommend a route.
- Train models on customer data by default.
- Support every insurance product or jurisdiction in the first release.
- Generate a final underwriting decision.

## 6. Target users

### Primary user: Underwriter

Needs a concise view of the submission, clear evidence for each flagged issue, visible uncertainty, and a fast way to confirm or override the proposed route.

### Secondary user: Underwriting operations analyst

Needs to monitor queues, identify incomplete submissions, resolve processing failures, and understand where manual effort is being spent.

### Oversight user: Compliance or audit reviewer

Needs a durable record of inputs, system reasoning, model and rule versions, human actions, and outcome history.

### Administrative user: Administrator

Needs to view and version supported products, application fields, document requirements, routing rules, reference documents, and reviewer queues without editing workflow code.

## 7. Core user journey

1. An application is submitted through an API or a demonstration upload interface.
2. UnderwriteFlow creates a case and records the original input.
3. The workflow extracts and normalizes application data.
4. Deterministic checks validate required fields, formats, and cross-document consistency.
5. AI-assisted analysis summarizes the case, identifies risk signals, and cites the evidence used.
6. The workflow measures confidence and identifies missing or conflicting information.
7. A routing node recommends one of the supported triage routes.
8. The case pauses at a human-review checkpoint.
9. An underwriter reviews the summary and evidence, then confirms or overrides the route with a reason.
10. The system records the action and sends the case to the selected downstream queue.

## 8. Triage routes

| Route | Intended use | Required human action |
| --- | --- | --- |
| Expedited review | Complete, internally consistent submissions with no material risk signal detected | Confirm or override the route |
| Standard review | Submissions requiring normal underwriting judgment | Confirm or override the route |
| Specialist review | High-complexity, conflicting, low-confidence, or policy-defined cases | Confirm or override the route and select a specialist queue |

These routes prioritize work; they do not represent approval, rejection, or pricing decisions.

## 9. Functional requirements

### FR-1: Case intake

- Accept structured application data and supported document attachments.
- Assign a unique case identifier.
- Preserve the original submission and ingestion timestamp.
- Reject unsupported file types safely and explain the problem to the user.

### FR-2: Data extraction and normalization

- Extract configured fields from supported documents.
- Normalize dates, currencies, addresses, identifiers, and enumerated values.
- Preserve source references for every extracted value.
- Attach a confidence value and extraction method to AI-derived fields.
- Never overwrite the original submitted value.

### FR-3: Validation

- Check required fields and document presence using configurable rules.
- Identify conflicts between application fields and supporting evidence.
- Separate deterministic validation failures from AI-generated observations.
- Allow the workflow to continue to human review when safe, even if enrichment fails.

### FR-4: Risk-signal analysis

- Evaluate configured underwriting signals relevant to the selected product.
- Explain each signal in plain language.
- Link each signal to its source evidence and applicable rule or guideline.
- Label unsupported conclusions and low-confidence observations explicitly.
- Avoid generating facts that are not present in the submitted or approved reference data.

### FR-5: Case summary

- Present key facts, missing information, conflicts, risk signals, and open questions.
- Distinguish submitted facts, extracted facts, deterministic rule results, and AI-generated interpretations.
- Provide direct access to the supporting source location when available.
- Show the workflow and model versions used to produce the summary.

### FR-6: Route recommendation

- Recommend exactly one supported triage route.
- Provide the factors that materially influenced the recommendation.
- Escalate low-confidence, conflicting, out-of-scope, or policy-defined cases to specialist review.
- Use deterministic policy constraints ahead of model preferences.
- Never map a triage route directly to a coverage decision.

### FR-7: Human review

- Pause the workflow before final routing.
- Allow an authorized underwriter to confirm or override the recommendation.
- Require a reason when the recommendation is overridden.
- Display all known uncertainties and processing failures before confirmation.
- Prevent the system from presenting an AI recommendation as a completed underwriting decision.

### FR-8: Audit trail

- Record inputs, extracted values, rule results, prompts or prompt versions, model identifiers, model outputs, workflow transitions, confidence values, evidence references, and timestamps.
- Record the reviewing user, selected route, override reason, and final triage timestamp.
- Make prior states inspectable without allowing silent alteration.
- Apply configurable retention and access policies.

### FR-9: Queue handoff

- Send confirmed cases to the appropriate review queue.
- Include the case summary, evidence links, and audit identifier.
- Make handoff failures visible and retryable without duplicating the case.

### FR-10: Product configuration

- Provide an Administrator-only Product Configuration area for motor, life, and health.
- Keep product configuration separate from applicant documents and case evidence.
- Represent each product through a structured, versioned configuration containing its product name, code, insurance family, India-focused demonstration scope, description, status, application fields, document requirements, routing rules, and specialist labels.
- Support required, optional, conditional, and not-applicable document requirements.
- Support field types, validation rules, conditional visibility, and applicant help text.
- Allow an administrator to view the active configuration, upload a new YAML configuration version, validate it, preview its effect on forms and routing, activate it, and inspect version history.
- Reject invalid or incomplete configurations without changing the active version.
- Seed the MVP with fictional configurations for private-car motor, individual term life, and individual or family-floater hospitalization insurance.
- Associate every case and workflow run with the exact product and rulebook versions used when processing began.
- Keep an in-progress case on its original configuration version when a newer version is activated.
- Store uploaded product-reference documents separately from structured rules and preserve their filename, content hash, version, uploader, and timestamp.
- Never activate an AI-inferred rule directly from an uploaded reference document; an administrator must explicitly approve the structured configuration.
- Record configuration validation, activation, replacement, and retirement as audit events.

## 10. LangGraph workflow requirements

The workflow should use explicit, inspectable states and resumable checkpoints. The initial graph is expected to contain these logical nodes:

1. `ingest_application`
2. `extract_and_normalize`
3. `validate_submission`
4. `analyze_risk_signals`
5. `assemble_case_summary`
6. `recommend_triage_route`
7. `human_review`
8. `dispatch_to_queue`
9. `record_completion`

Conditional edges should route processing failures, missing evidence, unsupported products, and low-confidence results toward human or specialist review. The graph must be resumable after the human-review interrupt and safe to retry without repeating irreversible actions.

## 11. Human-governance requirements

- Human confirmation is mandatory before a case leaves the triage workflow.
- The user interface must make AI-generated content visually distinguishable from submitted facts and deterministic rule results.
- A reviewer must be able to inspect the evidence behind a recommendation.
- A reviewer must be able to override the recommendation without fighting the system.
- The system must record overrides as feedback, but must not automatically use them for model training.
- Access to cases and actions must follow role-based authorization and least-privilege principles.
- Sensitive data must not be exposed in logs, prompts, analytics, or error messages beyond what is required for the task.
- Product and jurisdiction-specific compliance review is required before production use.

## 12. Non-functional requirements

### Reliability

- Workflow state must survive process restarts.
- Retried nodes must be idempotent where they can create external effects.
- A model or enrichment-provider failure must produce a visible review state rather than an untracked case loss.

### Performance

- For a representative MVP submission, the system should produce a review-ready case within 60 seconds at the 95th percentile, excluding the time spent waiting for human action.
- The case workspace should load within 2 seconds at the 95th percentile under the agreed pilot load.

### Security and privacy

- Encrypt data in transit and at rest.
- Enforce role-based access controls and authenticated user actions.
- Redact or tokenize sensitive data where full values are unnecessary.
- Define retention, deletion, and data-residency behavior before a production pilot.
- Complete threat modeling for document ingestion, prompt injection, data exfiltration, and unauthorized workflow actions.

### Explainability and auditability

- Material recommendations must be traceable to evidence and policy inputs.
- The system must retain the versions of rules, workflow, prompts, and models used for each case.
- Logs must support reconstruction of the case's state transitions without relying on hidden model reasoning.

### Accessibility

- The review interface should meet WCAG 2.2 AA for the supported flows.
- Status and risk information must not rely on color alone.

## 13. Data model overview

The MVP requires the following core entities:

- **Case:** identity, product, status, timestamps, current route, and workflow version.
- **Submission:** original structured data and document references.
- **Extracted field:** normalized value, original value, source, method, and confidence.
- **Validation result:** rule identifier, result, severity, and evidence.
- **Risk signal:** description, evidence, confidence, and applicable guideline.
- **Route recommendation:** recommended route, material factors, and confidence.
- **Human review:** reviewer, decision, override reason, timestamp, and notes.
- **Audit event:** actor, event type, prior state, new state, and immutable metadata.
- **Product configuration:** product identity, scope, application-field definitions, document requirements, status, and active version.
- **Rulebook version:** deterministic rules, routing outcomes, specialist labels, validation result, activation status, and version metadata.
- **Product reference document:** product version, storage reference, filename, content hash, uploader, and timestamp.

## 14. Success metrics

Pilot success should be assessed against a human-only baseline.

### Efficiency

- Median time from complete submission to confirmed triage route.
- Underwriter handling time per case.
- Percentage of cases requiring manual data reconciliation.

### Quality

- Agreement rate between the recommended route and the underwriter-confirmed route.
- Specialist-review recall for cases labeled as requiring specialist attention in the evaluation set.
- Rate of material evidence-link errors or unsupported claims.
- Rate of cases returned because required information was missed.

### Governance

- Percentage of recommendations with complete evidence and version metadata.
- Percentage of routed cases with recorded human confirmation.
- Override rate and categorized override reasons.
- Number of cases routed without a valid audit trail; target: zero.

The pilot must define target values after a baseline study. Agreement alone must not be treated as proof of correctness or fairness.

## 15. MVP scope

The first release will support:

- Three India-focused demonstration workflows: private-car motor, individual term life, and individual or family-floater hospitalization insurance.
- A limited, documented set of application fields and supporting document types.
- The three triage routes defined in this PRD.
- A web-based underwriter review workspace.
- Administrator views for validating, previewing, activating, and inspecting versioned YAML product configurations.
- Bundled fictional product configurations for motor, life, and health, imported into PostgreSQL during setup.
- Configurable application fields, document requirements, validation rules, routing rules, and specialist labels.
- One model provider behind an internal abstraction.
- Persistent LangGraph checkpoints and a complete audit trail.
- Evaluation against a 90-case fully synthetic dataset with fictional rulebook-derived reference labels.

## 16. Out-of-scope follow-on capabilities

- Additional insurance products, product variants, and jurisdictions.
- Broker-portal integration.
- Automated third-party data acquisition.
- Portfolio-level risk analytics.
- Continuous-learning or automated model retraining.
- Final underwriting, pricing, or policy administration decisions.

## 17. Acceptance criteria

The MVP is ready for a controlled pilot when:

1. A supported submission can complete the graph from intake to human-confirmed queue handoff.
2. Every extracted field and material risk signal shows its source or is clearly marked as unsupported.
3. Missing data, contradictory data, low confidence, and processing failures produce an appropriate human-review path.
4. No case can reach queue handoff without an authenticated human confirmation.
5. A reviewer can override the proposed route and the system records the reason.
6. An auditor can reconstruct the workflow, configuration, evidence, system outputs, and human actions for a case.
7. Retrying a paused or failed workflow does not duplicate the case or external handoff.
8. Evaluation results meet pilot thresholds approved by underwriting, compliance, and product owners.
9. Security, privacy, and compliance reviews are complete for the selected product and jurisdiction.
10. The interface clearly states that the recommendation supports triage and is not a coverage decision.
11. An administrator can validate and activate a new product-configuration version without editing application code.
12. Activating a new product version does not change the product or rulebook version associated with an in-progress case.
13. Uploading a reference document cannot silently create or activate an underwriting rule.

## 18. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Hallucinated or unsupported facts | Evidence links, confidence labels, constrained outputs, validation, and mandatory human review |
| Automation bias | Clear AI labeling, visible uncertainty, easy override, reviewer training, and override monitoring |
| Inconsistent routing | Versioned deterministic rules, evaluation sets, threshold review, and outcome monitoring |
| Sensitive-data exposure | Data minimization, access controls, encryption, redaction, retention controls, and vendor review |
| Prompt injection in uploaded documents | Treat documents as untrusted data, isolate instructions from content, constrain tools, and test adversarial files |
| Workflow duplication or lost state | Persistent checkpoints, idempotent external actions, unique case keys, and retry tests |
| Discriminatory impact | Exclude protected attributes and proxies, test for disparate outcomes, and require governance review |
| Scope mistaken for automated underwriting | Product language, UI controls, technical guardrails, and policy documentation that preserve human authority |

## 19. Dependencies

- A fictional, versioned demonstration rulebook for motor, life, and health.
- A 90-case synthetic evaluation dataset with rulebook-derived reference labels.
- Identity and role-management capability.
- Secure document storage and malware scanning.
- A persistent checkpoint store and audit-event store.
- Approved model and document-processing providers.
- Named underwriting, compliance, security, and product owners.

## 20. Finalized MVP decisions

The detailed, approved decisions for products, documents, routing, roles, queues, evaluation, runtime, providers, and release are maintained in [Finalized MVP Decisions](./PRD_FINALIZED_DECISIONS.md). That file forms part of this PRD and is normative for implementation.
