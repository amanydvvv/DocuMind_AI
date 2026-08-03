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

import logging

logger = logging.getLogger(__name__)


async def _validate_generative_model():
    """
    Startup guard: confirm GENERATIVE_MODEL actually exists, supports
    generateContent, and responds to a real (minimal) generation call.

    Google's model metadata can claim generateContent support even when the
    model 404s on actual invocation for newer API keys (e.g. gemini-2.5-flash).
    A lightweight smoke-test catches that case.

    Logs CRITICAL on failure (does not crash) so the health-check can still
    respond and ops can diagnose remotely.
    """
    model_name = settings.GENERATIVE_MODEL
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        logger.warning("GOOGLE_API_KEY is not set — skipping model validation.")
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Check model exists and declares generateContent support
            meta_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}?key={api_key}"
            resp = await client.get(meta_url)
            if resp.status_code == 404:
                logger.critical(
                    f"GENERATIVE_MODEL '{model_name}' returned HTTP 404 from Google API. "
                    f"This model does not exist or is no longer available. "
                    f"Chat will fail until this is fixed. "
                    f"Run: curl 'https://generativelanguage.googleapis.com/v1beta/models?key=<KEY>' "
                    f"to list valid models."
                )
                return
            data = resp.json()
            supported = data.get("supportedGenerationMethods", [])
            if "generateContent" not in supported:
                logger.critical(
                    f"GENERATIVE_MODEL '{model_name}' exists but does NOT support "
                    f"'generateContent'. Supported methods: {supported}. "
                    f"Chat generation will fail."
                )
                return

            # Step 2: Smoke-test a real generateContent call (minimal tokens)
            gen_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            smoke_payload = {
                "contents": [{"parts": [{"text": "Say OK"}]}],
                "generationConfig": {"maxOutputTokens": 4},
            }
            gen_resp = await client.post(gen_url, json=smoke_payload)
            if gen_resp.status_code != 200:
                body = gen_resp.text[:200]
                logger.critical(
                    f"GENERATIVE_MODEL '{model_name}' metadata says generateContent "
                    f"is supported, but actual call returned HTTP {gen_resp.status_code}: "
                    f"{body}. Chat will fail for users."
                )
                return

            logger.info(
                f"Model validation passed: '{model_name}' supports generateContent "
                f"(metadata + smoke-test OK)."
            )
    except Exception as e:
        logger.warning(f"Model validation check failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    # Startup
    await init_db()
    await _validate_generative_model()
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
