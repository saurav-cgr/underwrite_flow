"""Gemini extraction adapter with sanitized failures."""

import httpx

from underwriteflow.providers.schemas import ExtractionRequest, ExtractionResult
from underwriteflow.providers.service import ProviderError, build_messages, parse_result


class GeminiProvider:
    """Call Gemini's structured JSON generation endpoint."""

    # Configure the Gemini endpoint without retaining request content.
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    # Extract fields through Gemini while keeping document content isolated.
    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if not self.api_key:
            raise ProviderError("Gemini provider is not configured")
        messages = build_messages(request)
        payload = {
            "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, params={"key": self.api_key}, json=payload)
                response.raise_for_status()
                raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderError("Gemini provider failed") from error
        return parse_result(raw, "gemini")
