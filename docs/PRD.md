# DocuMind AI — Product Requirements Document (PRD)

## 1. Overview & Problem Statement
**DocuMind AI** is an AI-powered technical documentation assistant leveraging Retrieval-Augmented Generation (RAG). 

**The Problem:** Technical teams and users often struggle to find exact answers buried within lengthy PDFs or Markdown documentation. Keyword-based search is fragile and lacks contextual understanding.

**The Solution:** DocuMind AI allows users to upload technical documents, chunks and embeds them semantically into a vector database, and provides a conversational chat interface where users can ask natural language questions. The AI replies with answers grounded *exclusively* in the uploaded context, accompanied by exact source citations and multi-tenant security isolation.

## 2. Goals & Non-Goals

### In Scope (Goals)
- Robust background ingestion pipeline for parsing PDFs and Markdown files.
- Advanced Hybrid RAG (Retrieval-Augmented Generation) engine combining pgvector HNSW semantic search and PostgreSQL Full-Text Search with Reciprocal Rank Fusion (RRF).
- Multi-turn conversational memory, enabling follow-up questions.
- Strict LLM hallucination prevention via context-boundary prompt engineering.
- Modern web frontend for document management and real-time SSE token streaming chat.
- Query tracking and analytics for performance benchmarking.
- JWT Authentication and Multi-Tenancy isolation per user workspace.

### Out of Scope (Non-Goals)
- Web crawling (only uploaded files are supported).
- Multi-modal support (images/audio).

## 3. Core Features
| Feature | Description | Current Status | Relevant Files |
|---|---|---|---|
| **Document Upload & Ingestion** | Upload files, detect duplicates via hash, chunk text (RecursiveCharacterTextSplitter), batch embed, and store in pgvector. | ✅ Done | `app/routers/documents.py`, `app/services/ingestion.py` |
| **Hybrid RAG Retrieval & RRF** | Two-stage candidate retrieval (pgvector HNSW + PostgreSQL FTS) fused with Reciprocal Rank Fusion ($k=60$) and Stage 2 re-ranking. | ✅ Done | `app/routers/chat.py`, `app/services/retrieval.py` |
| **Multi-Turn Conversation Memory** | Store chat history in DB, retrieve prior messages (last 10 turns), and inject into LLM context for seamless follow-ups. | ✅ Done | `app/routers/chat.py`, `app/services/generation.py` |
| **Real-Time Token Streaming (SSE)** | Stream LLM responses token-by-token using Server-Sent Events (`text/event-stream`) for typewriter-style rendering. | ✅ Done | `app/routers/chat.py`, `app/services/generation.py`, `frontend/src/services/api.js` |
| **Conversation Management** | List, retrieve, and delete historical chat sessions with thread switching protection. | ✅ Done | `app/routers/conversations.py`, `frontend/src/hooks/useConversations.js` |
| **JWT Auth & Multi-Tenancy** | PBKDF2 password hashing, RFC 7519 JWT issuance/verification, user signup/login, and strict user workspace resource isolation. | ✅ Done | `app/core/security.py`, `app/routers/auth.py`, `app/models/user.py`, `frontend/src/components/AuthModal.jsx` |
| **Analytics & Logging** | Track query similarity scores, latency, and document retrieval frequencies. | ✅ Done | `app/routers/analytics.py` |
| **Frontend UI** | Modern React/Vite interface with drag-and-drop uploads, tabbed sidebar, auth modal, and interactive citation popovers. | ✅ Done | `frontend/src/*` |

## 4. Tech Stack & Architecture Decisions
| Layer | Choice | Reasoning (from STUDY_GUIDE.md) |
|---|---|---|
| **Backend Engine** | Python + FastAPI | Python is the industry standard for AI SDKs (LangChain); FastAPI provides modern async I/O and SSE streaming. |
| **Database & Vector Store** | PostgreSQL + `pgvector` | Unified relational and vector store; avoids network latency/overhead of separate databases. |
| **Vector Index** | `HNSW` | Graph-based traversal perfectly bypasses "empty-probe" Voronoi limitations of `ivfflat` on small datasets. |
| **ORM & Driver** | SQLAlchemy 2.0 + `asyncpg` | Non-blocking execution prevents thread exhaustion under high concurrency. |
| **LLM Orchestration** | LangChain + Gemini | Seamlessly chains prompts to Google's embeddings (`gemini-embedding-001`) and generation APIs (`gemini-3.5-flash`). |
| **Authentication** | PyJWT / Standard Library + PBKDF2 | Lightweight, dependency-free JWT issuance/decoding and secure password hashing. |

## 5. Data Model
Our PostgreSQL database implements strict isolation between transactional data, users, and vector storage:
- **`users`**: Manages user accounts (`id`, `email`, `hashed_password`, `created_at`).
- **`documents`**: Tracks uploaded files, upload status, processing state, content hashes, and `user_id` ownership.
- **`chunks`**: Stores the fragmented text from documents alongside their 768-dimension `vector` embeddings and FTS GIN index.
- **`conversations`**: Manages unique chat sessions linked to `user_id`.
- **`messages`**: Stores individual human/AI messages, linking them to a specific conversation, including metadata like latency and citations.
- **`query_logs`**: Logs query latency, similarity scores, and retrieved chunk IDs linked to `user_id`.

## 6. Success Criteria
The project is considered complete when:
- The backend passes the full automated integration test suite (`test_integration.py` and `test_auth_multitenancy.py`).
- The frontend provides a polished interface for user authentication, uploading documents, and real-time streaming Q&A.
- Multi-turn conversation memory works smoothly in the UI with thread isolation.
- Analytics endpoints successfully log metrics for future evaluation.
