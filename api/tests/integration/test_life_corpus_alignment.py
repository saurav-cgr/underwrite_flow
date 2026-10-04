"""Integration coverage for the shipped life guideline corpus."""

from pathlib import Path

from underwriteflow.knowledge.alignment import check_alignment
from underwriteflow.knowledge.corpus import load_corpus
from underwriteflow.products.service import load_configuration


# Resolve mounted paths in Docker and source paths during local inspection.
def project_root() -> Path:
    return Path("/app") if Path("/app").exists() else Path(__file__).parents[3]


# Load the active life product and shipped corpus from mounted files.
def test_shipped_life_corpus_aligns_with_v3() -> None:
    root = project_root()
    corpus_path = root / "knowledge-config/life-individual-term/g1.yaml"
    product_path = root / "product-config/life-individual-term-v3.yaml"

    result = check_alignment(
        load_corpus(corpus_path.read_text()),
        load_configuration(product_path.read_text()),
    )

    assert result == {"valid": True, "issues": []}


# Verify one changed threshold names its corpus section and mismatch.
def test_changed_life_threshold_fails_alignment() -> None:
    root = project_root()
    corpus_path = root / "knowledge-config/life-individual-term/g1.yaml"
    product_path = root / "product-config/life-individual-term-v3.yaml"
    original = corpus_path.read_text()
    changed = original.replace("value: 10000000", "value: 9999999", 1)

    result = check_alignment(
        load_corpus(changed),
        load_configuration(product_path.read_text()),
    )

    assert result["valid"] is False
    assert result["issues"][0]["section_id"] == (
        "life-cover-high-sum-assured"
    )
