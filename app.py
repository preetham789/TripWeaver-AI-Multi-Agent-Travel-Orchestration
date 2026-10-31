"""
TripMate AI — Enterprise FastAPI Application
=============================================
High-performance REST API and single-page web interface for the LangGraph
multi-agent travel orchestration system. Includes enterprise security headers,
request correlation tracing, rate limiting, and Kubernetes health probes.
"""

from pathlib import Path
import time
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend import run_travel_agent, resume_travel_agent
from core.config import settings
from core.database import check_db_health
from core.logging import logger
from core.security import SecurityHeadersMiddleware, check_prompt_injection, sanitize_input_text
from core.telemetry import metrics
from api.middleware import RequestContextMiddleware

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Enterprise Multi-Agent Travel Orchestration Engine built on LangGraph, "
        "FastAPI, Groq, PostgreSQL Checkpointing, and Model Context Protocol (MCP)."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Enterprise Middlewares ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)

# ── Static Files and Templates ───────────────────────────────────────────────
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Backward-Compatible Pydantic Schemas ─────────────────────────────────────
class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool
    feedback: str = ""


# ── Web UI Route ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ── Core Travel API ──────────────────────────────────────────────────────────
@app.post("/api/travel")
async def travel_planner(request_data: TravelRequest):
    try:
        raw_message = request_data.message.strip()

        if not raw_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty.",
                },
            )

        # Enterprise input sanitization
        user_message = sanitize_input_text(raw_message, max_chars=settings.MAX_REQUEST_SIZE_BYTES)

        start_time = time.time()
        result = await run_in_threadpool(
            run_travel_agent,
            user_input=user_message,
            thread_id=request_data.thread_id,
        )
        duration_s = round(time.time() - start_time, 2)

        return JSONResponse(
            content={
                "success": True,
                **result,
                "execution_time_seconds": duration_s,
            }
        )

    except Exception as exc:
        logger.error("Error executing travel_planner: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


@app.post("/api/travel/approve")
async def approve_travel_plan(request_data: ApprovalRequest):
    try:
        if not request_data.approved and not request_data.feedback.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Please provide revision feedback when rejecting the draft.",
                },
            )

        feedback_sanitized = sanitize_input_text(request_data.feedback, max_chars=2000)

        start_time = time.time()
        result = await run_in_threadpool(
            resume_travel_agent,
            thread_id=request_data.thread_id,
            approved=request_data.approved,
            feedback=feedback_sanitized,
        )
        duration_s = round(time.time() - start_time, 2)

        return JSONResponse(
            content={
                "success": True,
                **result,
                "execution_time_seconds": duration_s,
            }
        )

    except Exception as exc:
        logger.error("Error executing approve_travel_plan: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# ── Enterprise Observability & Health Probes ─────────────────────────────────
@app.get("/health")
async def health_check():
    """Standard liveness & capability check."""
    return {
        "status": "ok",
        "message": "TripMate AI API is running",
        "features": [
            "supervisor_agent",
            "input_guardrail",
            "human_in_the_loop",
        ],
    }


@app.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe: indicates process is responsive."""
    return {"status": "alive", "timestamp": time.time()}


@app.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe: verifies database and dependencies."""
    db_ok = check_db_health()
    status = "ready" if db_ok else "degraded"
    status_code = 200 if db_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "database_connected": db_ok,
            "groq_configured": bool(settings.GROQ_API_KEY),
            "environment": settings.ENVIRONMENT.value,
        },
    )


@app.get("/api/metrics")
async def operational_metrics():
    """Operational telemetry tracking requests, latencies, and agent runs."""
    return metrics.get_snapshot()


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
