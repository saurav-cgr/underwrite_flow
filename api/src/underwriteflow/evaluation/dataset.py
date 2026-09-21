"""Load the versioned synthetic evaluation reference set and product
configuration manifest each record's exact version and journey selects."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from underwriteflow.products.schemas import ProductConfiguration
from underwriteflow.products.service import load_configuration

# A source case ID may only be a short, safe, lowercase identifier: never
# a secret-shaped, punctuation-laden, or over-long string reaching a key,
# a query, or later, sanitized JSON output.
SAFE_CASE_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

SYNTHETIC_LABEL = "SYNTHETIC - FOR DEMONSTRATION ONLY"
EXPECTED_CASE_COUNT = 90
SUPPORTED_SPLITS = frozenset({"development", "holdout"})
EXPECTED_JOURNEY_COUNTS = {
    ("motor-private-car", "new_business"): 15,
    ("motor-private-car", "renewal"): 15,
    ("health-individual-family-floater", "new_business"): 15,
    ("health-individual-family-floater", "renewal"): 15,
    ("life-individual-term", "new_business"): 30,
}
EXPECTED_ROUTE_COUNTS = {"expedited": 30, "standard": 30, "specialist": 30}


class DatasetPreflightError(Exception):
    """One corpus-level rejection carrying only safe identifying fields."""

    # Record the sanitized rejection a caller reports instead of raising raw.
    def __init__(self, case_id: str, code: str) -> None:
        super().__init__(f"{case_id}:preflight:{code}")
        self.case_id = case_id
        self.stage = "preflight"
        self.code = code
        self.detail = {
            "case_id": case_id,
            "stage": "preflight",
            "code": code,
        }


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


# Compute the immutable SHA-256 identity of the exact dataset bytes.
def dataset_sha256(path: Path | None = None) -> str:
    return hashlib.sha256(
        (path or default_dataset_path()).read_bytes()
    ).hexdigest()


# Reject the whole corpus before any case runs, so every consumer applies
# the same distribution, label, split, and version rules.
def preflight_dataset(
    records: list[dict[str, Any]],
    configurations: dict[tuple[str, str], Any],
) -> None:
    case_ids = [record["case_id"] for record in records]
    if (
        len(records) != EXPECTED_CASE_COUNT
        or len(set(case_ids)) != len(case_ids)
    ):
        raise DatasetPreflightError("dataset", "case_count")
    for record in records:
        case_id = record["case_id"]
        if not isinstance(case_id, str) or not SAFE_CASE_ID.match(case_id):
            raise DatasetPreflightError(case_id, "unsafe_case_id")
    for record in records:
        if record.get("fixture_label") != SYNTHETIC_LABEL:
            raise DatasetPreflightError(record["case_id"], "fixture_label")
        if record.get("split") not in SUPPORTED_SPLITS:
            raise DatasetPreflightError(record["case_id"], "unsupported_split")
    journeys = Counter(
        (record["product_code"], record["journey_type"]) for record in records
    )
    if journeys != EXPECTED_JOURNEY_COUNTS:
        raise DatasetPreflightError("dataset", "journey_distribution")
    routes = Counter(record["expected"]["route"] for record in records)
    if routes != EXPECTED_ROUTE_COUNTS:
        raise DatasetPreflightError("dataset", "route_balance")
    for record in records:
        key = (record["product_code"], record["configuration_version"])
        configuration = configurations.get(key)
        if configuration is None:
            raise DatasetPreflightError(record["case_id"], "unknown_version")
        if record["journey_type"] not in configuration.supported_journeys:
            raise DatasetPreflightError(
                record["case_id"], "unsupported_journey"
            )
