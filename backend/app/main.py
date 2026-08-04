"""
DocuMind AI — FastAPI Application Entry Point
"""

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

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


import uuid
from fastapi import Request

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered technical documentation assistant with RAG",
    lifespan=lifespan,
    redirect_slashes=False,
)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# CORS
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" in origins else origins,
    allow_origin_regex=r"^https://docu-mind-ai(-[a-z0-9-]+)?\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse
from app.core.ratelimit import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429, content={"detail": "Too many requests. Please slow down and try again later."}
))
app.add_middleware(SlowAPIMiddleware)

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
    except Exception as e:
        print("DB HEALTH ERROR:", type(e), e)
        db_status = "unhealthy"

    # LLM Provider live check via embedding test
    llm_status = "unhealthy"
    if settings.GEMINI_API_KEY:
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
