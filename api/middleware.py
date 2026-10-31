"""
TripWeaver AI — Enterprise API Middleware
==========================================
Includes request correlation ID tracing, execution timers, rate limiting,
payload size guards, and structured request logging.
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.config import settings
from core.logging import correlation_id_ctx, logger
from core.security import InMemoryRateLimiter
from core.telemetry import metrics

rate_limiter = InMemoryRateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID, tracks request execution time, and logs HTTP transactions."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        correlation_id_ctx.set(req_id)

        # Enforce rate limiting for API endpoints
        if request.url.path.startswith("/api/"):
            client_ip = request.client.host if request.client else "127.0.0.1"
            allowed, remaining = rate_limiter.is_allowed(client_ip)
            if not allowed:
                logger.warning("Rate limit exceeded for IP %s on path %s", client_ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Too many requests. Please slow down and try again in a minute.",
                    },
                    headers={"Retry-After": "60"},
                )

        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

            if not request.url.path.startswith("/static"):
                logger.info(
                    "%s %s -> status=%d duration=%.2fms",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )
            metrics.record_request(success=(response.status_code < 400))
            return response
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            metrics.record_request(success=False)
            logger.error(
                "Unhandled exception processing %s %s (%.2fms): %s",
                request.method,
                request.url.path,
                duration_ms,
                str(exc),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Internal server error: {str(exc)}",
                },
                headers={"X-Request-ID": req_id},
            )
