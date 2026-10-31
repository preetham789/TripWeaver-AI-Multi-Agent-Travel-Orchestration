"""
TripWeaver AI — Graph Routing and Agent Registry
=================================================
Manages specialist agent sequence order and conditional edge routing logic.
"""

from typing import Dict, List, Set
from graph.state import TravelState

KNOWN_AGENTS: Set[str] = {
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
}

AGENT_ORDER: List[str] = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]

AGENT_ROUTE_MAP: Dict[str, str] = {
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
    "guardrail_blocked": "guardrail_blocked_agent",
}


def _next_selected_agent(selected: List[str], current: str) -> str:
    """Return the next agent in AGENT_ORDER that is in selected, or itinerary_agent."""
    ordered = [a for a in AGENT_ORDER if a in selected]
    if current not in ordered:
        return "itinerary_agent"
    idx = ordered.index(current)
    if idx + 1 < len(ordered):
        return ordered[idx + 1]
    return "itinerary_agent"


def route_from_supervisor(state: TravelState) -> str:
    """Determine first execution node from supervisor decision."""
    if not state.get("guardrail_allowed", True):
        return "guardrail_blocked"

    selected = state.get("selected_agents", [])
    ordered = [a for a in AGENT_ORDER if a in selected]

    if ordered:
        return ordered[0]
    return "itinerary_agent"


def route_after_flight(state: TravelState) -> str:
    selected = state.get("selected_agents", [])
    return _next_selected_agent(selected, "flight_agent")


def route_after_hotel(state: TravelState) -> str:
    selected = state.get("selected_agents", [])
    return _next_selected_agent(selected, "hotel_agent")


def route_after_weather(state: TravelState) -> str:
    selected = state.get("selected_agents", [])
    return _next_selected_agent(selected, "weather_agent")


def route_after_budget(state: TravelState) -> str:
    selected = state.get("selected_agents", [])
    return _next_selected_agent(selected, "budget_agent")


def route_from_human_approval(state: TravelState) -> str:
    return "final_agent"
