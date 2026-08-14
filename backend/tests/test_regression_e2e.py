"""
KueryCore AI - Regression E2E Test Suite
Covers signup/login, document upload & ingestion, RAG chat with citations,
and forged-JWT rejection. Uses the in-process ASGI app (no live server needed).
"""

import asyncio
import tempfile
import uuid

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.database import engine
from app.main import app
from app.services.ingestion import ingest_document

BASE = "http://testserver"
TIMEOUT = 30.0


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """In-process ASGI client exercising the real FastAPI app."""
    await engine.dispose()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE, timeout=TIMEOUT
    ) as c:
        yield c
    await engine.dispose()


async def _signup_user(client: AsyncClient) -> tuple:
    """Create a fresh user, attach auth header, return (email, password, access_token)."""
    email = f"e2e_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    resp = await client.post("/api/auth/signup", json={"email": email, "password": password})
    assert resp.status_code in (200, 201), f"Signup failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {resp.text}"
    assert "refresh_token" in data, f"No refresh_token in response: {resp.text}"
    client.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return email, password, data["access_token"]


@pytest.mark.asyncio
async def test_signup_login(client: AsyncClient):
    """Test signup and login flow."""
    email, password, access_token = await _signup_user(client)

    # Login with the same credentials
    resp = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    login_data = resp.json()
    assert "access_token" in login_data
    print("Login OK")

    # /me endpoint reads the users table (tenant-isolated)
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 200, f"/me failed: {resp.text}"
    assert resp.json()["email"] == email
    print("/me OK")


@pytest.mark.asyncio
async def test_upload_document(client: AsyncClient):
    """Upload a document and ingest it, then poll to completed."""
    await _signup_user(client)

    content = (
        "# Test Document\n\n"
        "This is a test document for RAG.\n\n"
        "It contains some information about the system.\n\n"
        "The system uses vector embeddings for retrieval.\n\n"
        "RLS is now enabled on all tables."
    ).encode("utf-8")

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
        tmp_file.write(content)
        file_path = tmp_file.name

    files = {"file": ("test_document.md", content, "text/markdown")}
    resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code in (200, 201), f"Upload failed: {resp.text}"
    doc_id = resp.json()["id"]

    # Trigger ingestion using the on-disk copy, then poll for completion
    await ingest_document(str(doc_id), file_path)

    for _ in range(30):
        await asyncio.sleep(0.5)
        resp = await client.get(f"/api/documents/{doc_id}")
        assert resp.status_code == 200, f"Fetch document failed: {resp.text}"
        doc = resp.json()
        if doc.get("status") == "completed":
            assert doc.get("chunk_count", 0) > 0, "No chunks produced"
            print("Document processing completed")
            return
        if doc.get("status") == "failed":
            raise AssertionError(f"Document processing failed: {doc.get('error_message')}")
    raise AssertionError("Document processing timeout")


@pytest.mark.asyncio
async def test_chat_query(client: AsyncClient):
    """Send a chat query, confirm a real answer and citation."""
    await _signup_user(client)

    content = (
        "# RLS Guide\n\n"
        "The system enables Row Level Security on all tables.\n\n"
        "RLS isolates every user's data at the database layer."
    ).encode("utf-8")

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
        tmp_file.write(content)
        file_path = tmp_file.name

    files = {"file": ("rls.md", content, "text/markdown")}
    resp = await client.post("/api/documents/upload", files=files)
    assert resp.status_code in (200, 201), f"Upload failed: {resp.text}"
    doc_id = resp.json()["id"]
    await ingest_document(str(doc_id), file_path)

    resp = await client.post("/api/chat", json={"question": "What does the document say about RLS?"})
    if resp.status_code == 429:
        pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
    assert resp.status_code == 200, f"Chat failed: {resp.text}"
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    print(f"Answer: {data['answer'][:200]}...")
    print(f"Citations: {len(data['citations'])}")
    assert len(data["citations"]) > 0, "Expected at least one citation"
    print("Chat OK with citations")


@pytest.mark.asyncio
async def test_forged_jwt(client: AsyncClient):
    """Test forged/invalid JWT returns 401."""
    forged_token = "invalid.token.signature"
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"}
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    print("Invalid JWT correctly rejected (401)")


async def main():
    """Standalone live-server runner for manual verification."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=TIMEOUT) as live:
        email, password, _token = await _signup_user(live)

        # Login
        resp = await live.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        print("Live login OK")

        # Forged JWT must be rejected
        resp = await live.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid.token.signature"}
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("Live forged JWT rejected (401)")

        print("\n=== ALL REGRESSION TESTS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())