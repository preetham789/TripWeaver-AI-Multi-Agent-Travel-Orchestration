"""
TripWeaver AI — Resilient Database Connection Manager
======================================================
Provides lazy-initialized connection handling, health checks, reconnection retry,
and seamless integration with LangGraph PostgreSQL checkpointing.
"""

import time
import psycopg
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver

from core.config import settings
from core.logging import logger

_connection = None
_checkpointer = None


def get_database_url() -> str:
    """Return the normalized PostgreSQL connection string."""
    return settings.DATABASE_URL


def get_connection(max_retries: int = 3, retry_delay: float = 1.0):
    """
    Get or create an active PostgreSQL connection with automatic reconnection.
    Lazy-initialized on first use so module imports never hang or fail.
    """
    global _connection

    if _connection is not None and not _connection.closed:
        return _connection

    db_url = get_database_url()
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Connecting to PostgreSQL checkpointer (attempt %d/%d)...", attempt, max_retries)
            _connection = psycopg.connect(
                db_url,
                autocommit=True,
                row_factory=dict_row,
            )
            logger.info("Successfully established PostgreSQL connection.")
            return _connection
        except Exception as e:
            last_err = e
            logger.warning("PostgreSQL connection attempt %d failed: %s", attempt, str(e))
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    logger.error("Failed to connect to PostgreSQL after %d attempts: %s", max_retries, str(last_err))
    raise last_err


def get_checkpointer():
    """
    Return the initialized LangGraph checkpointer.
    Uses PostgresSaver with automatic schema setup when reachable,
    falling back to MemorySaver in offline/isolated environments.
    """
    global _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    try:
        conn = get_connection(max_retries=2, retry_delay=0.5)
        saver = PostgresSaver(conn)
        saver.setup()
        _checkpointer = saver
        logger.info("PostgresSaver initialized and schema verified.")
        return _checkpointer
    except Exception as exc:
        logger.warning(
            "PostgreSQL is unavailable (%s). Falling back to resilient InMemory checkpointer.",
            str(exc),
        )
        saver = MemorySaver()
        _checkpointer = saver
        return _checkpointer


def check_db_health() -> bool:
    """Check whether PostgreSQL database is reachable and accepting queries."""
    try:
        conn = get_connection(max_retries=1)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            return result is not None
    except Exception:
        return False
