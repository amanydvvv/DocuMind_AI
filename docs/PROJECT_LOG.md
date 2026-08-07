# DocuMind AI — Project Log

> Chronological log of production incidents, code fixes, and cleanup. Newest entries at the top.

---

## 2026-08-07 — Summary Buffer Memory & Consistent Memory Persistence on Streaming, Green Test Suite

**Severity:** Low — feature work.

### Milestones
1. **Added `test_memory_integration.py` for summary persistence.**
   - Seeds a temp user/conversation/messages, invokes `update_conversation_summary`, and asserts `context_summary` is populated, non-empty, and preamble-free; cleans up all seeded rows in `finally`.

2. **Fixed SSE streaming background task gap via Starlette `BackgroundTask`.**
   - `/api/chat/stream` (`chat_stream`) was streaming answers without dispatching the summary worker at the end, so streamed conversations never got `context_summary` persisted.
   - Added `from starlette.background import BackgroundTask` and `background=BackgroundTask(update_conversation_summary, conversation_id)` on the `StreamingResponse` (worker opens its own session, so it survives request-scoped DB teardown).

3. **Resolved legacy test suite asyncio markers.**
   - `backend/tests/test_regression_e2e.py` was a standalone script: module-level `asyncio.run(main())` fired during pytest import, used `sys.exit(1)`, depended on live `localhost:8000`, and its four `async def test_*` lacked `@pytest.mark.asyncio`.
   - Rewrote it as a proper pytest module: `import pytest` / `pytest_asyncio`, `@pytest.mark.asyncio` on every async test, in-process `ASGITransport` against the app, auth header attached after signup, `await engine.dispose()` in the client fixture (setup + teardown) to avoid cross-loop pooled-connection `RuntimeError: Event loop is closed`, and standalone `main()` guarded behind `if __name__ == "__main__":`.

### Verification
- Full suite: `pytest tests/ -v` → **21 passed, 0 failures, 0 errors.**

---

## 2026-08-07 — Production Outage: Rate Limiter & 500 Crash

**Severity:** Critical — production down (all API routes returning 500).

### Root Causes (3)

1. **`NameError: name 'uuid' is not defined`** in `backend/app/main.py`
   - The `add_correlation_id` middleware called `uuid.uuid4()` without importing `uuid`.
   - Because the middleware runs on every request, every route (auth, upload, chat, health) crashed with HTTP 500.
   - Fixed by adding `import uuid` at the top of `backend/app/main.py`.

2. **Supabase connection pooler port mismatch**
   - DB credentials appeared invalid (`FATAL: password authentication failed`) although the password was correct.
   - The connect string used port `5432` (direct Postgres); Supabase's transaction/session pooler listens on port `6543`.
   - Verified by direct `psycopg2` connect to `:6543` → `SUCCESS!`. Port `6543` must be used for the pooler.

3. **Rate-limiter bypassable via spoofed `CF-Connecting-IP` / `X-Forwarded-For`**
   - `_rate_limit_key()` trusted the `cf-connecting-ip` header unconditionally, so a client could rotate header values to evade IP-based rate limits (e.g. brute-force signup/login).
   - Fixed with peer-anchored resolution: trust `CF-Connecting-IP` only when `request.client.host` starts with a private IP prefix (matches Render's internal proxy); otherwise fall back to the unspoofable socket peer.
   - Removed all `RATELIMIT_DEBUG` prints and the `X-Debug-Ratelimit` response header (debug commits `c95cb72a`, `ad4ffa49`).

### Files Changed
- `backend/app/main.py` — added missing `import uuid`.
- `backend/app/core/ratelimit.py` — peer-anchored rate-limit key; removed debug logging/header.
- `backend/tests/fixtures/` — moved `genuinely_blank.pdf`, `scanned_test_person_2026.pdf`, `test_document.md`, `test_document.txt`.
- `backend/db_snapshot.py` — deleted (dead code).
- `.gitignore` — ignore `*.pdf` / `*.txt` outside `backend/tests/fixtures/`.
- `docs/STUDY_GUIDE.md` — added Phase 9 concepts + interview Q&As.

### Verification
- `pytest tests/test_auth_multitenancy.py -v` → **8 passed** (incl. two rate-limit spoofing regression tests).

---

## Earlier — See `STUDY_GUIDE.md` for Phase-by-Phase lessons

Phase history (port remapping 5435, HNSW index, RRF re-ranking, OCR fallback, transaction boundaries, IDOR, etc.) lives in `docs/STUDY_GUIDE.md`.