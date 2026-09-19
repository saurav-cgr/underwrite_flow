"""Attach synthetic document material to every evaluation reference case.

The reference set originally carried only labels plus pre-filled conflict and
missing lists, so no pipeline could derive them: the inputs contained the
answers. This generator writes the documents each case needs, so extraction and
reconciliation have real input and the metrics can be computed from what the
pipeline produces.

The material is derived from the existing reference labels, which makes each
case an explicit scenario rather than a copy of its own answer. `R7c` proves the
metrics respond when pipeline output changes.

Run from the repository root:

    docker compose run --rm -v "$PWD/evaluation:/work" \
      api python evaluation/generate_evidence.py /work/cases.json
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml

EVALUATION_DIR = Path(__file__).resolve().parent
PRODUCT_CONFIG_DIR = EVALUATION_DIR.parent / "product-config"


# Load every published configuration, keyed by product code and version.
def all_configurations() -> dict[tuple[str, str], dict[str, Any]]:
    configurations: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(PRODUCT_CONFIG_DIR.glob("*.yaml")):
        configuration = yaml.safe_load(path.read_text())
        key = (configuration["product_code"], configuration["version"])
        configurations[key] = configuration
    return configurations


# Match the backend's default: an entry with no applies_to is new-business
# only, so a case's declared journey must match it explicitly to count.
def applies_to_journey(entry: dict[str, Any], journey: str) -> bool:
    return journey in entry.get("applies_to", ["new_business"])


# Read the required field keys one journey sees on one configuration.
#
# Optional fields are excluded: the applicant either answered them or left them
# unanswered, and the pipeline only expects evidence for what was answered.
def required_fields(
    configuration: dict[str, Any], journey: str
) -> list[str]:
    return [
        field["key"]
        for field in configuration["fields"]
        if field.get("required", True) and applies_to_journey(field, journey)
    ]


# Render one value the way a synthetic document line would carry it.
def render(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# Return a value that disagrees with the application answer.
def conflicting_value(value: Any) -> str:
    if isinstance(value, bool):
        return "false" if value else "true"
    if isinstance(value, (int, float)):
        return str(value + 7)
    return "other"


# Read the reconciliation checks one journey sees on one configuration.
def journey_checks(
    configuration: dict[str, Any], journey: str
) -> list[dict[str, Any]]:
    return [
        check
        for check in configuration.get("reconciliations", [])
        if applies_to_journey(check, journey)
    ]


# Derive one agreeing value for every evidence field a check reads.
def agreed_evidence(
    checks: list[dict[str, Any]], payload: dict[str, Any]
) -> dict[str, list[tuple[str, Any]]]:
    supplied: dict[str, list[tuple[str, Any]]] = {}
    derived: dict[str, Any] = {}
    for check in checks:
        claimed = check.get("inputs", {}).get("application")
        for source, field_name in check.get("inputs", {}).items():
            if source == "application":
                continue
            if field_name not in derived:
                if claimed is not None and claimed in payload:
                    derived[field_name] = payload[claimed]
                elif field_name.endswith("_date"):
                    # An unanswered renewal date leaves the check missing.
                    derived[field_name] = "2026-01-01"
                else:
                    derived[field_name] = "SYNTHETIC-AGREED"
            supplied.setdefault(source, []).append(
                (field_name, derived[field_name])
            )
    return supplied


# Build the document set that produces the labelled evidence state.
def build_documents(
    record: dict[str, Any],
    fields: list[str],
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    codes: list[str] = list(record["expected"]["evidence"])
    payload: dict[str, Any] = record["workflow_input"]["payload"]
    supplied = agreed_evidence(checks, payload)
    for source in supplied:
        if source not in codes:
            codes.append(source)
    primary_code = codes[-1]
    conflict_code = codes[0]
    absent_field = fields[-1] if record["expected"]["missing"] else None
    conflict_field = fields[0] if record["expected"]["conflict"] else None
    documents: list[dict[str, Any]] = []
    for code in codes:
        lines: list[str] = []
        if code == primary_code:
            lines = [
                f"{key}: {render(payload[key])}"
                for key in fields
                if key in payload and key != absent_field
            ]
        elif code == conflict_code and conflict_field is not None:
            lines = [
                f"{conflict_field}: "
                f"{conflicting_value(payload.get(conflict_field))}"
            ]
        lines.extend(
            f"{field_name}: {render(value)}"
            for field_name, value in supplied.get(code, [])
        )
        if not lines:
            lines = [f"document_reference: {code}"]
        documents.append(
            {
                "document_id": code,
                "filename": f"{code}.pdf",
                "lines": lines,
            }
        )
    # The reference evidence label is exactly the document set the case
    # carries, so regenerating after a configuration change stays stable.
    record["expected"]["evidence"] = sorted(
        document["document_id"] for document in documents
    )
    return documents


# Rewrite the reference set with per-case document material.
def main() -> None:
    cases_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else EVALUATION_DIR / "cases.json"
    )
    configurations = all_configurations()
    records: list[dict[str, Any]] = json.loads(cases_path.read_text())
    for record in records:
        key = (record["product_code"], record["configuration_version"])
        configuration = configurations[key]
        journey = record["journey_type"]
        record["documents"] = build_documents(
            record,
            required_fields(configuration, journey),
            journey_checks(configuration, journey),
        )
    cases_path.write_text(json.dumps(records, indent=2) + "\n")
    print(f"wrote {len(records)} records with document material")


if __name__ == "__main__":
    main()
