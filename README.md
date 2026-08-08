# DocuMind AI

[![DocuMind AI CI Pipeline](https://github.com/amanydvvv/DocuMind_AI/actions/workflows/ci.yml/badge.svg)](https://github.com/amanydvvv/DocuMind_AI/actions/workflows/ci.yml)

> An intelligent, production-grade Retrieval-Augmented Generation (RAG) assistant for natural language querying over technical documentation with JWT authentication, multi-tenancy isolation, hybrid search, Gemini Multimodal OCR for scanned PDFs, and real-time SSE token streaming.

---

## 🌐 Live Demo & Cloud Deployment

- **Frontend App (Vercel)**: [`https://docu-mind-ai-iota.vercel.app`](https://docu-mind-ai-iota.vercel.app)
- **Backend API (Render)**: [`https://documind-ai-97t5.onrender.com/api/health`](https://documind-ai-97t5.onrender.com/api/health)
- **Database (Supabase)**: Managed PostgreSQL 17.6 + `pgvector` (Singapore `ap-southeast-1`)

> [!NOTE]
> **First Load Notice**: Render free instances automatically pause after 15 minutes of inactivity. Initial request may take 20–30 seconds to cold-start. Uptime is protected via **UptimeRobot** HTTP keyword monitoring every 5 minutes on `/api/health`, preventing Supabase's 7-day auto-pause and eliminating Render cold starts.

---

## 🚀 Key Features

- **JWT Authentication & Multi-Tenancy**: Secure user signup, login, and workspace resource isolation using RFC 7519 JWT access tokens and PBKDF2-HMAC-SHA256 password hashing.
- **Document Ingestion & Multimodal OCR**: Upload PDF or Markdown files with text vector extraction. Automatic **vision-model OCR fallback** (`VISION_MODEL`, default `qwen/qwen3.6-27b` on Groq) transcribes text from scanned image-based PDFs (e.g. certificates and receipts) when text vector layer returns 0 characters.
- **Hybrid RAG Search (pgvector HNSW + PostgreSQL FTS)**: Two-stage candidate retrieval combining dense vector similarity search and sparse full-text search fused with Reciprocal Rank Fusion ($k=60$) and phrase-coverage re-ranking.
- **Real-Time Token Streaming (SSE)**: Server-Sent Events (`text/event-stream`) delivering typewriter-style token streaming to the frontend in real time with client-side 35s `AbortController` timeout resilience.
- **Multi-Turn RAG Chat & Session Persistence**: Natural language Q&A powered by Groq (`llama-3.1-8b-instant` primary, with qwen3-32b and Gemini `gemini-1.5-flash` fallbacks), maintaining conversation history across turns and persisting sessions to PostgreSQL.
- **History Sidebar & State Resiliency**: Interactive sidebar for browsing past chat threads, switching contexts with race-condition protection (`AbortController`), creating "+ New Chat" sessions, and guaranteed `try...finally` loading state cleanup.
- **Source Citation & Interactive Viewer**: Transparent AI responses linked directly to exact source chunks, complete with relevance scores, page numbers, and an interactive popover viewer.
- **PgBouncer & Connection Resilience**: Session-mode connection pooling against Supabase's PgBouncer (direct PostgreSQL on `5432`, session pooler on `6543`) with `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` eliminating PgBouncer prepared statement cache collisions.
- **RAG Analytics & Performance Tracking**: Real-time monitoring of query volume, average latency, vector similarity metrics, and document retrieval frequencies.

---

## 🛠️ Tech Stack

| Domain | Technology | Description |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Async REST API framework with Pydantic schemas |
| **Database & Vector Store** | [PostgreSQL 17.6](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) | Relational database with HNSW vector indexing & FTS GIN index |
| **ORM & Database Driver** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + `asyncpg` | Fully asynchronous database queries and Alembic migrations |
| **Connection Pooling** | Supabase PgBouncer | Session Mode (pooler port 6543, direct port 5432) with disabled statement cache |
| **Authentication** | RFC 7519 JWT + PBKDF2 | Security layer with Bearer token authentication & multi-tenant isolation |
| **LLM, Embeddings & OCR** | Groq + Google Gemini + [LangChain](https://www.langchain.com/) | `gemini-embedding-001` (768d) embeddings; Groq `llama-3.1-8b-instant` generation & `qwen/qwen3.6-27b` vision OCR |
| **Document Parsing** | [PyMuPDF](https://pymupdf.readthedocs.io/) | Fast PDF text extraction & page image rendering |
| **Frontend Framework** | [React 19](https://react.dev/) + [Vite](https://vitejs.dev/) | Single-page application with custom hooks & Auth modal |
| **Styling** | Vanilla CSS Tokens | Sleek dark mode design system with smooth animations |
| **Infrastructure** | [Render](https://render.com/) + [Vercel](https://vercel.com/) | Dockerized web service backend + static frontend deployment |

---

## 🚦 Getting Started (Local Development)

### Prerequisites

- **Python 3.10+**
- **Node.js 18+ & npm**
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

### 1. Environment Setup

Clone the repository and create your local environment file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and insert your credentials:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GROQ_API_KEY=your_actual_groq_api_key_here
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/documind
DATABASE_URL_SYNC=postgresql://postgres:password@localhost:5432/documind
```

### 2. Run Backend

**Option A — Docker Compose (recommended).** Starts the Postgres/pgvector DB
and API together. The API service reads your keys (`GROQ_API_KEY`,
`GEMINI_API_KEY`, `ENVIRONMENT`, etc.) straight from `backend/.env` and only
overrides the DB connection to use the local Docker database.

```bash
docker compose up -d --build
```

The container runs `alembic upgrade head` automatically on start, then serves
the API on `http://localhost:8000`. Verify:

```bash
curl http://localhost:8000/api/health
```

Expected output:
```json
{
  "status": "healthy",
  "database": "healthy",
  "llm_provider": "healthy",
  "version": "0.1.0"
}
```

**Option B — Legacy (venv + uvicorn).** For running the API directly without
Docker:

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt

# Run migrations (Docker Compose does this automatically)
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 3. Install & Run Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open **`http://localhost:5173`** in your browser!

---

## 🔌 API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Register a new user account and receive JWT access token |
| `POST` | `/api/auth/login` | Authenticate user credentials and receive JWT access token |
| `GET` | `/api/auth/me` | Return authenticated user profile details |
| `GET` | `/api/health` | Live health check for database & Gemini embedding API |
| `POST` | `/api/documents/upload` | Upload PDF/Markdown document for async ingestion (User Scoped) |
| `GET` | `/api/documents` | List all user documents with chunk counts & status |
| `GET` | `/api/documents/{id}` | Get status and details for a single document |
| `DELETE` | `/api/documents/{id}` | Delete user document, associated vector chunks, and disk file |
| `POST` | `/api/chat` | Send natural language query with hybrid retrieval & multi-turn Q&A |
| `POST` | `/api/chat/stream` | Stream natural language query answer in real-time via SSE |
| `GET` | `/api/conversations` | List user conversation sessions ordered by updated timestamp |
| `GET` | `/api/conversations/{id}` | Get full user conversation thread with messages |
| `DELETE` | `/api/conversations/{id}` | Delete conversation session and associated message history |
| `GET` | `/api/analytics/summary` | Aggregate RAG metrics (total queries, avg latency, avg similarity) |
| `GET` | `/api/analytics/queries` | Paginated query log history |
| `GET` | `/api/analytics/documents` | Per-document retrieval frequency statistics |

---

## 🧪 Testing

```bash
# Run multi-tenancy & JWT auth integration tests
cd backend
python -m pytest tests/test_auth_multitenancy.py -v

# Run RAG retrieval, hybrid search, and system integration tests
python -m pytest tests/test_integration.py -v
```
