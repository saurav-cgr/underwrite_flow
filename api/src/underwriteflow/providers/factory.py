"""Select the configured extraction provider for one application run."""

from urllib.parse import urlsplit

from underwriteflow.config import Settings
from underwriteflow.providers.fake import FakeProvider
from underwriteflow.providers.gemini import GEMINI_HOST, GeminiProvider
from underwriteflow.providers.ollama import OllamaProvider
from underwriteflow.providers.protocol import ExtractionProvider
from underwriteflow.providers.service import ProviderError

LOCAL_OLLAMA_HOSTS = frozenset({"ollama", "localhost", "127.0.0.1", "::1"})


# Refuse any provider destination outside the deployment allowlist.
def require_approved_host(host: str, settings: Settings) -> None:
    allowed = {item.lower() for item in settings.provider_allowed_hosts}
    if host.lower() not in allowed:
        raise ProviderError("Provider host is not approved")


# Build the configured provider behind the application-owned protocol.
def build_provider(settings: Settings) -> ExtractionProvider:
    if settings.generation_provider == "fake":
        return FakeProvider()
    if settings.generation_provider == "ollama":
        parsed = urlsplit(settings.ollama_base_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or host not in (
            LOCAL_OLLAMA_HOSTS
        ):
            raise ProviderError("Ollama provider must use a local URL")
        require_approved_host(host, settings)
        return OllamaProvider(
            settings.ollama_base_url,
            settings.ollama_model,
            timeout_seconds=settings.provider_timeout_seconds,
        )
    if not settings.gemini_no_training_acknowledged:
        raise ProviderError(
            "Gemini provider requires a no-training project acknowledgement"
        )
    require_approved_host(GEMINI_HOST, settings)
    return GeminiProvider(
        settings.gemini_api_key,
        settings.gemini_model,
        timeout_seconds=settings.provider_timeout_seconds,
        pii_redaction_terms=settings.pii_redaction_terms,
    )
