"""
DocuMind AI — Configuration
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://documind:documind_dev@localhost:5435/documind"
    DATABASE_URL_SYNC: str = "postgresql://documind:documind_dev@localhost:5435/documind"

    # LLM & Embeddings
    GOOGLE_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    GENERATIVE_MODEL: str = "gemini-3.6-flash"

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 200
    TOP_K: int = 5

    # Auth
    JWT_SECRET_KEY: str = "documind-dev-insecure-secret-do-not-use-in-prod"

    # Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list[str] = ["pdf", "md"]
    UPLOAD_DIR: str = "./uploads"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
