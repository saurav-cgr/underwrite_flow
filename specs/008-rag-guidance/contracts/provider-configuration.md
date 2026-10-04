# Provider Configuration Contract (US11)

## Public environment interface

- GENERATION_PROVIDER: fake, gemini, or ollama; default gemini.
- EMBEDDING_PROVIDER: fake, gemini, or ollama. Backend unset behavior
  falls back to GENERATION_PROVIDER; Compose's default remains fake.
- GENERATION_MODEL and EMBEDDING_MODEL: optional strings. Trim surrounding
  whitespace. Unset, empty, and whitespace-only mean automatic defaults.
  Explicit values apply only to the selected provider for that capability.

| Provider | Generation default | Embedding default |
|----------|--------------------|-------------------|
| Gemini | gemini-3.1-flash-lite | gemini-embedding-001 |
| Ollama | llama3.2 | embeddinggemma |

Fake providers ignore model overrides and retain their current identities.
Ollama guidance remains unavailable; this story adds no provider capability.

## Internal settings interface

Replace the four provider-specific fields with generation_model and
embedding_model, each str or None with default None. Normalize blank
strings to None. Add resolved_generation_model and resolved_embedding_model
properties: explicit override, otherwise selected provider default.
The properties return None for fake; fake builders do not read them.
Define named default constants in config.py and reference them only there.
Generation extraction and Gemini guidance share the resolved generation
model. Embeddings resolve against the effective embedding provider.

## Compose boundary

Forward common model values with empty-string defaults, never model names.
Reuse a shared provider environment YAML anchor for API and bootstrap.
Keep per-service settings outside it and retain evaluation/smoke overrides.
Preserve existing credentials, allowed hosts, redaction, retry, timeout,
acknowledgement, and tracing behavior. Do not log rendered credentials.

## Removed interface

GEMINI_MODEL, OLLAMA_MODEL, GEMINI_EMBEDDING_MODEL, and
OLLAMA_EMBEDDING_MODEL, plus their lowercase Settings fields, are removed.
No aliases, fallback lookup, or deprecation layer. Unknown variables retain
Settings' existing extra-ignore behavior and have no model-selection effect.
Rename private local overrides manually; never commit or print .env.

## Persistence

Usage metadata and source.embedding_model retain their existing formats.
The latter remains <provider>:<resolved model>. Existing re-import logic
re-embeds on a tag change. No schema, route, or audit-format change.
