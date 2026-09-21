# README Content Contract

## Required order

1. Product purpose and non-decision boundary
2. Implemented features
3. Quickstart with fake provider
4. Fictional demo accounts
5. Role-based manual verification
6. Automated verification
7. Architecture overview and invariants
8. Environment and evaluation summary
9. Troubleshooting
10. Known limits and deeper references

## Architecture diagram contract

The diagram MUST show:

- Applicant, Underwriter, and Administrator entering through web interface.
- API/business layer connecting to case, product, review, queue, and audit work.
- Workflow using local documents, PostgreSQL, and one selected product path.
- Deterministic reconciliation before recommendation.
- Human underwriter decision before queue handoff or completion.
- Provider boundary as optional and redacted, not a decision authority.
- Isolated evaluation stack as separate from development data.

## Role-check contract

- Applicant: submit a new-business or renewal case with synthetic evidence.
  Result: recommendation or needs-information state.
- Underwriter: inspect evidence, then confirm or override a route.
  Result: human route recorded before completion.
- Administrator: inspect product version and run synthetic evaluation.
  Result: activation stays explicit and evaluation stays isolated.

## Automated-check contract

| Command | Prerequisite | Expected outcome |
| --- | --- | --- |
| `make test-api` | Docker available | Deterministic API suite passes |
| `make test-web` | Docker available | Web suite passes |
| `make smoke` | Docker available | Synthetic end-to-end path passes |
| `make evaluate-e2e` | Docker available | Isolated run passes; cleans up |

## Safety wording contract

README MUST state all of these facts:

- Only synthetic data belongs in this repository and demo.
- Uploaded material is untrusted evidence.
- Deterministic rules outrank model suggestions.
- System recommends expedited, standard, or specialist review only.
- Authenticated underwriter confirms every final route.
- Project does not approve, decline, bind, price, issue, renew, or cancel.
- Production mode is an environment setting, not a compliance or readiness
  claim.
