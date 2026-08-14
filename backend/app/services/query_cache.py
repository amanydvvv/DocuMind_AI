"""
KueryCore AI — Retrieval Result Cache

In-process TTL LRU cache in front of the embed -> hybrid retrieval pipeline.

Primarily cuts RAG costs: each cache miss runs a Gemini embedding call plus
two Postgres queries per query. Repeated questions — the same prompt re-asked,
a follow-up on the same document, a retried request — are served from memory.

Key design decision (documented per the task requirement):
  - EXACT-normalized-match keying, NOT embedding-similarity-threshold.
    Why: a similarity-threshold cache must itself embed the query on every
    lookup, consuming exactly the cost we are trying to avoid; its cutoff
    requires tuning that drifts as documents change; and a mis-calibrated
    threshold risks cross-topic confusion inside one tenant. Exact matching is
    deterministic, trivially inspectable, and has zero false positives.
    Cost: near-duplicates phrased differently still miss (that is the measured
    ceiling for this approach — see the task report). If repeat-hit rates
    plateau low in practice, the cheap upgrade is to also serve cache entries
    for previously-retrieved *documents* — not attempted here.

Tenant isolation (requirement 3):
  - Keys are (user_id, document_id-scope, top_k, normalized_query). A result
    cached under user A is unreachable under user B by construction.
  - The stored payload is a plain snapshot (chunk id/document/page/content/
    metadata + score + filename). On a hit we rebuild detached Chunk objects;
    no session-bound ORM state is ever shared across requests.

Invalidation (requirement 4):
  - Full per-user flush on ANY content mutation: upload, delete, reindex,
    account deletion. Scope was decided after weighing per-document flush:
    entries are keyed by query, not by document, so scoped invalidation would
    need per-entry chunk-id provenance scoring on every mutation — complexity
    with no precision gain, because background ingestion means a user's corpus
    is changing asynchronously anyway. Per-user flush is O(1), unambiguously
    correct, and mutation frequency is low (a handful per session).

Observability (requirement 5):
  - hit/miss/eviction counters exposed via `stats()`; every hit and miss also
    logs an info line so effectiveness is visible in Render logs without tooling.

Deployment / scaling trade-off:
  - This cache is IN-PROCESS and in-memory by design. On Render's current
    single-worker deployment every query flows through one process, so the
    cache has full effect. If the app is ever scaled to multiple workers, the
    cache silently degrades to per-worker hit rates — no errors, no warnings,
    still correct (keys are tenant-scoped), just less effective. If multi-worker
    scaling ever happens, migrate the store to a shared Redis cache keyed the
    same way; until then a network dependency would only add latency and an
    outage surface for zero benefit.
"""

import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.models import Chunk

logger = logging.getLogger(__name__)
settings = get_settings()

_WS_RE = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """Lowercase, trim, collapse whitespace — the cache key's normalization."""
    return _WS_RE.sub(" ", (query or "").strip().lower())


class TTLQueryCache:
    """Tenant-scoped TTL LRU cache for retrieval results. Thread-safe."""

    def __init__(
        self,
        ttl_seconds: Optional[int] = None,
        max_entries: Optional[int] = None,
    ):
        # Settings are readable per instance; tests can shrink TTL/size.
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_SECONDS
        self.max_entries = max_entries if max_entries is not None else settings.CACHE_MAX_ENTRIES
        self._store: "OrderedDict[str, Tuple[float, list]]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    # --- keying ---------------------------------------------------------
    @staticmethod
    def _key(
        user_id: Optional[Any],
        document_id: Optional[Any],
        top_k: Optional[int],
        query: str,
    ) -> str:
        uid = str(user_id) if user_id is not None else "global"
        did = str(document_id) if document_id is not None else "_"
        return f"{uid}.{did}.{top_k}.{normalize_query(query)}"

    # --- api ------------------------------------------------------------
    def get(
        self,
        user_id: Optional[Any],
        document_id: Optional[Any],
        top_k: Optional[int],
        query: str,
    ) -> Optional[List[Tuple[Chunk, float, str]]]:
        """Return cached (chunk, score, filename) tuples for the key, or None on
        miss/expiry. Rebuilds detached Chunk objects so the shape matches a
        fresh retrieve_context() call exactly."""
        if not query or not query.strip():
            return None
        key = self._key(user_id, document_id, top_k, query)
        now = time.monotonic()
        with self._lock:
            entry = self._store.pop(key, None)
            if entry is not None:
                expires_at, snapshots = entry
                if now <= expires_at:
                    self._store[key] = (expires_at, snapshots)  # bump LRU recency
                    self.hits += 1
                    rebuilt = self._rebuild(snapshots)
                    logger.info("Retrieval cache HIT for key=%s", key)
                    return rebuilt
                # Expired — leave self._store without re-inserting.
                self.evictions += 1
            self.misses += 1
        logger.info("Retrieval cache MISS for key=%s", key)
        return None

    def put(
        self,
        user_id: Optional[Any],
        document_id: Optional[Any],
        top_k: Optional[int],
        query: str,
        result: List[Tuple[Chunk, float, str]],
    ) -> None:
        """Store a retrieval result. Snapshots live a detached copy of chunk
        columns the chat layer consumes (id, document_id, page_number, content,
        metadata_) plus score/filename."""
        if not result or not query or not query.strip():
            return
        snapshot = [
            (
                {
                    "id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "page_number": chunk.page_number,
                    "content": chunk.content,
                    "metadata_": dict(chunk.metadata_ or {}),
                },
                score,
                filename,
            )
            for chunk, score, filename in result
        ]
        key = self._key(user_id, document_id, top_k, query)
        expires_at = time.monotonic() + self.ttl_seconds
        with self._lock:
            existing = self._store.pop(key, None)
            self._store[key] = (expires_at, snapshot)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)
                self.evictions += 1
        logger.info("Retrieval cache populated key='%s' (%d chunks)", key, len(snapshot))

    def invalidate_user(self, user_id: Optional[Any]) -> int:
        """Drop every entry belonging to a tenant; returns count removed."""
        if user_id is None:
            return 0
        uid = str(user_id)
        with self._lock:
            doomed = [k for k in self._store if k.split(".", 1)[0] == uid]
            for k in doomed:
                del self._store[k]
        if doomed:
            logger.info("Retrieval cache flushed %d entries for user %s", len(doomed), uid)
        return len(doomed)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "entries": len(self._store),
            }

    # --- rebuild ---------------------------------------------------------
    @staticmethod
    def _rebuild(snapshots: list) -> List[Tuple[Chunk, float, str]]:
        rebuilt = []
        for raw, score, filename in snapshots:
            c = Chunk()
            c.id = raw["id"]
            c.document_id = raw["document_id"]
            c.page_number = raw["page_number"]
            c.content = raw["content"]
            c.metadata_ = raw["metadata_"]
            rebuilt.append((c, score, filename))
        return rebuilt


# Process-wide singleton shared by the retrieval pipeline and routers.
query_cache = TTLQueryCache()