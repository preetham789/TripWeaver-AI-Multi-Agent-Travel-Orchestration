# TripWeaver AI

> A FastAPI web app that turns travel requests into reviewable, multi-agent itineraries. LangGraph coordinates specialists, Groq generates planning guidance, MCP servers supply research, and PostgreSQL persists the human-review workflow.

The repository is called **TripWeaver AI**; the browser interface is branded **TripMate AI**.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white) ![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C) ![MIT License](https://img.shields.io/badge/License-MIT-22C55E)

## Contents

- [Overview](#overview)
- [Workflow and architecture](#workflow-and-architecture)
- [Agents and integrations](#agents-and-integrations)
- [Guardrails](#guardrails)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Install and configure](#install-and-configure)
- [Run and use the app](#run-and-use-the-app)
- [API reference](#api-reference)
- [Testing](#testing)
- [Docker](#docker)
- [Operational notes and limitations](#operational-notes-and-limitations)
- [License](#license)

## Overview

Ask for a trip in ordinary language:

```text
Plan a 7-day Japan trip from Bengaluru under ₹2 lakh with flights, hotels, sightseeing, and packing advice.
```

TripWeaver screens the request, identifies its constraints, selects the needed travel specialists, produces a day-by-day draft, and pauses for user review. The user can approve the draft or provide revision feedback. Only after that step does the graph generate its final answer.

This is a research and planning assistant, not a booking service. It does not make reservations, handle payments, or guarantee prices, availability, visa eligibility, safety, or any recommendation.

## Workflow and architecture

```text
Browser → POST /api/travel → FastAPI → LangGraph supervisor
                                          │
                         guardrail + specialist selection
                                          │
   flight → hotel → weather → budget → itinerary draft → human review pause
                                                             │
                                              POST /api/travel/approve
                                                             │
                                                        final plan
```

The supervisor can skip unnecessary specialists; `itinerary_agent` is always included. Chosen specialists run in a fixed sequence: flight, hotel, weather, budget, and itinerary.

```text
┌──────────────────────────────────────────────────────────────┐
│ Browser: Jinja2 + vanilla JavaScript                           │
│ Markdown rendering · copy · PDF export · localStorage          │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP JSON
┌─────────────────────────▼────────────────────────────────────┐
│ FastAPI (app.py)                                               │
│ GET / · GET /health · POST /api/travel · POST /api/travel/approve │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│ LangGraph (backend.py)                                         │
│ supervisor → optional specialists → itinerary → HITL → final  │
└───────┬─────────────────────┬──────────────────────┬─────────┘
        │                     │                      │
 AviationStack MCP        Tavily MCP       Local Weather FastMCP
    via uvx                (hosted)            → OpenWeather
                          │
                  PostgreSQL / PostgresSaver
                  persisted checkpoints by thread_id
```

### Human-in-the-loop lifecycle

1. `POST /api/travel` starts a LangGraph thread or uses a supplied `thread_id`.
2. `human_approval` calls LangGraph `interrupt()` after the draft itinerary is ready.
3. The API returns `requires_approval: true`, the draft, and an approval request.
4. `POST /api/travel/approve` resumes that exact thread with `approved` and optional feedback.
5. The final agent polishes an approved draft or applies the requested revision.

The browser stores its current thread ID as `travel_thread_id` in `localStorage`; PostgreSQL stores the graph checkpoint. Both must remain available for a paused workflow to resume.

When a request states a duration such as `7 days`, `one week`, or `two weeks`, the itinerary prompts require a separate section for every requested day. Explicit durations from 1 through 30 days are recognised.

## Agents and integrations

| Component | Responsibility | Dependency | What happens if it fails |
|---|---|---|---|
| Input guardrail | Allows travel-related requests and blocks clearly unrelated, harmful, or illegal ones | Groq | Fails open on model/JSON parsing errors. |
| Supervisor | Selects specialists; extracts destination, origin, duration, budget, style, preferences | Groq | Selects all specialists as a fallback. |
| Flight agent | Airport/airline context, likely routes, duration, estimates, booking advice | AviationStack MCP through `uvx` | Returns an unavailable message; workflow continues. |
| Hotel agent | Accommodation and neighbourhood research | Tavily hosted MCP | Provides clearly-labelled non-live advice. |
| Weather agent | Current conditions and forecast | Local FastMCP + OpenWeather | Provides general seasonal guidance. |
| Budget agent | Cost categories, risks, savings ideas, feasibility | Groq | An unhandled model error reaches the API. |
| Itinerary agent | Detailed draft plan | Groq | An unhandled model error reaches the API. |
| Final agent | Polishes or revises the itinerary after review | Groq | An unhandled model error reaches the API. |

The weather MCP server exposes `get_current_weather(city)` and `get_forecast(city)`. The forecast is the first five three-hour OpenWeather forecast entries, not a full multi-day forecast.

## Guardrails

Every new request first passes through an LLM-based input guardrail before the supervisor selects specialist agents. The guardrail permits travel-planning and travel-information requests, including questions about destinations, flights, accommodation, weather, budgets, visas, transport, sightseeing, food, packing, and itineraries. It blocks requests that are clearly unrelated to travel or that seek harmful or illegal instructions.

When blocked, the graph ends immediately: no specialist agent, MCP integration, itinerary, or approval step runs. The API returns `guardrail_allowed: false`, a user-facing `guardrail_reason`, an empty `selected_agents` list, and the reason as `answer`.

The guardrail is intentionally designed to fail open if the model call or strict-JSON parsing fails, so a temporary model-format problem does not make the travel planner unusable. This is a usability fallback, not a production safety boundary. Internet-facing deployments should add deterministic server-side validation, authentication, rate limiting, logging, and policy enforcement appropriate to their use case.

## Repository layout

```text
.
├── app.py                    # FastAPI app, routes, static files, templates
├── backend.py                # State, agents, LangGraph graph, Postgres persistence
├── mcp_client.py             # Tavily, AviationStack, Weather MCP client helpers
├── custom_weather_mcp.py     # Local stdio FastMCP server for OpenWeather
├── requirements.txt          # Pinned runtime dependencies
├── Dockerfile                # Python 3.11 container image
├── static/
│   ├── script.js             # API/approval UX, markdown, copy, PDF download
│   └── style.css             # Responsive visual design
├── templates/index.html      # Single-page browser UI
├── tests/
│   ├── test_api.py           # Routes, models, template/assets tests
│   ├── test_backend_units.py # Agent/routing/helper tests
│   └── test_weather_and_utils.py # Weather MCP and MCP utility tests
└── output/pdf/               # Project-report artifact
```

## Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.11+ | Supported runtime; Docker uses Python 3.11. |
| PostgreSQL | Mandatory LangGraph checkpoint store. |
| Groq API key | Mandatory at backend import/startup. |
| `uv` / `uvx` | Required only for AviationStack flight research. |
| Tavily API key | Required when hotel research runs. |
| AviationStack API key | Required when flight research runs. |
| OpenWeather API key | Required when weather research runs. |

Get keys from [Groq](https://console.groq.com/), [Tavily](https://tavily.com/), [AviationStack](https://aviationstack.com/), and [OpenWeather](https://openweathermap.org/api). Install `uv` using the [official guide](https://docs.astral.sh/uv/getting-started/installation/) if flight MCP support is needed.

## Install and configure

```powershell
git clone https://github.com/preetham789/TripWeaver-AI-Multi-Agent-Travel-Orchestration.git
cd TripWeaver-AI-Multi-Agent-Travel-Orchestration

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS/Linux, activate the environment with `source .venv/bin/activate`.

Create a `.env` file in the repository root. It is ignored by Git—never commit it.

```env
# Required at application startup
GROQ_API_KEY=gsk_your_key
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE

# Required only when their specialist is selected
TAVILY_API_KEY=tvly_your_key
AVIATION_STACK_API_KEY=your_aviationstack_key
OPENWEATHER_API_KEY=your_openweather_key

# Optional; default: openai/gpt-oss-120b
GROQ_MODEL=openai/gpt-oss-120b
```

`AVIATIONSTACK_API_KEY` is accepted for compatibility, but `AVIATION_STACK_API_KEY` is preferred. If `DATABASE_URL` has no `sslmode` parameter, the backend appends `sslmode=require`. Startup creates the LangGraph checkpoint tables through `checkpointer.setup()`.

## Run and use the app

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). FastAPI's generated API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and the lightweight health endpoint is [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

In the UI:

1. Enter a travel request or choose a sample prompt.
2. Select **Generate Draft**; the workflow card shows guardrail status, routing rationale, and selected agents.
3. Review the Markdown itinerary.
4. Select **Approve & Generate Final**, or enter concrete feedback and select **Revise Using Feedback**.
5. Copy the result or export it to PDF.

`Ctrl+Enter` submits the form. While a draft is awaiting review, the UI prevents starting a new request. Markdown rendering and PDF export use `marked.js` and `html2pdf.js` from public CDNs, so those browser features need CDN access.

## API reference

### `GET /`

Returns the single-page TripMate AI web application.

### `GET /health`

Returns a lightweight process health response; it does not test database or third-party connectivity.

```json
{
  "status": "ok",
  "message": "TripMate AI API is running",
  "features": ["supervisor_agent", "input_guardrail", "human_in_the_loop"]
}
```

### `POST /api/travel`

Starts the planning workflow, normally returning a draft awaiting approval.

```json
{
  "message": "Plan a 5-day Dubai trip from Bengaluru with hotels and sightseeing.",
  "thread_id": "user_optional_existing_thread"
}
```

| Field | Type | Required | Notes |
|---|---|---:|---|
| `message` | string | Yes | Whitespace-only input returns `400`. |
| `thread_id` | string or null | No | Omit it to create `user_<uuid>`. |

A successful response contains `success`, `thread_id`, `answer`, `requires_approval`, `approval_request`, `itinerary`, `flight_results`, `hotel_results`, `weather_results`, `budget_results`, `selected_agents`, `trip_constraints`, `supervisor_reasoning`, guardrail fields, review fields, and `llm_calls`.

For a normal draft, `requires_approval` is `true`; `answer` and `itinerary` contain the draft. A blocked request completes directly, with its explanation in `answer`.

### `POST /api/travel/approve`

Resumes a paused workflow.

```json
{
  "thread_id": "user_existing_thread",
  "approved": false,
  "feedback": "Keep the budget under ₹1.5 lakh and add vegetarian food options."
}
```

| Field | Type | Required | Notes |
|---|---|---:|---|
| `thread_id` | string | Yes | Must be non-empty. |
| `approved` | boolean | Yes | `true` polishes the plan; `false` revises it. |
| `feedback` | string | Conditional | Non-whitespace text is required when `approved` is `false`. |

It returns the same result shape as the initial endpoint, now with a final `answer` and `requires_approval: false`.

### Errors

| Status | Meaning |
|---:|---|
| `400` | Empty request or a rejected draft with no feedback. |
| `422` | Request schema validation failed. |
| `500` | An unhandled backend, persistence, MCP, or model error occurred. |

## Testing

The repository currently contains **187 tests**. They mock external services; they are not intended to make live API or database calls.

```powershell
pip install pytest

# Keep test_api.py last: it inserts a backend stub for endpoint tests.
.\.venv\Scripts\python.exe -m pytest `
  tests\test_backend_units.py `
  tests\test_weather_and_utils.py `
  tests\test_api.py -v

.\.venv\Scripts\python.exe -m py_compile `
  app.py backend.py mcp_client.py custom_weather_mcp.py
```

## Docker

```powershell
docker build -t tripweaver-ai .
docker run --rm --env-file .env -p 8000:8000 tripweaver-ai
```

The image installs Python dependencies and serves Uvicorn on port 8000, but it does **not** install `uv`/`uvx`. AviationStack flight MCP calls will therefore fail in the stock container while the rest of the workflow can continue. Install `uv` in the image before relying on flight research in Docker. The container also needs network access to PostgreSQL and all selected providers.

## Operational notes and limitations

- The backend loads `.env` and connects to PostgreSQL at import time. Missing `GROQ_API_KEY` or `DATABASE_URL` prevents startup.
- Store API keys and database credentials in environment or secret management, not in source control. Use a managed database, HTTPS, logging, rate limiting, authentication, and user isolation before exposing this app publicly.
- The default model is `openai/gpt-oss-120b`. Set `GROQ_MODEL` only to a model supported by your Groq account.
- The AviationStack client calls `list_airports` and `list_airlines`; availability depends on the MCP server and your AviationStack plan. It does not provide guaranteed live ticket pricing.
- Flight, hotel, and weather failures are designed to degrade gracefully, but all generated advice remains advisory and may be stale or incomplete.
- The model-driven guardrail intentionally fails open when it cannot parse its own result. It is not sufficient as a sole production safety control.
- The project has no booking workflow, payments, authentication, rate limits, availability guarantee, or formal user-data isolation.
- `thread_id` identifies persisted planning state. Treat it as sensitive application state and do not expose predictable IDs in a multi-user deployment.
- Verify visas, local laws, opening hours, schedules, prices, safety, and health requirements with official sources before travelling.

## License

Copyright © 2026 Preetham P. Released under the [MIT License](LICENSE).
