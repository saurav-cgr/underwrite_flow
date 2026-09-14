"""Load the versioned synthetic evaluation reference set."""

import json
from pathlib import Path
from typing import Any


# Locate the dataset in Compose and in the source checkout.
def default_dataset_path() -> Path:
    mounted_path = Path("/app/evaluation/cases.json")
    if mounted_path.exists():
        return mounted_path
    return Path(__file__).resolve().parents[4] / "evaluation" / "cases.json"


# Read and validate the non-empty synthetic case collection.
def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    dataset_path = path or default_dataset_path()
    records = json.loads(dataset_path.read_text())
    if not isinstance(records, list) or not records:
        raise ValueError("evaluation dataset must be a non-empty list")
    return records
