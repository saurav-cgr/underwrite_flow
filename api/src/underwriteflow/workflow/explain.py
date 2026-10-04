"""LangGraph route-explanation node."""

from underwriteflow.knowledge.explainer import RouteExplainer


# Run route explanation outside serializable state dependencies.
async def explain_route(
    state: dict[str, object], explainer: RouteExplainer
) -> dict[str, object]:
    explanation = await explainer.explain(state)
    return {"route_explanation": explanation} if explanation else {}
