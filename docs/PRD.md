# DocuMind AI — Product Requirements Document (PRD)

## 1. Overview & Problem Statement
**DocuMind AI** is an AI-powered technical documentation assistant leveraging Retrieval-Augmented Generation (RAG). 
**The Problem:** Technical teams and users often struggle to find exact answers buried within lengthy PDFs or Markdown documentation. Keyword-based search is fragile and lacks contextual understanding.
**The Solution:** DocuMind AI allows users to upload technical documents, chunks and embeds them semantically into a vector database, and provides a conversational chat interface where users can ask natural language questions. The AI replies with answers grounded *exclusively* in the uploaded context, accompanied by exact source citations.

## 2. Goals & Non-Goals
### In Scope (Goals)
- Robust background ingestion pipeline for parsing PDFs and Markdown files.
- Advanced RAG (Retrieval-Augmented Generation) engine utilizing cosine similarity search.
- Multi-turn conversational memory, enabling follow-up questions.
- Strict LLM hallucination prevention via context-boundary prompt engineering.
- Modern web frontend for document management and chat.
- Query tracking and analytics for performance benchmarking.

### Out of Scope (Non-Goals)
- User authentication and multi-tenant isolation (this is a single-user portfolio/reference project).
- Web crawling (only uploaded files are supported).
- Multi-modal support (images/audio).

## 3. Core Features
| Feature | Description | Current Status | Relevant Files |
|---|---|---|---|
| **Document Upload & Ingestion** | Upload files, detect duplicates via hash, chunk text (RecursiveCharacterTextSplitter), batch embed, and store in pgvector. | ✅ Done | `app/routers/documents.py`, `app/services/ingestion.py` |
| **RAG Chat Retrieval** | Embed user query, run HNSW cosine similarity search to retrieve top-K relevant chunks, format as citations. | ✅ Done | `app/routers/chat.py`, `app/services/retrieval.py` |
| **Multi-Turn Conversation Memory** | Store chat history in DB, retrieve prior messages, and inject into LLM context for seamless follow-ups. | ✅ Done | `app/routers/chat.py`, `app/services/generation.py` |
| **Conversation Management** | List, retrieve, and delete historical chat sessions. | 🟡 Stubbed | `app/routers/conversations.py` |
| **Analytics & Logging** | Track query similarity scores, latency, and LLM hit rates for benchmarking. | 🟡 Stubbed | `app/routers/analytics.py` |
| **Frontend UI** | Modern React/Vite interface with drag-and-drop uploads and chat view. | ❌ Not Started | `frontend/src/*` |

## 4. Tech Stack & Architecture Decisions
| Layer | Choice | Reasoning (from STUDY_GUIDE.md) |
|---|---|---|
| **Backend Engine** | Python + FastAPI | Python is the industry standard for AI SDKs (LangChain); FastAPI provides modern async I/O. |
| **Database & Vector Store** | PostgreSQL + `pgvector` | Unified transactional and vector store; avoids network latency/overhead of separate databases. |
| **Vector Index** | `HNSW` | Graph-based traversal perfectly bypasses "empty-probe" Voronoi limitations of `ivfflat` on small datasets. |
| **ORM & Driver** | SQLAlchemy 2.0 + `asyncpg` | Non-blocking execution prevents thread exhaustion under high concurrency. |
| **LLM Orchestration** | LangChain + Gemini | Seamlessly chains prompts to Google's embeddings and generation APIs. |

## 5. Data Model
Our PostgreSQL database implements strict isolation between transactional data and vector storage:
- **`documents`**: Tracks uploaded files, upload status, processing state, and SHA-256 duplicate detection hashes.
- **`chunks`**: Stores the fragmented text from documents alongside their 768-dimension `vector` embeddings.
- **`conversations`**: Manages unique chat sessions (multi-turn memory boundaries).
- **`messages`**: Stores individual human/AI messages, linking them to a specific conversation, including metadata like latency and citations.
- **`query_logs`**: Designed for Phase 5 analytics tracking (latency, scores).

## 6. Success Criteria
The project is considered complete when:
- The backend passes a full automated integration test suite (Health, Ingestion, Q&A, Hallucination-prevention).
- The frontend provides a polished, usable interface for both uploading documents and querying them.
- Multi-turn conversation memory works smoothly in the UI.
- Analytics endpoints successfully log metrics for future evaluation.

## 7. Open Questions / Future Considerations
- **Frontend Framework Choice:** React (Vite) vs Next.js.
- **Analytics Implementation:** What specific visualization metrics do we want the frontend to display?
- **Streaming LLM Responses:** Should we upgrade the `/api/chat` endpoint to use Server-Sent Events (SSE) for typewriter-style streaming in the frontend?
