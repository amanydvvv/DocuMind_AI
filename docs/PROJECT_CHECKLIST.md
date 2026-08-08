# DocuMind AI â€” Project Checklist

This is a living execution tracker structured around development phases.

## Phase 1: Foundation & Architecture [âœ… COMPLETE]
- [x] Scaffold FastAPI backend and initialize `app/main.py`
- [x] Set up environment configuration (`pydantic-settings`)
- [x] Define robust PostgreSQL async database configuration (`asyncpg`)
- [x] Resolve Docker host port conflicts (mapped to `5435`)
- [x] Separate ORM models (`app/models`) from API schemas (`app/schemas`)
- [x] Initialize Alembic migrations and create baseline

## Phase 2: Ingestion Pipeline [âœ… COMPLETE]
- [x] Implement document upload endpoint with file validation
- [x] Add SHA-256 duplicate document detection
- [x] Build background extraction worker utilizing PyMuPDF
- [x] Implement LangChain chunking algorithm (`RecursiveCharacterTextSplitter`)
- [x] Embed chunks in batches via Google Gemini API
- [x] Insert chunks and embeddings into `pgvector` store

## Phase 3: RAG Retrieval & Generation [âœ… COMPLETE]
- [x] Build `retrieve_context` service using cosine similarity (`<=>`)
- [x] Construct strict prompt template to prevent hallucination
- [x] Build LCEL LangChain orchestration (`prompt | llm`) to fetch AI answers
- [x] Wire up `POST /api/chat` with source citations
- [x] Resolve 0-row retrieval bug by migrating `ivfflat` index to `HNSW`
- [x] Implement multi-turn conversation memory (storing history in `messages` DB)
- [x] Build idempotent automated integration test suite (`tests/test_integration.py`)

## Phase 4: Frontend Development [âœ… COMPLETE]
- [x] Choose and initialize frontend framework (React/Vite) in `frontend/src`
- [x] Build global layout and navigation structure
- [x] Implement Document Upload Panel (drag-and-drop, status indicators)
- [x] Implement Document Management Dashboard (list/delete uploaded files)
- [x] Build Conversational Chat Interface (input, message bubbles)
- [x] Create interactive Citation Viewer (clicking citations highlights chunk text)
- [x] Connect frontend API client to FastAPI backend

## Phase 5: Analytics & Logging [âœ… COMPLETE]
- [x] Flesh out the `app/routers/analytics.py` endpoints (`/queries`, `/summary`, `/documents`)
- [x] Automatically log queries, latency, and average similarity to `query_logs`
- [x] Build frontend dashboard to visualize RAG performance metrics

## Phase 6: Conversation Persistence & History Navigation [âœ… COMPLETE]
- [x] Define SQLAlchemy ORM models (`Conversation` and `Message`) in `backend/app/models/conversation.py`
- [x] Verify database schema synchronization with PostgreSQL via Alembic
- [x] Un-stub CRUD endpoints (`GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`) in `backend/app/routers/conversations.py`
- [x] Update `POST /api/chat` in `backend/app/routers/chat.py` to retrieve up to 10 prior turns (`chat_history`) and pass them to the LLM
- [x] Enforce transactional integrity with `await db.flush()` for prompt IDs and single atomic `await db.commit()` after LLM response generation
- [x] Implement robust rollback handling (`await db.rollback()`) and `RateLimitError` (HTTP 429) mapping for Google API quota bounds
- [x] Create encapsulated custom hook (`frontend/src/hooks/useConversations.js`) with `AbortController` race condition defense
- [x] Build history navigation UI (`ConversationSidebar.jsx`, `ConversationItem.jsx`, tabbed `Layout.jsx`) with "+ New Chat" reset and active thread deletion fallbacks
- [x] Standardize model configuration default to `llama-3.1-8b-instant` (Groq) in `.env`

## Phase 7: Real-Time Token Streaming (SSE) [âœ… COMPLETE]
- [x] Implement `generate_answer_stream()` async generator in `backend/app/services/generation.py` using `chain.astream()`
- [x] Build `POST /api/chat/stream` endpoint in `backend/app/routers/chat.py` returning `StreamingResponse(media_type="text/event-stream")`
- [x] Enforce structured SSE event protocol (`metadata` -> `token` -> `done` / `error`)
- [x] Maintain atomic database transaction commits (`await db.commit()`) post-stream completion with clean `await db.rollback()` on exceptions
- [x] Implement `sendChatMessageStream()` in `frontend/src/services/api.js` using `ReadableStream` reader
- [x] Update `useConversations.js` hook to progressively append incoming token deltas for typewriter-style UI rendering

## Phase 8: Hybrid Search (BM25 + pgvector) with RRF & Re-Ranking [âœ… COMPLETE]
- [x] Evaluate and select PostgreSQL native Full-Text Search (`tsvector`/`tsquery` with GIN indexing) for unified zero-latency BM25 lexical keyword search
- [x] Refactor `backend/app/services/retrieval.py` into a two-stage hybrid retrieval pipeline (`_retrieve_vector_candidates`, `_retrieve_lexical_candidates`)
- [x] Implement Reciprocal Rank Fusion algorithm (`_reciprocal_rank_fusion`) with $k=60$ to merge non-comparable sparse and dense candidate ranks
- [x] Implement Stage 2 Cross-Scoring Re-Ranker (`_cross_score_rerank`)
- [x] Add GIN FTS index (`idx_chunks_fts`) to `Chunk` ORM model in `backend/app/models/__init__.py`
- [x] Add automated test cases `test_hybrid_retrieval_exact_keyword`, `test_hybrid_retrieval_semantic_match`, `test_rrf_fused_ranking` in `backend/tests/test_integration.py`
- [x] Update `docs/STUDY_GUIDE.md` with educational concepts and interview Q&A for Hybrid Search, RRF, and Re-Ranking

## Phase 9: JWT Authentication & Multi-Tenancy [âœ… COMPLETE]
- [x] Create `User` ORM model in `backend/app/models/user.py` (`id`, `email`, `hashed_password`, `created_at`)
- [x] Add `user_id` foreign key columns with `ondelete="CASCADE"` to `documents`, `conversations`, and `query_logs` tables in `backend/app/models/__init__.py`
- [x] Generate and execute Alembic migration `e5f67a890123_add_users_table_and_user_id_foreign_keys.py` against PostgreSQL
- [x] Build `backend/app/core/security.py` featuring PBKDF2-HMAC-SHA256 password hashing, RFC 7519 JWT creation/decoding, and `get_current_user` FastAPI dependency
- [x] Implement `backend/app/routers/auth.py` with `POST /api/auth/signup`, `POST /api/auth/login`, and `GET /api/auth/me` endpoints
- [x] Scope all document, conversation, and chat endpoints in `documents.py`, `conversations.py`, and `chat.py` to `current_user.id`
- [x] Update candidate vector/lexical retrieval in `backend/app/services/retrieval.py` to filter search by `Document.user_id == user_id`
- [x] Update `frontend/src/services/api.js` to manage JWT tokens in `localStorage` and inject `Authorization: Bearer <token>` into all HTTP requests
- [x] Build `frontend/src/components/AuthModal.jsx` for Login/Signup modal toggling and update `App.jsx` & `Layout.jsx` with User badge and Logout button
- [x] Build automated integration test suite `backend/tests/test_auth_multitenancy.py` (**3/3 tests passed in 18.57s**)

## Phase 10: Full-Stack Dockerization & Free Cloud Deployment Setup [âœ… COMPLETE]
- [x] Create multi-stage `frontend/Dockerfile` (Node 20 build stage + Nginx Alpine static server)
- [x] Build `frontend/nginx.conf` handling SPA client-side rewrites (`try_files $uri /index.html`) and `/api/` reverse proxying
- [x] Add `frontend` service to `docker-compose.yml` mapped to port `3000:80` depending on `api`
- [x] Create `.github/workflows/ci.yml` with `pgvector:pg16` PostgreSQL container service, running migrations, Pytest suite, and `npm run build`
- [x] Create infrastructure-as-code blueprint `render.yaml` for Render free Web Service deployment
- [x] Create `frontend/vercel.json` SPA rewrite rules for Vercel free static hosting
- [x] Document Supabase (Managed `pgvector` PostgreSQL), Render, and Vercel 100% free cloud deployment steps in `README.md`
- [x] Outline manual UptimeRobot keep-alive setup instructions (5-minute HTTP keyword check on `/api/health` to prevent Render 15-min sleep and Supabase 7-day auto-pause)

## Phase 11: Production Hardening, Gemini Vision OCR & UI Resiliency [âœ… COMPLETE]
- [x] **Supabase PgBouncer & Asyncpg Fix**: Configured session-mode pooling (direct Postgres on `5432`, session pooler on `6543`) and added `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` in `backend/app/database.py` to eliminate `DuplicatePreparedStatementError` across connection pools.
- [x] **CORS Multi-Tenant Domain Matching**: Updated `CORSMiddleware` in `backend/app/main.py` with `allow_origin_regex=r"https://docu-?mind-?ai(-[a-z0-9-]+)?\.vercel\.app"` supporting Vercel production and preview deploys with hyphens.
- [x] **Scanned PDF Vision OCR**: Integrated `qwen/qwen3.6-27b` (Groq) vision OCR fallback via `VISION_MODEL` in `backend/app/services/ingestion.py` for scanned image-based PDFs (e.g. income certificates) when text vector layer returns 0 characters.
- [x] **Client-Side Timeout & Guaranteed State Cleanup**: Added 35s `AbortController` timeout to `sendChatMessageStream` in `frontend/src/services/api.js` and wrapped `sendMessage` in `try...finally` block in `frontend/src/hooks/useConversations.js` to guarantee `isGenerating` resets to `false`, preventing UI spinner hangs.
- [x] **LLM & Vector Embedding Request Timeouts**: Configured `request_timeout=30.0` on `ChatGoogleGenerativeAI` and `GoogleGenerativeAIEmbeddings` to prevent silent backend socket stalls.
## Phase 12: Enterprise Production-Readiness Audit & Hardening [✅ COMPLETE]
- [x] **G1 DDL & Database Schema Hardening**: Added `is_active` and `is_verified` to `User` model, `ck_messages_role` check constraint, and composite index `idx_messages_conv_created` with Alembic migration `f1a2b3c4d5e6`.
- [x] **G2 Strict CORS Origin Regex**: Enforced strict origin regex `^https://docu-mind-ai(-[a-z0-9-]+)?\.vercel\.app$` and purged unrelated third-party domains.
- [x] **G3 Production Docker Deployment**: Configured auto-migration boot command (`alembic upgrade head && uvicorn`) and created `backend/.dockerignore` to block credential leaks.
- [x] **G4 Authentication Hardening**: Enforced 12-character minimum password policy, strict JWT secret validation, and token destruction on logout.
- [x] **Critical IDOR Prevention**: Secured `/api/analytics/*` endpoints with `get_current_user` dependency and `user_id` tenant scoping.
- [x] **Database Transaction Integrity**: Added explicit `await db.commit()` calls in `delete_document` and `reindex_document` routes.
- [x] **RAG & LLM Reliability**: Added `max_output_tokens=1024` LLM cap, sanitized SSE stream error responses, and added batch embedding retries with vector dimension validation.
- [x] **Frontend Hook & Auth Lifecycle**: Corrected `loadConversationList()` destructuring in `App.jsx`, wired stream cancellation signals, and replaced blocking `alert()` popups with React error banners.
- [x] **Refresh-Token Rotation Flow**: Added `POST /api/auth/refresh` with single-use JTI rotation (revoked on reuse), `refresh_token_jti` column + migration, and `refresh_token` issuance on signup/login; frontend `authedFetch` wrapper silently refreshes on 401.
- [x] **JSON-Only Login**: Removed form/multipart parsing from `/api/auth/login`; credentials accepted only as JSON via `LoginRequest` schema.
- [x] **JWT Secret Strictness**: Replaced hardcoded fallback secret with required `JWT_SECRET_KEY` setting (dev default documented, Render `sync: false` env var added); access tokens carry a `type=access` claim rejected by refresh flow.
- [x] **Account Lifecycle Enforcement**: `login` and `refresh` reject `is_active == False` accounts (403/401).
- [x] **API Rate Limiting**: Added slowapi limiter with peer-anchored keying — `CF-Connecting-IP` is trusted ONLY when the TCP peer is a private address (Render proxy); `X-Forwarded-For` is never consulted (client-spoofable) — 5/min signup, 10/min login/refresh, 10/min chat endpoints, with 429 JSON handler.
- [x] **Chat Query Efficiency & Error Hygiene**: History now uses `ORDER BY created_at DESC LIMIT 10` (was full-table load + `[-10:]`), and non-stream 500s no longer leak `str(e)` to clients (logged server-side).
- [x] **Dead Config Removal**: Removed unused `SIMILARITY_THRESHOLD` setting (never consumed by retrieval).
- [x] **Ingestion Resilience**: `request_timeout=30.0` on embeddings, tenacity exponential-backoff retry on rate-limited/transient embedding failures, and `_normalize_embedding` pad/truncate to `EMBEDDING_DIMENSION` with mismatch logging.
- [x] **CORS Allow-Origins Cleanup**: Dropped hardcoded prod origin append; `allow_origins` now reflects `CORS_ORIGINS` only, regex covers Vercel domains.
- [x] **Frontend Test Enablement**: Added `vitest` + `@testing-library/react` + `jsdom` and `npm test` script; 3/3 hook state-resiliency tests pass; production build passes; oxlint has 0 errors.

## Phase 13: GENERATIVE_MODEL Incident Hardening [CHANGE] [✅ COMPLETE]
- [x] **Model Migration**: Pinned `GENERATIVE_MODEL` to `llama-3.1-8b-instant` (Groq) across `config.py` (line 41), `render.yaml` (line 20), both `.env.example` files, `README.md`, and `docs/PRD.md`. `VISION_MODEL` pinned to `qwen/qwen3.6-27b` (Groq) in `config.py` (line 44), with `gemini-1.5-flash` as the cross-provider generation fallback (`generation.py`).
- [x] **Startup Model Validation Guard**: Added `_validate_generative_model()` in `backend/app/main.py` lifespan hook — calls Google ListModels API to confirm model exists and supports `generateContent`, then performs a lightweight `generateContent` smoke-test (4-token "Say OK") to catch models that pass metadata checks but fail on actual invocation (e.g. gemini-2.5-flash). Logs CRITICAL on failure without crashing, so `/api/health` remains reachable for ops diagnosis.
- [x] **Deprecated Parameter Fix**: Changed `request_timeout=30.0` → `timeout=30.0` in `generation.py` `ChatGoogleGenerativeAI` constructor (langchain-google-genai deprecation warning).
- [x] **Corrupted render.yaml Fix**: Removed duplicate `services:` block introduced by prior ad-hoc edits.
- [x] **Stale .env.example Cleanup**: Added `GENERATIVE_MODEL` and `JWT_SECRET_KEY` to both `.env.example` files; removed dead `SIMILARITY_THRESHOLD`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- [x] **API Key Exposure Flag**: `GOOGLE_API_KEY` was printed in plaintext to terminal logs during diagnostic session — user must rotate key in Google AI Studio and update Render env var.

### Study Notes
- **Why hardcoded Gemini model IDs are a recurring production liability**: Google deprecates and removes model generations on fixed schedules (e.g. `gemini-1.0-pro` removed Feb 2025, `gemini-2.0-flash-lite` removed June 2026, `gemini-2.5-flash` scheduled Oct 2026). A model that works today can 404 silently tomorrow with no code-level warning — the failure only surfaces when a real user sends a query.
- **Auto-updating aliases vs. pinned versions**: Aliases like `gemini-flash-latest` auto-resolve to whichever model Google currently considers "latest," which can change without notice. This means your app's behavior, quality, and even availability can shift between deployments. Pinned versions (e.g. `llama-3.1-8b-instant` or `gemini-1.5-flash`) give deterministic behavior but require manual rotation when deprecated.
- **Google's "new project" restriction pattern**: Google sometimes restricts older model generations to existing API keys/projects while removing access for newly created keys. This means `gemini-2.5-flash` may work for one developer's key but 404 for another's, creating intermittent failures that are hard to diagnose without testing against the specific key in use.
- **The correct safeguard**: Neither pinning nor aliasing alone is sufficient. A startup validation guard that performs an actual `generateContent` smoke-test against the configured model + key is the only reliable way to detect model availability issues before users hit them.
