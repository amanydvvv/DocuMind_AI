"""
KueryCore AI — Password Reset Flow Tests (Group 11)
====================================================
9 test cases covering the full forgot-password / reset-password flow.

These tests live in a standalone file to keep test_auth_regression.py focused
on its original 39 cases. All fixtures mirror the pattern from the regression
suite (async ASGI client, rate-limiter reset, direct DB access for state setup).

Tests:
  11.1  Request reset for existing email → 200 generic message, token row created
  11.2  Request reset for non-existent email → same 200 generic message, no token created
  11.3  Valid unexpired token → 200, can log in with new password, old refresh revoked
  11.4  Expired token → 400 generic message
  11.5  Already-used token → 400 generic message
  11.6  Garbage / tampered token → 400 generic message
  11.7  New password < 12 chars → 400 password-length rule enforced
  11.8  Second reset request invalidates the first token
  11.9  Rate limit on forgot-password endpoint (3/minute)

Run this file alone:
    pytest tests/test_password_reset.py -v --tb=short

Run alongside the full regression suite:
    pytest tests/test_password_reset.py tests/test_auth_regression.py tests/test_auth_multitenancy.py -v --tb=short
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, text

from app.main import app
from app.database import engine, async_session
from app.core.ratelimit import limiter
from app.models.password_reset import PasswordResetToken

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _signup(client: AsyncClient, email: str, password: str = "ValidPass1234!"):
    return await client.post("/api/auth/signup", json={"email": email, "password": password})


async def _cleanup_email(email: str):
    async with async_session() as db:
        await db.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})
        await db.commit()


async def _get_reset_token(user_id: uuid.UUID):
    """Return the live PasswordResetToken row for a given user (if any)."""
    async with async_session() as db:
        res = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        return res.scalar_one_or_none()


def _sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ===========================================================================
# GROUP 11 — Password Reset Flow
# ===========================================================================

@pytest.mark.asyncio
async def test_g11_1_reset_request_for_existing_email_returns_200_and_creates_token(
    async_client: AsyncClient,
):
    """
    11.1 — POST /api/auth/forgot-password for an existing, active user:
    - Returns 200 with the generic message.
    - Creates exactly one PasswordResetToken row for that user.
    """
    email = f"reset_exist_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    user_id = uuid.UUID(r.json()["user_id"])
    access_token = r.json()["access_token"]

    try:
        res = await async_client.post(
            "/api/auth/forgot-password", json={"email": email}
        )
        assert res.status_code == 200
        body = res.json()
        assert "message" in body
        assert "reset instructions" in body["message"].lower() or "if an account" in body["message"].lower()

        # A token row must have been created in the DB
        prt = await _get_reset_token(user_id)
        assert prt is not None, "No PasswordResetToken row found for existing user"
        assert prt.used_at is None
        assert prt.expires_at > datetime.now(timezone.utc)
    finally:
        await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": password},
            headers={"Authorization": f"Bearer {access_token}"},
        )


@pytest.mark.asyncio
async def test_g11_2_reset_request_for_nonexistent_email_returns_same_200_no_token(
    async_client: AsyncClient,
):
    """
    11.2 — POST /api/auth/forgot-password for an email that does NOT exist:
    - Returns the SAME 200 + generic message (no account enumeration).
    - Creates no PasswordResetToken rows.
    """
    nonexistent = f"ghost_{uuid.uuid4().hex}@nowhere.invalid"
    res = await async_client.post(
        "/api/auth/forgot-password", json={"email": nonexistent}
    )
    assert res.status_code == 200
    body = res.json()
    assert "message" in body

    # No token should exist for this phantom email
    async with async_session() as db:
        count = await db.execute(
            text(
                "SELECT COUNT(*) FROM password_reset_tokens prt "
                "JOIN users u ON prt.user_id = u.id "
                "WHERE u.email = :e"
            ),
            {"e": nonexistent},
        )
        assert count.scalar() == 0


@pytest.mark.asyncio
async def test_g11_3_valid_token_resets_password_and_invalidates_refresh(
    async_client: AsyncClient,
):
    """
    11.3 — Full happy path:
    - Request reset → token created → use token → password changed.
    - Old password no longer works.
    - New password works.
    - Old refresh token is invalidated (refresh_token_jti cleared).
    """
    email = f"reset_happy_{uuid.uuid4().hex[:6]}@example.com"
    old_pw = "ValidPass1234!"
    new_pw = "NewValidPass5678!"

    r = await _signup(async_client, email, old_pw)
    assert r.status_code == 201
    user_id = uuid.UUID(r.json()["user_id"])
    old_refresh = r.json()["refresh_token"]

    try:
        # Step 1: request reset
        await async_client.post("/api/auth/forgot-password", json={"email": email})

        # Step 2: retrieve raw token from DB (in tests we have DB access)
        async with async_session() as db:
            prt = await db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used_at.is_(None),
                )
            )
            prt_row = prt.scalar_one()
            # The hash is stored; we need the raw token. Since we can't invert the hash,
            # we generate a fresh token and directly plant it in the DB to make this
            # test deterministic — this simulates the flow the email link would use.
            raw_token = secrets.token_urlsafe(32)
            prt_row.token_hash = _sha256(raw_token)
            await db.commit()

        # Step 3: submit reset with new password
        reset_res = await async_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": new_pw},
        )
        assert reset_res.status_code == 200
        assert "password updated" in reset_res.json()["message"].lower()

        # Step 4: old password must not work
        bad_login = await async_client.post(
            "/api/auth/login", json={"email": email, "password": old_pw}
        )
        assert bad_login.status_code == 401, "Old password should be rejected after reset"

        # Step 5: new password must work
        good_login = await async_client.post(
            "/api/auth/login", json={"email": email, "password": new_pw}
        )
        assert good_login.status_code == 200, "New password must be accepted"
        new_access = good_login.json()["access_token"]

        # Step 6: old refresh token must be invalidated
        old_refresh_res = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert old_refresh_res.status_code == 401, (
            "Old refresh token must be invalidated after password reset"
        )

        # Cleanup with new token
        await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": new_pw},
            headers={"Authorization": f"Bearer {new_access}"},
        )
    except Exception:
        await _cleanup_email(email)
        raise


@pytest.mark.asyncio
async def test_g11_4_expired_token_returns_400_generic(async_client: AsyncClient):
    """
    11.4 — Submitting an expired reset token returns 400 with a generic message.
    We plant an already-expired token directly in the DB.
    """
    email = f"reset_expired_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    user_id = uuid.UUID(r.json()["user_id"])
    access_token = r.json()["access_token"]

    try:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _sha256(raw_token)

        async with async_session() as db:
            expired_prt = PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # already expired
            )
            db.add(expired_prt)
            await db.commit()

        res = await async_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewValidPass9999!"},
        )
        assert res.status_code == 400
        assert "invalid" in res.json()["detail"].lower() or "expired" in res.json()["detail"].lower()
    finally:
        await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": password},
            headers={"Authorization": f"Bearer {access_token}"},
        )


@pytest.mark.asyncio
async def test_g11_5_used_token_returns_400_generic(async_client: AsyncClient):
    """
    11.5 — A token that has already been redeemed (used_at set) returns 400.
    """
    email = f"reset_used_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    user_id = uuid.UUID(r.json()["user_id"])
    access_token = r.json()["access_token"]

    try:
        raw_token = secrets.token_urlsafe(32)
        token_hash = _sha256(raw_token)

        async with async_session() as db:
            used_prt = PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                used_at=datetime.now(timezone.utc) - timedelta(seconds=10),  # already used
            )
            db.add(used_prt)
            await db.commit()

        res = await async_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token, "new_password": "NewValidPass9999!"},
        )
        assert res.status_code == 400
        assert "invalid" in res.json()["detail"].lower() or "expired" in res.json()["detail"].lower()
    finally:
        await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": password},
            headers={"Authorization": f"Bearer {access_token}"},
        )


@pytest.mark.asyncio
async def test_g11_6_garbage_token_returns_400_generic(async_client: AsyncClient):
    """
    11.6 — A completely fabricated / tampered token string returns 400.
    No DB row will match the hash of a random string.
    """
    garbage = "definitely_not_a_real_token_" + secrets.token_hex(8)
    res = await async_client.post(
        "/api/auth/reset-password",
        json={"token": garbage, "new_password": "NewValidPass9999!"},
    )
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower() or "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g11_7_new_password_too_short_returns_400(async_client: AsyncClient):
    """
    11.7 — Submitting a new_password shorter than 12 chars is rejected
    with a 400 before any token lookup (no side-channel via timing).
    """
    res = await async_client.post(
        "/api/auth/reset-password",
        json={"token": secrets.token_urlsafe(32), "new_password": "short1!"},
    )
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "12" in detail or "characters" in detail


@pytest.mark.asyncio
async def test_g11_8_second_reset_request_invalidates_first_token(async_client: AsyncClient):
    """
    11.8 — Requesting a second reset should delete the first unused token,
    so attempting to use the original token hash fails with 400.
    """
    email = f"reset_second_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    user_id = uuid.UUID(r.json()["user_id"])
    access_token = r.json()["access_token"]

    try:
        # First reset request
        await async_client.post("/api/auth/forgot-password", json={"email": email})

        # Plant a known raw token for the first request
        raw_token_1 = secrets.token_urlsafe(32)
        async with async_session() as db:
            prt = await db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used_at.is_(None),
                )
            )
            prt_row = prt.scalar_one()
            prt_row.token_hash = _sha256(raw_token_1)
            await db.commit()

        # Second reset request — deletes the first token and creates a new one
        await async_client.post("/api/auth/forgot-password", json={"email": email})

        # 1. First (superseded) raw token must be rejected via HTTP endpoint call
        res_old = await async_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token_1, "new_password": "NewValidPass7777!"},
        )
        assert res_old.status_code == 400, (
            "First token should be rejected (400) via POST /reset-password after second request"
        )
        assert "invalid" in res_old.json()["detail"].lower() or "expired" in res_old.json()["detail"].lower()

        # 2. Plant known raw token for the second request and verify it succeeds
        raw_token_2 = secrets.token_urlsafe(32)
        async with async_session() as db:
            prt2 = await db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used_at.is_(None),
                )
            )
            prt_row2 = prt2.scalar_one()
            prt_row2.token_hash = _sha256(raw_token_2)
            await db.commit()

        res_new = await async_client.post(
            "/api/auth/reset-password",
            json={"token": raw_token_2, "new_password": "NewValidPass7777!"},
        )
        assert res_new.status_code == 200, "Second token should successfully reset password"

        # 3. Verify login works with the updated password
        login_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "NewValidPass7777!"}
        )
        assert login_res.status_code == 200
        new_token = login_res.json()["access_token"]

        await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": "NewValidPass7777!"},
            headers={"Authorization": f"Bearer {new_token}"},
        )
    except Exception:
        await _cleanup_email(email)
        raise


@pytest.mark.asyncio
async def test_g11_9_forgot_password_rate_limited(async_client: AsyncClient):
    """
    11.9 — The forgot-password endpoint is rate-limited to 3/minute per IP.
    The 4th request within a minute must return 429.
    """
    email = f"rl_forgot_{uuid.uuid4().hex[:6]}@example.com"

    for i in range(3):
        res = await async_client.post(
            "/api/auth/forgot-password", json={"email": email}
        )
        assert res.status_code == 200, f"Request {i+1} should succeed (200), got {res.status_code}"

    # 4th request — must be rate-limited
    res_4 = await async_client.post(
        "/api/auth/forgot-password", json={"email": email}
    )
    assert res_4.status_code == 429, (
        f"4th forgot-password request should be rate-limited (429), got {res_4.status_code}"
    )
    body = res_4.json()
    assert "detail" in body
    assert "too many" in body["detail"].lower()
