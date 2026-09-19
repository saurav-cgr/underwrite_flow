"""Load the versioned synthetic evaluation reference set and product
configuration manifest each record's exact version and journey selects."""

import json
from pathlib import Path
from typing import Any

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.service import load_configuration


# Locate the dataset in Compose and in the source checkout.
def default_dataset_path() -> Path:
    mounted_path = Path("/app/evaluation/cases.json")
    if mounted_path.exists():
        return mounted_path
    return Path(__file__).resolve().parents[4] / "evaluation" / "cases.json"


# Locate mounted product configurations or their source-checkout fallback.
def product_config_root() -> Path:
    mounted_path = Path("/app/product-config")
    if mounted_path.exists():
        return mounted_path
    return Path(__file__).resolve().parents[4] / "product-config"


# Read and validate the non-empty synthetic case collection.
def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    dataset_path = path or default_dataset_path()
    records = json.loads(dataset_path.read_text())
    if not isinstance(records, list) or not records:
        raise ValueError("evaluation dataset must be a non-empty list")
    return records


# Load every published configuration, keyed by product code and version, so
# a record's exact `configuration_version` resolves to one specific version
# rather than the earliest one on disk.
def load_configuration_manifest() -> (
    dict[tuple[str, str], ProductConfiguration]
):
    configurations: dict[tuple[str, str], ProductConfiguration] = {}
    for path in sorted(product_config_root().glob("*.yaml")):
        configuration = load_configuration(path.read_text())
        key = (configuration.product_code, configuration.version)
        configurations[key] = configuration
    return configurations
