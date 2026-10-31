# TripWeaver AI — Enterprise Multi-Agent Travel Orchestration

> **Production Enterprise Edition (v2.1.0)**  
> High-performance, resilient, multi-agent travel orchestration engine built on **LangGraph 1.2**, **FastAPI**, **Groq**, **PostgreSQL State Checkpointing**, and the **Model Context Protocol (MCP)** with Human-in-the-Loop governance.

The repository is called **TripWeaver AI**; the web UI is branded **TripMate AI**.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI 0.136](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph 1.2](https://img.shields.io/badge/LangGraph-1.2-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![Docker Multi-Stage](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?logo=docker&logoColor=white)](Dockerfile)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/Tests-208%20Passed-22C55E?logo=pytest&logoColor=white)](tests/)
[![License MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Table of Contents

- [Enterprise Highlights](#enterprise-highlights)
- [System Architecture](#system-architecture)
- [Agent Pipeline & Governance](#agent-pipeline--governance)
- [Security & Guardrails](#security--guardrails)
- [Observability & Telemetry](#observability--telemetry)
- [Project Structure](#project-structure)
- [Prerequisites & Environment](#prerequisites--environment)
- [Local Quickstart](#local-quickstart)
- [Docker & Container Orchestration](#docker--container-orchestration)
- [API Reference](#api-reference)
- [Automated Testing Suite](#automated-testing-suite)
- [CI/CD Pipeline](#cicd-pipeline)
- [Operational Notes & Disclaimers](#operational-notes--disclaimers)
- [License](#license)

---

## Enterprise Highlights

| Dimension | Enterprise Capability |
|---|---|
| **Orchestration Engine** | Stateful, resumable directed acyclic graph (DAG) powered by **LangGraph 1.2** with dynamic supervisor routing. |
| **High Availability State** | **PostgreSQL** persistence via `PostgresSaver` with automatic connection recovery and offline in-memory fallback. |
| **Human-in-the-Loop (HITL)** | Built-in `interrupt()` governance with interactive frontend draft review, revision feedback, and approval dispatching. |
| **Tool Integration (MCP)** | Decoupled Model Context Protocol clients for AviationStack (flights via `uvx`), Tavily (hotels), and FastMCP (weather). |
| **Security Hardening** | Sliding-window IP rate limiter, OWASP security headers (HSTS, CSP, nosniff, DENY), heuristic prompt-injection guardrails, and request sanitization. |
| **Observability** | Correlation IDs (`X-Request-ID`), process timing headers (`X-Process-Time-Ms`), structured logging, operational telemetry (`/api/metrics`), and Kubernetes probes (`/health/live`, `/health/ready`). |
| **Container Hardening** | Non-root container (`appuser`, UID 10001), multi-stage Docker build, embedded `uv` toolchain, Docker Compose stack (`app`, `postgres:16`, `redis:7`). |
| **Quality Assurance** | Comprehensive test coverage across **208 automated tests** passing in ~5 seconds. |

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Web Browser / Client UI                         │
│   Single-page app · Interactive HITL Approval Drawer · PDF Export     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST (X-Request-ID)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Enterprise FastAPI Gateway (app.py)                  │
│  Rate Limiting · Security Headers · Pydantic v2 · CORS · Telemetry     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Threadpool Dispatch
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              LangGraph Multi-Agent Engine (backend.py)                 │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │   Supervisor Agent: Heuristic Guardrail + Specialist Routing   │   │
│   └──────┬───────────────┬───────────────┬───────────────┬─────────┘   │
│          │               │               │               │             │
│          ▼               ▼               ▼               ▼             │
│     Flight Agent    Hotel Agent    Weather Agent   Budget Agent        │
│          │               │               │               │             │
│          │ (uvx stdio)   │ (HTTP)        │ (FastMCP)     │ (Groq LLM)  │
│          ▼               ▼               ▼               ▼             │
│    AviationStack      Tavily       OpenWeather     Cost Analysis       │
│          │               │               │               │             │
│          └───────────────┴───────┬───────┴───────────────┘             │
│                                  │                                     │
│                                  ▼                                     │
│                      Itinerary Synthesis Agent                         │
│                                  │                                     │
│                                  ▼                                     │
│                  Human-in-the-Loop Review (interrupt)                  │
│                                  │                                     │
│                                  ▼                                     │
│                      Final Polish & Delivery                           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
        PostgreSQL State Store (PostgresSaver / MemorySaver Fallback)
```

---

## Agent Pipeline & Governance

1. **Supervisor Agent**:
   - Evaluates incoming travel requests against safety and relevance guardrails.
   - Extracts trip parameters: destination, origin, duration, budget constraints, travel style.
   - Selects which specialist agents to activate, bypassing unnecessary tools.
2. **Flight Specialist**: Queries airport coordinates and carrier networks via the AviationStack MCP subprocess.
3. **Hotel Specialist**: Discovers top-rated accommodations and neighborhood recommendations via Tavily MCP.
4. **Weather Specialist**: Connects to the local FastMCP server to retrieve current metrics and 5-entry forecasts via OpenWeather.
5. **Budget Specialist**: Performs cost viability assessments, identifies budget risks, and suggests practical savings.
6. **Itinerary Synthesis Agent**: Collates all specialist findings into a unified, day-by-day itinerary draft.
7. **Human Approval Gateway**: Halts graph execution using LangGraph's `interrupt()`, awaiting client approval or revision feedback.
8. **Final Agent**:
   - If approved: Formats and polishes the draft into a presentation-ready travel plan.
   - If revision requested: Re-synthesizes the itinerary incorporating explicit user feedback.

---

## Security & Guardrails

- **Prompt Injection Defense**: Pre-LLM heuristic scanning detects instruction override attempts and system prompt extraction patterns.
- **Input Sanitization**: Control characters, null bytes, and non-printable sequences are stripped; inputs exceeding length bounds are truncated safely.
- **Sliding-Window Rate Limiter**: Per-IP request throttling shields external LLM and tool APIs from denial-of-service or quota exhaustion.
- **Security Headers**: Standard OWASP protection headers enforced across all responses (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`).
- **CORS Protection**: Configurable allowed origins preventing unauthorized cross-origin browser requests in production.

---

## Observability & Telemetry

Enterprise telemetry endpoints and headers ensure end-to-end visibility:

- `X-Request-ID`: Correlation ID attached to every request and carried into application logs and LangSmith traces.
- `X-Process-Time-Ms`: High-resolution server processing duration header.
- `GET /health/live`: Kubernetes liveness probe (validates that the event loop is responsive).
- `GET /health/ready`: Kubernetes readiness probe (verifies database connectivity and API key readiness).
- `GET /api/metrics`: Live telemetry tracking request counts, error rates, agent invocations, and average agent execution latencies.

---

## Project Structure

```text
TripWeaver-AI-Multi-Agent-Travel-Orchestration/
│
├── core/                           # Enterprise Foundation
│   ├── config.py                   # Type-safe Pydantic BaseSettings & secrets handling
│   ├── database.py                 # Resilient PostgreSQL pool & checkpointer manager
│   ├── logging.py                  # Structured JSON logging & correlation ID context
│   ├── security.py                 # Rate limiting, input sanitizer & prompt guards
│   └── telemetry.py                # Operational metrics registry & timing tracker
│
├── api/                            # API Gateway Layer
│   ├── middleware.py               # RequestID, Timing, Rate Limiting & Security Middlewares
│   └── schemas.py                  # Pydantic v2 schemas for requests, responses & health
│
├── graph/                          # LangGraph Architecture
│   ├── state.py                    # TravelState TypedDict & constraints helpers
│   └── routing.py                  # Agent registry & conditional edge routers
│
├── app.py                          # FastAPI production server & route handlers
├── backend.py                      # Multi-agent orchestrator & backward-compatible facade
├── mcp_client.py                   # MCP client adapters (AviationStack, Tavily, Weather)
├── custom_weather_mcp.py           # FastMCP stdio server for OpenWeather API
│
├── static/                         # Frontend Static Assets
│   ├── script.js                   # Client UI logic, HITL approval handling, PDF export
│   └── style.css                   # Dark-themed responsive design & layout
├── templates/
│   └── index.html                  # Single-page UI with approval drawer & action chips
│
├── Dockerfile                      # Production multi-stage Docker build (non-root appuser)
├── docker-compose.yml              # Multi-container stack (App + PostgreSQL + Redis)
├── requirements.txt                # Pinned production Python dependencies
├── .github/workflows/ci.yml        # GitHub Actions automated test & build pipeline
│
└── tests/                          # Automated Pytest Suite (208 tests)
    ├── test_backend_units.py       # Core backend logic, routing & agent tests (70 tests)
    ├── test_weather_and_utils.py   # MCP tools & configuration tests (52 tests)
    ├── test_api.py                 # FastAPI endpoints & Pydantic validation (68 tests)
    └── test_enterprise.py          # Security, telemetry, config & probes (18 tests)
```

---

## Prerequisites & Environment

- **Python**: 3.11, 3.12, or 3.14
- **PostgreSQL**: Version 14+ (Local, Render, Supabase, Neon, or Docker)
- **UV Toolchain**: Required for AviationStack MCP (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **API Keys**:
  - `GROQ_API_KEY`: Fast LLM inference ([console.groq.com](https://console.groq.com))
  - `TAVILY_API_KEY`: Real-time web search for hotels ([tavily.com](https://tavily.com))
  - `AVIATIONSTACK_API_KEY`: Real-time aviation intelligence ([aviationstack.com](https://aviationstack.com))
  - `OPENWEATHER_API_KEY`: Weather forecasts ([openweathermap.org](https://openweathermap.org))

Create a `.env` file in the project root:

```env
# ── Core Database & LLM ───────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# ── External MCP Tool Providers ──────────────────────────────────────────────
TAVILY_API_KEY=tvly-...
AVIATIONSTACK_API_KEY=...
OPENWEATHER_API_KEY=...
DEFAULT_ORIGIN_IATA=IND

# ── Enterprise Configuration (Optional) ──────────────────────────────────────
ENVIRONMENT=production
RATE_LIMIT_PER_MINUTE=60
LANGSMITH_TRACING=false
```

---

## Local Quickstart

```powershell
# 1. Clone repository
git clone https://github.com/preetham789/TripWeaver-AI-Multi-Agent-Travel-Orchestration.git
cd TripWeaver-AI-Multi-Agent-Travel-Orchestration

# 2. Set up virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Windows PowerShell
# source .venv/bin/activate     # On macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start production Uvicorn server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000** to access the UI, or **http://localhost:8000/docs** for OpenAPI Swagger documentation.

---

## Docker & Container Orchestration

### Using Docker Compose (Recommended)

Starts the application, a persistent PostgreSQL database, and a Redis instance with integrated healthchecks:

```bash
docker compose up -d
```

Check service status:
```bash
docker compose ps
```

### Standalone Docker Image

```bash
# Build production multi-stage image
docker build -t tripweaver-ai:latest .

# Run container with environment configuration
docker run -d --name tripweaver \
  -p 8000:8000 \
  --env-file .env \
  tripweaver-ai:latest
```

---

## API Reference

### 1. Initiate Travel Planning
`POST /api/travel`

**Request:**
```json
{
  "message": "Plan a 7-day trip to Tokyo under $2500 with flights and hotels.",
  "thread_id": "optional-uuid"
}
```

**Response (Draft Ready for Human Review):**
```json
{
  "success": true,
  "thread_id": "user_4a1b8c2d",
  "answer": "## 7-Day Tokyo Itinerary (Draft)...",
  "requires_approval": true,
  "approval_request": "Please review the draft itinerary...",
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {
    "destination": "Tokyo",
    "duration": "7 days",
    "budget": "$2500"
  },
  "flight_results": "...",
  "hotel_results": "...",
  "weather_results": "...",
  "budget_results": "...",
  "itinerary": "...",
  "llm_calls": 6,
  "execution_time_seconds": 8.42
}
```

### 2. Submit Human Approval / Revision
`POST /api/travel/approve`

**Approve Draft:**
```json
{
  "thread_id": "user_4a1b8c2d",
  "approved": true,
  "feedback": ""
}
```

**Request Revision:**
```json
{
  "thread_id": "user_4a1b8c2d",
  "approved": false,
  "feedback": "Swap day 4 museum visit for a day trip to Mount Fuji and look for budget hostels."
}
```

### 3. Kubernetes Probes & Telemetry

- `GET /health`: Standard capability & service liveness summary.
- `GET /health/live`: Lightweight probe for container restart decisions.
- `GET /health/ready`: Dependency check verifying PostgreSQL and credentials.
- `GET /api/metrics`: Real-time operational metrics and latency tracking.

---

## Automated Testing Suite

The project includes **208 automated tests** covering backend units, MCP utilities, FastAPI endpoints, rate limiting, security guards, and telemetry:

```powershell
# Run the complete test suite
pytest tests/test_backend_units.py tests/test_weather_and_utils.py tests/test_api.py tests/test_enterprise.py -v
```

| Test Module | Tests | Scope |
|---|---|---|
| `tests/test_backend_units.py` | 70 | Context truncation, JSON extraction, routing rules, supervisor logic, state serialization. |
| `tests/test_weather_and_utils.py` | 52 | FastMCP weather queries, destination parsing, environment isolation, Dockerfile compliance. |
| `tests/test_api.py` | 68 | FastAPI routes, Pydantic v2 schemas, HITL approve/revise flows, static asset validation. |
| `tests/test_enterprise.py` | 18 | BaseSettings, rate limiter, prompt injection screening, telemetry, and health probes. |
| **Total** | **208** | **100% Passing (~5.3 seconds)** |

---

## CI/CD Pipeline

The `.github/workflows/ci.yml` pipeline runs on every push and pull request:
1. **Multi-Version Matrix**: Tests against Python 3.11 and 3.12.
2. **PostgreSQL Service Container**: Spins up a test database instance with automated readiness check.
3. **Syntax Verification**: Runs bytecode compiler check across all modules.
4. **Full Test Execution**: Runs all 208 unit and integration tests.
5. **Docker Build Check**: Verifies multi-stage container build and non-root user setup.

---

## Operational Notes & Disclaimers

1. **Advisory Tool**: TripWeaver AI generates informational travel recommendations. It does not complete bookings, process payments, or guarantee fares, hotel availability, or visa requirements.
2. **Aviation Data**: Live ticket fares are subject to real-time market fluctuations; price estimates provided by the agents should be verified directly with airlines.
3. **Weather Forecasts**: Meteorological data is sourced from OpenWeather API; forecasts are limited to the provider's active prediction window.

---

## License

Distributed under the [MIT License](LICENSE). Copyright © 2026 Preetham P.
