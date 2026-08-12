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


from app.core.ratelimit import limiter


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    """Reset slowapi rate limiter memory storage before each test for clean isolation."""
    limiter.reset()
    yield
    limiter.reset()


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

    # Clean up account so the test leaves zero residual data in the shared DB
    del_res = await async_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204


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

    # 10. Clean up both accounts so the test leaves zero residual data in the shared DB
    del_a = await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": "password1234"},
        headers=headers_a,
    )
    assert del_a.status_code == 204
    del_b = await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": "password1234"},
        headers=headers_b,
    )
    assert del_b.status_code == 204


@pytest.mark.asyncio
async def test_account_deletion_requires_correct_password(async_client: AsyncClient):
    """Verify DELETE /api/auth/me rejects incorrect password with 401 and preserves account."""
    user_email = f"del_pass_{uuid.uuid4().hex[:6]}@example.com"
    password = "CorrectPass123!"

    signup_res = await async_client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": password}
    )
    assert signup_res.status_code == 201
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt deletion with WRONG password
    del_fail = await async_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": "WrongPassword123!"},
        headers=headers,
    )
    assert del_fail.status_code == 401
    assert "Incorrect email or password" in del_fail.json()["detail"]

    # Profile endpoint must still function normally
    me_res = await async_client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == user_email

    # Clean up account with correct password so the test leaves zero residual data
    del_ok = await async_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": password},
        headers=headers,
    )
    assert del_ok.status_code == 204


@pytest.mark.asyncio
async def test_account_deletion_purges_user_and_cascade_data(async_client: AsyncClient):
    """Verify DELETE /api/auth/me purges user, docs, chunks, conversations, messages, query_logs, refresh token, and files."""
    from app.models import User, Document, Chunk, Conversation, Message, QueryLog
    from app.database import async_session
    from sqlalchemy import select, func

    user_email = f"del_full_{uuid.uuid4().hex[:6]}@example.com"
    password = "CorrectPass123!"

    signup_res = await async_client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": password}
    )
    assert signup_res.status_code == 201
    data = signup_res.json()
    token = data["access_token"]
    refresh_token = data["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve user_id
    me_init = await async_client.get("/api/auth/me", headers=headers)
    assert me_init.status_code == 200
    user_id = uuid.UUID(me_init.json()["id"])

    # Upload physical document
    file_content = b"# Document To Delete\nPhysical file cleanup test."
    upload_res = await async_client.post(
        "/api/documents/upload",
        files={"file": ("to_delete.md", file_content, "text/markdown")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = uuid.UUID(upload_res.json()["id"])

    # Verify document bytes are stored in DB (no local file anymore)
    async with async_session() as db:
        doc_obj = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        assert doc_obj.raw_bytes == file_content, "Document bytes should be stored in raw_bytes column"

    # Create conversation
    chat_res = await async_client.post(
        "/api/chat",
        json={"question": "Test query before deletion"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    conv_id = uuid.UUID(chat_res.json()["conversation_id"])

    # Execute account deletion with CORRECT password
    del_res = await async_client.request(
        "DELETE",
        "/api/auth/me",
        json={"password": password},
        headers=headers,
    )
    assert del_res.status_code == 204

    # Old access token must now be rejected with 401 across all protected endpoints
    assert (await async_client.get("/api/auth/me", headers=headers)).status_code == 401
    assert (await async_client.get("/api/documents", headers=headers)).status_code == 401
    assert (await async_client.get("/api/conversations", headers=headers)).status_code == 401

    # Old refresh token must be invalidated: CAS rotation fails because the user row is gone
    refresh_res = await async_client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 401

    # DB Assertions: Directly verify CASCADE purged all child table rows
    async with async_session() as db:
        user_cnt = (await db.execute(select(func.count()).where(User.id == user_id))).scalar_one()
        doc_cnt = (await db.execute(select(func.count()).where(Document.user_id == user_id))).scalar_one()
        chunk_cnt = (await db.execute(select(func.count()).where(Chunk.document_id == doc_id))).scalar_one()
        conv_cnt = (await db.execute(select(func.count()).where(Conversation.user_id == user_id))).scalar_one()
        msg_cnt = (await db.execute(select(func.count()).where(Message.conversation_id == conv_id))).scalar_one()
        log_cnt = (await db.execute(select(func.count()).where(QueryLog.user_id == user_id))).scalar_one()

        assert user_cnt == 0, "User record must be deleted"
        assert doc_cnt == 0, "Document records must be cascade deleted"
        assert chunk_cnt == 0, "Chunk records must be cascade deleted"
        assert conv_cnt == 0, "Conversation records must be cascade deleted"
        assert msg_cnt == 0, "Message records must be cascade deleted"
        assert log_cnt == 0, "QueryLog records must be cascade deleted"

    # Old refresh token is invalid because the jti lives on the users row, now gone
    # (already asserted via /api/auth/refresh above)

    # No physical file to check — raw_bytes goes away with the row


@pytest.mark.asyncio
async def test_rate_limit_cannot_be_bypassed_via_spoofed_header(async_client: AsyncClient):
    """
    Verify that varying the prepended client-supplied X-Forwarded-For IP does NOT bypass rate limits.
    Signup endpoint is limited to 5/minute.
    """
    password = "Password123!"
    created: list[tuple[str, str]] = []  # (access_token, password) for cleanup

    try:
        # Perform 5 signups (within 5/min limit) with spoofed prepended headers.
        # On Render a client can prepend arbitrary IPs to X-Forwarded-For, so a
        # key that trusts that header is trivially bypassable. The fix must
        # ignore X-Forwarded-For entirely: every request shares the same
        # unspoofable key (here the 127.0.0.1 ASGI peer) regardless of the
        # spoofed header values.
        for i in range(5):
            email = f"ratelimit_{i}_{uuid.uuid4().hex[:4]}@example.com"
            spoofed_header = f"1.2.3.{i+1}, 203.0.113.100"
            res = await async_client.post(
                "/api/auth/signup",
                json={"email": email, "password": password},
                headers={"X-Forwarded-For": spoofed_header},
            )
            assert res.status_code == 201, f"Signup {i+1} should succeed"
            created.append((res.json()["access_token"], password))

        # 6th request with a DIFFERENT spoofed prepended IP -> Must still get 429
        bypass_email = f"ratelimit_bypass_{uuid.uuid4().hex[:4]}@example.com"
        res_6 = await async_client.post(
            "/api/auth/signup",
            json={"email": bypass_email, "password": password},
            headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.100"},
        )
        assert res_6.status_code == 429
        assert "too many requests" in res_6.json().get("detail", "").lower()
    finally:
        # Clean up the created users so the suite leaves zero residual data
        for token, pw in created:
            await async_client.request(
                "DELETE",
                "/api/auth/me",
                json={"password": pw},
                headers={"Authorization": f"Bearer {token}"},
            )


@pytest.mark.asyncio
async def test_rate_limit_direct_origin_without_cf_header_cannot_be_bypassed(async_client: AsyncClient):
    """
    Verify that direct-origin requests (without CF-Connecting-IP) with custom X-Forwarded-For
    headers are NOT allowed to bypass rate limiting by rotating X-Forwarded-For values.
    """
    password = "Password123!"
    created: list[tuple[str, str]] = []

    try:
        # Perform 5 signups with varying custom X-Forwarded-For headers and NO CF-Connecting-IP
        for i in range(5):
            email = f"direct_origin_{i}_{uuid.uuid4().hex[:4]}@example.com"
            res = await async_client.post(
                "/api/auth/signup",
                json={"email": email, "password": password},
                headers={"X-Forwarded-For": f"10.0.0.{i+1}"},
            )
            assert res.status_code == 201, f"Direct origin signup {i+1} should succeed"
            created.append((res.json()["access_token"], password))

        # 6th request with a different X-Forwarded-For header and NO CF-Connecting-IP -> 429
        bypass_email = f"direct_origin_bypass_{uuid.uuid4().hex[:4]}@example.com"
        res_6 = await async_client.post(
            "/api/auth/signup",
            json={"email": bypass_email, "password": password},
            headers={"X-Forwarded-For": "10.0.0.99"},
        )
        assert res_6.status_code == 429
        assert "too many requests" in res_6.json().get("detail", "").lower()
    finally:
        for token, pw in created:
            await async_client.request(
                "DELETE",
                "/api/auth/me",
                json={"password": pw},
                headers={"Authorization": f"Bearer {token}"},
            )




@pytest.mark.asyncio
async def test_deactivated_user_cannot_access_api(async_client: AsyncClient):
    """
    A deactivated account (is_active=False) must be rejected with 403 on all
    bearer-token-protected endpoints — even when presenting a valid, unexpired JWT.

    Security gap fixed: get_current_user() previously only checked user existence,
    not is_active. A deactivated account with a valid token could still access the API.
    """
    from sqlalchemy import text
    from app.database import async_session

    user_email = f"deactivated_{uuid.uuid4().hex[:6]}@example.com"
    password = "testpassword123"

    # 1. Create a valid account and confirm it works before deactivation
    signup_res = await async_client.post(
        "/api/auth/signup",
        json={"email": user_email, "password": password},
    )
    assert signup_res.status_code == 201, f"Signup failed: {signup_res.text}"
    token = signup_res.json()["access_token"]

    me_res = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200

    # 2. Directly deactivate the account via DB (simulates an admin/ops action)
    async with async_session() as session:
        await session.execute(
            text("UPDATE users SET is_active = FALSE WHERE email = :email"),
            {"email": user_email},
        )
        await session.commit()

    # 3. Same valid token must now return 403 — not 200, not 401
    me_after = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_after.status_code == 403, (
        f"Expected 403 for deactivated account, got {me_after.status_code}: {me_after.text}"
    )
    assert "deactivated" in me_after.json().get("detail", "").lower()

    # 4. Documents endpoint must also reject — confirms the fix lives in the shared
    #    get_current_user() dependency, not just /api/auth/me
    docs_res = await async_client.get(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert docs_res.status_code == 403

    # Cleanup: remove the test user
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": user_email},
        )
        await session.commit()
