"""
TripWeaver AI — Graph Workflow State
=====================================
Defines the state schema passed between agents in the LangGraph orchestration flow.
"""

import operator
from typing import Annotated, Any, List, Optional, TypedDict
from langchain_core.messages import AnyMessage


class TravelState(TypedDict, total=False):
    """
    State container passed through the LangGraph multi-agent execution pipeline.
    Maintains user intent, specialist research findings, budget assessments,
    and human-in-the-loop review actions.
    """
    messages: Annotated[List[AnyMessage], operator.add]
    user_query: str

    # Supervisor + guardrail metadata
    guardrail_allowed: bool
    guardrail_reason: str
    selected_agents: List[str]
    trip_constraints: dict[str, Any]
    supervisor_reasoning: str

    # Specialist agent results
    flight_results: str
    hotel_results: str
    weather_results: str
    budget_results: str

    # Itinerary and Human-in-the-Loop review
    itinerary: str
    approval_request: str
    approved: Optional[bool]
    human_feedback: str

    # Polished output and observability
    final_response: str
    llm_calls: int


def get_empty_constraints() -> dict[str, Any]:
    """Return default empty travel constraints structure."""
    return {
        "destination": "",
        "origin": "",
        "duration": "",
        "budget": "",
        "travel_style": "",
        "special_preferences": [],
    }
