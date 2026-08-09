"""
DocuMind AI — Document File Endpoint Test Suite
Covers the tenant-scoped GET /api/documents/{id}/file route used by the
PDF citation viewer: success, content type, cross-tenant isolation (404),
unsupported type (415), and persistence across restarts (DB-backed storage).
"""

import asyncio
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.config import get_settings
from app.database import engine
from app.main import app

BASE = "http://testserver"
TIMEOUT = 30.0
FIXTURES = Path(__file__).parent / "fixtures"

_ip_counter = 0


def _next_client() -> AsyncClient:
    """In-process ASGI client with a unique peer IP (loopback + CF-Connecting-IP).

    Rate limits key by client IP (see app/core/ratelimit.py). Tests hit the
    app on loopback where the peer is always 127.0.0.1, so without a distinct
    forwarded header every test in the suite shares one 5/min signup bucket.
    Each client gets its own private-range forwarded IP => independent bucket,
    mirroring production where each user originates from a distinct address.
    """
    global _ip_counter
    _ip_counter += 1
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE,
        timeout=TIMEOUT,
        headers={"cf-connecting-ip": f"10.9.9.{_ip_counter}"},
    )


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Fresh engine + per-test client (see _ip_client for IP bucketing)."""
    await engine.dispose()
    async with _next_client() as c:
        yield c
    await engine.dispose()


async def _signup_user(client: AsyncClient) -> str:
    """Create a fresh user and attach their auth header; return access token."""
    email = f"filetest_{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/auth/signup", json={"email": email, "password": "TestPass123!"}
    )
    assert resp.status_code in (200, 201), f"Signup failed: {resp.text}"
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return token


async def _upload_pdf(client: AsyncClient, filename: str = "scanned_test_person_2026.pdf") -> str:
    """Upload a real PDF fixture; return the document id."""
    content = (FIXTURES / filename).read_bytes()
    files = {"file": (filename, content, "application/pdf")}
    resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    return resp.json()["id"]


async def _upload_markdown(client: AsyncClient) -> str:
    """Upload a markdown fixture; return the document id."""
    content = (FIXTURES / "test_document.md").read_bytes()
    files = {"file": ("test_document.md", content, "text/markdown")}
    resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_get_pdf_file_success(client: AsyncClient):
    """Owned PDF is served with application/pdf and Content-Disposition filename."""
    await _signup_user(client)
    doc_id = await _upload_pdf(client)

    resp = await client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers["content-type"].startswith("application/pdf")
    assert "scanned_test_person_2026.pdf" in resp.headers.get("content-disposition", "")
    assert len(resp.content) > 0, "Expected non-empty PDF body"
    assert resp.content.startswith(b"%PDF"), "Body does not look like a PDF"


@pytest.mark.asyncio
async def test_get_file_rejects_markdown(client: AsyncClient):
    """Only PDF documents are viewable; markdown must answer 415."""
    await _signup_user(client)
    doc_id = await _upload_markdown(client)

    resp = await client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 415, f"Expected 415, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_get_file_unknown_document_404(client: AsyncClient):
    """A random (or other-tenant) document id must be indistinguishable: 404."""
    await _signup_user(client)
    resp = await client.get(f"/api/documents/{uuid.uuid4()}/file")
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_get_file_cross_tenant_is_404(client: AsyncClient):
    """User B must not be able to read user A's PDF via the file endpoint."""
    await _signup_user(client)
    doc_id = await _upload_pdf(client)

    # Second tenant on a fresh client session (own rate-limit bucket).
    async with _next_client() as other:
        await _signup_user(other)
        resp = await other.get(f"/api/documents/{doc_id}/file")
        assert resp.status_code == 404, f"Expected 404 cross-tenant, got {resp.status_code}"


@pytest.mark.asyncio
async def test_get_file_persists_across_restart(client: AsyncClient):
    """PDF served from DB survives container restart (simulated by clearing upload dir)."""
    await _signup_user(client)
    doc_id = await _upload_pdf(client)

    # Verify initial access works
    resp = await client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200
    original_content = resp.content

    # Simulate container restart: clear the legacy upload directory
    # (new uploads never write there, but this proves DB is source of truth)
    upload_dir = Path(get_settings().UPLOAD_DIR)
    if upload_dir.exists():
        for f in upload_dir.iterdir():
            f.unlink()

    # File should still be accessible from DB storage
    resp = await client.get(f"/api/documents/{doc_id}/file")
    assert resp.status_code == 200, f"Expected 200 after restart simulation, got {resp.status_code}: {resp.text}"
    assert resp.content == original_content, "PDF content changed after restart simulation"
    assert resp.headers["content-type"].startswith("application/pdf")
    assert "scanned_test_person_2026.pdf" in resp.headers.get("content-disposition", "")


async def main():
    """Standalone live-server runner for manual verification."""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=TIMEOUT) as live:
        await _signup_user(live)
        print("Live file endpoint smoke test not performed here; run pytest locally.")


if __name__ == "__main__":
    asyncio.run(main())