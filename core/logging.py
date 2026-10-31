"""
TripWeaver AI — Enterprise Structured Logging
==============================================
Provides high-performance, structured JSON logging with correlation IDs,
request latency tracking, and context propagation for distributed tracing.
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context variable for request correlation ID
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for log aggregators (ELK, Datadog, CloudWatch)."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
        }

        # Include custom extra attributes if present
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "levelname", "levelno", "lineno",
                "module", "msecs", "message", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info",
                "thread", "threadName"
            ):
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> logging.Logger:
    """Configures application-wide logging with optional JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplication
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    return logging.getLogger("tripweaver")


logger = setup_logging()
