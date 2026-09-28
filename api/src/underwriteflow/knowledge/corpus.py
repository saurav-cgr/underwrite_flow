"""Typed parser for fictional guideline corpus files."""

import re
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

CORPUS_LABEL = "SYNTHETIC - FOR DEMONSTRATION ONLY"
SECTION_ID_PATTERN = re.compile(r"^[a-z]+(-[a-z0-9]+)+$")
PRODUCT_TOPICS = {
    "life-individual-term": frozenset(
        {
            "age",
            "cover-amount",
            "health-declaration",
            "identity",
            "income-record",
            "lapse-gap",
            "occupation",
            "previous-policy",
        }
    ),
}


class CorpusValidationError(ValueError):
    """Raised when a corpus file violates its source contract."""

    # Preserve the stable issue code for callers and tests.
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        message = f"{code}: {detail}" if detail else code
        super().__init__(message)


class Threshold(BaseModel):
    """One corpus claim that must match a product rule or parameter."""

    model_config = ConfigDict(extra="forbid")

    rule_code: str = Field(min_length=1, max_length=100)
    field: str = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=50)
    value: Any


class GuidelineSection(BaseModel):
    """One bounded, citable fictional guideline passage."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        min_length=3,
        max_length=200,
        pattern=r"^[a-z]+(-[a-z0-9]+)+$",
    )
    title: str = Field(min_length=1, max_length=300)
    topic: str = Field(min_length=1, max_length=100)
    age_min: int | None = None
    age_max: int | None = None
    sum_assured_min: int | float | None = None
    sum_assured_max: int | float | None = None
    thresholds: list[Threshold] = Field(default_factory=list, max_length=50)
    body: str = Field(min_length=1, max_length=1200)

    # Reject inverted age or sum-assured ranges at the model boundary.
    @model_validator(mode="after")
    def validate_bands(self) -> "GuidelineSection":
        if (
            self.age_min is not None
            and self.age_max is not None
            and self.age_min > self.age_max
        ):
            raise ValueError("invalid_band: age_min above age_max")
        if (
            self.sum_assured_min is not None
            and self.sum_assured_max is not None
            and self.sum_assured_min > self.sum_assured_max
        ):
            raise ValueError(
                "invalid_band: sum_assured_min above sum_assured_max"
            )
        return self


class GuidelineCorpus(BaseModel):
    """One versioned corpus for one fictional product."""

    model_config = ConfigDict(extra="forbid")

    product_code: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    aligned_product_version: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=64)
    topics: list[str] = Field(min_length=1, max_length=50)
    sections: list[GuidelineSection] = Field(min_length=1, max_length=500)
    allowed_topics: ClassVar[dict[str, frozenset[str]]] = PRODUCT_TOPICS

    # Enforce unique sections and the product's closed topic vocabulary.
    @model_validator(mode="after")
    def validate_sections(self) -> "GuidelineCorpus":
        ids = [section.id for section in self.sections]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_section_id")
        declared = set(self.topics)
        allowed = self.allowed_topics.get(self.product_code, frozenset())
        for section in self.sections:
            if section.topic not in declared or section.topic not in allowed:
                raise ValueError(f"unknown_topic: {section.topic}")
        if self.label != CORPUS_LABEL:
            raise ValueError("missing_label")
        return self


# Check raw source fields so stable corpus issue codes survive Pydantic errors.
def _validate_raw_source(raw: Any) -> None:
    if not isinstance(raw, dict):
        raise CorpusValidationError("invalid_corpus")
    if raw.get("label") != CORPUS_LABEL:
        raise CorpusValidationError("missing_label")
    sections = raw.get("sections")
    if not isinstance(sections, list):
        raise CorpusValidationError("invalid_sections")
    ids: set[str] = set()
    allowed = PRODUCT_TOPICS.get(raw.get("product_code"), frozenset())
    for section in sections:
        if not isinstance(section, dict):
            raise CorpusValidationError("invalid_section")
        section_id = section.get("id")
        if not isinstance(section_id, str) or not SECTION_ID_PATTERN.fullmatch(
            section_id
        ):
            raise CorpusValidationError("invalid_section_id")
        if section_id in ids:
            raise CorpusValidationError("duplicate_section_id")
        ids.add(section_id)
        if section.get("topic") not in allowed:
            raise CorpusValidationError("unknown_topic")
        body = section.get("body")
        if not isinstance(body, str) or len(body) > 1200:
            raise CorpusValidationError("body_length")
        for minimum, maximum in (
            (section.get("age_min"), section.get("age_max")),
            (
                section.get("sum_assured_min"),
                section.get("sum_assured_max"),
            ),
        ):
            if (
                minimum is not None
                and maximum is not None
                and minimum > maximum
            ):
                raise CorpusValidationError("invalid_band")


# Parse YAML and return one fully validated typed corpus.
def load_corpus(text: str) -> GuidelineCorpus:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise CorpusValidationError("invalid_yaml") from error
    _validate_raw_source(raw)
    try:
        return GuidelineCorpus.model_validate(raw)
    except ValueError as error:
        raise CorpusValidationError(str(error)) from error
