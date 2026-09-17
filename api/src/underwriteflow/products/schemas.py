"""Typed schemas for fictional product configuration YAML."""

import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from underwriteflow.document_types import SUPPORTED_CONTENT_TYPES

FieldType = Literal["text", "integer", "number", "date", "boolean", "enum"]
Requirement = Literal["required", "optional", "conditional", "not_applicable"]
Route = Literal["manual", "needs_information", "specialist", "standard", "expedited"]
ReconciliationKind = Literal["ncb_match", "asset_match", "policy_lapse"]

SUPPORTED_OPERATORS = frozenset({"equals", "greater_than"})
COMPARABLE_OPERATORS = frozenset({"greater_than"})
FIELD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Source key for values the applicant claimed rather than evidence supplied.
APPLICATION_SOURCE = "application"


# Return the effective operator for a configured condition.
def condition_operator(condition: dict[str, Any]) -> Any:
    return condition.get("operator") or "equals"


# Return the comparison value for a configured condition.
def condition_value(condition: dict[str, Any]) -> Any:
    if condition.get("operator") is not None:
        return condition.get("value")
    # Accept the {field, equals} shorthand used for field visibility.
    return condition.get("equals")


# Validate one configured condition without changing its stored shape.
def validate_condition(
    condition: dict[str, Any], field_keys: set[str], where: str
) -> None:
    operator = condition_operator(condition)
    field = condition.get("field")
    value = condition_value(condition)
    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"{where}: unsupported operator {operator!r}")
    if not isinstance(field, str) or not FIELD_NAME_PATTERN.match(field):
        raise ValueError(f"{where}: malformed field path")
    if field not in field_keys:
        raise ValueError(f"{where}: unknown field {field!r}")
    if value is None or isinstance(value, (dict, list)):
        raise ValueError(f"{where}: condition value must be a scalar")
    if operator in COMPARABLE_OPERATORS and (
        isinstance(value, bool) or not isinstance(value, (int, float))
    ):
        raise ValueError(f"{where}: numeric comparison value required")


class ProductField(BaseModel):
    """One applicant field rendered by the product form."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    type: FieldType
    required: bool = False
    help_text: str = Field(min_length=1, max_length=500)
    validation: dict[str, Any] = Field(default_factory=dict)
    visible_when: dict[str, Any] | None = None
    options: list[str] = Field(default_factory=list)


class ProductDocument(BaseModel):
    """One evidence requirement for a product."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    requirement: Requirement
    accepted_types: list[str] = Field(min_length=1)
    condition: dict[str, Any] | None = None

    # Refuse evidence types the upload path cannot store at all.
    @field_validator("accepted_types")
    @classmethod
    def validate_accepted_types(cls, value: list[str]) -> list[str]:
        unsupported = sorted(
            item
            for item in set(value)
            if item not in SUPPORTED_CONTENT_TYPES
        )
        if unsupported:
            raise ValueError(
                "unsupported accepted_types: " + ", ".join(unsupported)
            )
        return value

    # Require a condition only for conditional evidence requirements.
    @model_validator(mode="after")
    def validate_condition(self) -> "ProductDocument":
        if self.requirement == "conditional" and not self.condition:
            raise ValueError("conditional documents require a condition")
        if self.requirement != "conditional" and self.condition is not None:
            raise ValueError("only conditional documents may define a condition")
        return self


class RoutingRule(BaseModel):
    """One deterministic fictional routing rule."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    condition: dict[str, Any] = Field(min_length=1)
    route: Route
    specialist_label: str | None = None


class ReconciliationCheck(BaseModel):
    """One configured pure reconciliation check.

    Configuration supplies only the check code, the fixed implementation kind,
    and the source-to-field mapping. The comparison itself stays in code, so a
    configuration can never introduce executable behaviour.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100)
    kind: ReconciliationKind
    inputs: dict[str, str] = Field(min_length=1)


class ProductConfiguration(BaseModel):
    """Complete versioned product and rulebook configuration."""

    model_config = ConfigDict(extra="forbid")

    product_code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    family: Literal["motor", "life", "health"]
    scope: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=1000)
    version: str = Field(min_length=1, max_length=100)
    status: Literal["draft", "active", "retired"] = "draft"
    fields: list[ProductField] = Field(min_length=1)
    documents: list[ProductDocument] = Field(min_length=1)
    routing_rules: list[RoutingRule] = Field(min_length=1)
    reconciliations: list[ReconciliationCheck] = Field(default_factory=list)
    specialist_labels: list[str] = Field(min_length=1)

    # Ensure identifiers and specialist references are unambiguous.
    @model_validator(mode="after")
    def validate_references(self) -> "ProductConfiguration":
        field_keys = [field.key for field in self.fields]
        document_codes = [document.code for document in self.documents]
        rule_codes = [rule.code for rule in self.routing_rules]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError("field keys must be unique")
        if len(document_codes) != len(set(document_codes)):
            raise ValueError("document codes must be unique")
        if len(rule_codes) != len(set(rule_codes)):
            raise ValueError("routing rule codes must be unique")
        labels = set(self.specialist_labels)
        for rule in self.routing_rules:
            if rule.route == "specialist" and rule.specialist_label not in labels:
                raise ValueError("specialist rules must use a declared label")
        keys = set(field_keys)
        for field in self.fields:
            if field.visible_when is not None:
                validate_condition(
                    field.visible_when, keys, f"field {field.key}"
                )
        for document in self.documents:
            if document.condition is not None:
                validate_condition(
                    document.condition, keys, f"document {document.code}"
                )
        for rule in self.routing_rules:
            validate_condition(rule.condition, keys, f"rule {rule.code}")
        self.validate_reconciliations(keys, set(document_codes))
        return self

    # Ensure each reconciliation check names real sources and declared fields.
    def validate_reconciliations(
        self, field_keys: set[str], document_codes: set[str]
    ) -> None:
        check_codes = [check.code for check in self.reconciliations]
        if len(check_codes) != len(set(check_codes)):
            raise ValueError("reconciliation codes must be unique")
        # A comparison needs two sides. A check therefore reads the
        # applicant's claim plus a document, or two documents, so every source
        # key must be `application` or a declared document code.
        allowed_sources = document_codes | {APPLICATION_SOURCE}
        for check in self.reconciliations:
            where = f"reconciliation {check.code}"
            if not FIELD_NAME_PATTERN.match(check.code):
                raise ValueError(f"{where}: malformed code")
            unknown = sorted(set(check.inputs) - allowed_sources)
            if unknown:
                raise ValueError(f"{where}: unknown input sources {unknown}")
            if not set(check.inputs) - {APPLICATION_SOURCE}:
                raise ValueError(
                    f"{where}: at least one document source is required"
                )
            if len(check.inputs) < 2:
                raise ValueError(
                    f"{where}: two comparison sources are required"
                )
            for source, field_name in check.inputs.items():
                if not FIELD_NAME_PATTERN.match(field_name):
                    raise ValueError(
                        f"{where}: malformed field name for {source}"
                    )
            claimed = check.inputs.get(APPLICATION_SOURCE)
            if claimed is not None and claimed not in field_keys:
                raise ValueError(
                    f"{where}: application field {claimed!r} is not declared"
                )


class YamlPayload(BaseModel):
    """Raw configuration content submitted by an administrator."""

    yaml_text: str = Field(min_length=1, max_length=500_000)


class VersionPayload(BaseModel):
    """Version selector for lifecycle operations."""

    version: str = Field(min_length=1, max_length=100)
