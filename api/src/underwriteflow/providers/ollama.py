"""Optional local Ollama extraction adapter."""

import httpx

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


# Read Ollama's local token counts, or mark them unavailable.
def ollama_usage(model: str, body: dict) -> ProviderUsage:
    prompt = body.get("prompt_eval_count")
    completion = body.get("eval_count")
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


class OllamaProvider:
    """Call a local Ollama chat endpoint for structured extraction."""

    name = "ollama"

    # Configure the local Ollama endpoint and model.
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    # Extract fields through Ollama with JSON response enforcement.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        payload = {
            "model": self.model,
            "messages": build_messages(request),
            "format": "json",
            "stream": False,
        }
        request_payload = provider_payload_bytes(payload)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    content=request_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                body = response.json()
                raw = body["message"]["content"]
                usage = ollama_usage(self.model, body)
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise TransientProviderError(
                "Ollama provider is temporarily unavailable"
            ) from error
        except httpx.HTTPStatusError as error:
            if is_transient_status(error.response.status_code):
                raise TransientProviderError(
                    "Ollama provider is temporarily unavailable"
                ) from error
            raise ProviderError("Ollama provider failed") from error
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise ProviderError("Ollama provider failed") from error
        return parse_result(
            raw,
            "ollama",
            request.field_specifications,
            usage,
            request_hash=provider_payload_hash(request_payload),
            result_hash=provider_payload_hash(raw),
        )
