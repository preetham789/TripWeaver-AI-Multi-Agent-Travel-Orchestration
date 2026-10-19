"""
TripWeaver AI — FastAPI & Frontend Tests
=========================================
Uses a backend stub so no real DB/LLM calls are made.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Build and inject the backend stub ────────────────────────────────────────

_TRAVEL_OK = {
    "thread_id": "user_test123",
    "answer": "## Trip Summary\nTest plan",
    "requires_approval": False,
    "approval_request": "",
    "flight_results": "Test flight info",
    "hotel_results": "Test hotel info",
    "weather_results": "Test weather info",
    "budget_results": "Test budget info",
    "itinerary": "Test itinerary",
    "selected_agents": ["flight_agent", "itinerary_agent"],
    "trip_constraints": {},
    "supervisor_reasoning": "test",
    "guardrail_allowed": True,
    "guardrail_reason": "",
    "approved": None,
    "human_feedback": "",
    "llm_calls": 4,
}

_RESUME_OK = {
    "thread_id": "user_test123",
    "answer": "## Final Plan\nApproved plan",
    "requires_approval": False,
    "approval_request": "",
    "flight_results": "",
    "hotel_results": "",
    "weather_results": "",
    "budget_results": "",
    "itinerary": "",
    "selected_agents": [],
    "trip_constraints": {},
    "supervisor_reasoning": "",
    "guardrail_allowed": True,
    "guardrail_reason": "",
    "approved": True,
    "human_feedback": "",
    "llm_calls": 5,
}

stub = types.ModuleType("backend")
stub.run_travel_agent = MagicMock(return_value=_TRAVEL_OK)
stub.resume_travel_agent = MagicMock(return_value=_RESUME_OK)
sys.modules["backend"] = stub

from fastapi.testclient import TestClient  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Static & Template Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestStaticAssets:
    def test_static_script_js_exists(self):
        assert (ROOT / "static" / "script.js").is_file()

    def test_static_style_css_exists(self):
        assert (ROOT / "static" / "style.css").is_file()

    def test_template_index_html_exists(self):
        assert (ROOT / "templates" / "index.html").is_file()

    def test_index_html_has_required_ids(self):
        html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        for eid in ("userInput", "sendBtn", "resultSection", "resultBox", "errorBox"):
            assert eid in html, f"Missing id '{eid}'"

    def test_index_html_references_marked(self):
        assert "marked" in (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    def test_index_html_references_html2pdf(self):
        assert "html2pdf" in (ROOT / "templates" / "index.html").read_text(encoding="utf-8")

    def test_index_html_has_example_prompts(self):
        html = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        assert "Japan" in html or "Dubai" in html

    def test_script_js_sends_to_api_travel(self):
        assert "/api/travel" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_uses_localstorage(self):
        assert "localStorage" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_has_send_message(self):
        assert "async function sendMessage" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_has_copy_result(self):
        assert "function copyResult" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_has_download_pdf(self):
        assert "function downloadPDF" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_ctrl_enter(self):
        js = (ROOT / "static" / "script.js").read_text(encoding="utf-8")
        assert "ctrlKey" in js and "Enter" in js

    def test_script_js_set_prompt_function(self):
        assert "function setPrompt" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_set_loading_function(self):
        assert "function setLoading" in (ROOT / "static" / "script.js").read_text(encoding="utf-8")

    def test_script_js_thread_id_persisted(self):
        js = (ROOT / "static" / "script.js").read_text(encoding="utf-8")
        assert "travel_thread_id" in js


# ─────────────────────────────────────────────────────────────────────────────
# /health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self):
        assert client.get("/health").status_code == 200

    def test_status_ok(self):
        assert client.get("/health").json()["status"] == "ok"

    def test_has_message(self):
        assert "message" in client.get("/health").json()

    def test_features_supervisor_agent(self):
        assert "supervisor_agent" in client.get("/health").json()["features"]

    def test_features_input_guardrail(self):
        assert "input_guardrail" in client.get("/health").json()["features"]

    def test_features_human_in_the_loop(self):
        assert "human_in_the_loop" in client.get("/health").json()["features"]


# ─────────────────────────────────────────────────────────────────────────────
# GET /
# ─────────────────────────────────────────────────────────────────────────────

class TestHomeEndpoint:
    def test_returns_200(self):
        assert client.get("/").status_code == 200

    def test_returns_html_content_type(self):
        assert "text/html" in client.get("/").headers["content-type"]

    def test_contains_tripmate(self):
        assert "TripMate" in client.get("/").text

    def test_contains_generate_plan(self):
        assert "Generate Plan" in client.get("/").text


# ─────────────────────────────────────────────────────────────────────────────
# GET /favicon.ico
# ─────────────────────────────────────────────────────────────────────────────

class TestFaviconEndpoint:
    def test_returns_200(self):
        assert client.get("/favicon.ico").status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/travel
# ─────────────────────────────────────────────────────────────────────────────

class TestTravelEndpoint:
    def setup_method(self):
        stub.run_travel_agent.reset_mock()
        stub.run_travel_agent.return_value = _TRAVEL_OK
        stub.run_travel_agent.side_effect = None

    def test_valid_request_200(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert r.status_code == 200

    def test_valid_request_success_true(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert r.json()["success"] is True

    def test_valid_request_thread_id_present(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert "thread_id" in r.json()

    def test_valid_request_answer_present(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert "answer" in r.json()

    def test_valid_request_flight_results_present(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert "flight_results" in r.json()

    def test_valid_request_hotel_results_present(self):
        r = client.post("/api/travel", json={"message": "Plan a Tokyo trip."})
        assert "hotel_results" in r.json()

    def test_empty_message_400(self):
        r = client.post("/api/travel", json={"message": ""})
        assert r.status_code == 400

    def test_empty_message_error_contains_empty(self):
        r = client.post("/api/travel", json={"message": ""})
        assert "empty" in r.json()["error"].lower()

    def test_whitespace_message_400(self):
        r = client.post("/api/travel", json={"message": "   "})
        assert r.status_code == 400

    def test_missing_message_422(self):
        r = client.post("/api/travel", json={})
        assert r.status_code == 422

    def test_existing_thread_id_accepted(self):
        r = client.post("/api/travel", json={
            "message": "Plan a Dubai trip",
            "thread_id": "user_existing123"
        })
        assert r.status_code == 200

    def test_backend_called_with_message(self):
        client.post("/api/travel", json={"message": "Plan a Paris trip."})
        stub.run_travel_agent.assert_called_once()
        call_kwargs = stub.run_travel_agent.call_args
        assert "Plan a Paris trip." in str(call_kwargs)

    def test_backend_exception_returns_500(self):
        stub.run_travel_agent.side_effect = RuntimeError("DB down")
        r = client.post("/api/travel", json={"message": "Plan a trip."})
        assert r.status_code == 500

    def test_backend_exception_success_false(self):
        stub.run_travel_agent.side_effect = RuntimeError("DB down")
        r = client.post("/api/travel", json={"message": "Plan a trip."})
        assert r.json()["success"] is False

    def test_backend_exception_error_message_included(self):
        stub.run_travel_agent.side_effect = RuntimeError("DB down")
        r = client.post("/api/travel", json={"message": "Plan a trip."})
        assert "DB down" in r.json()["error"]

    def test_llm_calls_in_response(self):
        r = client.post("/api/travel", json={"message": "Plan a trip."})
        assert r.json()["llm_calls"] == 4

    def test_unicode_message_accepted(self):
        r = client.post("/api/travel", json={"message": "プラン 7日間の日本旅行"})
        assert r.status_code == 200

    def test_very_long_message_accepted(self):
        long_msg = "Plan a trip to Japan. " * 200
        r = client.post("/api/travel", json={"message": long_msg})
        assert r.status_code == 200

    def test_special_chars_message_accepted(self):
        r = client.post("/api/travel", json={"message": "Trip! @$200 & hotel."})
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/travel/approve
# ─────────────────────────────────────────────────────────────────────────────

class TestApproveEndpoint:
    def setup_method(self):
        stub.resume_travel_agent.reset_mock()
        stub.resume_travel_agent.return_value = _RESUME_OK
        stub.resume_travel_agent.side_effect = None

    def test_approval_true_200(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": True, "feedback": ""
        })
        assert r.status_code == 200

    def test_approval_success_true(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": True, "feedback": ""
        })
        assert r.json()["success"] is True

    def test_rejection_no_feedback_400(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": False, "feedback": ""
        })
        assert r.status_code == 400

    def test_rejection_whitespace_feedback_400(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": False, "feedback": "   "
        })
        assert r.status_code == 400

    def test_rejection_error_mentions_feedback(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": False, "feedback": ""
        })
        assert "feedback" in r.json()["error"].lower()

    def test_rejection_with_feedback_200(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123",
            "approved": False,
            "feedback": "More local food suggestions please."
        })
        assert r.status_code == 200

    def test_missing_thread_id_422(self):
        r = client.post("/api/travel/approve", json={"approved": True})
        assert r.status_code == 422

    def test_empty_thread_id_422(self):
        r = client.post("/api/travel/approve", json={
            "thread_id": "", "approved": True
        })
        assert r.status_code == 422

    def test_resume_called_with_correct_thread(self):
        client.post("/api/travel/approve", json={
            "thread_id": "user_abc", "approved": True, "feedback": ""
        })
        stub.resume_travel_agent.assert_called_once()
        call_kwargs = stub.resume_travel_agent.call_args
        assert "user_abc" in str(call_kwargs)

    def test_resume_exception_500(self):
        stub.resume_travel_agent.side_effect = RuntimeError("Resume failed")
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": True, "feedback": ""
        })
        assert r.status_code == 500

    def test_resume_exception_success_false(self):
        stub.resume_travel_agent.side_effect = RuntimeError("Resume failed")
        r = client.post("/api/travel/approve", json={
            "thread_id": "user_test123", "approved": True, "feedback": ""
        })
        assert r.json()["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class TestPydanticModels:
    def test_travel_request_valid(self):
        from app import TravelRequest
        req = TravelRequest(message="Plan a trip to Paris")
        assert req.message == "Plan a trip to Paris"
        assert req.thread_id is None

    def test_travel_request_with_thread_id(self):
        from app import TravelRequest
        req = TravelRequest(message="Plan a trip", thread_id="user_abc")
        assert req.thread_id == "user_abc"

    def test_travel_request_none_thread_id_valid(self):
        from app import TravelRequest
        req = TravelRequest(message="Plan a trip", thread_id=None)
        assert req.thread_id is None

    def test_approval_request_valid(self):
        from app import ApprovalRequest
        req = ApprovalRequest(thread_id="user_abc", approved=True)
        assert req.approved is True
        assert req.feedback == ""

    def test_approval_request_with_feedback(self):
        from app import ApprovalRequest
        req = ApprovalRequest(thread_id="t1", approved=False, feedback="More hotels")
        assert req.feedback == "More hotels"

    def test_approval_request_empty_thread_id_raises(self):
        import pydantic
        from app import ApprovalRequest
        with pytest.raises(pydantic.ValidationError):
            ApprovalRequest(thread_id="", approved=True)

    def test_approval_request_missing_approved_raises(self):
        import pydantic
        from app import ApprovalRequest
        with pytest.raises(pydantic.ValidationError):
            ApprovalRequest(thread_id="user_abc")
