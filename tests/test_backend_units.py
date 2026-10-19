"""
TripWeaver AI — Backend Unit Tests
====================================
Tests pure helper functions, routing logic, guardrail logic, and serialisation
from backend.py directly — without triggering the DB/graph compilation.

Strategy:
  - Temporarily redirect sys.modules["backend"] so the real module can be
    imported under an alias (real_backend).
  - Patch psycopg.connect and PostgresSaver.setup at import time so the module
    level DB connection code doesn't fail.
"""

import json
import os
import sys
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ── Load the real backend module (avoiding the API stub) ──────────────────────

def _load_real_backend():
    """Import backend.py with DB calls mocked out."""
    # Remove any existing stub so we get the real module
    sys.modules.pop("backend", None)

    mock_conn = MagicMock()

    # LangGraph validates the checkpointer type — use InMemorySaver to satisfy it.
    # Add a stub setup() so backend.py's checkpointer.setup() call doesn't fail.
    from langgraph.checkpoint.memory import MemorySaver
    real_saver = MemorySaver()
    real_saver.setup = lambda: None  # backend.py calls checkpointer.setup()

    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch(
            "langgraph.checkpoint.postgres.PostgresSaver",
            return_value=real_saver,
        ),
        patch("langchain_groq.ChatGroq"),
    ):
        import backend as _b
        return _b


try:
    real_backend = _load_real_backend()
    BACKEND_AVAILABLE = True
except Exception as e:
    BACKEND_AVAILABLE = False
    BACKEND_ERROR = str(e)

skip_if_no_backend = pytest.mark.skipif(
    not BACKEND_AVAILABLE,
    reason=f"backend not importable: {BACKEND_ERROR if not BACKEND_AVAILABLE else ''}",
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper Function Tests
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestLimitContext:
    def test_short_string_unchanged(self):
        assert real_backend._limit_context("Hello world", 100) == "Hello world"

    def test_long_string_truncated(self):
        result = real_backend._limit_context("A" * 200, 50)
        assert "[Context truncated]" in result

    def test_truncated_result_starts_with_original(self):
        result = real_backend._limit_context("Hello world!", 5)
        assert result.startswith("Hello")

    def test_exact_length_not_truncated(self):
        s = "B" * 50
        assert real_backend._limit_context(s, 50) == s

    def test_zero_limit_truncated(self):
        result = real_backend._limit_context("Hello", 0)
        assert "[Context truncated]" in result

    def test_non_string_input_converted(self):
        result = real_backend._limit_context({"key": "value"}, 1000)
        assert "key" in result

    def test_integer_input(self):
        result = real_backend._limit_context(42, 1000)
        assert "42" in result


@skip_if_no_backend
class TestJsonFromLlm:
    def test_valid_json_extracted(self):
        raw = 'Some text {"allowed": true, "reason": ""} extra'
        result = real_backend._json_from_llm(raw)
        assert result["allowed"] is True

    def test_nested_json_extracted(self):
        raw = '{"a": {"b": 1}}'
        assert real_backend._json_from_llm(raw)["a"]["b"] == 1

    def test_extra_text_before_and_after(self):
        raw = 'Preamble {"key": "value"} trailing text'
        assert real_backend._json_from_llm(raw)["key"] == "value"

    def test_no_braces_raises_value_error(self):
        with pytest.raises(ValueError):
            real_backend._json_from_llm("no JSON here")

    def test_malformed_json_raises(self):
        with pytest.raises(Exception):
            real_backend._json_from_llm("{invalid: json}")

    def test_empty_object(self):
        assert real_backend._json_from_llm("{}") == {}

    def test_only_closing_brace_raises(self):
        with pytest.raises(ValueError):
            real_backend._json_from_llm("}")


@skip_if_no_backend
class TestEmptyConstraints:
    def test_has_all_required_keys(self):
        c = real_backend._empty_constraints()
        for key in ("destination", "origin", "duration", "budget",
                    "travel_style", "special_preferences"):
            assert key in c

    def test_all_strings_are_empty(self):
        c = real_backend._empty_constraints()
        for key in ("destination", "origin", "duration", "budget", "travel_style"):
            assert c[key] == ""

    def test_special_preferences_is_empty_list(self):
        assert real_backend._empty_constraints()["special_preferences"] == []

    def test_returns_independent_copies(self):
        c1 = real_backend._empty_constraints()
        c2 = real_backend._empty_constraints()
        c1["destination"] = "Tokyo"
        assert c2["destination"] == ""


# ─────────────────────────────────────────────────────────────────────────────
# _serialize_result Tests
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestSerializeResult:
    def _base_result(self, **overrides):
        base = {
            "messages": [],
            "final_response": "Great trip!",
            "flight_results": "Flights OK",
            "hotel_results": "Hotels OK",
            "weather_results": "Sunny",
            "budget_results": "Feasible",
            "itinerary": "Day 1...",
            "selected_agents": ["flight_agent"],
            "trip_constraints": {},
            "supervisor_reasoning": "",
            "guardrail_allowed": True,
            "guardrail_reason": "",
            "approved": True,
            "human_feedback": "",
            "llm_calls": 4,
        }
        base.update(overrides)
        return base

    def test_basic_serialization(self):
        out = real_backend._serialize_result(self._base_result(), "user_t1")
        assert out["thread_id"] == "user_t1"
        assert out["answer"] == "Great trip!"
        assert out["requires_approval"] is False

    def test_llm_calls_passed_through(self):
        out = real_backend._serialize_result(self._base_result(llm_calls=7), "t")
        assert out["llm_calls"] == 7

    def test_no_interrupt_requires_approval_false(self):
        out = real_backend._serialize_result(self._base_result(), "t")
        assert out["requires_approval"] is False

    def test_with_interrupt_requires_approval_true(self):
        from unittest.mock import MagicMock
        interrupt_obj = MagicMock()
        interrupt_obj.value = {
            "draft_itinerary": "Draft plan",
            "approval_request": "Please approve",
        }
        result = self._base_result()
        result["__interrupt__"] = [interrupt_obj]
        out = real_backend._serialize_result(result, "t")
        assert out["requires_approval"] is True

    def test_interrupt_approval_request_extracted(self):
        interrupt_obj = MagicMock()
        interrupt_obj.value = {
            "draft_itinerary": "Draft",
            "approval_request": "Approve me",
        }
        result = self._base_result()
        result["__interrupt__"] = [interrupt_obj]
        out = real_backend._serialize_result(result, "t")
        assert out["approval_request"] == "Approve me"

    def test_fallback_to_last_message_when_no_final_response(self):
        from langchain_core.messages import AIMessage
        result = self._base_result()
        del result["final_response"]  # remove so fallback triggers
        result["messages"] = [AIMessage(content="Fallback answer")]
        out = real_backend._serialize_result(result, "t")
        assert out["answer"] == "Fallback answer"

    def test_empty_messages_and_no_final_response_gives_empty(self):
        result = self._base_result()
        del result["final_response"]
        result["messages"] = []
        out = real_backend._serialize_result(result, "t")
        assert out["answer"] == ""

    def test_selected_agents_passed_through(self):
        out = real_backend._serialize_result(
            self._base_result(selected_agents=["flight_agent", "hotel_agent"]), "t"
        )
        assert "flight_agent" in out["selected_agents"]


@skip_if_no_backend
class TestInterruptPayload:
    def test_empty_result_returns_none(self):
        assert real_backend._interrupt_payload({}) is None

    def test_empty_interrupt_list_returns_none(self):
        assert real_backend._interrupt_payload({"__interrupt__": []}) is None

    def test_dict_value_extracted(self):
        mock_int = MagicMock()
        mock_int.value = {"question": "Approve?"}
        result = real_backend._interrupt_payload({"__interrupt__": [mock_int]})
        assert result == {"question": "Approve?"}

    def test_non_dict_value_wrapped(self):
        mock_int = MagicMock()
        mock_int.value = "plain string"
        result = real_backend._interrupt_payload({"__interrupt__": [mock_int]})
        assert result == {"value": "plain string"}


# ─────────────────────────────────────────────────────────────────────────────
# Routing Logic Tests
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestRoutingLogic:
    def test_route_from_supervisor_blocked(self):
        state = {"guardrail_allowed": False, "selected_agents": []}
        assert real_backend.route_from_supervisor(state) == "guardrail_blocked"

    def test_route_from_supervisor_first_agent(self):
        state = {
            "guardrail_allowed": True,
            "selected_agents": ["flight_agent", "hotel_agent", "itinerary_agent"],
        }
        assert real_backend.route_from_supervisor(state) == "flight_agent"

    def test_route_from_supervisor_empty_selected_defaults_itinerary(self):
        state = {"guardrail_allowed": True, "selected_agents": []}
        assert real_backend.route_from_supervisor(state) == "itinerary_agent"

    def test_route_from_supervisor_hotel_only(self):
        state = {
            "guardrail_allowed": True,
            "selected_agents": ["hotel_agent", "itinerary_agent"],
        }
        assert real_backend.route_from_supervisor(state) == "hotel_agent"

    def test_route_after_flight_goes_to_hotel(self):
        route = real_backend.route_after_agent("flight_agent")
        state = {"selected_agents": ["flight_agent", "hotel_agent", "itinerary_agent"]}
        assert route(state) == "hotel_agent"

    def test_route_after_flight_skips_hotel_when_absent(self):
        route = real_backend.route_after_agent("flight_agent")
        state = {"selected_agents": ["flight_agent", "weather_agent", "itinerary_agent"]}
        assert route(state) == "weather_agent"

    def test_route_after_hotel_goes_to_weather(self):
        route = real_backend.route_after_agent("hotel_agent")
        state = {"selected_agents": ["hotel_agent", "weather_agent", "itinerary_agent"]}
        assert route(state) == "weather_agent"

    def test_route_after_budget_goes_to_itinerary(self):
        route = real_backend.route_after_agent("budget_agent")
        state = {"selected_agents": ["budget_agent", "itinerary_agent"]}
        assert route(state) == "itinerary_agent"

    def test_route_after_weather_goes_to_budget(self):
        route = real_backend.route_after_agent("weather_agent")
        state = {"selected_agents": ["weather_agent", "budget_agent", "itinerary_agent"]}
        assert route(state) == "budget_agent"

    def test_route_after_last_specialist_defaults_to_itinerary(self):
        route = real_backend.route_after_agent("weather_agent")
        state = {"selected_agents": ["weather_agent", "itinerary_agent"]}
        assert route(state) == "itinerary_agent"

    def test_selected_agents_follows_agent_order(self):
        state = {"selected_agents": ["itinerary_agent", "flight_agent", "hotel_agent"]}
        result = real_backend._selected_agents(state)
        positions = [real_backend.AGENT_ORDER.index(a) for a in result]
        assert positions == sorted(positions)

    def test_selected_agents_filters_unknown(self):
        state = {"selected_agents": ["flight_agent", "unknown_agent", "itinerary_agent"]}
        result = real_backend._selected_agents(state)
        assert "unknown_agent" not in result


# ─────────────────────────────────────────────────────────────────────────────
# Agent Registry Tests
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestAgentRegistry:
    def test_known_agents_has_five_entries(self):
        assert len(real_backend.KNOWN_AGENTS) == 5

    def test_known_agents_contains_all_expected(self):
        expected = {
            "flight_agent", "hotel_agent", "weather_agent",
            "budget_agent", "itinerary_agent"
        }
        assert real_backend.KNOWN_AGENTS == expected

    def test_agent_order_starts_with_flight(self):
        assert real_backend.AGENT_ORDER[0] == "flight_agent"

    def test_agent_order_ends_with_itinerary(self):
        assert real_backend.AGENT_ORDER[-1] == "itinerary_agent"

    def test_agent_order_no_duplicates(self):
        ao = real_backend.AGENT_ORDER
        assert len(ao) == len(set(ao))

    def test_agent_order_matches_known_agents(self):
        assert set(real_backend.AGENT_ORDER) == real_backend.KNOWN_AGENTS

    def test_route_map_covers_all_known_agents(self):
        for agent in real_backend.KNOWN_AGENTS:
            assert agent in real_backend.ROUTE_MAP

    def test_route_map_has_guardrail_blocked(self):
        assert "guardrail_blocked" in real_backend.ROUTE_MAP


# ─────────────────────────────────────────────────────────────────────────────
# Supervisor / Guardrail Agent Tests (mocked LLM)
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestGuardrailAndSupervisor:
    def _make_state(self, query: str) -> dict:
        return {
            "user_query": query,
            "messages": [],
            "guardrail_allowed": True,
            "guardrail_reason": "",
            "selected_agents": [],
            "trip_constraints": real_backend._empty_constraints(),
            "supervisor_reasoning": "",
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "itinerary": "",
            "budget_results": "",
            "approval_request": "",
            "approved": False,
            "human_feedback": "",
            "final_response": "",
            "llm_calls": 0,
        }

    def test_guardrail_allows_travel_request(self):
        real_backend.llm.invoke = MagicMock(side_effect=[
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(content=json.dumps({
                "selected_agents": ["flight_agent", "hotel_agent", "itinerary_agent"],
                "trip_constraints": {
                    "destination": "Japan", "origin": "India",
                    "duration": "7 days", "budget": "2 lakhs",
                    "travel_style": "", "special_preferences": []
                },
                "reasoning": "Full trip requested",
            })),
        ])
        result = real_backend.supervisor_agent(self._make_state(
            "Plan a 7-day Japan trip from India under 2 lakhs."
        ))
        assert result["guardrail_allowed"] is True
        assert "flight_agent" in result["selected_agents"]
        assert "itinerary_agent" in result["selected_agents"]

    def test_guardrail_blocks_non_travel_request(self):
        real_backend.llm.invoke = MagicMock(return_value=MagicMock(
            content='{"allowed": false, "reason": "Not a travel request."}'
        ))
        result = real_backend.supervisor_agent(self._make_state(
            "Write me a Python web scraper."
        ))
        assert result["guardrail_allowed"] is False
        assert result["selected_agents"] == []
        assert "Not a travel request" in result["guardrail_reason"]

    def test_guardrail_fails_open_on_parse_error(self):
        """Garbage JSON from the guardrail should allow the request (fail-open)."""
        real_backend.llm.invoke = MagicMock(side_effect=[
            MagicMock(content="totally not JSON at all"),
            MagicMock(content=json.dumps({
                "selected_agents": ["itinerary_agent"],
                "trip_constraints": {},
                "reasoning": "",
            })),
        ])
        result = real_backend.supervisor_agent(self._make_state("Plan a trip to Paris."))
        assert result["guardrail_allowed"] is True

    def test_supervisor_fallback_uses_full_agent_order(self):
        """If supervisor JSON parsing fails, all agents are selected as fallback."""
        real_backend.llm.invoke = MagicMock(side_effect=[
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(content="not valid JSON"),
        ])
        result = real_backend.supervisor_agent(self._make_state("Plan a trip anywhere."))
        assert result["guardrail_allowed"] is True
        assert set(result["selected_agents"]) == set(real_backend.AGENT_ORDER)

    def test_itinerary_agent_always_included(self):
        """Supervisor must include itinerary_agent even if LLM omits it."""
        real_backend.llm.invoke = MagicMock(side_effect=[
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(content=json.dumps({
                "selected_agents": ["flight_agent"],  # itinerary missing
                "trip_constraints": {},
                "reasoning": "",
            })),
        ])
        result = real_backend.supervisor_agent(self._make_state("Book me a flight to Paris."))
        assert "itinerary_agent" in result["selected_agents"]

    def test_supervisor_increments_llm_calls(self):
        real_backend.llm.invoke = MagicMock(side_effect=[
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(content=json.dumps({
                "selected_agents": ["itinerary_agent"],
                "trip_constraints": {},
                "reasoning": "",
            })),
        ])
        result = real_backend.supervisor_agent(self._make_state("Plan a trip."))
        assert result["llm_calls"] == 2  # guardrail + supervisor

    def test_guardrail_blocked_agent_uses_final_response(self):
        state = {"final_response": "Blocked!", "guardrail_reason": ""}
        result = real_backend.guardrail_blocked_agent(state)
        assert result["final_response"] == "Blocked!"

    def test_guardrail_blocked_agent_fallback_message(self):
        result = real_backend.guardrail_blocked_agent({})
        assert "blocked" in result["final_response"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Configuration Tests
# ─────────────────────────────────────────────────────────────────────────────

@skip_if_no_backend
class TestDatabaseUrlConfig:
    def test_raises_when_database_url_missing(self):
        saved = os.environ.pop("DATABASE_URL", None)
        try:
            with pytest.raises(ValueError, match="DATABASE_URL"):
                real_backend.get_database_url()
        finally:
            if saved:
                os.environ["DATABASE_URL"] = saved

    def test_appends_sslmode_when_absent(self):
        os.environ["DATABASE_URL"] = "postgresql://user:pass@host/db"
        url = real_backend.get_database_url()
        assert "sslmode=require" in url

    def test_no_duplicate_sslmode(self):
        os.environ["DATABASE_URL"] = "postgresql://user:pass@host/db?sslmode=require"
        url = real_backend.get_database_url()
        assert url.count("sslmode=") == 1

    def test_uses_ampersand_when_query_string_present(self):
        os.environ["DATABASE_URL"] = "postgresql://user:pass@host/db?other=val"
        url = real_backend.get_database_url()
        assert "sslmode=require" in url
        assert "&sslmode=require" in url
