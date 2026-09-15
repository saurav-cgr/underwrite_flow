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


# Read the requested field keys for each fictional product configuration.
def product_fields() -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for path in sorted(PRODUCT_CONFIG_DIR.glob("*.yaml")):
        configuration = yaml.safe_load(path.read_text())
        fields[configuration["product_code"]] = [
            field["key"] for field in configuration["fields"]
        ]
    return fields


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


# Build the document set that produces the labelled evidence state.
def build_documents(
    record: dict[str, Any], fields: list[str]
) -> list[dict[str, Any]]:
    codes: list[str] = list(record["expected"]["evidence"])
    payload: dict[str, Any] = record["workflow_input"]["payload"]
    primary_code = codes[-1]
    conflict_code = codes[0]
    absent_field = fields[-1] if record["expected"]["missing"] else None
    conflict_field = fields[0] if record["expected"]["conflict"] else None
    documents: list[dict[str, Any]] = []
    for code in codes:
        lines: list[str] = []
        if code == primary_code:
            lines = [
                f"{key}: {render(payload.get(key))}"
                for key in fields
                if key != absent_field
            ]
        elif code == conflict_code and conflict_field is not None:
            lines = [
                f"{conflict_field}: "
                f"{conflicting_value(payload.get(conflict_field))}"
            ]
        if not lines:
            lines = [f"document_reference: {code}"]
        documents.append(
            {
                "document_id": code,
                "filename": f"{code}.pdf",
                "lines": lines,
            }
        )
    return documents


# Rewrite the reference set with per-case document material.
def main() -> None:
    cases_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else EVALUATION_DIR / "cases.json"
    )
    fields = product_fields()
    records: list[dict[str, Any]] = json.loads(cases_path.read_text())
    for record in records:
        record["documents"] = build_documents(
            record, fields[record["product_code"]]
        )
    cases_path.write_text(json.dumps(records, indent=2) + "\n")
    print(f"wrote {len(records)} records with document material")


if __name__ == "__main__":
    main()
