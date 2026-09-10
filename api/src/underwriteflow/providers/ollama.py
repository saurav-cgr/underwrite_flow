"""Optional local Ollama extraction adapter."""

import httpx

from underwriteflow.providers.schemas import ExtractionRequest, ExtractionResult
from underwriteflow.providers.service import ProviderError, build_messages, parse_result


class OllamaProvider:
    """Call a local Ollama chat endpoint for structured extraction."""

    # Configure the local Ollama endpoint and model.
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    # Extract fields through Ollama with JSON response enforcement.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": build_messages(request),
                        "format": "json",
                        "stream": False,
                    },
                )
                response.raise_for_status()
                raw = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise ProviderError("Ollama provider failed") from error
        return parse_result(raw, "ollama")
