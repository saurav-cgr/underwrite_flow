"""Recommendation and human-review interrupt graph."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from underwriteflow.reviews.schemas import ReviewCommand
from underwriteflow.workflow.state import TriageState


# Assemble evidence, conflicts, missing inputs, and deterministic signals.
def assemble_case_summary(state: TriageState) -> dict[str, dict[str, object]]:
    return {
        "summary": {
            "evidence": state.get("evidence", []),
            "conflicts": state.get("conflicts", []),
            "missing_information": sorted(set(state.get("missing_information", []))),
            "risk_signals": state.get("risk_signals", []),
            "open_questions": sorted(set(state.get("missing_information", []))),
        }
    }


# Apply cautious deterministic precedence to produce one recommendation.
def recommend_triage_route(state: TriageState) -> dict[str, dict[str, object]]:
    validations = state.get("validations", [])
    triggered_routes = {
        item.get("route") for item in validations if item.get("status") == "triggered"
    }
    if state.get("unsupported_product"):
        route, factor = "manual", "unsupported_product"
    elif "manual" in triggered_routes:
        route, factor = "manual", "manual_rule"
    elif state.get("missing_information") or "needs_information" in triggered_routes:
        route, factor = "needs_information", "missing_information"
    elif (
        state.get("risk_signals")
        or state.get("conflicts")
        or state.get("low_confidence")
        or any(item.get("status") == "error" for item in validations)
    ):
        route, factor = "specialist", "specialist_signal"
    elif any(
        item.get("status") == "triggered" and item.get("route") == "standard"
        for item in validations
    ):
        route, factor = "standard", "standard_rule"
    else:
        route, factor = "expedited", "complete_consistent_submission"
    return {"recommendation": {"route": route, "factors": [factor]}}


# Pause before final routing and accept only a typed human command on resume.
def human_review(state: TriageState) -> dict[str, dict[str, object]]:
    decision = interrupt(
        {
            "type": "human_review",
            "case_id": state.get("case_id"),
            "summary": state.get("summary", {}),
            "recommendation": state.get("recommendation", {}),
        }
    )
    command = ReviewCommand.model_validate(decision)
    return {"review_command": command.model_dump(mode="json", exclude_none=True)}


# Apply the resumed human decision as the only source of final routing.
def apply_human_review(state: TriageState) -> dict[str, str | None]:
    command = ReviewCommand.model_validate(state["review_command"])
    if command.action == "request_information":
        return {"final_route": None, "review_status": "needs_information"}
    route = (
        command.selected_route
        if command.action == "override"
        else state["recommendation"]["route"]
    )
    if route == "needs_information":
        return {"final_route": None, "review_status": "needs_information"}
    return {
        "final_route": route,
        "review_status": "overridden" if command.action == "override" else "confirmed",
    }


# Compile a resumable triage graph with a human checkpoint before final routing.
def build_triage_graph(checkpointer: BaseCheckpointSaver | None = None):
    builder = StateGraph(TriageState)
    builder.add_node("assemble_case_summary", assemble_case_summary)
    builder.add_node("recommend_triage_route", recommend_triage_route)
    builder.add_node("human_review", human_review)
    builder.add_node("apply_human_review", apply_human_review)
    builder.add_edge(START, "assemble_case_summary")
    builder.add_edge("assemble_case_summary", "recommend_triage_route")
    builder.add_edge("recommend_triage_route", "human_review")
    builder.add_edge("human_review", "apply_human_review")
    builder.add_edge("apply_human_review", END)
    return builder.compile(checkpointer=checkpointer)
