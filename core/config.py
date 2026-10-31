"""
TripWeaver AI — Enterprise Configuration
=========================================
Centralized, validated, type-safe settings powered by Pydantic v2 Settings.
Supports development, staging, and production profiles with secrets masking.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application Environment ───────────────────────────────────────────────
    APP_NAME: str = "TripMate AI"
    APP_VERSION: str = "2.1.0"
    ENVIRONMENT: EnvironmentType = EnvironmentType.PRODUCTION
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Security & CORS ───────────────────────────────────────────────────────
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    MAX_REQUEST_SIZE_BYTES: int = 1_048_576  # 1MB
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Database Configuration ────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/tripweaver",
        description="PostgreSQL connection string with checkpointer tables",
    )
    DB_POOL_MIN_SIZE: int = 1
    DB_POOL_MAX_SIZE: int = 10
    DB_POOL_TIMEOUT_SECONDS: float = 30.0

    @field_validator("DATABASE_URL")
    @classmethod
    def ensure_sslmode(cls, v: str) -> str:
        """Ensure sslmode=require for remote cloud databases unless localhost."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty.")
        if "localhost" not in v and "127.0.0.1" not in v and "sslmode=" not in v:
            separator = "&" if "?" in v else "?"
            return f"{v}{separator}sslmode=require"
        return v

    # ── Groq LLM Configuration ───────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = Field(default=None, description="Groq API key")
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="High-throughput primary model (12k TPM free-tier limit)",
    )
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 4
    LLM_REQUEST_TIMEOUT: float = 60.0

    # ── MCP External Tool Credentials ─────────────────────────────────────────
    TAVILY_API_KEY: Optional[str] = None
    AVIATIONSTACK_API_KEY: Optional[str] = None
    AVIATION_STACK_API_KEY: Optional[str] = None
    DEFAULT_ORIGIN_IATA: str = "IND"
    OPENWEATHER_API_KEY: Optional[str] = None

    # ── Observability & LangSmith ─────────────────────────────────────────────
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com/"
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "TripWeaver-AI"

    def get_aviation_key(self) -> Optional[str]:
        return self.AVIATIONSTACK_API_KEY or self.AVIATION_STACK_API_KEY


settings = Settings()
