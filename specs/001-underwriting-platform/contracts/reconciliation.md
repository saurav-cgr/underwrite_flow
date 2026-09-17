# Reconciliation Contract

## Boundary

Reconciliation is a pure backend operation. It accepts serializable normalized
evidence plus pinned configuration and returns typed results. It performs no
database access, provider call, file access, logging, audit write, or routing.

## Input

```json
{
  "case_id": "generated-uuid",
  "product_version": "1.0.0",
  "rulebook_version": "1.0.0",
  "application": {
    "claimed_ncb_percent": 20,
    "new_policy_start": "2026-09-18"
  },
  "evidence": [
    {
      "field_name": "ncb_percent",
      "value": 20,
      "document_id": "generated-uuid",
      "document_code": "previous_policy",
      "source_locator": "page:1",
      "confidence": 0.99
    }
  ],
  "checks": [
    {
      "code": "motor_ncb_match",
      "kind": "ncb_match",
      "inputs": {
        "application": "claimed_ncb_percent",
        "previous_policy": "ncb_percent",
        "claims_history": "claim_count"
      }
    }
  ]
}
```

## Output

```json
{
  "results": [
    {
      "check_code": "motor_ncb_match",
      "kind": "ncb_match",
      "status": "CLEARED",
      "comparisons": [
        {
          "field_key": "ncb_percent",
          "left": 20,
          "right": 20,
          "matched": true,
          "evidence": [
            {
              "document_id": "generated-uuid",
              "source_locator": "page:1"
            }
          ],
          "explanation_code": "ncb_matches"
        }
      ],
      "discrepancies": [],
      "evidence": [
        {
          "document_id": "generated-uuid",
          "source_locator": "page:1"
        }
      ],
      "missing_inputs": [],
      "rule_version": "1.0.0"
    }
  ],
  "overall_status": "CLEARED"
}
```

## Status Rules

- `MISSING_EVIDENCE`: at least one required input is absent or unusable.
  `missing_inputs` lists the source keys with no usable value, so a caller can
  tell an unanswered optional claim (`application`) from a claim the configured
  documents cannot verify.
- `FLAGGED_DISCREPANCY`: all required inputs exist and deterministic comparison
  finds a mismatch or a configured threshold breach.
- `CLEARED`: all required inputs exist and every comparison passes.

Overall precedence is `MISSING_EVIDENCE`, then `FLAGGED_DISCREPANCY`, then
`CLEARED`. This is a case evidence state, not a final triage route.

## Check Semantics

### `ncb_match`

- Compare normalized claimed NCB percentage with previous-policy NCB.
- Apply configured tier progression and claims-history adjustment.
- Missing prior policy, NCB, or required claims evidence returns
  `MISSING_EVIDENCE`.
- Gemini confidence never changes the deterministic numeric result.

### `asset_match`

- Compare configured engine, chassis, and registration identifiers.
- Normalize Unicode, trim whitespace, remove configured separators, and apply
  case-folding before equality comparison.
- Preserve original values only in local evidence; result carries normalized
  values and source references.
- Any missing required identifier returns `MISSING_EVIDENCE` for that check.

### `policy_lapse`

- Parse ISO dates already validated by the extraction schema.
- Compute whole calendar days from previous expiry to new policy start.
- Apply the configured inclusive/exclusive boundary and maximum allowed gap.
- Invalid or missing dates return `MISSING_EVIDENCE`, never a guessed lapse.

## Determinism

- Sort checks by `check_code`.
- Sort comparisons by `field_key`.
- Sort evidence by `(document_id, source_locator)`.
- Use stable explanation and discrepancy codes, not generated prose.
- Identical normalized inputs and versions must produce identical serialized
  output.

## Failure Contract

Invalid check configuration fails product validation before activation.
Unexpected runtime input becomes a typed check error persisted as a validation
and specialist review signal; successful sibling checks remain available.

No reconciliation function raises an exception containing raw evidence values.
