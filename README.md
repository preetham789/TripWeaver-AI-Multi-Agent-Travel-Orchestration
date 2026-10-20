<div align="center">

<h1>✈️ TripWeaver AI</h1>

<p><strong>A production-ready multi-agent travel planning system built with LangGraph, FastAPI, and Groq.</strong></p>

<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi&logoColor=white"></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img alt="LangGraph" src="https://img.shields.io/badge/LangGraph-1.2-1C3C3C?style=flat-square"></a>
  <a href="https://groq.com/"><img alt="Groq" src="https://img.shields.io/badge/Groq-LLM-F55036?style=flat-square"></a>
  <a href="https://www.postgresql.org/"><img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Checkpointer-336791?style=flat-square&logo=postgresql&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square"></a>
</p>

<p>
  Turn any natural-language trip request into a weather-aware, research-backed, budget-conscious itinerary — powered by a supervisor-orchestrated agent pipeline with human-in-the-loop review.
</p>

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Agent Workflow](#agent-workflow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Running the Application](#running-the-application)
  - [Local Development](#local-development)
  - [Docker](#docker)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Overview

TripWeaver AI (branded **TripMate AI** in the web interface) is a full-stack web application that orchestrates a team of specialist AI agents to plan complete trips. A single natural-language prompt — such as *"Plan a 7-day Japan trip from India under ₹2 lakh"* — triggers a supervised pipeline that researches flights, hotels, and live weather before drafting and refining a day-by-day itinerary.

Workflow state is persisted in **PostgreSQL** via LangGraph's checkpoint system, enabling multi-turn conversations across browser sessions using a stable `thread_id`.

---

## Key Features

| Feature | Description |
|---|---|
| **Supervisor agent** | Routes each request to only the specialist agents actually needed, based on the query. |
| **Input guardrail** | Rejects off-topic requests (non-travel content, harmful prompts) before any specialist work begins. |
| **Human-in-the-loop (HITL)** | The pipeline pauses after the draft itinerary is generated; the user approves or requests a revision before the final polished plan is produced. |
| **Live flight data** | Airport and airline context via the AviationStack MCP server (launched with `uvx`). |
| **Live hotel research** | Real-time accommodation search via Tavily's hosted MCP service. |
| **Live weather** | Current conditions and a 5-entry forecast via a local FastMCP server backed by OpenWeather API. |
| **Budget analysis** | Dedicated budget agent evaluates cost feasibility and surfaces money-saving suggestions. |
| **Persistent threads** | LangGraph PostgreSQL checkpointer stores workflow state; the browser saves `thread_id` in `localStorage` for session continuity. |
| **Markdown export** | Results rendered with `marked.js`; one-click copy or PDF download via `html2pdf.js`. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (HTML / CSS / JS)                 │
│    Markdown rendering · Copy · PDF export · localStorage     │
└────────────────────────┬────────────────────────────────────┘
                         │  POST /api/travel
                         │  POST /api/travel/approve
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI  (app.py)                            │
│         Pydantic validation · asyncio.to_thread             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Workflow  (backend.py)                │
│                                                             │
│  supervisor ──► flight_agent ──► hotel_agent                │
│                     │                │                      │
│              AviationStack MCP   Tavily MCP                 │
│                                   │                         │
│                         weather_agent                       │
│                              │                              │
│                         Weather MCP (local FastMCP)         │
│                              │                              │
│                         budget_agent                        │
│                              │                              │
│                       itinerary_agent                       │
│                              │                              │
│                      human_approval ◄── interrupt()         │
│                              │                              │
│                         final_agent                         │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
        PostgreSQL  (LangGraph PostgresSaver)
        Checkpoint storage · thread_id continuity
```

---

## Agent Workflow

```
Travel request
      │
      ▼
Supervisor agent
  ├─ Input guardrail  →  blocks off-topic / harmful requests
  └─ Selects agents + extracts trip constraints
      │
      ├──► Flight agent   ──► AviationStack MCP
      ├──► Hotel agent    ──► Tavily MCP
      ├──► Weather agent  ──► Local OpenWeather MCP
      └──► Budget agent   ──► LLM analysis
      │
      ▼
Itinerary agent   (integrates all specialist results)
      │
      ▼
Human approval  ◄──── interrupt() pauses graph here
  ├─ Approved  ──►  Final agent (polish & format)
  └─ Rejected  ──►  Final agent (apply feedback & revise)
      │
      ▼
  Structured Markdown response
```

Each specialist agent is only invoked when the supervisor determines it is relevant. The `itinerary_agent` is always the final specialist stage.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Web framework** | FastAPI, Uvicorn, Jinja2 |
| **Data validation** | Pydantic v2 |
| **Agent orchestration** | LangGraph 1.2, LangChain 1.3 |
| **Language model** | Groq (`openai/gpt-oss-120b` by default) via `langchain-groq` |
| **MCP integration** | `langchain-mcp-adapters`, Tavily hosted MCP, AviationStack MCP (`uvx`), local FastMCP weather server |
| **Weather data** | OpenWeather API (current + 5-entry forecast) |
| **Flight data** | AviationStack API (airports, airlines) |
| **Hotel research** | Tavily Search API |
| **State persistence** | PostgreSQL, Psycopg 3, `langgraph-checkpoint-postgres` |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript, `marked.js`, `html2pdf.js` |
| **Containerisation** | Docker (python:3.11-slim) |
| **Testing** | pytest, unittest.mock |

---

## Project Structure

```
TripWeaver-AI-Multi-Agent-Travel-Orchestration/
│
├── app.py                      # FastAPI app: routes, static files, Jinja2 setup
├── backend.py                  # LangGraph workflow: TravelState, all agents, graph compilation,
│                               #   PostgreSQL checkpointer, run/resume helpers
├── mcp_client.py               # MCP client: Tavily, AviationStack, local Weather servers;
│                               #   extract_destination() LLM helper
├── custom_weather_mcp.py       # FastMCP server: get_current_weather(), get_forecast()
│                               #   backed by OpenWeather REST API (stdio transport)
│
├── requirements.txt            # Python dependencies (pinned versions)
├── Dockerfile                  # python:3.11-slim image, port 8000
├── .env                        # API keys and DB URL (not committed)
├── .gitignore
├── .dockerignore
├── LICENSE                     # MIT
│
├── static/
│   ├── script.js               # API client, thread persistence (localStorage),
│   │                           #   Markdown rendering, copy-to-clipboard, PDF export
│   └── style.css               # Responsive dark-theme UI (Inter font, radial gradients)
│
├── templates/
│   └── index.html              # Single-page frontend: textarea, quick-prompt chips,
│                               #   result section, error box, Markdown/PDF libraries
│
└── tests/
    ├── test_api.py             # FastAPI route tests, Pydantic model tests, static asset tests
    ├── test_backend_units.py   # Backend helper, routing logic, guardrail/supervisor, DB config
    └── test_weather_and_utils.py  # Weather MCP, MCP client utils, project structure tests
```

> **Note:** The `__pycache__` directory is auto-generated and excluded from version control.

---

## Getting Started

### Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.11+** | 3.12 or 3.14 also confirmed working |
| **PostgreSQL** | Any reachable instance (local, Render, Supabase, etc.) |
| **[uv](https://docs.astral.sh/uv/)** | Required for launching the AviationStack MCP server via `uvx` |
| **Groq API key** | [console.groq.com](https://console.groq.com/) |
| **Tavily API key** | [tavily.com](https://tavily.com/) |
| **AviationStack API key** | [aviationstack.com](https://aviationstack.com/) |
| **OpenWeather API key** | [openweathermap.org](https://openweathermap.org/api) |

### Installation

```powershell
# 1. Clone the repository
git clone https://github.com/preetham789/TripWeaver-AI-Multi-Agent-Travel-Orchestration.git
cd TripWeaver-AI-Multi-Agent-Travel-Orchestration

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
# source .venv/bin/activate    # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file (see Configuration below)
```

### Configuration

Create a `.env` file in the project root:

```env
# ── Required ──────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://username:password@host:5432/database

# ── Required for specialist agents ───────────────────────────────────────────
TAVILY_API_KEY=tvly-...
AVIATIONSTACK_API_KEY=...
OPENWEATHER_API_KEY=...

# ── Optional ──────────────────────────────────────────────────────────────────
GROQ_MODEL=openai/gpt-oss-120b        # Override the default model
LANGSMITH_TRACING=true                 # Enable LangSmith tracing
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=TripWeaver-AI
```

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | ✅ Yes | Groq LLM authentication — validated at startup |
| `DATABASE_URL` | ✅ Yes | PostgreSQL connection for LangGraph checkpointing; `sslmode=require` appended automatically if absent |
| `TAVILY_API_KEY` | For hotel research | Passed to Tavily's hosted MCP endpoint |
| `AVIATIONSTACK_API_KEY` | For flight research | Passed to the AviationStack MCP subprocess |
| `OPENWEATHER_API_KEY` | For weather data | Used by `custom_weather_mcp.py` |
| `GROQ_MODEL` | No | Defaults to `openai/gpt-oss-120b` |
| `LANGSMITH_*` | No | Optional observability with LangSmith |

> ⚠️ Never commit `.env` to version control. It is already listed in `.gitignore`.

---

## Running the Application

### Local Development

```powershell
# Activate the virtual environment first
.\.venv\Scripts\Activate.ps1

# Start the development server with hot-reload
uvicorn app:app --reload
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

Health check endpoint: **[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)**

### Docker

```powershell
# Build the image
docker build -t tripweaver-ai .

# Run with your environment file
docker run --rm --env-file .env -p 8000:8000 tripweaver-ai
```

> **Note:** `uv` is not pre-installed in the Docker image. The AviationStack MCP flight research feature requires `uv` on the host `PATH`. Install it in the image or run the application outside Docker if you need flight data.

---

## API Reference

### `GET /`

Returns the single-page HTML frontend.

---

### `GET /health`

Health check. Returns `200 OK` with:

```json
{
  "status": "ok",
  "message": "TripMate AI API is running",
  "features": ["supervisor_agent", "input_guardrail", "human_in_the_loop"]
}
```

---

### `POST /api/travel`

Start a new travel planning request.

**Request body:**

```json
{
  "message": "Plan a 7-day Japan trip from India with flights, hotels, and sightseeing under ₹2 lakh.",
  "thread_id": "user_abc123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | ✅ Yes | Natural-language trip request. Blank or whitespace → `400 Bad Request`. |
| `thread_id` | string | No | Existing checkpoint thread to continue. A new `user_<uuid>` ID is generated if omitted. |

**Success response** (before human approval — `requires_approval: true`):

```json
{
  "success": true,
  "thread_id": "user_abc123",
  "answer": "## Day 1 — Arrival in Tokyo\n...",
  "requires_approval": true,
  "approval_request": "Please review the draft itinerary...",
  "flight_results": "...",
  "hotel_results": "...",
  "weather_results": "...",
  "budget_results": "...",
  "itinerary": "...",
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": { "destination": "Japan", "origin": "India", "duration": "7 days", "budget": "2 lakhs", "travel_style": "", "special_preferences": [] },
  "supervisor_reasoning": "...",
  "guardrail_allowed": true,
  "guardrail_reason": "",
  "approved": null,
  "human_feedback": "",
  "llm_calls": 6
}
```

**Error responses:**

| Status | Condition |
|---|---|
| `400` | Empty or whitespace-only message |
| `422` | Missing `message` field (Pydantic validation) |
| `500` | Internal error (DB connection failure, LLM error, etc.) |

---

### `POST /api/travel/approve`

Resume a paused workflow after human review.

**Request body:**

```json
{
  "thread_id": "user_abc123",
  "approved": true,
  "feedback": ""
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `thread_id` | string | ✅ Yes | Must be non-empty (min length 1). |
| `approved` | boolean | ✅ Yes | `true` to approve the draft; `false` to request a revision. |
| `feedback` | string | When rejecting | Required and non-whitespace when `approved` is `false`. |

**Error responses:**

| Status | Condition |
|---|---|
| `400` | `approved: false` with empty or whitespace-only `feedback` |
| `422` | Missing `thread_id` or `approved`, or empty `thread_id` |
| `500` | Thread not found, DB error, or LLM error |

---

## Testing

The test suite has **177 tests** covering all aspects of the application. No real API calls or database connections are made — all external services are mocked.

```powershell
# Install test dependencies (first time only)
pip install pytest

# Run the full test suite
# (run test_backend_units first to avoid sys.modules conflicts with the API stub)
.venv\Scripts\python.exe -m pytest tests\test_backend_units.py tests\test_weather_and_utils.py tests\test_api.py -v
```

| Test File | Tests | What it covers |
|---|---|---|
| `tests/test_backend_units.py` | 62 | Helper functions, LangGraph routing, supervisor/guardrail (mocked LLM), result serialisation, agent registry, DB config |
| `tests/test_weather_and_utils.py` | 53 | Weather MCP (API key, HTTP errors, current weather, forecast), MCP client utilities, project structure |
| `tests/test_api.py` | 62 | All FastAPI endpoints, Pydantic model validation, static asset integrity, edge cases |

**Syntax check (no network calls):**

```powershell
python -m py_compile app.py backend.py mcp_client.py custom_weather_mcp.py
```

---

## Known Limitations

- **Booking**: TripWeaver AI provides planning guidance only. It does not book flights, hotels, or any services, process payments, or guarantee availability.
- **Pricing accuracy**: AviationStack MCP returns airport and airline context but not live ticket prices. Treat all price estimates as approximate.
- **AviationStack plan**: Some AviationStack MCP tools, including airport and airline lookups, may be unavailable on the current subscription plan. Flight guidance can still be generated, but those lookups require a plan that grants access.
- **Docker & uv**: The current Dockerfile does not install `uv`. AviationStack MCP (flight research) will be unavailable when running inside the container unless `uv` is added to the image.
- **External API availability**: A failing MCP integration (Tavily, AviationStack, or OpenWeather) causes only that specialist agent to degrade gracefully — the rest of the pipeline continues.
- **Fact accuracy**: Visa requirements, opening hours, safety conditions, and prices change frequently. Always verify with official sources before travel.

---

## License

Copyright © 2026 Preetham P. Distributed under the [MIT License](LICENSE)..
