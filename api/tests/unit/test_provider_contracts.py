"""Provider field schema, usage, redaction, and page-locator contracts."""

import pytest

from underwriteflow.config import Settings
from underwriteflow.providers.factory import build_provider
from underwriteflow.providers.redaction import redact_personal_data
from underwriteflow.providers.schemas import (
    DocumentPage,
    FieldSpecification,
    ProviderUsage,
)
from underwriteflow.providers.service import (
    ProviderError,
    document_content,
    parse_result,
    trusted_page_locator,
)


# Build one requested field specification for schema validation tests.
def specification(
    field_key: str,
    value_type: str,
    options: list[str] | None = None,
) -> FieldSpecification:
    return FieldSpecification(
        field_key=field_key,
        value_type=value_type,
        allowed_values=options or [],
    )


# Verify a provider value that contradicts its declared type is refused.
def test_provider_output_rejects_wrong_scalar_type() -> None:
    with pytest.raises(ProviderError):
        parse_result(
            [
                {
                    "field_name": "vehicle_age",
                    "value": "many",
                    "source_locator": "page:1",
                    "confidence": 1.0,
                }
            ],
            "gemini",
            specifications=[specification("vehicle_age", "integer")],
        )


# Verify a provider value matching its declared type is accepted.
def test_provider_output_accepts_matching_scalar_type() -> None:
    result = parse_result(
        [
            {
                "field_name": "vehicle_age",
                "value": "4",
                "source_locator": "page:1",
                "confidence": 1.0,
            }
        ],
        "gemini",
        specifications=[specification("vehicle_age", "integer")],
    )

    assert result.fields[0].value == "4"


# Verify an enum value outside the configured options is refused.
def test_provider_output_rejects_unknown_enum_value() -> None:
    with pytest.raises(ProviderError):
        parse_result(
            [
                {
                    "field_name": "vehicle_use",
                    "value": "spaceship",
                    "source_locator": "page:1",
                    "confidence": 1.0,
                }
            ],
            "gemini",
            specifications=[
                specification(
                    "vehicle_use", "enum", ["personal", "commute"]
                )
            ],
        )


# Verify a field the configuration never declared is refused.
def test_provider_output_rejects_undeclared_field() -> None:
    with pytest.raises(ProviderError):
        parse_result(
            [
                {
                    "field_name": "invented_field",
                    "value": "1",
                    "source_locator": "page:1",
                    "confidence": 1.0,
                }
            ],
            "gemini",
            specifications=[specification("vehicle_age", "integer")],
        )


# Verify the canonical result hash ignores the order fields arrive in.
def test_provider_result_hash_is_canonical() -> None:
    fields = [
        {
            "field_name": "vehicle_age",
            "value": "4",
            "source_locator": "page:1",
            "confidence": 1.0,
        },
        {
            "field_name": "vehicle_use",
            "value": "personal",
            "source_locator": "page:1",
            "confidence": 0.9,
        },
    ]

    first = parse_result(fields, "gemini")
    reordered = parse_result(list(reversed(fields)), "gemini")
    changed = parse_result([dict(fields[0], value="5"), fields[1]], "gemini")

    assert first.result_hash == reordered.result_hash
    assert first.result_hash != changed.result_hash
    assert len(first.result_hash) == 64


# Verify a provider without usage reporting is marked unavailable.
def test_provider_usage_is_marked_unavailable_by_default() -> None:
    result = parse_result([], "gemini")

    assert result.usage.unavailable is True
    assert result.usage.prompt_tokens is None
    assert result.usage.completion_tokens is None


# Verify reported token counts survive into the shared usage metadata.
def test_provider_usage_keeps_reported_token_counts() -> None:
    usage = ProviderUsage(
        model="synthetic-model",
        prompt_tokens=12,
        completion_tokens=8,
        unavailable=False,
    )

    result = parse_result([], "gemini", usage=usage)

    assert result.usage.model == "synthetic-model"
    assert result.usage.prompt_tokens == 12
    assert result.usage.completion_tokens == 8
    assert result.usage.unavailable is False


# Verify provider input keeps each trusted page boundary with its text.
def test_document_content_keeps_trusted_page_boundaries() -> None:
    pages = [
        DocumentPage(
            page_number=1, text="first page", source_locator="page:1"
        ),
        DocumentPage(
            page_number=2, text="second page", source_locator="page:2"
        ),
    ]

    assert document_content(pages) == (
        "page:1\nfirst page\npage:2\nsecond page"
    )


# Verify a provider line locator maps onto the trusted page that holds it.
def test_provider_line_locator_maps_to_trusted_page() -> None:
    pages = [
        DocumentPage(page_number=1, text="one\ntwo", source_locator="page:1"),
        DocumentPage(page_number=2, text="three", source_locator="page:2"),
    ]

    assert trusted_page_locator(pages, "line:1") == "page:1"
    assert trusted_page_locator(pages, "line:3") == "page:1"
    assert trusted_page_locator(pages, "line:4") == "page:2"
    assert trusted_page_locator(pages, "line:99") == "page:2"


# Verify a locator the application did not issue is left untouched.
def test_unknown_locator_shape_is_preserved() -> None:
    pages = [
        DocumentPage(page_number=1, text="one", source_locator="page:1")
    ]

    assert trusted_page_locator(pages, "sheet:a") == "sheet:a"


# Verify configured personal identifiers are redacted before an external call.
def test_redaction_removes_aadhaar_pan_email_and_phone() -> None:
    redacted = redact_personal_data(
        "aadhaar 2345 6789 0123 pan ABCDE1234F "
        "email synthetic@example.test phone 9876543210"
    )

    assert "2345 6789 0123" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "synthetic@example.test" not in redacted
    assert "9876543210" not in redacted
    assert redacted.count("[redacted]") == 4


# Verify local configuration can add deployment-specific literal PII.
def test_redaction_removes_configured_literal_terms() -> None:
    redacted = redact_personal_data(
        "member reference SYNTHETIC-MEMBER-42",
        ("SYNTHETIC-MEMBER-42",),
    )

    assert redacted == "member reference [redacted]"


# Verify empty or unbounded configured literals are rejected.
@pytest.mark.parametrize("term", ["", "x" * 201])
def test_redaction_terms_are_bounded(term: str) -> None:
    with pytest.raises(ValueError):
        Settings(pii_redaction_terms=(term,))


# Verify Gemini cannot run without an explicit no-training acknowledgement.
def test_gemini_requires_no_training_acknowledgement() -> None:
    with pytest.raises(ProviderError, match="no-training"):
        build_provider(Settings(generation_provider="gemini"))


# Verify a configured provider host must appear in the deployment allowlist.
def test_gemini_requires_an_approved_host() -> None:
    settings = Settings(
        generation_provider="gemini",
        gemini_no_training_acknowledged=True,
        provider_allowed_hosts=("synthetic.invalid",),
    )

    with pytest.raises(ProviderError, match="not approved"):
        build_provider(settings)


# Verify Ollama cannot be redirected outside the local environment.
@pytest.mark.parametrize(
    "base_url",
    ["https://example.test:11434", "http://ollama.example.test:11434"],
)
def test_ollama_rejects_non_local_urls(base_url: str) -> None:
    settings = Settings(
        generation_provider="ollama",
        ollama_base_url=base_url,
        provider_allowed_hosts=("example.test", "ollama.example.test"),
    )

    with pytest.raises(ProviderError, match="local"):
        build_provider(settings)


# Verify approved Gemini and local Ollama configurations remain available.
@pytest.mark.parametrize("provider", ["gemini", "ollama"])
def test_approved_provider_boundaries_pass(provider: str) -> None:
    settings = Settings(
        generation_provider=provider,
        gemini_no_training_acknowledged=True,
    )

    assert build_provider(settings).name == provider
