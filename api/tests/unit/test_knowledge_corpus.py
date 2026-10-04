"""Unit tests for fictional guideline corpus parsing."""

import copy

import pytest
import yaml

from underwriteflow.knowledge.corpus import load_corpus


VALID_CORPUS = """
product_code: life-individual-term
version: g1
aligned_product_version: v3
label: SYNTHETIC - FOR DEMONSTRATION ONLY
topics: [cover-amount, occupation]
sections:
  - id: life-cover-high-sum-assured
    title: High requested cover
    topic: cover-amount
    sum_assured_min: 10000001
    thresholds:
      - rule_code: high_cover_standard
        field: requested_cover
        operator: greater_than
        value: 10000000
    body: Requested cover above 10000000 needs standard review.
  - id: life-occupation-hazardous
    title: Hazardous occupation
    topic: occupation
    body: Hazardous occupation needs specialist review.
"""


# Return mutable valid corpus data for one rejection case.
def corpus_data() -> dict:
    return yaml.safe_load(VALID_CORPUS)


# Serialize one corpus mutation using the same YAML boundary as production.
def corpus_text(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False)


# Verify a valid corpus exposes stable typed section data.
def test_load_corpus_accepts_valid_file() -> None:
    corpus = load_corpus(VALID_CORPUS)

    assert corpus.product_code == "life-individual-term"
    assert [section.id for section in corpus.sections] == [
        "life-cover-high-sum-assured",
        "life-occupation-hazardous",
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("label"), "missing_label"),
        (
            lambda data: data["sections"].append(
                copy.deepcopy(data["sections"][0])
            ),
            "duplicate_section_id",
        ),
        (
            lambda data: data["sections"][0].update(
                {"topic": "unknown-topic"}
            ),
            "unknown_topic",
        ),
        (
            lambda data: data["sections"][0].update(
                {"age_min": 50, "age_max": 40}
            ),
            "invalid_band",
        ),
        (
            lambda data: data["sections"][0].update({"id": "bad_id"}),
            "section_id",
        ),
        (
            lambda data: data["sections"][0].update(
                {"body": "x" * 1201}
            ),
            "body",
        ),
    ],
)
# Verify each corpus validation rule rejects malformed source data.
def test_load_corpus_rejects_invalid_documents(mutation, message) -> None:
    data = corpus_data()
    mutation(data)

    with pytest.raises(ValueError, match=message):
        load_corpus(corpus_text(data))


# Verify repeated parses preserve section identity and ordering.
def test_load_corpus_section_ids_are_stable() -> None:
    first = load_corpus(VALID_CORPUS)
    second = load_corpus(VALID_CORPUS)

    assert [item.id for item in first.sections] == [
        item.id for item in second.sections
    ]
