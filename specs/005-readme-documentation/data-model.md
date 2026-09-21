# Content Model: Improve Project README

## README sections

| Section | Reader need | Source of truth |
| --- | --- | --- |
| Product summary | Purpose and non-decision boundary | README, PRD |
| Feature map | Implemented capabilities | README, feature specs |
| Quickstart | Start local fake-provider demo | README, `.env.example` |
| Demo accounts | Fictional role credentials | `web/src/entry.tsx` |
| Role checks | Manual acceptance paths | README, `docs/DEMO.md` |
| Architecture | Components and flow | README, `docs/ARCHITECTURE.md` |
| Verification | Automated checks and results | README, Makefile |
| Environments | Mode and evaluation rule | README, evaluation quickstart |
| Troubleshooting | Common recovery steps | README, Compose behavior |
| References | Deeper documents | README links |

## Relationships

- Product summary links to feature map and architecture overview.
- Quickstart provides prerequisites for role checks and automated verification.
- Role checks link to detailed demo guide.
- Architecture overview links to detailed architecture documentation.
- Environment guidance links to detailed evaluation-loader instructions.
- Every section repeats or links to human authority and synthetic-data limits
  where a reader could otherwise misread system behavior.

## Content validation rules

- Use only facts verified in repository documentation, configuration, or code.
- Use only fictional accounts and data; never add real examples.
- State that recommendations are not final insurance decisions.
- State that cases remain pinned to selected product version and journey.
- State that production mode is not a production-readiness claim.
- Link long explanations instead of reproducing them.
- Keep commands executable from repository root and match existing Make targets.
