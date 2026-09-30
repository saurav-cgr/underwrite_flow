"""Alignment checks for every newest fictional product corpus."""

from pathlib import Path

import pytest

from underwriteflow.knowledge.alignment import check_alignment
from underwriteflow.knowledge.corpus import load_corpus
from underwriteflow.products.service import load_configuration

ROOT = Path("/app") if Path("/app").exists() else Path(__file__).parents[3]

PRODUCTS = (
    (
        "motor-private-car",
        "v5",
        "motor-private-car/g1.yaml",
    ),
    (
        "health-individual-family-floater",
        "v3",
        "health-individual-family-floater/g1.yaml",
    ),
)


# Verify every newest motor and health corpus matches its product rules.
@pytest.mark.parametrize("product_code,version,corpus_name", PRODUCTS)
def test_newest_product_corpus_aligns(
    product_code: str, version: str, corpus_name: str
) -> None:
    corpus = load_corpus(
        (ROOT / "knowledge-config" / corpus_name).read_text()
    )
    configuration = load_configuration(
        (ROOT / "product-config" / f"{product_code}-{version}.yaml")
        .read_text()
    )

    assert corpus.product_code == product_code
    assert corpus.aligned_product_version == version
    assert check_alignment(corpus, configuration) == {
        "valid": True,
        "issues": [],
    }


# Verify a changed motor or health threshold names its corpus section.
@pytest.mark.parametrize(
    ("product_code", "version", "corpus_name", "old", "section_id"),
    [
        (
            "motor-private-car",
            "v5",
            "motor-private-car/g1.yaml",
            "12",
            "motor-vehicle-age-specialist",
        ),
        (
            "health-individual-family-floater",
            "v3",
            "health-individual-family-floater/g1.yaml",
            "4",
            "health-large-floater-standard",
        ),
    ],
)
def test_changed_product_threshold_fails_alignment(
    product_code: str,
    version: str,
    corpus_name: str,
    old: str,
    section_id: str,
) -> None:
    source = (ROOT / "knowledge-config" / corpus_name).read_text()
    changed = source.replace(f"value: {old}", "value: 999", 1)
    corpus = load_corpus(changed)
    configuration = load_configuration(
        (ROOT / "product-config" / f"{product_code}-{version}.yaml")
        .read_text()
    )

    result = check_alignment(corpus, configuration)

    assert result["valid"] is False
    assert result["issues"][0]["section_id"] == section_id
