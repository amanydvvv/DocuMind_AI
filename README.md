# DocuMind AI

> An intelligent, production-grade Retrieval-Augmented Generation (RAG) assistant for natural language querying over technical documentation.

---

## 🚀 Features

- **Document Ingestion & Parsing**: Upload PDF or Markdown files with automated text extraction (via PyMuPDF) and deduplication (SHA-256 content hashing).
- **Vector Search with pgvector & HNSW**: Efficient semantic similarity search using PostgreSQL's `pgvector` extension with HNSW (`vector_cosine_ops`) indexing for fast retrieval.
- **Multi-Turn RAG Chat & Session Persistence**: Natural language Q&A powered by Google Gemini (`gemini-3.5-flash` / `gemini-1.5-flash`), maintaining conversation history across turns and persisting sessions to PostgreSQL.
- **History Sidebar & Navigation**: Interactive sidebar for browsing past chat threads, switching contexts with race-condition protection (`AbortController`), and creating or deleting chat sessions.
- **Source Citation & Interactive Viewer**: Transparent AI responses linked directly to exact source chunks, complete with relevance scores, page numbers, and an interactive popover viewer.
- **System Resilience & Rate Limit Handling**: Automatic mapping of third-party API rate limits to HTTP 429 status codes with atomic transaction rollbacks (`await db.rollback()`).
- **RAG Analytics & Performance Tracking**: Real-time monitoring of query volume, average latency, vector similarity metrics, and document retrieval frequencies.
- **Decoupled Architecture**: High-performance FastAPI backend paired with a modern React + Vite + Tailwind CSS frontend.

---

## 🛠️ Tech Stack

| Domain | Technology | Description |
|---|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Async REST API framework with Pydantic schemas |
| **Database & Vector Store** | [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) | Relational database with HNSW vector indexing |
| **ORM & Database Driver** | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + `asyncpg` | Fully asynchronous database queries and migrations |
| **LLM & Embeddings** | [Google Gemini](https://ai.google.dev/) + [LangChain](https://www.langchain.com/) | `gemini-embedding-001` (768d) & `gemini-3.5-flash` / `gemini-1.5-flash` |
| **Document Parsing** | [PyMuPDF](https://pymupdf.readthedocs.io/) | Fast PDF text extraction & page parsing |
| **Frontend Framework** | [React](https://react.dev/) + [Vite](https://vitejs.dev/) | Single-page application with custom hooks & state machine |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) | Modern, utility-first CSS design system |
| **Infrastructure** | [Docker Compose](https://www.docker.com/) | Containerized PostgreSQL/pgvector and API service |

---

## 📐 Architecture Overview

DocuMind AI implements a fully decoupled Retrieval-Augmented Generation pipeline designed for accuracy and traceability:

1. **Ingestion Pipeline**: Uploaded PDF or Markdown documents are checked for duplicate content hashes (SHA-256). Valid files are parsed into text pages (using PyMuPDF for PDFs), split into overlapping chunks (RecursiveCharacterTextSplitter with chunk size 800 and overlap 200), embedded into 768-dimensional vectors via Google Gemini Embeddings (`gemini-embedding-001`), and persisted to PostgreSQL with an HNSW cosine index (`vector_cosine_ops`).
2. **Query & Retrieval Pipeline**: When a user submits a question, the backend generates an embedding for the query string and performs a vector cosine distance search (`Chunk.embedding.cosine_distance(vec)`) in PostgreSQL using pgvector.
3. **Context Injection & Generation**: Top-matching chunks passing the similarity threshold are injected alongside prior conversation turns (windowed to the last 10 messages) into a grounded system prompt. Google Gemini (`gemini-3.5-flash` / `gemini-1.5-flash`) generates a factual answer strictly grounded in the retrieved context.
4. **Citation Binding & Analytics**: The response is returned to the client alongside structured citations (chunk ID, document ID, filename, page number, relevance score, content preview). Every query transaction logs latency, average similarity, and retrieved chunk IDs to `query_logs` for real-time analytics.

---

## 🚦 Getting Started

### Prerequisites

- **Docker & Docker Compose** (for PostgreSQL + pgvector)
- **Python 3.12+**
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

### 2. Start Database & Backend Services

Run Docker Compose to launch PostgreSQL (port 5435) and the FastAPI backend (port 8000):

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

### 3. Start Frontend Development Server

In a new terminal window, navigate to the `frontend/` folder and install dependencies:

```bash
cd frontend
npm install
npm run dev
```

Open your browser to **`http://localhost:5173`** to access the DocuMind AI Web UI.

---

## 🔌 API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Live health check for database & Gemini embedding API |
| `POST` | `/api/documents/upload` | Upload PDF/Markdown document for async ingestion |
| `GET` | `/api/documents` | List all uploaded documents with chunk counts & status |
| `GET` | `/api/documents/{id}` | Get status and details for a single document |
| `DELETE` | `/api/documents/{id}` | Delete document, associated vector chunks, and disk file |
| `POST` | `/api/chat` | Send natural language query with context retrieval & multi-turn Q&A |
| `GET` | `/api/conversations` | List past conversation sessions ordered by updated timestamp |
| `GET` | `/api/conversations/{id}` | Get full conversation thread with chronologically ordered messages |
| `DELETE` | `/api/conversations/{id}` | Delete conversation session and associated message history |
| `GET` | `/api/analytics/summary` | Aggregate RAG metrics (total queries, avg latency, avg similarity) |
| `GET` | `/api/analytics/queries` | Paginated query log history |
| `GET` | `/api/analytics/documents` | Per-document retrieval frequency statistics |

---

## 📁 Project Structure

```text
Proj2/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & CORS configuration
│   │   ├── config.py          # Settings validation via pydantic-settings
│   │   ├── database.py        # SQLAlchemy async engine & session setup
│   │   ├── models/            # SQLAlchemy ORM models (Document, Chunk, Conversation, Message, QueryLog)
│   │   ├── schemas/           # Pydantic validation & response schemas
│   │   ├── services/          # Core RAG logic (ingestion, retrieval, generation)
│   │   └── routers/           # API router endpoints (documents, chat, conversations, analytics)
│   ├── tests/                 # Pytest integration & multi-turn verification suites
│   ├── Dockerfile             # Python 3.12 backend container build
│   └── requirements.txt       # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/          # ChatContainer, MessageList, MessageBubble, ChatInput
│   │   │   ├── documents/     # DocumentSidebar, UploadPanel
│   │   │   ├── sidebar/       # ConversationSidebar, ConversationItem
│   │   │   ├── shared/        # CitationViewer modal overlay
│   │   │   └── layout/        # Main Layout shell with tabbed navigation
│   │   ├── hooks/             # useConversations state machine hook
│   │   ├── services/api.js    # Typed API client for backend communication
│   │   ├── App.jsx            # React root component
│   │   └── main.jsx           # Entry point
│   ├── index.html
│   └── vite.config.js         # Vite configuration with Tailwind CSS v4
├── docs/
│   ├── PRD.md                 # Product Requirements Document
│   ├── PROJECT_CHECKLIST.md   # System build order & phase completion state
│   └── STUDY_GUIDE.md         # Comprehensive architectural & engineering guide
├── docker-compose.yml         # Container configuration for DB & API
└── README.md
```

---

## 🧪 Testing

The repository includes an integration test suite validating end-to-end RAG retrieval, similarity thresholds, and multi-turn generation.

> [!IMPORTANT]
> `test_integration.py` makes real HTTP requests against a live server and database. You must ensure Docker Compose (`docker-compose up -d --build`) is running on `http://localhost:8000` before executing tests.

To run the integration tests locally:

```bash
# Ensure Docker container & DB are running
cd backend
python -m pytest tests/test_integration.py -v
```

---

## 🗺️ Project Status & Roadmap

Per [`docs/PROJECT_CHECKLIST.md`](docs/PROJECT_CHECKLIST.md), **Phases 1 through 6 are complete**:

- [x] **Phase 1: Foundation & DB Setup** (pgvector, async SQLAlchemy, migrations)
- [x] **Phase 2: Core Ingestion Pipeline** (PyMuPDF parser, chunking, Gemini embeddings)
- [x] **Phase 3: RAG Retrieval & Q&A Engine** (Cosine similarity search, HNSW index, Gemini generation)
- [x] **Phase 4: Frontend Development** (React UI, drag-and-drop upload, chat stream, citation modal)
- [x] **Phase 5: Analytics & Logging** (QueryLog persistence, summary metrics, document retrieval frequency)
- [x] **Phase 6: Conversation Persistence & History Navigation** (Multi-turn ORM memory, sessions CRUD, custom hook, sidebar drawer)

### Future Enhancements (Roadmap)
- [ ] **Authentication & Multi-Tenancy**: User accounts and workspace isolation.
- [ ] **Streaming Responses**: Server-Sent Events (SSE) for token-by-token answer generation.
- [ ] **Cloud Deployment**: Helm charts / Terraform scripts for Kubernetes deployment.
