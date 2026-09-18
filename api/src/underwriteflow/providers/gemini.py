"""Gemini extraction adapter with sanitized failures."""

import httpx

from underwriteflow.providers.redaction import redacted_request
from underwriteflow.providers.schemas import (
    ExtractionRequest,
    ExtractionResult,
    ProviderUsage,
)
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
    build_messages,
    is_transient_status,
    parse_result,
    provider_payload_bytes,
    provider_payload_hash,
)


# Read Gemini's reported token counts, or mark them unavailable.
def gemini_usage(model: str, metadata: dict) -> ProviderUsage:
    prompt = metadata.get("promptTokenCount")
    completion = metadata.get("candidatesTokenCount")
    if not isinstance(prompt, int) and not isinstance(completion, int):
        return ProviderUsage(model=model)
    return ProviderUsage(
        model=model,
        prompt_tokens=prompt if isinstance(prompt, int) else None,
        completion_tokens=(
            completion if isinstance(completion, int) else None
        ),
        unavailable=False,
    )


class GeminiProvider:
    """Call Gemini's structured JSON generation endpoint."""

    name = "gemini"

    # Configure the Gemini endpoint without retaining request content.
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 30,
        pii_redaction_terms: tuple[str, ...] = (),
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.pii_redaction_terms = pii_redaction_terms

    # Extract fields through Gemini while keeping document content isolated.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if not self.api_key:
            raise ProviderError("Gemini provider is not configured")
        # An external provider never receives raw personal identifiers.
        safe_request = redacted_request(
            request, self.pii_redaction_terms
        )
        messages = build_messages(safe_request)
        payload = {
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        request_payload = provider_payload_bytes(payload)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    url,
                    params={"key": self.api_key},
                    content=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                body = response.json()
                raw = body["candidates"][0]["content"]["parts"][0]["text"]
                usage = gemini_usage(
                    self.model, body.get("usageMetadata") or {}
                )
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise TransientProviderError("Gemini provider is temporarily unavailable") from error
        except httpx.HTTPStatusError as error:
            if is_transient_status(error.response.status_code):
                raise TransientProviderError("Gemini provider is temporarily unavailable") from error
            raise ProviderError("Gemini provider failed") from error
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderError("Gemini provider failed") from error
        return parse_result(
            raw,
            "gemini",
            request.field_specifications,
            usage,
            request_hash=provider_payload_hash(request_payload),
            result_hash=provider_payload_hash(raw),
        )
