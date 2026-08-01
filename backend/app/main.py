"""
DocuMind AI — FastAPI Application Entry Point
"""

import httpx
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, close_db
from app.schemas import HealthResponse
from app.routers import (
    documents_router,
    chat_router,
    conversations_router,
    analytics_router,
    auth_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered technical documentation assistant with RAG",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(analytics_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check server, database, and LLM provider connectivity."""
    from sqlalchemy import text
    from app.database import async_session

    # Database check
    db_status = "unhealthy"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # LLM Provider live check via embedding test
    llm_status = "unhealthy"
    if settings.GOOGLE_API_KEY:
        try:
            import asyncio
            from app.services.retrieval import embeddings
            await asyncio.wait_for(embeddings.aembed_query("healthcheck"), timeout=4.0)
            llm_status = "healthy"
        except Exception:
            llm_status = "unreachable"

    overall = "healthy" if db_status == "healthy" else "unhealthy"
    if llm_status != "healthy":
        overall = "degraded" if overall == "healthy" else overall

    return HealthResponse(
        status=overall,
        database=db_status,
        llm_provider=llm_status,
        version=settings.APP_VERSION,
    )
