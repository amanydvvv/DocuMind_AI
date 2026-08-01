# DocuMind AI — Personal Study Guide & Interview Notes

> **Purpose:** This document is a living study guide and technical cheat sheet for **DocuMind AI**. It captures every architectural decision, bug fix, and theoretical concept learned during development. Use this to review core engineering concepts and prepare for technical interviews.

---

## 📚 Table of Contents
1. [Phase 1: Foundation & Architecture Concepts](#phase-1-foundation--architecture-concepts)
   - [Why Python (FastAPI) vs. Java (Spring Boot)?](#1-why-python-fastapi-vs-java-spring-boot)
   - [What is Docker & Container Isolation? (The Port Remapping Lesson)](#2-what-is-docker--container-isolation-the-port-remapping-lesson)
   - [Synchronous vs. Asynchronous Execution (Why asyncpg?)](#3-synchronous-vs-asynchronous-execution-why-asyncpg)
   - [What is pgvector & Why Vector Databases?](#4-what-is-pgvector--why-vector-databases)
   - [Pydantic Schemas vs. ORM Models](#5-pydantic-schemas-vs-orm-models)
2. [Phase 2: Ingestion Pipeline Concepts](#phase-2-ingestion-pipeline-concepts)
3. [Phase 3: RAG Retrieval & LLM Generation](#phase-3-rag-retrieval--llm-generation)
4. [💡 Master Interview Cheat Sheet](#-master-interview-cheat-sheet)

---

## Phase 1: Foundation & Architecture Concepts

### 1. Why Python (FastAPI) vs. Java (Spring Boot)?
In general software engineering, **Java (Spring Boot)** is an enterprise giant used heavily in banking and legacy microservices. However, for modern **AI, LLM, and RAG applications**, **Python** is the industry standard.

#### The 3 Core Reasons:
1. **The Day-1 Ecosystem Advantage:** Almost every major AI research lab (OpenAI, Google DeepMind, Anthropic, Meta) releases their official SDKs in Python first. Crucial RAG libraries like **LangChain**, **LlamaIndex**, and **PyMuPDF** are Python-native. Java wrappers (like `Spring AI`) are often 6–12 months behind.
2. **Data & Vector Manipulation:** RAG pipelines require heavy unstructured data processing (stripping PDF text, chunking paragraphs, matrix math for embeddings). Python accomplishes in 15 readable lines what takes 50+ lines of stream boilerplate in Java.
3. **FastAPI Modern Design:** FastAPI provides native asynchronous I/O (`async/await`) out of the box, automatic Swagger/OpenAPI documentation generation, and Pydantic validation that handles messy LLM JSON payloads effortlessly.

---

### 2. What is Docker & Container Isolation? (The Port Remapping Lesson)
During Phase 1, we learned why containers are vital for consistent development.

#### The Concept:
A **Docker Container** is an isolated mini-computer running inside your machine with its own OS, dependencies, and file system. An **Image** (`pgvector/pgvector:pg16`) is the read-only blueprint, while the **Container** (`documind-db`) is the running instance.

#### The Real-World Port Collision We Solved:
* **The Bug:** When we first started Docker on port `5432`, our Python application crashed with `password authentication failed for user "documind"`.
* **The Cause:** Using terminal diagnostics (`netstat -ano`), we discovered that the Windows host machine already had a native PostgreSQL service running in the background on ports `5432` and `5433`. When Python connected to `localhost:5432`, Windows routed the traffic to the old local Windows database instead of our Docker container!
* **The Engineering Fix:** We remapped our Docker host binding in `docker-compose.yml` to **`5435:5432`** (Host Port 5435 -> Container Port 5432). Now, connecting to `localhost:5435` cleanly isolates our traffic into the Docker container without conflicting with native Windows services.

---

### 3. Synchronous vs. Asynchronous Execution (Why `asyncpg`?)
In traditional web frameworks (like Django or old Flask), database requests are **Synchronous (Blocking)**. 

* **Synchronous (Blocking):** When Server Thread A asks PostgreSQL for a record, the thread freezes completely until the database replies. If 1,000 users query at once, the server runs out of threads and crashes.
* **Asynchronous (Non-Blocking):** Using FastAPI and **SQLAlchemy 2.0 Async (`asyncpg`)**, when the server sends a database query, it says: *"I'm going to work on other user requests while you fetch that data. Wake me up when you have the answer."* This allows a single server process to handle thousands of concurrent I/O operations.

---

### 4. What is `pgvector` & Why Vector Databases?
Standard relational databases (like MySQL or plain PostgreSQL) search for exact keyword matches (SQL `LIKE '%keyword%'`). They do not understand *meaning* or *semantics*.

* **Vector Embeddings:** An AI embedding model (like Gemini `text-embedding-004`) converts sentences into lists of floating-point numbers called vectors (e.g., a 768-dimension array). Words with similar meanings point to similar directions in mathematical space.
* **`pgvector` Extension:** Transforms standard PostgreSQL into a vector database. It allows us to store 768-D vectors in SQL columns and use mathematical operators (like Cosine Similarity `<=>`) to find chunks of text that answer a user's question, even if they don't share exact keywords.

---

### 5. Pydantic Schemas vs. ORM Models
In professional backend architecture, we strictly separate our **Database Layer** from our **Network/API Layer**:

| Layer | Library | File Location | Purpose |
| :--- | :--- | :--- | :--- |
| **ORM Models** | `SQLAlchemy` | `app/models/` | Represents SQL database tables and relationships. Directly touches disk storage. |
| **API Schemas** | `Pydantic` | `app/schemas/` | Represents JSON data sent over HTTP. Validates types, enforces required fields, and sanitizes input/output before it ever touches the database. |

---

## Phase 2: Ingestion Pipeline Concepts

- [x] Document Parsing Strategies (PyMuPDF vs. OCR)
- [x] Chunking Algorithms (RecursiveCharacterTextSplitter & Overlap)
- [x] Vector Embedding Generation & Batching

### 1. Document Parsing Strategies (PyMuPDF vs. OCR)
In our pipeline, we use **PyMuPDF** to extract raw text and metadata (like page numbers) from digitally created PDFs. This is vastly faster and more accurate than OCR (Optical Character Recognition) tools like Tesseract, which are only necessary when dealing with scanned images where the text is baked into the pixels.

### 2. Chunking Algorithms (`RecursiveCharacterTextSplitter` & Overlap)
Large language models have finite context windows. We cannot feed a 500-page book at once.
* **Chunking:** We break documents down into smaller, digestible pieces (e.g., 800 characters).
* **`RecursiveCharacterTextSplitter`:** LangChain's smart algorithm that tries to split on paragraphs (`\n\n`) first, then sentences (`\n`), then words, keeping related ideas together rather than cutting words in half.
* **Overlap:** We use a 200-character overlap between chunks to ensure we don't accidentally split a key concept down the middle, preserving the context that connects adjacent chunks.

### 3. Vector Embedding Generation & Batching
Once we have chunks, we convert them into high-dimensional vectors (arrays of floating-point numbers) using `GoogleGenerativeAIEmbeddings` (`text-embedding-004`).
* **Batching:** Instead of sending chunks one by one across the network (which causes massive HTTP overhead), we batch them (e.g., 100 at a time). This optimizes network latency and throughput when talking to the LLM embedding provider via OmniRoute.
* **Storage:** These embeddings are saved in PostgreSQL using the `pgvector` extension to allow for semantic similarity searches later.

### 4. SQLAlchemy 1.4 vs 2.0 Type Hinting (`Column` vs `Mapped`)
Modern Python leans heavily on static type checking (like Pyright/Pylance).
* **The Bug:** Defining models with `status = Column(String)` caused type checkers to throw errors when we wrote `doc.status = "completed"` because they saw us assigning a string to a `Column` object.
* **The Fix:** We migrated our ORM models to SQLAlchemy 2.0 syntax using `Mapped[str] = mapped_column(String)`. This makes the models fully type-safe and eliminates IDE warnings.

### 5. Dynamic Configuration & Pydantic Validation
Hardcoding API keys or endpoints is a dangerous anti-pattern. We learned how to use `pydantic-settings` to load configurations from a `.env` file dynamically.
* **The Bug:** Our background worker was failing because it was hardcoded to hit a mock OmniRoute server (`http://localhost:20128`) even when we wanted to use a direct Google API key. Additionally, Pydantic's strict validation crashed the server when we added an un-registered `GOOGLE_API_KEY` to `.env`.
* **The Fix:** We properly registered `GOOGLE_API_KEY` inside `app/config.py` and rewrote the embedding initialization to dynamically check the environment variables and route traffic correctly without modifying source code.

---

## Phase 3: RAG Retrieval & LLM Generation

- [x] Cosine Similarity vs. Euclidean Distance
- [x] Prompt Engineering & Context Injection
- [x] LangChain Orchestration & Memory
- [x] Vector Indexing (`ivfflat` vs `hnsw`) & Async Caching

### 1. Cosine Similarity vs. Euclidean Distance
When `pgvector` compares a user's question to the document chunks, it needs a mathematical way to define "closeness."
*   **Euclidean Distance (L2):** Measures the straight-line distance between two points in space. If a document is very long, its vector magnitude might throw off the distance calculation.
*   **Cosine Similarity (Distance):** Measures the *angle* between two vectors, regardless of their magnitude (length). We use the `<=>` operator in pgvector for this. If two vectors point in the exact same direction (angle = 0), they are highly similar in meaning. This is the industry standard for LLM embeddings.

### 2. Prompt Engineering & Context Injection
LLMs like Gemini are prone to "hallucinations" (making up facts). To prevent this in a RAG system, we use **Context Injection**.
*   **The Workflow:** We intercept the user's question, perform the vector search, and then wrap both the retrieved chunks and the question in a strict `PromptTemplate`.
*   **The Guardrail:** Our prompt explicitly says: *"You are an expert AI assistant tasked with answering questions based ONLY on the provided context... If the answer is not contained in the context, say 'I don't have enough information'."* This locks the LLM into answering purely from our uploaded documents.

### 3. LangChain Orchestration
Instead of manually crafting HTTP requests to Google's API, we use LangChain's `ChatGoogleGenerativeAI`.
*   LangChain acts as the orchestration layer, utilizing the LCEL (LangChain Expression Language) syntax (`prompt | llm`) to chain the prompt construction directly into the LLM invocation, seamlessly parsing the asynchronous `ainvoke` responses into manageable Python objects.

### 4. Vector Indexing (`ivfflat` vs `hnsw`) & Async Caching
During Phase 3, we hit a critical bug where multi-turn queries returned `0` context chunks randomly when chained together, despite chunks existing in the database.
*   **The Bug:** We originally used an `ivfflat` index on our pgvector `embedding` column. `ivfflat` works by clustering data into "Voronoi partitions". However, on very small datasets (e.g., our small test documents), `ivfflat` fails dramatically because queries probe empty partitions and return zero rows, especially when combined with asyncpg prepared statement caching.
*   **The Fix:** We migrated the database index from `ivfflat` to **`HNSW` (Hierarchical Navigable Small World)**. HNSW builds a multi-layered graph linking nearest neighbors. It handles small datasets perfectly without "empty probe" issues, and natively avoids prepared statement cache conflicts in SQLAlchemy/asyncpg. We forced PostgreSQL to verify index usage using `EXPLAIN ANALYZE` and `SET enable_seqscan = off`.

### Phase 3 Verification & Testing

#### Test Idempotency
An integration test that uploads static content will pass once, then fail on every subsequent run — not because the app broke, but because the app correctly detected a duplicate via content hashing. The fix was to generate unique content per test run (embedding a fresh UUID) rather than reusing a static file. Lesson: a failing test can mean either "the feature broke" or "the test itself isn't idempotent" — distinguishing these is a core debugging skill, and the fix belongs in the test, not the app, when the app's behavior is actually correct.

---

## Phase 6: Multi-Turn RAG & System Resilience

- [x] Multi-Turn RAG Windowing Strategy
- [x] Database Transaction Boundaries (`flush` vs `commit`)
- [x] Third-Party API Quotas & HTTP 429 Exception Mapping
- [x] Frontend Race Condition Prevention (`AbortController`)

### 1. Multi-Turn RAG Windowing Strategy
Passing an entire unlimited chat history to an LLM on every turn causes exponential token growth, increased API costs, and context window exhaustion.
*   **The Solution:** In `backend/app/routers/chat.py`, we window conversation history by querying the database for the **last 10 messages** (`Message.conversation_id == conversation_id`, ordered chronologically).
*   **Context Injection:** Prior user/assistant exchanges are formatted into a `Conversation History` prompt section. This enables the LLM to resolve coreferences (e.g., "Who is the lead engineer for *that project*?") while keeping token overhead tightly bounded.

### 2. Database Transaction Boundaries (`flush` vs `commit`)
In an asynchronous API route handling external service calls, managing database transaction lifecycles is critical for data consistency:
*   **`await db.flush()`**: Flushes pending ORM objects (`Conversation`, user `Message`) to PostgreSQL within the open transaction. This generates auto-assigned primary keys (UUIDs) so child models can reference them immediately without locking or committing the transaction.
*   **Single Atomic `await db.commit()`**: We defer committing until *after* vector retrieval and LLM answer generation succeed. This guarantees that user input, assistant response, citations, and analytics logs are written in a single atomic database commit.
*   **Clean Rollback (`await db.rollback()`)**: If third-party LLM generation fails or times out, `await db.rollback()` unwinds the transaction, preventing orphaned user messages from polluting the database.

### 3. Third-Party API Quotas & HTTP 429 Exception Mapping
*   **HTTP 500 vs. HTTP 429:** A third-party rate limit (Google Gemini `ResourceExhausted` / 429) is an operational constraint, not an internal application crash. Returning an HTTP 500 server error hides root causes from clients and degrades UX.
*   **Resilience Pattern:** We created a custom `RateLimitError` exception in `backend/app/services/generation.py` that catches Google API quota violations (`ResourceExhausted` / "Quota exceeded") and translates them into an **HTTP 429 (Too Many Requests)** status code. The frontend renders a clean, actionable warning banner rather than breaking.
*   **Model Selection for Free Tier Limits:** Frontier preview models (e.g. `gemini-3.6-flash`) enforce strict Free Tier daily caps (e.g. 20 requests/day). Standard production models like `gemini-3.5-flash` or `gemini-1.5-flash` provide higher operational limits (15 RPM / 1,500 RPD), making them ideal for high-throughput testing and development.

### 4. Frontend Race Condition Prevention (`AbortController`)
When users switch rapidly between chat threads in a SPA sidebar, asynchronous network fetches (`GET /api/conversations/{id}`) can return out of order.
*   **The Bug:** If a user clicks Thread A, then immediately clicks Thread B, Thread A's delayed network response could arrive *after* Thread B loads, overwriting Thread B's messages with Thread A's data.
*   **The Fix:** Inside `useConversations.js`, `selectConversation(id)` instantiates an `AbortController`. When a new thread is selected, any active fetch is explicitly aborted (`controller.abort()`), ensuring only the latest active thread updates React state.

---

## Phase 8: Hybrid Search, Reciprocal Rank Fusion & Re-Ranking

- [x] Lexical Search (BM25) vs. Dense Vector Search
- [x] Native PostgreSQL Full-Text Search (`tsvector`/`tsquery`) vs. External Search Engines
- [x] Reciprocal Rank Fusion (RRF) Candidate Merging
- [x] Candidate Pool Min-Max Normalization & Two-Stage Re-Ranking
- [x] Concurrent DB Queries (`asyncio.gather`) & Alembic Schema Migrations

### 1. Lexical Search (BM25) vs. Dense Vector Search
*   **Dense Vector Search (Semantic):** Maps sentences into high-dimensional embedding spaces (`gemini-embedding-001`). Excellent at understanding intent and paraphrasing (e.g., matching "how do I fix an error" to "troubleshooting guide"), but can fail on exact keyword match requirements such as specific part numbers, function names, or classified project identifiers (e.g., "Project Xyzzy").
*   **Lexical Search (BM25 / Keyword):** Matches exact word tokens, stems, and frequency. Excels at exact term matching but lacks understanding of semantic synonyms.
*   **Hybrid Search:** Combines both paradigms in a unified pipeline so the system understands both semantic meaning and exact terminology.

### 2. Native PostgreSQL Full-Text Search (`tsvector`/`tsquery`) vs. External Search Engines
Instead of adding an external search cluster (e.g., Elasticsearch, Meilisearch) which introduces network overhead, distributed synchronization complexity, and extra operational cost:
*   We utilize PostgreSQL's built-in **Full-Text Search (`to_tsvector` / `plainto_tsquery`)** with a **GIN (Generalized Inverted Index)** on `Chunk.content`.
*   Alembic migration `c1a82f4e9012_add_fts_gin_index.py` executes transactional DDL to provision `idx_chunks_fts` in PostgreSQL.

### 3. Reciprocal Rank Fusion (RRF) Candidate Merging & Candidate Pool Sizing
Combining raw vector cosine similarity scores (bounded [0, 1]) with BM25 `ts_rank_cd` scores (unbounded floats) during candidate retrieval is mathematically invalid because raw scores have non-comparable distributions.
*   **RRF Solution:** Reciprocal Rank Fusion operates purely on relative *ranks* rather than raw scores:
    $$RRF\_Score(d) = \sum_{m \in \{vector, lexical\}} \frac{1}{60 + r_m(d)}$$
*   **Explicit Candidate Pool Sizing:**
    - `VECTOR_TOP_N = 20` (dense candidates from pgvector HNSW)
    - `LEXICAL_TOP_N = 20` (sparse candidates from PostgreSQL FTS)
    - `RRF_FUSED_TOP_K = 10` (surviving candidates entering Stage 2 re-ranking)
    - `FINAL_TOP_K = 5` (final re-ranked chunks passed to LLM generation)

### 4. Min-Max Normalization & Stage 2 Re-Ranking (Option 2b: Phrase Coverage & Lexical Re-Scorer)
To combine feature scores into a unified final sort key without score distortion, we apply **Min-Max Normalization** over the fused RRF candidate pool ($N=10$):
$$S_{norm} = \frac{S - S_{min}}{S_{max} - S_{min} + \epsilon}$$
- Maps raw vector similarity ($S_{vec}$), lexical rank ($S_{lex}$), and independent phrase & token coverage ($S_{phrase}$) into $[0.0, 1.0]$.
- Applies weighted hybrid re-ranking: $S_{final} = 0.50 \cdot S_{vec\_norm} + 0.30 \cdot S_{lex\_norm} + 0.20 \cdot S_{phrase\_norm}$.
- **Cross-Encoder vs. Phrase-Coverage Heuristic (Option 2b):** A true deep-learning Cross-Encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) jointly encodes query and document tokens through a transformer model to compute cross-attention scores. We deliberately chose Option 2b (a lightweight, independent phrase-coverage re-scorer) for performance reasons: it executes in **<5ms** with **0MB** memory bloat, zero GPU/PyTorch dependencies, and zero API cost. The precision tradeoff accepted is that it uses keyword token/phrase overlap heuristics rather than deep neural cross-attention context modeling.

### 5. Result Diversity & Chunk Overlap (Confirmed Tradeoff & MMR Solution)
*   **The Overlapping Chunk & Duplicate Document Phenomenon (Empirically Confirmed):** In multi-topic test runs against a corpus containing overlapping sliding-window chunks or duplicate document uploads, `retrieve_context()` correctly scores the top matching chunk at **1.0000**, cleanly separating it from unrelated documents (~0.05). However, ranks 2–5 are frequently dominated by near-duplicate chunks from adjacent windows of the same document or identical duplicate uploads.
*   **Architectural Fix — Maximal Marginal Relevance (MMR) & Document Deduplication:** To prevent redundant content from dominating the context window passed to the LLM:
    $$MMR = \arg\max_{d_i \in R \setminus S} \left[ \lambda \cdot Sim_1(d_i, q) - (1 - \lambda) \max_{d_j \in S} Sim_2(d_i, d_j) \right]$$
    MMR penalizes candidates that have high cosine similarity to already-selected chunks ($S$). Combining MMR with post-retrieval document-ID deduplication is the planned architectural enhancement for future phases.

### 6. Concurrent Query Execution & Latency
- Dense vector search and sparse lexical search execute within a unified PostgreSQL database session.
- **Latency Budget**: Stage 1 candidate retrieval takes ~15–20ms; Stage 2 RRF + Min-Max phrase re-ranking takes <5ms. Total retrieval latency completes in **<30ms**, well before SSE token streaming starts.

---

## 💡 Master Interview Cheat Sheet

When an interviewer asks you about your technical decisions on DocuMind AI, use these exact, high-impact responses:

#### Q: "Why did you build this backend in Python instead of Java/Spring Boot?"
> *"I evaluate languages based on the specific workload. For heavy enterprise CRUD transaction engines, Java and Spring Boot are fantastic for their strict OOP contracts. However, for an AI/RAG application, Python is the industry standard. Building DocuMind AI in Python allowed me to leverage native LangChain orchestration, direct vector embedding manipulation, and FastAPI's asynchronous I/O and Pydantic validation—giving me production-grade AI capabilities that would require unnecessary boilerplate in Java."*

#### Q: "How did you handle database connectivity and scaling in your backend?"
> *"I implemented a non-blocking, asynchronous database access layer using **FastAPI**, **SQLAlchemy 2.0 Async ORM**, and the **asyncpg** driver. By utilizing asynchronous execution, server threads aren't blocked waiting for network I/O from the database, allowing the backend to handle high-concurrency RAG queries efficiently without thread exhaustion."*

#### Q: "Tell me about a technical challenge or debugging experience during database setup."
> *"During local environment provisioning with Docker Compose, I encountered password authentication failures because native Windows PostgreSQL background services were colliding on standard ports 5432 and 5433. Using process diagnostics, I identified the host-level socket collisions and remapped our container bindings to an isolated host port (5435), ensuring clean container networking without interfering with existing OS services."*

#### Q: "Why did you use PostgreSQL instead of a specialized vector DB like Pinecone or Weaviate?"
> *"I chose **PostgreSQL with the pgvector extension** to implement a unified transactional and vector store. Running separate databases for relational metadata and vector embeddings adds unnecessary network latency, distributed synchronization complexity, and operational overhead. With pgvector, I can perform ACID-compliant relational joins and cosine similarity vector searches within a single query engine."*

#### Q: "How do you implement Hybrid Search, and why not use an external search engine like Elasticsearch?"
> *"I designed a two-stage hybrid retrieval engine directly within PostgreSQL using **pgvector HNSW** for dense semantic search and PostgreSQL native **Full-Text Search (`tsvector`/`tsquery` with a GIN index)** for lexical keyword search. I chose native Postgres FTS over Elasticsearch to maintain a single, zero-latency unified database engine without distributed data synchronization overhead. I merge ranks using **Reciprocal Rank Fusion (RRF, k=60)**, and apply **Min-Max Normalization** over the candidate pool before re-ranking."*

#### Q: "Why use Min-Max Normalization in your re-ranker instead of raw score blending?"
> *"Mixing unnormalized cosine similarity (bounded [0, 1]), `ts_rank_cd` (unbounded floats), and term overlap scores distorts rankings because the scales are completely non-comparable. RRF is rank-based so it handles candidate pool generation safely without raw scores. For Stage 2 re-ranking, I apply Min-Max normalization ($S_{norm} = (S - S_{min}) / (S_{max} - S_{min})$) across the candidate pool for each feature first. This maps every feature onto a uniform [0, 1] scale before applying weighted cross-scoring, producing mathematically sound and reliable rankings."*

#### Q: "Why choose Option 2b (Phrase-Coverage Re-Scorer) over a deep-learning ML Cross-Encoder model?"
> *"A true ML Cross-Encoder (e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`) jointly encodes query and document tokens through transformer self-attention layers to compute context relevance. While cross-encoders offer higher precision, they require downloading ~90MB weights and add 100ms+ PyTorch CPU inference latency. External API re-rankers (like Cohere Rerank) add network RTT and per-query cost. I chose Option 2b: an independent phrase-coverage & term-matching re-scorer that executes in under 5ms with 0MB memory overhead and zero external dependencies, accepting a minor precision tradeoff for sub-30ms total retrieval latency."*

#### Q: "How do you manage database transaction boundaries when calling third-party AI APIs?"
> *"I decouple object creation from transaction commits. In the chat endpoint, I use `await db.flush()` to assign primary keys to the user's prompt without locking or committing the transaction. I only perform a single `await db.commit()` after the LLM successfully returns an answer. If Google Gemini throws a rate limit or network exception, I catch it and execute `await db.rollback()`, ensuring we never persist orphaned prompts or corrupt history states."*

#### Q: "How do you prevent third-party rate limits from crashing your application?"
> *"I implement custom exception mapping and model fallback strategies. In our generation service, I catch Google's `ResourceExhausted` exceptions and map them to an HTTP 429 (Too Many Requests) response rather than allowing a raw HTTP 500 error to bubble up. Additionally, I configure defaults to high-quota production models (`gemini-3.5-flash` / `gemini-1.5-flash`), providing 1,500 requests per day on free tier accounts."*

#### Q: "How do you handle race conditions in React when fetching historical threads?"
> *"In my `useConversations` custom hook, I use the browser's `AbortController` API inside `selectConversation(id)`. When a user rapidly clicks between historical threads in the sidebar, any in-flight HTTP request from a previous click is immediately aborted. This guarantees that stale asynchronous responses never overwrite active React state."*


#### Q: "How do you ensure type safety between your database and API?"
> *"I use a combination of Pydantic for API validation and SQLAlchemy 2.0's `Mapped` syntax for ORM models. By explicitly typing model attributes with `Mapped[str] = mapped_column(...)`, I ensure full compatibility with static type checkers like Pyright. This eliminates runtime assignment errors and keeps the codebase incredibly robust."*

#### Q: "How do you manage environment configurations and secrets?"
> *"I utilized `pydantic-settings` to dynamically load environment variables from `.env` files. This enforces strict schema validation at startup—if a required key is missing or an invalid key is present, the application fails fast rather than crashing mid-execution. It also allowed me to seamlessly hot-swap between a local OmniRoute mock server and a live Google API endpoint without altering business logic."*

#### Q: "Tell me about a time you solved a complex production database bug."
> *"While implementing multi-turn RAG retrieval, I encountered a bug where vector searches inconsistently returned zero rows on subsequent queries. I traced the issue to how PostgreSQL's query planner interacts with `asyncpg` prepared statement caching and the `ivfflat` vector index. Because `ivfflat` relies on Voronoi partitioning, small datasets often lead to probing empty partitions, which was exacerbated by cached execution plans. I solved this by migrating the embedding index to `HNSW` (Hierarchical Navigable Small World), which uses graph-based traversal, perfectly bypassing the empty-probe limitation on small datasets while maintaining high retrieval performance at scale. I verified the fix directly in the DB using `EXPLAIN ANALYZE`."*
