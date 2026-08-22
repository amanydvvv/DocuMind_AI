"""
KueryCore AI — Retrieval Cache Unit Tests

Validates the exact-normalized-match TTL LRU in front of retrieve_context:
- hit/miss behavior with a spy on the embed + hybrid pipeline
- query normalization (case, whitespace collapse)
- per-user tenant isolation (a result cached for A is unreachable for B)
- TTL expiry re-running the pipeline
- max-size LRU eviction
- per-user flush on upload/delete (router wiring, DB-backed)

All retrieval-layer calls are mocked: no Gemini, no real embeddings.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import app.services.retrieval as retrieval
from app.services.query_cache import TTLQueryCache, normalize_query
from app.database import engine
from app.main import app

BASE = "http://testserver"
TIMEOUT = 30.0


class FakeChunk:
    """Stand-in for a SQLAlchemy Chunk with only the columns the chat layer reads."""

    def __init__(self, content: str, page_number: int | None = None):
        self.id = uuid.uuid4()
        self.document_id = uuid.uuid4()
        self.content = content
        self.page_number = page_number
        self.metadata_ = {}


class PipelineSpy:
    """Records embed/retrieval invocations; returns deterministic candidates."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.vector_calls = 0
        self.lexical_calls = 0

    async def vector(self, **kwargs):
        self.vector_calls += 1
        return [(c, 0.9) for c in self.chunks]

    async def lexical(self, **kwargs):
        self.lexical_calls += 1
        return [(c, 0.8) for c in self.chunks]


class DispatchSpy:
    """Refers candidates by user_id: simulates per-tenant corpora with ONE spy."""

    def __init__(self, corpus):
        self.corpus = corpus
        self.vector_calls = 0
        self.lexical_calls = 0

    async def vector(self, **kwargs):
        self.vector_calls += 1
        uid = kwargs.get("user_id")
        return [(c, 0.9) for c in self.corpus.get(uid, [])]

    async def lexical(self, **kwargs):
        self.lexical_calls += 1
        uid = kwargs.get("user_id")
        return [(c, 0.8) for c in self.corpus.get(uid, [])]


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows


class NoopDB:
    """Only the doc-map query touches the DB in the mocked pipeline."""

    def __init__(self, doc_rows):
        self._rows = doc_rows
        self.execute_calls = 0

    async def execute(self, stmt):
        self.execute_calls += 1
        return _Result(self._rows)


def _install_pipeline(monkeypatch, chunks: list):
    """Monkeypatch the two Stage-1 retrievers; return (spy, noop-db)."""
    spy = PipelineSpy(chunks)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)
    doc_rows = [(c.document_id, "doc.md") for c in chunks]
    return spy, NoopDB(doc_rows)


def _fresh_cache(monkeypatch, **kwargs) -> TTLQueryCache:
    """Swap the process-wide cache for an isolated test instance."""
    cache = TTLQueryCache(**kwargs)
    monkeypatch.setattr(retrieval, "query_cache", cache)
    return cache


async def _retrieve(query, user_id, db, **kwargs):
    return await retrieval.retrieve_context(query=query, db=db, user_id=user_id, **kwargs)


# ---------------------------------------------------------------------------
# Pure unit tests (no DB, no network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hit_skips_pipeline_and_returns_same_shape(monkeypatch):
    chunks = [FakeChunk("alpha", page_number=3), FakeChunk("beta")]
    spy, db = _install_pipeline(monkeypatch, chunks)
    uid = uuid.uuid4()

    first = await _retrieve("what is RLS?", uid, db)
    assert spy.vector_calls == 1 and spy.lexical_calls == 1

    second = await _retrieve("what is RLS?", uid, db)
    assert spy.vector_calls == 1 and spy.lexical_calls == 1, "Pipeline must not rerun on a hit"

    assert [(c.content, s, fn) for c, s, fn in first] == [
        (c.content, s, fn) for c, s, fn in second
    ]
    assert second[0][2] == "doc.md"


@pytest.mark.asyncio
async def test_normalized_queries_hit_same_entry(monkeypatch):
    chunks = [FakeChunk("alpha")]
    spy, db = _install_pipeline(monkeypatch, chunks)
    uid = uuid.uuid4()

    await _retrieve("  What   is   RLS  ", uid, db)
    assert spy.vector_calls == 1

    second = await _retrieve("what is rls", uid, db)
    assert spy.vector_calls == 1, "Case/whitespace variant should hit the base entry"
    assert second[0][0].content == "alpha"
    # Fused score: the chunk surfaces on both paths, so RRF+rerank blends
    # (0.5*vec + 0.3*lex + 0.2*phrase) = 0.8 with zero lexical phrase overlap.
    assert second[0][1] == 0.8

    third = await _retrieve("what is RLS anyway", uid, db)
    assert spy.vector_calls == 2, "Different text must not hit"


@pytest.mark.asyncio
async def test_per_user_isolation(monkeypatch):
    uid_a, uid_b = uuid.uuid4(), uuid.uuid4()
    corpus = {uid_a: [FakeChunk("alice-secret")], uid_b: [FakeChunk("bob-secret")]}
    spy = DispatchSpy(corpus)
    monkeypatch.setattr(retrieval, "_retrieve_vector_candidates", spy.vector)
    monkeypatch.setattr(retrieval, "_retrieve_lexical_candidates", spy.lexical)
    db = NoopDB([(c.document_id, "doc.md") for c in corpus[uid_a]])

    await _retrieve("shared question", uid_a, db)
    await _retrieve("shared question", uid_b, db)
    assert spy.vector_calls == 2, "Each tenant's first ask runs its own pipeline"

    # Same query, different tenant: distinct content served.
    hit_a = await _retrieve("shared question", uid_a, db)
    hit_b = await _retrieve("shared question", uid_b, db)
    assert hit_a[0][0].content == "alice-secret"
    assert hit_b[0][0].content == "bob-secret"

    # Both re-asks were hits.
    assert spy.vector_calls == 2


@pytest.mark.asyncio
async def test_ttl_expiry_reruns_pipeline(monkeypatch):
    spy, db = _install_pipeline(monkeypatch, [FakeChunk("alpha")])
    _fresh_cache(monkeypatch, ttl_seconds=-2, max_entries=50)
    uid = uuid.uuid4()

    await _retrieve("ttl question", uid, db)
    await _retrieve("ttl question", uid, db)
    assert spy.vector_calls == 2, "Expired TTL means every call reruns the pipeline"
    assert spy.lexical_calls == 2


def test_lru_eviction_caps_entries():
    cache = TTLQueryCache(ttl_seconds=60, max_entries=2)
    ua, ub, uc = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    cache.put(ua, None, 5, "first question", [(FakeChunk("a"), 0.5, "d.md")])
    cache.put(ub, None, 5, "second", [(FakeChunk("b"), 0.5, "d.md")])
    cache.put(uc, None, 5, "third", [(FakeChunk("c"), 0.5, "d.md")])

    stats = cache.stats()
    assert stats["entries"] == 2, f"LRU should cap at max_entries, got {stats}"
    assert stats["evictions"] == 1

    # LRU evicted the oldest entry ("first question" under ua).
    assert cache.get(ua, None, 5, "first question") is None
    assert cache.get(ub, None, 5, "second") is not None


def test_invalidate_user_is_scoped():
    cache = TTLQueryCache(ttl_seconds=60, max_entries=100)
    ua, ub = uuid.uuid4(), uuid.uuid4()

    cache.put(ua, None, 5, "q a1", [(FakeChunk("a1"), 0.5, "d.md")])
    cache.put(ua, None, 5, "q a2", [(FakeChunk("a2"), 0.5, "d.md")])
    cache.put(ub, None, 5, "q b1", [(FakeChunk("b1"), 0.5, "d.md")])
    assert cache.stats()["entries"] == 3

    removed = cache.invalidate_user(ua)
    assert removed == 2
    assert cache.stats()["entries"] == 1

    # User B still hits.
    hit = cache.get(ub, None, 5, "q b1")
    assert hit is not None and hit[0][0].content == "b1"
    # User A now misses.
    assert cache.get(ua, None, 5, "q a1") is None


def test_normalize_query_smoke():
    assert normalize_query("  What   is   RLS?  ") == "what is rls?"
    assert normalize_query("What is RLS?") == normalize_query("  WHAT is   rls?  ")


# ---------------------------------------------------------------------------
# DB-backed wiring: document upload/delete flush the tenant cache.
# ---------------------------------------------------------------------------


async def _signup_user(client: AsyncClient) -> str:
    email = f"cacheboot{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/auth/signup", json={"email": email, "password": "TestPass123!"}
    )
    assert resp.status_code in (200, 201), f"Signup failed: {resp.text}"
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return email


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await engine.dispose()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE,
        timeout=TIMEOUT,
        # Unique rate-limit bucket for this suite (see ratelimit.py keying).
        headers={"cf-connecting-ip": "10.8.8.8"},
    ) as c:
        yield c
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_and_delete_invalidate_tenant_cache(client, monkeypatch):
    """Upload + DELETE hit invalidate_user for that tenant (no cache leak)."""
    await _signup_user(client)

    calls = []
    real_invalidate = TTLQueryCache.invalidate_user

    def spied_invalidate(self, user_id):
        calls.append(str(user_id))
        return real_invalidate(self, user_id)

    monkeypatch.setattr(TTLQueryCache, "invalidate_user", spied_invalidate)

    resp = await client.post(
        "/api/documents/upload",
        files={"file": ("note.md", b"# Note\nPayload for cache invalidation.", "text/markdown")},
    )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    assert len(calls) == 1, f"Upload must invalidate cache for the tenant, got {len(calls)} calls"

    doc_id = resp.json()["id"]
    resp = await client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 204, f"Delete failed: {resp.text}"
    assert len(calls) == 2, "Delete must invalidate cache again"

    assert calls[0] == calls[1], "Both mutations flush the same tenant"