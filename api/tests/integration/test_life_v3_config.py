"""Life v3 configuration and evaluation fixture checks."""

import json
from pathlib import Path

from underwriteflow.cases.validation import validate_complete_application
from underwriteflow.products.import_configs import CONFIGURATION_FILES
from underwriteflow.products.service import load_configuration


# Load life v3 and validate every synthetic life evaluation payload.
def test_life_v3_validates_evaluation_payloads() -> None:
    configuration = load_configuration(
        Path("/app/product-config/life-individual-term-v3.yaml")
        .read_text()
    )
    assert "life-individual-term-v3.yaml" in CONFIGURATION_FILES
    assert configuration.version == "v3"
    date_field = next(
        field for field in configuration.fields if field.key == "date_of_birth"
    )
    assert date_field.required is True
    assert date_field.type == "date"
    assert date_field.validation == {"not_future": True}

    records = json.loads(Path("/app/evaluation/cases.json").read_text())
    life_records = [
        record
        for record in records
        if record["product_code"] == "life-individual-term"
    ]
    assert life_records
    assert {
        record["configuration_version"] for record in life_records
    } == {configuration.version}
    for record in life_records:
        validate_complete_application(
            record["workflow_input"]["payload"],
            [item["code"] for item in record["workflow_input"]["evidence"]],
            configuration,
        )
