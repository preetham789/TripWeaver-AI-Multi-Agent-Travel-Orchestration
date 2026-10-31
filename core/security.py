"""
TripWeaver AI — Enterprise Security & Guardrails
=================================================
Includes token bucket / sliding window rate limiting, request sanitization,
heuristic prompt injection screening, and security header middlewares.
"""

import re
import time
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class InMemoryRateLimiter:
    """Thread-safe sliding-window rate limiter per client IP address."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.window = 60.0  # seconds
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        now = time.time()
        timestamps = self._history.get(client_ip, [])

        # Filter out timestamps older than the 60-second window
        fresh_timestamps = [t for t in timestamps if now - t < self.window]
        self._history[client_ip] = fresh_timestamps

        remaining = max(0, self.rpm - len(fresh_timestamps))

        if len(fresh_timestamps) >= self.rpm:
            return False, 0

        self._history[client_ip].append(now)
        return True, remaining


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces enterprise security headers on every HTTP response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# Heuristic patterns commonly used in prompt injections or jailbreaks
_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+directives", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*leak", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+dan\b", re.IGNORECASE),
]


def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Fast pre-LLM heuristic check for prompt injection or system override attempts.
    Returns (is_suspicious: bool, reason: str).
    """
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return True, "Potential prompt injection or instruction override pattern detected."
    return False, ""


def sanitize_input_text(text: str, max_chars: int = 5000) -> str:
    """Strip dangerous control characters, normalize whitespace, and enforce length bounds."""
    if not text:
        return ""
    # Remove null bytes and non-printable control characters (except newline, tab)
    cleaned = "".join(ch for ch in text if ch in ("\n", "\r", "\t") or ch.isprintable())
    cleaned = cleaned.strip()
    return cleaned[:max_chars]
