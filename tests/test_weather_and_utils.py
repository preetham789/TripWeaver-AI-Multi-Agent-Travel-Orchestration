"""
TripWeaver AI — Weather MCP & MCP Client Utility Tests
========================================================
Tests custom_weather_mcp.py and the utility functions in mcp_client.py.
No real API calls are made — all HTTP/LLM interactions are mocked.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Weather MCP Tests (custom_weather_mcp.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestWeatherMCPApiKey:
    def test_raises_when_key_missing(self):
        import custom_weather_mcp as cwm
        old = cwm.OPENWEATHER_API_KEY
        cwm.OPENWEATHER_API_KEY = None
        with pytest.raises(RuntimeError, match="OPENWEATHER_API_KEY"):
            cwm._get_api_key()
        cwm.OPENWEATHER_API_KEY = old

    def test_returns_key_when_set(self):
        import custom_weather_mcp as cwm
        old = cwm.OPENWEATHER_API_KEY
        cwm.OPENWEATHER_API_KEY = "my_test_key"
        assert cwm._get_api_key() == "my_test_key"
        cwm.OPENWEATHER_API_KEY = old

    def test_raises_on_empty_string(self):
        import custom_weather_mcp as cwm
        old = cwm.OPENWEATHER_API_KEY
        cwm.OPENWEATHER_API_KEY = ""
        with pytest.raises(RuntimeError):
            cwm._get_api_key()
        cwm.OPENWEATHER_API_KEY = old


class TestWeatherMCPRequestJson:
    @patch("custom_weather_mcp.requests.get")
    def test_success_returns_json(self, mock_get):
        import custom_weather_mcp as cwm
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"key": "val"}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = cwm._request_json("http://example.com", {"q": "test"})
        assert result == {"key": "val"}

    @patch("custom_weather_mcp.requests.get")
    def test_raises_runtime_error_on_http_error(self, mock_get):
        import requests as req_lib
        import custom_weather_mcp as cwm
        mock_resp = MagicMock()
        mock_resp.text = "Not Found"
        exc = req_lib.HTTPError("404")
        exc.response = mock_resp
        mock_resp.raise_for_status.side_effect = exc
        mock_get.return_value = mock_resp
        with pytest.raises(RuntimeError, match="OpenWeather request failed"):
            cwm._request_json("http://example.com", {})

    @patch("custom_weather_mcp.requests.get")
    def test_raises_runtime_error_on_connection_error(self, mock_get):
        import requests as req_lib
        import custom_weather_mcp as cwm
        mock_get.side_effect = req_lib.ConnectionError("No connection")
        with pytest.raises(RuntimeError, match="OpenWeather request failed"):
            cwm._request_json("http://example.com", {})

    @patch("custom_weather_mcp.requests.get")
    def test_passes_params_to_get(self, mock_get):
        import custom_weather_mcp as cwm
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        cwm._request_json("http://api.test.com", {"appid": "key", "q": "city"})
        call_kwargs = mock_get.call_args
        assert call_kwargs[1]["params"]["q"] == "city"


class TestGetCurrentWeather:
    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_returns_expected_fields(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = {
            "name": "Tokyo",
            "main": {"temp": 22.5, "feels_like": 21.0, "humidity": 65},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 3.5},
        }
        result = cwm.get_current_weather("Tokyo")
        assert result["city"] == "Tokyo"
        assert result["temperature_c"] == 22.5
        assert result["feels_like_c"] == 21.0
        assert result["humidity"] == 65
        assert result["condition"] == "clear sky"
        assert result["wind_speed"] == 3.5

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_empty_city_raises_value_error(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        with pytest.raises(ValueError, match="city cannot be empty"):
            cwm.get_current_weather("   ")

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_whitespace_city_stripped(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = {
            "name": "Paris",
            "main": {"temp": 15.0, "feels_like": 14.0, "humidity": 70},
            "weather": [{"description": "partly cloudy"}],
            "wind": {"speed": 2.0},
        }
        result = cwm.get_current_weather("  Paris  ")
        assert result["city"] == "Paris"

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_uses_metric_units(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = {
            "name": "London",
            "main": {"temp": 10.0, "feels_like": 9.0, "humidity": 80},
            "weather": [{"description": "rain"}],
            "wind": {"speed": 5.0},
        }
        cwm.get_current_weather("London")
        call_params = mock_req.call_args[0][1]
        assert call_params.get("units") == "metric"


class TestGetForecast:
    def _mock_forecast_data(self, n_entries=5):
        return {
            "city": {"name": "Paris"},
            "list": [
                {
                    "dt_txt": f"2025-06-0{i+1} 12:00:00",
                    "main": {"temp": 20.0 + i},
                    "weather": [{"description": "sunny"}],
                }
                for i in range(n_entries)
            ],
        }

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_returns_correct_structure(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = self._mock_forecast_data()
        result = cwm.get_forecast("Paris")
        assert result["city"] == "Paris"
        assert "forecast" in result
        assert len(result["forecast"]) == 5

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_forecast_entries_have_required_fields(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = self._mock_forecast_data(1)
        result = cwm.get_forecast("Paris")
        entry = result["forecast"][0]
        assert "datetime" in entry
        assert "temperature_c" in entry
        assert "condition" in entry

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_empty_city_raises(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        with pytest.raises(ValueError, match="city cannot be empty"):
            cwm.get_forecast("")

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_fewer_than_5_entries_handled(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = self._mock_forecast_data(2)
        result = cwm.get_forecast("Tiny City")
        assert len(result["forecast"]) == 2

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_caps_at_5_entries(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = self._mock_forecast_data(10)
        result = cwm.get_forecast("Big City")
        assert len(result["forecast"]) == 5

    @patch("custom_weather_mcp._request_json")
    @patch("custom_weather_mcp._get_api_key", return_value="fake_key")
    def test_uses_metric_units(self, mock_key, mock_req):
        import custom_weather_mcp as cwm
        mock_req.return_value = self._mock_forecast_data()
        cwm.get_forecast("London")
        call_params = mock_req.call_args[0][1]
        assert call_params.get("units") == "metric"


# ─────────────────────────────────────────────────────────────────────────────
# MCP Client Utility Tests (mcp_client.py)
# ─────────────────────────────────────────────────────────────────────────────

class TestMCPClientSubprocessEnv:
    def test_preserves_path_variable(self):
        import mcp_client as mc
        env = mc._subprocess_env()
        assert "PATH" in env or "Path" in env

    def test_adds_custom_key(self):
        import mcp_client as mc
        env = mc._subprocess_env(MY_KEY="abc123")
        assert env["MY_KEY"] == "abc123"

    def test_ignores_none_values(self):
        import mcp_client as mc
        env = mc._subprocess_env(NULL_KEY=None)
        assert "NULL_KEY" not in env

    def test_ignores_empty_string_values(self):
        import mcp_client as mc
        env = mc._subprocess_env(EMPTY_KEY="")
        assert "EMPTY_KEY" not in env

    def test_multiple_keys(self):
        import mcp_client as mc
        env = mc._subprocess_env(KEY1="val1", KEY2="val2")
        assert env["KEY1"] == "val1"
        assert env["KEY2"] == "val2"


class TestMCPClientRequireEnv:
    def test_raises_when_value_is_none(self):
        import mcp_client as mc
        with pytest.raises(RuntimeError, match="MISSING_KEY"):
            mc._require_env("MISSING_KEY", None)

    def test_raises_when_value_is_empty_string(self):
        import mcp_client as mc
        with pytest.raises(RuntimeError):
            mc._require_env("EMPTY_KEY", "")

    def test_returns_value_when_set(self):
        import mcp_client as mc
        result = mc._require_env("MY_KEY", "my_value")
        assert result == "my_value"

    def test_error_message_includes_key_name(self):
        import mcp_client as mc
        try:
            mc._require_env("SPECIAL_KEY", None)
        except RuntimeError as e:
            assert "SPECIAL_KEY" in str(e)


class TestExtractDestination:
    @patch("mcp_client.llm")
    def test_returns_extracted_city(self, mock_llm):
        import mcp_client as mc
        mock_llm.invoke.return_value = MagicMock(content="Tokyo")
        result = mc.extract_destination("Plan a 7-day trip to Tokyo.")
        assert result == "Tokyo"

    @patch("mcp_client.llm")
    def test_strips_whitespace(self, mock_llm):
        import mcp_client as mc
        mock_llm.invoke.return_value = MagicMock(content="  Paris  ")
        result = mc.extract_destination("Plan a trip to Paris.")
        assert result == "Paris"

    @patch("mcp_client.llm")
    def test_raises_on_empty_response(self, mock_llm):
        import mcp_client as mc
        mock_llm.invoke.return_value = MagicMock(content="")
        with pytest.raises(ValueError, match="could not be extracted"):
            mc.extract_destination("Plan a trip.")

    @patch("mcp_client.llm")
    def test_raises_on_whitespace_only_response(self, mock_llm):
        import mcp_client as mc
        mock_llm.invoke.return_value = MagicMock(content="   ")
        with pytest.raises(ValueError):
            mc.extract_destination("Plan a trip.")

    @patch("mcp_client.llm")
    def test_passes_query_to_llm(self, mock_llm):
        import mcp_client as mc
        mock_llm.invoke.return_value = MagicMock(content="Bali")
        mc.extract_destination("I want to go to Bali for 5 days.")
        call_args = mock_llm.invoke.call_args
        assert "Bali" in str(call_args)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Project Structure Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestProjectStructure:
    def test_env_file_exists(self):
        assert (ROOT / ".env").is_file()

    def test_requirements_txt_exists(self):
        assert (ROOT / "requirements.txt").is_file()

    def test_dockerfile_exists(self):
        assert (ROOT / "Dockerfile").is_file()

    def test_readme_exists(self):
        assert (ROOT / "README.md").is_file()

    def test_gitignore_exists(self):
        assert (ROOT / ".gitignore").is_file()

    def test_requirements_fastapi(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "fastapi" in reqs.lower()

    def test_requirements_langgraph(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "langgraph" in reqs.lower()

    def test_requirements_langchain_groq(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "langchain-groq" in reqs.lower()

    def test_requirements_uvicorn(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "uvicorn" in reqs.lower()

    def test_requirements_psycopg(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "psycopg" in reqs.lower()

    def test_requirements_mcp(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "mcp" in reqs.lower()

    def test_requirements_tavily(self):
        reqs = (ROOT / "requirements.txt").read_text()
        assert "tavily" in reqs.lower()

    def test_dockerfile_starts_with_from(self):
        content = (ROOT / "Dockerfile").read_text()
        assert content.strip().startswith("FROM")

    def test_dockerfile_has_requirements(self):
        assert "requirements.txt" in (ROOT / "Dockerfile").read_text()

    def test_dockerfile_pip_install(self):
        assert "pip install" in (ROOT / "Dockerfile").read_text()

    def test_dockerfile_has_port_8000(self):
        assert "8000" in (ROOT / "Dockerfile").read_text()

    def test_readme_contains_api_section(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "API" in readme or "api" in readme

    def test_readme_contains_env_vars(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "GROQ_API_KEY" in readme

    def test_custom_weather_mcp_exists(self):
        assert (ROOT / "custom_weather_mcp.py").is_file()

    def test_mcp_client_exists(self):
        assert (ROOT / "mcp_client.py").is_file()
