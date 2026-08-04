"""
DocuMind AI — Configuration
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import secrets
import tempfile
from pathlib import Path

from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://documind:documind_dev@localhost:5435/documind"
    DATABASE_URL_SYNC: str = "postgresql://documind:documind_dev@localhost:5435/documind"
    
    @field_validator("DATABASE_URL")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # LLM & Embeddings
    GEMINI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    GENERATIVE_MODEL: str = "llama-3.1-8b-instant"

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5

    # Environment: "development" auto-generates a JWT secret; anything else
    # (default "production") requires JWT_SECRET_KEY to be explicitly set.
    ENVIRONMENT: str = "production"

    # Auth
    JWT_SECRET_KEY: str | None = None

    # Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "md"]
    # Single source of truth for the upload directory. OS-native temp dir
    # (survives non-root containers on Render and varies safely by platform).
    UPLOAD_DIR: str = str(Path(tempfile.gettempdir()) / "documind_uploads")

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://docu-mind-ai-git-main-docmind2.vercel.app"
    ]

    @model_validator(mode="after")
    def enforce_jwt_secret(self) -> "Settings":
        # Never fall back to a fixed, predictable secret. In production (any
        # non-development environment) an unset JWT_SECRET_KEY is a hard startup
        # error so the app fails loudly instead of silently signing tokens with
        # an insecure default. Only explicit ENVIRONMENT=development may
        # auto-generate a random secret for local convenience.
        if not self.JWT_SECRET_KEY:
            if self.ENVIRONMENT.lower() == "development":
                self.JWT_SECRET_KEY = secrets.token_hex(32)
            else:
                raise ValueError(
                    "JWT_SECRET_KEY must be set. Export a random value (e.g. "
                    "`python -c \"import secrets; print(secrets.token_hex(32))\"`) "
                    "or set ENVIRONMENT=development to auto-generate one for local dev."
                )
        return self

    @model_validator(mode="after")
    def backfill_gemini_key(self) -> "Settings":
        # Accept legacy GOOGLE_API_KEY as the Gemini key when GEMINI_API_KEY
        # is absent, so one, both, or neither can be supplied without crashing.
        if not self.GEMINI_API_KEY and self.GOOGLE_API_KEY:
            self.GEMINI_API_KEY = self.GOOGLE_API_KEY
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # Ignore unknown/legacy env vars instead of crashing startup.
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
