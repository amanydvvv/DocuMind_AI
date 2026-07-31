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
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(analytics_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check server, database, and OmniRoute connectivity."""
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

    # OmniRoute check
    omniroute_status = "unhealthy"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OMNIROUTE_BASE_URL}/api/health")
            omniroute_status = "healthy" if resp.status_code == 200 else "degraded"
    except Exception:
        omniroute_status = "unreachable"

    overall = "healthy" if db_status == "healthy" else "unhealthy"
    if omniroute_status != "healthy":
        overall = "degraded" if overall == "healthy" else overall

    return HealthResponse(
        status=overall,
        database=db_status,
        omniroute=omniroute_status,
        version=settings.APP_VERSION,
    )
