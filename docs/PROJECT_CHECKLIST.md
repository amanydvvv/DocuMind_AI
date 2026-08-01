# DocuMind AI — Project Checklist

This is a living execution tracker structured around development phases.

## Phase 1: Foundation & Architecture [✅ COMPLETE]
- [x] Scaffold FastAPI backend and initialize `app/main.py`
- [x] Set up environment configuration (`pydantic-settings`)
- [x] Define robust PostgreSQL async database configuration (`asyncpg`)
- [x] Resolve Docker host port conflicts (mapped to `5435`)
- [x] Separate ORM models (`app/models`) from API schemas (`app/schemas`)
- [x] Initialize Alembic migrations and create baseline

## Phase 2: Ingestion Pipeline [✅ COMPLETE]
- [x] Implement document upload endpoint with file validation
- [x] Add SHA-256 duplicate document detection
- [x] Build background extraction worker utilizing PyMuPDF
- [x] Implement LangChain chunking algorithm (`RecursiveCharacterTextSplitter`)
- [x] Embed chunks in batches via Google Gemini API
- [x] Insert chunks and embeddings into `pgvector` store

## Phase 3: RAG Retrieval & Generation [✅ COMPLETE]
- [x] Build `retrieve_context` service using cosine similarity (`<=>`)
- [x] Construct strict prompt template to prevent hallucination
- [x] Build LCEL LangChain orchestration (`prompt | llm`) to fetch AI answers
- [x] Wire up `POST /api/chat` with source citations
- [x] Resolve 0-row retrieval bug by migrating `ivfflat` index to `HNSW`
- [x] Implement multi-turn conversation memory (storing history in `messages` DB)
- [x] Build idempotent automated integration test suite (`tests/test_integration.py`)

## Phase 4: Frontend Development [🟢 COMPLETE]

### Phase 4 Implementation Plan
- **Framework:** React + Vite (Best fit for SPA client-state architecture, decoupling from the FastAPI backend)
- **Styling:** Tailwind CSS (Rapid iteration, dynamic design, industry standard)
- **Component Architecture:**
  - `DocumentSidebar` -> `UploadPanel` (calls `POST /api/documents/upload`, `GET /api/documents`)
  - `ChatInterface` -> `MessageBubble`, `ChatInput` (calls `POST /api/chat`)
  - `CitationViewer` (interactive source chunk display)
- **State Management:** Local React State (`useState`) + lightweight Context (`ChatContext`) for prop-drilling prevention.
- **Folder Structure:** Organized by feature domain (`src/components/chat`, `src/components/documents`, `src/components/shared`).
- **Build Order:** 1) Scaffolding -> 2) Upload/Sidebar -> 3) Chat Interface -> 4) Citation Viewer.

- [x] Choose and initialize frontend framework (React/Vite or Next.js) in `frontend/src`
- [x] Build global layout and navigation structure
- [x] Implement Document Upload Panel (drag-and-drop, status indicators)
- [x] Implement Document Management Dashboard (list/delete uploaded files)
- [x] Build Conversational Chat Interface (input, message bubbles)
- [x] Create interactive Citation Viewer (clicking citations highlights chunk text)
- [x] Connect frontend API client to FastAPI backend

### Open Questions & Architecture Notes
- **Conversation History:** Conversation history will be managed strictly client-side during Phase 4 implementation to allow rapid UI iteration. Backend conversation persistence (un-stubbing `app/routers/conversations.py`) is deferred.
- **OmniRoute Cleanup:** OmniRoute proxy logic was fully removed across `config.py`, `main.py`, `ingestion.py`, `retrieval.py`, and `generation.py`. The application now connects directly to the Google Gemini API with a live embedding health check, eliminating dormant code paths.

## Phase 5: Analytics & Logging [🟢 COMPLETE]
- [x] Flesh out the `app/routers/analytics.py` endpoints (`/queries`, `/summary`, `/documents`)
- [x] Automatically log queries, latency, and average similarity to `query_logs`
- [x] Build basic frontend dashboard to visualize RAG performance metrics

## Phase 6: Conversation Persistence & History Navigation [🟢 COMPLETE]
- [x] Define SQLAlchemy ORM models (`Conversation` and `Message`) in `backend/app/models/conversation.py`
- [x] Verify database schema synchronization with PostgreSQL via Alembic
- [x] Un-stub CRUD endpoints (`GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`) in `backend/app/routers/conversations.py`
- [x] Update `POST /api/chat` in `backend/app/routers/chat.py` to retrieve up to 10 prior turns (`chat_history`) and pass them to the LLM
- [x] Enforce transactional integrity with `await db.flush()` for prompt IDs and single atomic `await db.commit()` after LLM response generation
- [x] Implement robust rollback handling (`await db.rollback()`) and `RateLimitError` (HTTP 429) mapping for Google API quota bounds
- [x] Create encapsulated custom hook (`frontend/src/hooks/useConversations.js`) with `AbortController` race condition defense
- [x] Build history navigation UI (`ConversationSidebar.jsx`, `ConversationItem.jsx`, tabbed `Layout.jsx`) with "+ New Chat" reset and active thread deletion fallbacks
- [x] Standardize model configuration default to `gemini-3.5-flash` / `gemini-1.5-flash` in `.env` for high free-tier limits (1,500 RPD)

## Phase 7: Real-Time Token Streaming (SSE) [🟢 COMPLETE]
- [x] Implement `generate_answer_stream()` async generator in `backend/app/services/generation.py` using `chain.astream()`
- [x] Build `POST /api/chat/stream` endpoint in `backend/app/routers/chat.py` returning `StreamingResponse(media_type="text/event-stream")`
- [x] Enforce structured SSE event protocol (`metadata` -> `token` -> `done` / `error`)
- [x] Maintain atomic database transaction commits (`await db.commit()`) post-stream completion with clean `await db.rollback()` on exceptions
- [x] Implement `sendChatMessageStream()` in `frontend/src/services/api.js` using `ReadableStream` reader
- [x] Update `useConversations.js` hook to progressively append incoming token deltas for typewriter-style UI rendering

## Phase 8: Hybrid Search (BM25 + pgvector) with RRF & Re-Ranking [🟢 COMPLETE]
- [x] Evaluate and select PostgreSQL native Full-Text Search (`tsvector`/`tsquery` with GIN indexing) for unified zero-latency BM25 lexical keyword search
- [x] Refactor `backend/app/services/retrieval.py` into a two-stage hybrid retrieval pipeline (`_retrieve_vector_candidates`, `_retrieve_lexical_candidates`)
- [x] Implement Reciprocal Rank Fusion algorithm (`_reciprocal_rank_fusion`) with $k=60$ to merge non-comparable sparse and dense candidate ranks
- [x] Implement Stage 2 Cross-Scoring Re-Ranker (`_cross_score_rerank`) computing $0.50 \cdot S_{vec} + 0.30 \cdot S_{lex} + 0.20 \cdot S_{cross}$
- [x] Add GIN FTS index (`idx_chunks_fts`) to `Chunk` ORM model in `backend/app/models/__init__.py`
- [x] Add automated test case `test_hybrid_retrieval_exact_keyword` in `backend/tests/test_integration.py` (**7/7 tests passed in 21.45s**)
- [x] Update `docs/STUDY_GUIDE.md` with educational concepts and interview Q&A for Hybrid Search, RRF, and Re-Ranking



