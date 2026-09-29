"""Build stored route explanations from pinned retrieval results."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from underwriteflow.audit.events import build_audit_event
from underwriteflow.knowledge.retrieval import retrieve
from underwriteflow.providers.embedding import EmbeddingProvider
from underwriteflow.providers.guidance import (
    GuidanceCitation,
    GuidanceOutput,
    GuidanceProvider,
    GuidanceRequest,
)
from underwriteflow.providers.service import (
    ProviderError,
    TransientProviderError,
)

LOGGER = logging.getLogger(__name__)


class RouteExplainer:
    """Retrieve pinned passages and create one bounded route explanation."""

    # Keep workflow dependencies outside serializable graph state.
    def __init__(
        self,
        session: AsyncSession,
        provider: GuidanceProvider,
        embedder: EmbeddingProvider,
        provider_retry_count: int = 0,
    ) -> None:
        self.session = session
        self.provider = provider
        self.embedder = embedder
        self.provider_retry_count = provider_retry_count

    # Explain one route, falling back without changing deterministic routing.
    async def explain(
        self, state: dict[str, object]
    ) -> dict[str, object] | None:
        recommendation = state.get("recommendation") or {}
        route = str(recommendation.get("route", ""))
        if route in {"", "manual"} or state.get("unsupported_product"):
            return None
        context = state.get("guidance_context") or {}
        version_id = context.get("guideline_version_id")
        if not version_id:
            return None
        query = self._query(state, context)
        try:
            # A savepoint keeps a failed query from aborting the case write.
            async with self.session.begin_nested():
                passages = await retrieve(
                    self.session,
                    self.embedder,
                    version_id,
                    query,
                    {
                        "age": context.get("age"),
                        "sum_assured": context.get("sum_assured"),
                    },
                )
        except (ProviderError, SQLAlchemyError) as error:
            LOGGER.warning(
                "route guidance retrieval failed: case_id=%s error=%s",
                state.get("case_id"),
                type(error).__name__,
            )
            return self._unavailable()
        if not passages:
            return self._template(state, [])
        request = GuidanceRequest(
            route=route,
            factors=[str(item) for item in recommendation.get("factors", [])],
            missing_items=self._missing_items(state),
            context={
                key: value
                for key, value in context.items()
                if key in {"case_id", "product_code", "age", "sum_assured"}
            },
            passages=passages,
        )
        for attempt in range(self.provider_retry_count + 1):
            try:
                output = await self.provider.explain(request)
            except TransientProviderError:
                if attempt == self.provider_retry_count:
                    return self._template(state, passages)
            except ProviderError:
                return self._template(state, passages)
            else:
                return self._validated_output(state, output, passages)
        return self._template(state, passages)

    # Build a stable retrieval query from identifiers, numbers, and rule codes.
    def _query(
        self, state: dict[str, object], context: dict[str, object]
    ) -> str:
        recommendation = state.get("recommendation") or {}
        values = [
            context.get("product_code"),
            recommendation.get("route"),
            *recommendation.get("factors", []),
            *state.get("missing_information", []),
        ]
        return " ".join(str(value) for value in values if value is not None)

    # Convert missing identifiers into provider-safe reason objects.
    def _missing_items(self, state: dict[str, object]) -> list[dict[str, str]]:
        return [
            {
                "item": str(item),
                "reason": "Required before route confirmation.",
            }
            for item in state.get("missing_information", [])
        ]

    # Return the fixed retrieval/provider failure representation.
    def _unavailable(self) -> dict[str, object]:
        return {
            "status": "unavailable",
            "text": "Explanation unavailable.",
            "missing_items": [],
            "citations": [],
            "provider": None,
            "model": None,
            "request_hash": None,
        }

    # Build a deterministic explanation from route factors and passage titles.
    def _template(
        self,
        state: dict[str, object],
        passages: list[dict[str, object]],
    ) -> dict[str, object]:
        recommendation = state.get("recommendation") or {}
        route = str(recommendation.get("route", "review"))
        factors = [str(item) for item in recommendation.get("factors", [])]
        titles = [str(item.get("title")) for item in passages]
        detail = ", ".join(factors) or "the submitted evidence"
        text = f"{route.capitalize()} review is recommended because {detail}."
        if titles:
            text += " Relevant guidance: " + ", ".join(titles) + "."
        citations = [self._citation(item) for item in passages]
        missing = [
            {
                "item": item["item"],
                "reason": item["reason"],
                "citations": citations[:1],
            }
            for item in self._missing_items(state)
        ]
        return {
            "status": "template",
            "text": text,
            "missing_items": missing,
            "citations": citations,
            "provider": None,
            "model": None,
            "request_hash": None,
        }

    # Convert one retrieved passage into the public citation shape.
    def _citation(self, passage: dict[str, object]) -> dict[str, object]:
        return {
            "version": passage.get("version"),
            "version_id": passage.get("version_id"),
            "passage_key": passage.get("passage_key"),
        }

    # Keep only citations returned by the pinned retrieval query.
    def _validated_output(
        self,
        state: dict[str, object],
        output: GuidanceOutput,
        passages: list[dict[str, object]],
    ) -> dict[str, object]:
        allowed = {
            (str(item.get("version")), str(item.get("passage_key"))): item
            for item in passages
        }
        valid = []
        for citation in output.citations:
            item = allowed.get((citation.version, citation.passage_key))
            if item is None:
                self._drop_citation(state, citation.passage_key)
                continue
            valid.append(self._citation(item))
        missing = []
        for item in output.missing_items:
            item_citations = []
            for citation in item.citations:
                found = allowed.get((citation.version, citation.passage_key))
                if found is None:
                    self._drop_citation(state, citation.passage_key)
                    continue
                item_citations.append(self._citation(found))
            missing.append(
                {
                    "item": item.item,
                    "reason": item.reason,
                    "citations": item_citations,
                }
            )
        required_items = {
            item["item"] for item in self._missing_items(state)
        }
        covered_items = {
            item["item"] for item in missing if item["citations"]
        }
        if required_items - covered_items:
            return self._template(state, passages)
        if not valid:
            return self._template(state, passages)
        return {
            "status": "generated",
            "text": output.text,
            "missing_items": missing,
            "citations": valid,
            "provider": output.provider,
            "model": output.model,
            "request_hash": output.request_hash,
        }

    # Record one dropped provider citation without storing text content.
    def _drop_citation(
        self, state: dict[str, object], passage_key: str
    ) -> None:
        self.session.add(
            build_audit_event(
                "citation_dropped",
                {
                    "case_id": state.get("case_id"),
                    "output_kind": "route_explanation",
                    "passage_key": passage_key,
                },
            )
        )
