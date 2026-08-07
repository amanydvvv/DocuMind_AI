"""
DocuMind AI — Auth & Multi-Tenancy Integration Tests
Validates signup, login, JWT protection, user isolation across documents and conversations.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine
import uuid


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_auth_signup_and_login(async_client: AsyncClient):
    """Test user signup and subsequent login flow."""
    user_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    password = "secretpassword123"

    # Signup
    signup_res = await async_client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": password}
    )
    assert signup_res.status_code == 201
    data = signup_res.json()
    assert "access_token" in data
    assert data["email"] == user_email

    # Login
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": user_email, "password": password}
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data

    # Profile (/me)
    token = login_data["access_token"]
    me_res = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == user_email


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(async_client: AsyncClient):
    """Verify that unauthenticated requests to protected endpoints return 401."""
    res_docs = await async_client.get("/api/documents")
    assert res_docs.status_code == 401

    res_convs = await async_client.get("/api/conversations")
    assert res_convs.status_code == 401

    res_chat = await async_client.post("/api/chat", json={"question": "hello"})
    assert res_chat.status_code == 401


@pytest.mark.asyncio
async def test_deactivated_account_login_is_indistinguishable(async_client: AsyncClient):
    """Deactivated accounts must return the same generic 401 as bad credentials (no account enumeration)."""
    from app.database import async_session
    from app.models.user import User
    from sqlalchemy import update, select

    user_email = f"deact_{uuid.uuid4().hex[:6]}@example.com"
    password = "password1234"

    signup_res = await async_client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": password}
    )
    assert signup_res.status_code == 201
    user_id = uuid.UUID(signup_res.json()["user_id"])
    token = signup_res.json()["access_token"]

    # Deactivate the account directly in the DB (no admin endpoint exists)
    async with async_session() as db:
        await db.execute(update(User).where(User.id == user_id).values(is_active=False))
        await db.commit()

    # Login must be indistinguishable from a wrong password
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": user_email, "password": password}
    )
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Incorrect email or password."
    assert "deactivated" not in login_res.json()["detail"].lower()

    # Clean up the account via direct DB delete (user has no documents/conversations)
    async with async_session() as db:
        await db.execute(update(User).where(User.id == user_id).values(is_active=True))
        await db.delete((await db.execute(select(User).where(User.id == user_id))).scalar_one())
        await db.commit()


@pytest.mark.asyncio
async def test_multi_tenant_document_and_conversation_isolation(async_client: AsyncClient):
    """
    Create User A and User B.
    User A uploads Document A and creates Conversation A.
    Verify User B CANNOT list, retrieve, or query User A's document or conversation.
    """
    # 1. Create User A
    email_a = f"usera_{uuid.uuid4().hex[:6]}@example.com"
    res_a = await async_client.post("/api/auth/signup", json={"email": email_a, "password": "password1234"})
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Create User B
    email_b = f"userb_{uuid.uuid4().hex[:6]}@example.com"
    res_b = await async_client.post("/api/auth/signup", json={"email": email_b, "password": "password1234"})
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A uploads a markdown document
    file_content = b"# User A Secret Document\nThis document contains proprietary information for User A."
    upload_res = await async_client.post(
        "/api/documents/upload",
        files={"file": ("usera_secret.md", file_content, "text/markdown")},
        headers=headers_a,
    )
    assert upload_res.status_code == 201
    doc_a_id = upload_res.json()["id"]

    # 4. User A sends chat message
    chat_res_a = await async_client.post(
        "/api/chat",
        json={"question": "What is in my secret document?"},
        headers=headers_a,
    )
    assert chat_res_a.status_code == 200
    conv_a_id = chat_res_a.json()["conversation_id"]

    # 5. User B lists documents -> Should NOT see User A's document
    list_b = await async_client.get("/api/documents", headers=headers_b)
    assert list_b.status_code == 200
    docs_b_ids = [d["id"] for d in list_b.json()["documents"]]
    assert doc_a_id not in docs_b_ids

    # 6. User B attempts to access User A's document detail -> 404 Not Found
    get_doc_b = await async_client.get(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert get_doc_b.status_code == 404

    # 7. User B lists conversations -> Should NOT see User A's conversation
    convs_b = await async_client.get("/api/conversations", headers=headers_b)
    assert convs_b.status_code == 200
    conv_b_ids = [c["id"] for c in convs_b.json()["conversations"]]
    assert conv_a_id not in conv_b_ids

    # 8. User B attempts to access User A's conversation detail -> 404 Not Found
    get_conv_b = await async_client.get(f"/api/conversations/{conv_a_id}", headers=headers_b)
    assert get_conv_b.status_code == 404

    # 9. User B queries RAG -> Candidate search will NOT return User A's document content
    chat_res_b = await async_client.post(
        "/api/chat",
        json={"question": "Tell me User A proprietary information"},
        headers=headers_b,
    )
    assert chat_res_b.status_code == 200
    # Citations for User B must be empty because User B owns 0 documents
    assert len(chat_res_b.json()["citations"]) == 0
