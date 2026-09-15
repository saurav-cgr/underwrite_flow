"""Select the configured extraction provider for one application run."""

from underwriteflow.config import Settings
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.providers.gemini import GeminiProvider
from underwriteflow.providers.ollama import OllamaProvider
from underwriteflow.providers.protocol import ExtractionProvider


# Build the configured provider behind the application-owned protocol.
def build_provider(settings: Settings) -> ExtractionProvider:
    if settings.generation_provider == "fake":
        return FakeProvider()
    if settings.generation_provider == "ollama":
        return OllamaProvider(
            settings.ollama_base_url,
            settings.ollama_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
    return GeminiProvider(
        settings.gemini_api_key,
        settings.gemini_model,
        timeout_seconds=settings.provider_timeout_seconds,
    )
