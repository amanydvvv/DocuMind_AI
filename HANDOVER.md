# DocuMind AI — Agent Handover & Memory Transfer Guide

> **Purpose:** This file contains full architectural context, current execution state, codebase mapping, and verified capabilities of **DocuMind AI** to enable seamless memory transfer and continuity for any incoming AI agent or developer.

---

## 📌 Executive Summary & Project Status

**DocuMind AI** is a production-grade **Retrieval-Augmented Generation (RAG)** assistant built to query technical documentation (PDFs and Markdown files) with zero hallucinations, exact source citations, and multi-turn session persistence.

### Status: **Phases 1 through 7 are 100% COMPLETE & VERIFIED**

- **Latest Git Commit:** `0741c275` (`feat: complete Phase 7 real-time token streaming (SSE)`)
- **Backend Health:** `http://localhost:8000/api/health` -> `{"status":"healthy","database":"healthy","llm_provider":"healthy"}`
- **Frontend App:** Running at `http://localhost:5173` (React + Vite + Tailwind CSS v4)
- **Database:** PostgreSQL 16 with `pgvector` HNSW vector index running in Docker on host port `5435`

---

## 📐 Technology Stack & Ports

| Component | Technology | Local Port / URI | Description |
|---|---|---|---|
| **Backend Framework** | FastAPI (Python 3.12/3.10) | `http://localhost:8000` | Async REST API & SSE streaming server |
| **Vector Database** | PostgreSQL 16 + `pgvector` | `localhost:5435` | Relational DB + HNSW cosine vector index |
| **ORM & Driver** | SQLAlchemy 2.0 Async + `asyncpg` | DB: `documind` | Asynchronous, non-blocking database queries |
| **LLM & Embeddings** | Google Gemini (`gemini-3.5-flash`) | API Key configured | `gemini-embedding-001` (768d) & `gemini-3.5-flash` |
| **Document Parsing** | PyMuPDF | Ingestion worker | Extracts clean text & page numbers from PDFs |
| **Frontend UI** | React + Vite + Tailwind CSS | `http://localhost:5173` | Single-page SPA with tabbed sidebar and typewriter streaming |

---

## 🗺️ Codebase Map

```text
Proj2/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & CORS configuration
│   │   ├── config.py          # pydantic-settings environment validation
│   │   ├── database.py        # Async SQLAlchemy engine & session factory
│   │   ├── models/            # SQLAlchemy ORM models (Document, Chunk, Conversation, Message, QueryLog)
│   │   ├── schemas/           # Pydantic validation schemas (ChatRequest, ChatResponse, Citation)
│   │   ├── services/
│   │   │   ├── ingestion.py   # PyMuPDF parsing, SHA-256 deduplication, chunking, Gemini batch embeddings
│   │   │   ├── retrieval.py   # pgvector HNSW cosine similarity search (<=> operator)
│   │   │   └── generation.py  # Gemini LLM Q&A generation (ainvoke) & real-time SSE streaming (astream)
│   │   └── routers/
│   │       ├── documents.py   # Document upload, status retrieval, and deletion CRUD
│   │       ├── chat.py        # RAG endpoints: POST /api/chat & SSE POST /api/chat/stream
│   │       ├── conversations.py # Chat history sessions CRUD (GET, DELETE)
│   │       └── analytics.py   # RAG metrics summary & query log pagination
│   ├── tests/                 # Automated pytest integration test suite (tests/test_integration.py)
│   └── Dockerfile             # Python 3.12 backend container definition
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/          # ChatContainer, MessageList, MessageBubble, ChatInput
│   │   │   ├── documents/     # DocumentSidebar, UploadPanel
│   │   │   ├── sidebar/       # ConversationSidebar, ConversationItem
│   │   │   ├── shared/        # CitationViewer modal overlay
│   │   │   └── layout/        # Layout shell with tabbed navigation (Chats / Docs)
│   │   ├── hooks/             # useConversations custom hook (state machine & SSE token streaming)
│   │   ├── services/api.js    # Typed API client with fetch & ReadableStream SSE reader
│   │   └── App.jsx            # Main app controller
│   └── vite.config.js         # Vite configuration with Tailwind CSS v4
├── docs/
│   ├── PRD.md                 # Product Requirements Document
│   ├── PROJECT_CHECKLIST.md   # Execution tracker across development phases
│   └── STUDY_GUIDE.md         # Architecture, design decisions, and interview Q&A guide
├── docker-compose.yml         # Container configuration for PostgreSQL (5435) & FastAPI (8000)
└── HANDOVER.md                # This file (Context transfer document for next agent)
```

---

## ⚡ Completed Capabilities & Architecture Highlights

### 1. Ingestion & Vector Storage (Phases 1 & 2)
- SHA-256 content hashing prevents duplicate document uploads.
- `RecursiveCharacterTextSplitter` chunks document text into 800-character segments with 200-character overlaps.
- 768-dimensional vectors embedded via `gemini-embedding-001` and stored in PostgreSQL using `HNSW` (`vector_cosine_ops`) indexing.

### 2. Multi-Turn RAG & Database Integrity (Phases 3, 5 & 6)
- **Windowed Memory**: `POST /api/chat` and `POST /api/chat/stream` retrieve the **last 10 messages** from `Message` ORM table to maintain context without context window overflow.
- **Transaction Boundaries (`flush` vs `commit`)**: `await db.flush()` assigns primary keys to user prompts without locking. Atomic `await db.commit()` runs *only* after answer generation succeeds.
- **Rate Limit Resilience**: Catches Google Gemini `ResourceExhausted` (429) errors, executes `await db.rollback()`, and returns clean HTTP 429 status codes.
- **Race Condition Prevention**: Frontend `useConversations` hook uses `AbortController` to abort in-flight thread requests during rapid sidebar navigation.

### 3. Real-Time Token Streaming (Phase 7)
- `POST /api/chat/stream` streams responses using Server-Sent Events (`text/event-stream`).
- Event protocol: `metadata` (delivers citations/IDs) -> `token` (delivers delta words) -> `done` (commits DB transaction & returns latency).
- React UI renders typewriter-style token streaming in real time.

---

## 🧪 How to Verify System Health

Run the following commands to confirm everything is operational:

```bash
# 1. Start Docker containers (if stopped)
docker-compose up -d

# 2. Check Backend API health
curl http://localhost:8000/api/health

# 3. Run full automated integration test suite (6/6 should pass)
cd backend
venv\Scripts\python.exe -m pytest tests/test_integration.py -v

# 4. Verify Frontend Production Build
cd frontend
npm run build
```

---

## 🚀 Suggested Next Steps for the Incoming Agent

1. **Option A: Advanced RAG (Hybrid Search & Re-ranking)**
   - Combine BM25 keyword search with `pgvector` semantic search using Reciprocal Rank Fusion (RRF).
   - Add a Cross-Encoder re-ranker model for precision boost on complex technical documentation.

2. **Option B: Authentication & Multi-Tenancy**
   - Implement JWT authentication (OAuth2 Password Bearer).
   - Add user account tables and isolate documents/conversations per workspace/tenant.

3. **Option C: Cloud Deployment & CI/CD**
   - Create Helm charts / Terraform scripts for Kubernetes deployment.
   - Configure GitHub Actions pipeline for automated pytest and build checks.
