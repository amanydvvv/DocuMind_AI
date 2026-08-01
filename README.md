# DocuMind AI

[![DocuMind AI CI Pipeline](https://github.com/amanc/Proj2/actions/workflows/ci.yml/badge.svg)](https://github.com/amanc/Proj2/actions/workflows/ci.yml)

> An intelligent, production-grade Retrieval-Augmented Generation (RAG) assistant for natural language querying over technical documentation with JWT authentication, multi-tenancy isolation, hybrid search, and real-time SSE token streaming.

---

## 🌐 Live Demo & Cloud Deployment

- **Frontend App (Vercel)**: `https://documind-ai.vercel.app` *(or your assigned Vercel URL)*
- **Backend API (Render)**: `https://documind-api.onrender.com/api/health`
- **Database (Supabase)**: Managed PostgreSQL 16 + `pgvector`

> [!NOTE]
> **First Load Notice**: Render free instances automatically pause after 15 minutes of inactivity. Initial request may take 20–30 seconds to cold-start.
> Uptime is protected via **UptimeRobot** HTTP keyword monitoring every 5 minutes on `/api/health`, preventing Supabase's 7-day auto-pause and eliminating Render cold starts.

---

## 🚀 Features

- **JWT Authentication & Multi-Tenancy**: Secure user signup, login, and workspace resource isolation using RFC 7519 JWT access tokens and PBKDF2-HMAC-SHA256 password hashing.
- **Document Ingestion & Parsing**: Upload PDF or Markdown files with automated text extraction (via PyMuPDF) and deduplication (SHA-256 content hashing).
- **Hybrid RAG Search (pgvector HNSW + PostgreSQL FTS)**: Two-stage candidate retrieval combining dense vector similarity search and sparse full-text search fused with Reciprocal Rank Fusion ($k=60$) and phrase-coverage re-ranking.
- **Real-Time Token Streaming (SSE)**: Server-Sent Events (`text/event-stream`) delivering typewriter-style token streaming to the frontend in real time.
- **Multi-Turn RAG Chat & Session Persistence**: Natural language Q&A powered by Google Gemini (`gemini-3.5-flash`), maintaining conversation history across turns and persisting sessions to PostgreSQL.
- **History Sidebar & Navigation**: Interactive sidebar for browsing past chat threads, switching contexts with race-condition protection (`AbortController`), creating "+ New Chat" sessions, or deleting threads.
- **Source Citation & Interactive Viewer**: Transparent AI responses linked directly to exact source chunks, complete with relevance scores, page numbers, and an interactive popover viewer.
- **System Resilience & Rate Limit Handling**: Automatic mapping of third-party API rate limits to HTTP 429 status codes with atomic transaction rollbacks (`await db.rollback()`).
- **RAG Analytics & Performance Tracking**: Real-time monitoring of query volume, average latency, vector similarity metrics, and document retrieval frequencies.
- **Decoupled Architecture**: High-performance FastAPI backend paired with a modern React + Vite + Tailwind CSS frontend.

---

## 🛠️ Tech Stack

| Domain | Technology | Description |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Async REST API framework with Pydantic schemas |
| **Database & Vector Store** | [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) | Relational database with HNSW vector indexing & FTS GIN index |
| **ORM & Database Driver** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + `asyncpg` | Fully asynchronous database queries and Alembic migrations |
| **Authentication** | RFC 7519 JWT + PBKDF2 | Security layer with Bearer token authentication & multi-tenant isolation |
| **LLM & Embeddings** | [Google Gemini](https://ai.google.dev/) + [LangChain](https://www.langchain.com/) | `gemini-embedding-001` (768d) & `gemini-3.5-flash` |
| **Document Parsing** | [PyMuPDF](https://pymupdf.readthedocs.io/) | Fast PDF text extraction & page parsing |
| **Frontend Framework** | [React](https://react.dev/) + [Vite](https://vitejs.dev/) | Single-page application with custom hooks & Auth modal |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) | Modern, utility-first CSS design system |
| **Infrastructure** | [Docker Compose](https://www.docker.com/) | Containerized PostgreSQL/pgvector and API service |

---

## 🚦 Getting Started (Local Run via Docker Compose)

### Prerequisites

- **Docker & Docker Compose** (for PostgreSQL + pgvector)
- **Python 3.10+**
- **Node.js 18+ & npm**
- **Google Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/))

### 1. Environment Setup

Clone the repository and copy the environment configuration:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and insert your Google API Key:

```env
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

### 2. Start Full Stack Containers

Run Docker Compose to launch PostgreSQL (port 5435), FastAPI backend (port 8000), and React Frontend (port 3000):

```bash
docker-compose up -d --build
```

Verify backend health by calling the health endpoint:

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

### 3. Open Frontend Application

Open your browser to **`http://localhost:3000`** (or `http://localhost:5173` for Vite dev server).

---

## ☁️ 100% Free Cloud Deployment Guide (Supabase + Render + Vercel)

### Step 1: Database (Supabase)
1. Create a free account at [Supabase](https://supabase.com) (no credit card required).
2. Create a new PostgreSQL project and run `CREATE EXTENSION IF NOT EXISTS vector;` in the SQL Editor.
3. Obtain connection strings:
   - **Direct Connection (DDL & Migrations)**: `postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres` (set as `DATABASE_URL_SYNC`).
   - **Transaction Pooler (Async Application)**: `postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres` (set as `DATABASE_URL`).
4. Run migrations: `cd backend && DATABASE_URL_SYNC="<Direct Connection>" alembic upgrade head`.

### Step 2: Backend API (Render)
1. Create a free account at [Render](https://render.com).
2. Create a new Web Service using Blueprint `render.yaml` or linking your GitHub repo (`backend/Dockerfile`).
3. Set environment variables: `DATABASE_URL`, `DATABASE_URL_SYNC`, `GOOGLE_API_KEY`, `CORS_ORIGINS`.
4. Verify `/api/health` returns `status: "healthy"`.

### Step 3: Frontend Web App (Vercel)
1. Create a free account at [Vercel](https://vercel.com).
2. Import repository, set root directory to `frontend`, and configure `VITE_API_URL` to your Render API URL.
3. Deploy and update Render `CORS_ORIGINS` with the assigned Vercel domain.

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
| `POST` | `/api/chat/stream` | Stream natural language query answer in real-time via Server-Sent Events (SSE) |
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
