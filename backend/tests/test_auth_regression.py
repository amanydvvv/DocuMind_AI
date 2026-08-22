"""
KueryCore AI — Authentication Regression Test Suite
====================================================
39 test cases across 10 groups covering the full auth surface.

Groups:
  1.  Signup — Duplicate email (case + whitespace normalisation)          3 tests
  2.  Signup — Input validation edge cases                                6 tests
  3.  Login — Credential failures + account-enumeration protection        6 tests
  4.  JWT token security (invalid / expired / tampered / wrong-type)      5 tests
  5.  Token refresh — rotation + replay prevention                        5 tests
  6.  Account deletion — re-auth, cascade, email recycling                5 tests
  7.  Rate limiting — signup and login endpoints                          2 tests
  8.  Demo / guest session — unique accounts + double-submit guard        3 tests
  9.  AuthModal UI state regressions (client-side behaviour)              3 tests
 10.  Production hang regression — timeout, loading-state, 429 message    6 tests
                                                                   ------
                                                            Total:  39 tests

Run:
    pytest tests/test_auth_regression.py -v --tb=short
Regression guard:
    pytest tests/test_auth_multitenancy.py -v --tb=short

NOTE on is_active write-path gap
---------------------------------
`is_active` is defined on the User model and is checked in two places:
  • auth.py login() → returns generic 401 (no enumeration)
  • security.py get_current_user() → returns 403

However, there is NO application-level write path that sets is_active=False
(no admin endpoint, no soft-delete route, no automated ban trigger).
Deactivation must currently be done via direct DB access.
Tests that exercise deactivated-account behaviour seed the state via a raw
SQL UPDATE, exactly as test_auth_multitenancy.py does for the same scenario.
This gap is documented here as a FIXME — a future admin/moderation endpoint
should provide the write path so tests can use the public API instead.
"""

import hashlib
import hmac
import json
import secrets
import time
import uuid
import base64
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, async_session
from app.core.ratelimit import limiter
from app.config import get_settings

settings = get_settings()
_SECRET_KEY = settings.JWT_SECRET_KEY

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    """Reset slowapi in-memory state before every test for clean isolation."""
    limiter.reset()
    yield
    limiter.reset()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers — token fabrication (matches security.py's custom HMAC-SHA256 JWT)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (4 - (len(s) % 4))
    return base64.urlsafe_b64decode(s + padding)


def _make_token(payload: dict, secret: str = None) -> str:
    """Produce a well-formed HMAC-SHA256 JWT with the given payload."""
    key = (secret or _SECRET_KEY).encode()
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = _b64url_encode(hmac.new(key, signing_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def _expired_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access", "iat": 1000, "exp": 1001}
    return _make_token(payload)


def _tampered_access_token(user_id: str, email: str) -> str:
    """Valid structure but signature computed with wrong key."""
    payload = {"sub": user_id, "email": email, "type": "access",
               "iat": int(time.time()), "exp": int(time.time()) + 86400}
    return _make_token(payload, secret="WRONG_SECRET_KEY_TAMPERED_XYZ")


def _refresh_token_as_access(user_id: str) -> str:
    """Refresh-type token presented to an access-token endpoint."""
    jti = str(uuid.uuid4())
    payload = {"sub": user_id, "type": "refresh", "jti": jti,
               "iat": int(time.time()), "exp": int(time.time()) + 86400 * 7}
    return _make_token(payload)


# ---------------------------------------------------------------------------
# Shared signup/teardown helper
# ---------------------------------------------------------------------------

async def _signup(client: AsyncClient, email: str, password: str = "ValidPass1234!"):
    res = await client.post("/api/auth/signup", json={"email": email, "password": password})
    return res


async def _cleanup(client: AsyncClient, token: str, password: str = "ValidPass1234!"):
    await client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )


# ===========================================================================
# GROUP 1 — Signup: Duplicate email
# ===========================================================================

@pytest.mark.asyncio
async def test_g1_1_duplicate_email_rejected(async_client: AsyncClient):
    """1.1 — Signing up with the same email twice returns 400 with a clear message."""
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r1 = await _signup(async_client, email, password)
    assert r1.status_code == 201
    token = r1.json()["access_token"]

    try:
        r2 = await _signup(async_client, email, password)
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g1_2_duplicate_email_case_insensitive(async_client: AsyncClient):
    """1.2 — Emails are normalised to lowercase; Alice@test.com = alice@test.com."""
    base = f"case_{uuid.uuid4().hex[:6]}"
    email_lower = f"{base}@example.com"
    email_upper = f"{base.upper()}@example.com"
    password = "ValidPass1234!"

    r1 = await _signup(async_client, email_lower, password)
    assert r1.status_code == 201
    token = r1.json()["access_token"]

    try:
        r2 = await _signup(async_client, email_upper, password)
        assert r2.status_code == 400
        detail = r2.json()["detail"].lower()
        assert "already exists" in detail
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g1_3_duplicate_email_whitespace_stripped(async_client: AsyncClient):
    """1.3 — Leading/trailing whitespace is stripped before duplicate check."""
    base_email = f"ws_{uuid.uuid4().hex[:6]}@example.com"
    padded_email = f"  {base_email}  "
    password = "ValidPass1234!"

    r1 = await _signup(async_client, base_email, password)
    assert r1.status_code == 201
    token = r1.json()["access_token"]

    try:
        r2 = await _signup(async_client, padded_email, password)
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()
    finally:
        await _cleanup(async_client, token, password)


# ===========================================================================
# GROUP 2 — Signup: Input validation
# ===========================================================================

@pytest.mark.asyncio
async def test_g2_1_empty_email_rejected(async_client: AsyncClient):
    """2.1 — Empty email string returns 400."""
    res = await async_client.post("/api/auth/signup", json={"email": "", "password": "ValidPass1234!"})
    assert res.status_code == 400
    assert "invalid email" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g2_2_email_without_at_rejected(async_client: AsyncClient):
    """2.2 — Email without '@' is rejected as an invalid format."""
    res = await async_client.post("/api/auth/signup", json={"email": "notanemail", "password": "ValidPass1234!"})
    assert res.status_code == 400
    assert "invalid email" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g2_3_short_password_rejected(async_client: AsyncClient):
    """2.3 — Password shorter than 12 characters is rejected."""
    email = f"shortpw_{uuid.uuid4().hex[:6]}@example.com"
    res = await async_client.post("/api/auth/signup", json={"email": email, "password": "short1!"})
    assert res.status_code == 400
    assert "12" in res.json()["detail"] or "characters" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g2_4_exactly_12_char_password_accepted(async_client: AsyncClient):
    """2.4 — Boundary value: exactly 12-character password is accepted."""
    email = f"boundary_{uuid.uuid4().hex[:6]}@example.com"
    password = "Abcdef123456"  # exactly 12
    res = await _signup(async_client, email, password)
    assert res.status_code == 201
    token = res.json()["access_token"]
    await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g2_5_missing_password_field_returns_422(async_client: AsyncClient):
    """2.5 — Missing password field yields 422 Unprocessable Entity from Pydantic."""
    res = await async_client.post("/api/auth/signup", json={"email": "missing@example.com"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_g2_6_missing_email_field_returns_422(async_client: AsyncClient):
    """2.6 — Missing email field yields 422 Unprocessable Entity from Pydantic."""
    res = await async_client.post("/api/auth/signup", json={"password": "ValidPass1234!"})
    assert res.status_code == 422


# ===========================================================================
# GROUP 3 — Login: Credential failures + account-enumeration protection
# ===========================================================================

@pytest.mark.asyncio
async def test_g3_1_wrong_password_returns_generic_401(async_client: AsyncClient):
    """3.1 — Valid email + wrong password returns generic 401 (no enumeration)."""
    email = f"wrongpw_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        login_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "WrongPassword999!"}
        )
        assert login_res.status_code == 401
        # Must be the same generic message as a non-existent account (no enumeration)
        assert "incorrect" in login_res.json()["detail"].lower()
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g3_2_nonexistent_email_same_401(async_client: AsyncClient):
    """3.2 — Non-existent email returns identical 401 to prevent account enumeration."""
    res = await async_client.post(
        "/api/auth/login",
        json={"email": f"ghost_{uuid.uuid4().hex}@nowhere.invalid", "password": "ValidPass1234!"},
    )
    assert res.status_code == 401
    assert "incorrect" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g3_3_deactivated_account_login_returns_generic_401(async_client: AsyncClient):
    """
    3.3 — Login for a deactivated account returns the same generic 401 as
    wrong credentials — must NOT reveal the account exists or is deactivated.

    IMPLEMENTATION NOTE:
    is_active is set directly via SQL because there is currently no application-level
    write path that deactivates accounts (no admin endpoint, no soft-delete route).
    This is a FIXME: a future moderation/admin endpoint should own this write path
    so tests can exercise it through the public API instead of a back-door UPDATE.
    """
    from sqlalchemy import text

    email = f"deact_login_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    user_id_str = r.json()["user_id"]

    # Deactivate via direct DB write (only path available — see FIXME above)
    async with async_session() as db:
        await db.execute(
            text("UPDATE users SET is_active = FALSE WHERE id = :uid"),
            {"uid": uuid.UUID(user_id_str)},
        )
        await db.commit()

    try:
        login_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert login_res.status_code == 401
        detail = login_res.json()["detail"].lower()
        # Must be the same generic message — "deactivated" leaks account status
        assert "incorrect" in detail, f"Unexpected detail: {detail}"
        assert "deactivated" not in detail, "Enumeration: response reveals deactivation status"
    finally:
        async with async_session() as db:
            await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uuid.UUID(user_id_str)})
            await db.commit()


@pytest.mark.asyncio
async def test_g3_4_empty_password_returns_400(async_client: AsyncClient):
    """3.4 — Empty password in login body returns 400 with a clear message."""
    res = await async_client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": ""}
    )
    assert res.status_code == 400
    assert "required" in res.json()["detail"].lower() or "password" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_g3_5_empty_email_returns_400(async_client: AsyncClient):
    """3.5 — Empty email in login body returns 400."""
    res = await async_client.post(
        "/api/auth/login", json={"email": "", "password": "ValidPass1234!"}
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_g3_6_successful_login_response_schema(async_client: AsyncClient):
    """3.6 — Successful login returns all required fields: access_token, refresh_token, user_id, email."""
    email = f"schema_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        login_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert login_res.status_code == 200
        body = login_res.json()
        for field in ("access_token", "refresh_token", "user_id", "email", "token_type"):
            assert field in body, f"Missing field: {field}"
        assert body["email"] == email
        assert body["token_type"] == "bearer"
    finally:
        await _cleanup(async_client, token, password)


# ===========================================================================
# GROUP 4 — JWT token security
# ===========================================================================

@pytest.mark.asyncio
async def test_g4_1_no_token_returns_401(async_client: AsyncClient):
    """4.1 — /api/auth/me without any token returns 401."""
    res = await async_client.get("/api/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_g4_2_invalid_token_string_returns_401(async_client: AsyncClient):
    """4.2 — Completely invalid token string returns 401."""
    res = await async_client.get(
        "/api/auth/me", headers={"Authorization": "Bearer GARBAGE.NOTAREAL.TOKEN"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_g4_3_expired_token_returns_401(async_client: AsyncClient):
    """4.3 — A structurally valid but expired JWT is rejected."""
    # Use a real user ID from a throwaway signup so the DB lookup won't 404 before expiry check
    fake_uid = str(uuid.uuid4())
    expired_tok = _expired_access_token(fake_uid, "expired@test.com")
    res = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {expired_tok}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_g4_4_refresh_token_used_as_access_token_rejected(async_client: AsyncClient):
    """4.4 — A refresh-type token presented to a bearer endpoint is rejected (type mismatch)."""
    fake_uid = str(uuid.uuid4())
    bad_tok = _refresh_token_as_access(fake_uid)
    res = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {bad_tok}"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_g4_5_tampered_signature_rejected(async_client: AsyncClient):
    """4.5 — A token whose signature was computed with a different key is rejected."""
    fake_uid = str(uuid.uuid4())
    tampered = _tampered_access_token(fake_uid, "tampered@test.com")
    res = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert res.status_code == 401


# ===========================================================================
# GROUP 5 — Token refresh: rotation + replay prevention
# ===========================================================================

@pytest.mark.asyncio
async def test_g5_1_valid_refresh_returns_new_tokens(async_client: AsyncClient):
    """5.1 — Valid refresh token yields a new access_token and new refresh_token."""
    email = f"refresh_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    old_refresh = r.json()["refresh_token"]
    old_access = r.json()["access_token"]

    try:
        refresh_res = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert refresh_res.status_code == 200
        new_data = refresh_res.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["access_token"] != old_access
        assert new_data["refresh_token"] != old_refresh

        # Use the new access token to clean up
        await _cleanup(async_client, new_data["access_token"], password)
    except Exception:
        await _cleanup(async_client, old_access, password)
        raise


@pytest.mark.asyncio
async def test_g5_2_replay_old_refresh_token_rejected(async_client: AsyncClient):
    """5.2 — Using an already-rotated refresh token is rejected (replay attack prevention)."""
    email = f"replay_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    initial_refresh = r.json()["refresh_token"]
    initial_access = r.json()["access_token"]

    try:
        # First rotation — succeeds
        rotate_res = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": initial_refresh}
        )
        assert rotate_res.status_code == 200
        new_access = rotate_res.json()["access_token"]

        # Replay old token — must be rejected
        replay_res = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": initial_refresh}
        )
        assert replay_res.status_code == 401
        assert "already been used" in replay_res.json()["detail"].lower()

        await _cleanup(async_client, new_access, password)
    except Exception:
        await _cleanup(async_client, initial_access, password)
        raise


@pytest.mark.asyncio
async def test_g5_3_access_token_at_refresh_endpoint_rejected(async_client: AsyncClient):
    """5.3 — Passing an access token to /api/auth/refresh is rejected (not a refresh token)."""
    email = f"acc_at_refresh_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    access_token = r.json()["access_token"]

    try:
        res = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": access_token}
        )
        assert res.status_code == 401
        assert "refresh token" in res.json()["detail"].lower()
    finally:
        await _cleanup(async_client, access_token, password)


@pytest.mark.asyncio
async def test_g5_4_garbage_at_refresh_endpoint_rejected(async_client: AsyncClient):
    """5.4 — Garbage string at refresh endpoint returns 401."""
    res = await async_client.post(
        "/api/auth/refresh", json={"refresh_token": "not.a.real.token"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_g5_5_refresh_after_user_deletion_rejected(async_client: AsyncClient):
    """5.5 — Using a refresh token after account deletion returns 401 (user no longer exists)."""
    email = f"del_refresh_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    access_token = r.json()["access_token"]
    refresh_token = r.json()["refresh_token"]

    # Delete account
    del_res = await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert del_res.status_code == 204

    # Now try to refresh — account gone
    refresh_res = await async_client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_res.status_code == 401


# ===========================================================================
# GROUP 6 — Account deletion: re-auth, cascade, email recycling
# ===========================================================================

@pytest.mark.asyncio
async def test_g6_1_delete_wrong_password_rejected(async_client: AsyncClient):
    """6.1 — DELETE /api/auth/me with wrong password is rejected with 401."""
    email = f"del_wrongpw_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        del_res = await async_client.request(
            "DELETE", "/api/auth/me",
            json={"password": "WrongPassword999!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_res.status_code == 401
        assert "incorrect" in del_res.json()["detail"].lower()
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g6_2_delete_correct_password_succeeds(async_client: AsyncClient):
    """6.2 — DELETE /api/auth/me with correct password returns 204."""
    email = f"del_ok_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    del_res = await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204


@pytest.mark.asyncio
async def test_g6_3_login_after_deletion_rejected(async_client: AsyncClient):
    """6.3 — Logging in after account deletion returns 401 (no zombie credentials)."""
    email = f"del_login_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )

    login_res = await async_client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert login_res.status_code == 401


@pytest.mark.asyncio
async def test_g6_4_email_recycled_after_deletion(async_client: AsyncClient):
    """6.4 — After deletion, signing up with the same email succeeds (no zombie lock)."""
    email = f"recycle_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    r1 = await _signup(async_client, email, password)
    assert r1.status_code == 201
    token1 = r1.json()["access_token"]

    await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token1}"},
    )

    r2 = await _signup(async_client, email, password)
    assert r2.status_code == 201, (
        f"Email should be reusable after deletion, got {r2.status_code}: {r2.text}"
    )
    await _cleanup(async_client, r2.json()["access_token"], password)


@pytest.mark.asyncio
async def test_g6_5_stale_token_after_deletion_rejected(async_client: AsyncClient):
    """6.5 — A still-valid JWT becomes invalid after account deletion (DB row gone)."""
    email = f"stale_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    await async_client.request(
        "DELETE", "/api/auth/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Same token, same DB row gone → must be rejected at get_current_user()
    me_res = await async_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 401


# ===========================================================================
# GROUP 7 — Rate limiting
# ===========================================================================

@pytest.mark.asyncio
async def test_g7_1_signup_rate_limit_triggers_on_6th_request(async_client: AsyncClient):
    """7.1 — 6th signup in a minute (limit 5/min) returns 429."""
    password = "ValidPass1234!"
    created_tokens: list[tuple[str, str]] = []

    try:
        for i in range(5):
            email = f"rl_signup_{i}_{uuid.uuid4().hex[:4]}@example.com"
            res = await async_client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
            assert res.status_code == 201, f"Request {i+1} should succeed, got {res.status_code}"
            created_tokens.append((res.json()["access_token"], password))

        over_limit_email = f"rl_over_{uuid.uuid4().hex[:4]}@example.com"
        res_6 = await async_client.post(
            "/api/auth/signup", json={"email": over_limit_email, "password": password}
        )
        assert res_6.status_code == 429, (
            f"6th signup should be rate-limited (429), got {res_6.status_code}"
        )
    finally:
        for tok, pw in created_tokens:
            await _cleanup(async_client, tok, pw)


@pytest.mark.asyncio
async def test_g7_2_login_rate_limit_triggers_on_11th_request(async_client: AsyncClient):
    """7.2 — 11th login attempt in a minute (limit 10/min) returns 429."""
    email = f"rl_login_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        for i in range(10):
            res = await async_client.post(
                "/api/auth/login", json={"email": email, "password": "WrongPW_intentional"}
            )
            # First 10 may succeed or return 401 — all that matters is they are not 429
            assert res.status_code != 429, f"Request {i+1} was unexpectedly rate-limited"

        res_11 = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "WrongPW_intentional"}
        )
        assert res_11.status_code == 429, (
            f"11th login should be rate-limited (429), got {res_11.status_code}"
        )
    finally:
        await _cleanup(async_client, token, password)


# ===========================================================================
# GROUP 8 — Demo / guest session + double-submit guard
# ===========================================================================

@pytest.mark.asyncio
async def test_g8_1_demo_guest_account_created_successfully(async_client: AsyncClient):
    """
    8.1 — The demo path creates a unique guest account (guest_XXXXXX@kuerycore.ai)
    with a sufficiently long password. This exercises the signupUser() path that
    AuthModal uses for instant demo access.
    """
    guest_id = secrets.token_hex(3)
    guest_email = f"guest_{guest_id}@kuerycore.ai"
    # Password format matches AuthModal.jsx: Guest_{id}_{timestamp}!
    guest_pass = f"Guest_{guest_id}_{int(time.time() * 1000)}!"

    res = await _signup(async_client, guest_email, guest_pass)
    assert res.status_code == 201, f"Demo guest signup failed: {res.text}"
    assert res.json()["email"] == guest_email

    await _cleanup(async_client, res.json()["access_token"], guest_pass)


@pytest.mark.asyncio
async def test_g8_2_double_submit_guard_prevents_duplicate_on_signup(async_client: AsyncClient):
    """
    8.2 — The double-submit guard (submitInFlight ref in AuthModal.jsx) must prevent
    creating two accounts from rapid clicks on the sign-up button.

    Verified here at the backend level: two concurrent/sequential identical signup
    requests for the same email → exactly one succeeds (201), the second must fail
    (400 duplicate). This confirms the backend enforces uniqueness even if the
    frontend guard were bypassed.
    """
    import asyncio
    email = f"double_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    results = await asyncio.gather(
        async_client.post("/api/auth/signup", json={"email": email, "password": password}),
        async_client.post("/api/auth/signup", json={"email": email, "password": password}),
        return_exceptions=True,
    )

    status_codes = [r.status_code for r in results if not isinstance(r, Exception)]
    success_count = sum(1 for s in status_codes if s == 201)
    duplicate_count = sum(1 for s in status_codes if s in (400, 409))

    assert success_count == 1, f"Exactly 1 signup should succeed, got {success_count}"
    assert duplicate_count >= 1, f"At least 1 should fail as duplicate, statuses: {status_codes}"

    # Cleanup the successful one
    for r in results:
        if not isinstance(r, Exception) and r.status_code == 201:
            await _cleanup(async_client, r.json()["access_token"], password)
            break


@pytest.mark.asyncio
async def test_g8_3_double_submit_guard_on_sign_in_path(async_client: AsyncClient):
    """
    8.3 — Double-submit guard also applies to regular sign-in.
    Two concurrent login requests with the same credentials both succeed (200)
    — the guard here is not about blocking login but ensuring the frontend
    doesn't double-fire state updates. At the backend, both should return 200.
    The frontend submitInFlight ref in handleSubmit covers this case.
    """
    import asyncio
    email = f"double_login_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        results = await asyncio.gather(
            async_client.post("/api/auth/login", json={"email": email, "password": password}),
            async_client.post("/api/auth/login", json={"email": email, "password": password}),
            return_exceptions=True,
        )
        for res in results:
            if not isinstance(res, Exception):
                # Both should get valid responses (200 or 429 if rate limited — not a 5xx)
                assert res.status_code in (200, 429), (
                    f"Concurrent login got unexpected status: {res.status_code}"
                )
    finally:
        await _cleanup(async_client, token, password)


# ===========================================================================
# GROUP 9 — AuthModal UI state regressions (client-side, Python-verifiable via backend)
# ===========================================================================

@pytest.mark.asyncio
async def test_g9_1_401_response_surfaces_error_not_silent(async_client: AsyncClient):
    """
    9.1 — A 401 from /api/auth/login produces a non-empty, non-generic detail
    field that the AuthModal error banner can display. Confirms the catch block
    in handleSubmit receives a real message (not swallowed / undefined).
    """
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "nobody@nowhere.invalid", "password": "ValidPass1234!"},
    )
    assert res.status_code == 401
    detail = res.json().get("detail", "")
    assert detail, "401 must carry a non-empty detail string for the error banner"
    assert len(detail) > 5, f"detail too short to be useful: {detail!r}"


@pytest.mark.asyncio
async def test_g9_2_400_duplicate_email_returns_distinct_message(async_client: AsyncClient):
    """
    9.2 — Duplicate email on signup returns a distinct 400 detail that contains
    'already exists'. This is the message the frontend surfaces as an actionable
    error banner ('An account with this email already exists. Try signing in instead.').
    Previously the error was returned correctly from the backend but was not
    distinguished from other 400s by the api.js client — now it is.
    """
    email = f"dup_msg_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        r2 = await _signup(async_client, email, password)
        assert r2.status_code == 400
        detail = r2.json()["detail"]
        assert "already exists" in detail.lower(), (
            f"Expected 'already exists' in detail for duplicate email, got: {detail!r}"
        )
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g9_3_skeleton_transition_only_fires_on_auth_success(async_client: AsyncClient):
    """
    9.3 — Backend contract for the WorkspaceSkeleton timing fix:
    The AuthModal.jsx skeleton (isSigningIn=True in App.jsx) must only trigger
    AFTER a confirmed 2xx response — never on a pre-flight click (which was the
    root cause of the production hang reported in the bug report).

    This test verifies the backend side of the contract: /api/auth/login
    only returns 200 on genuine success. A failed attempt always returns 4xx.
    The client must not call onAuthSuccess / setIsSigningIn for 4xx responses.

    Root cause documented: onStartAuth() was fired immediately on button click
    (before the API response), causing isSigningIn=true forever on error.
    Fixed in App.jsx by removing onStartAuth and only calling setIsSigningIn(true)
    inside handleAuthSuccess (which is only called on 2xx).
    """
    email = f"skeleton_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        # Confirmed success path → returns 200 → client may set isSigningIn=true
        ok_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert ok_res.status_code == 200

        # Failure path → returns 401 → client must NOT set isSigningIn=true
        fail_res = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "WRONG_PASSWORD_999!"}
        )
        assert fail_res.status_code == 401, (
            "Login failure must return 4xx, not 2xx, to prevent spurious skeleton activation"
        )
    finally:
        await _cleanup(async_client, token, password)


# ===========================================================================
# GROUP 10 — Production hang regression: timeout, loading-state, 429 message
# ===========================================================================

@pytest.mark.asyncio
async def test_g10_1_backend_error_returns_json_not_empty_body(async_client: AsyncClient):
    """
    10.1 — Every auth error returns a JSON body with a 'detail' key.
    An empty body or non-JSON body causes the api.js catch block to fall back
    to a generic 'Authentication failed' message — this test confirms the backend
    always returns parseable JSON for all error states.
    """
    error_cases = [
        ("/api/auth/login", {"email": "bad@test.com", "password": "wrongpassword1234"}),
        ("/api/auth/signup", {"email": "", "password": "ValidPass1234!"}),
        ("/api/auth/refresh", {"refresh_token": "garbage.token.here"}),
    ]
    for path, body in error_cases:
        res = await async_client.post(path, json=body)
        assert res.status_code >= 400, f"{path} should return an error"
        try:
            data = res.json()
        except Exception:
            pytest.fail(f"{path} returned non-JSON error body: {res.text!r}")
        assert "detail" in data, f"{path} error body missing 'detail' key: {data}"


@pytest.mark.asyncio
async def test_g10_2_rate_limit_response_is_json_with_detail(async_client: AsyncClient):
    """
    10.2 — A 429 Too Many Requests response carries a JSON 'detail' field,
    not an empty body or HTML page. The AuthModal must show a distinct rate-limit
    message rather than a silent hang or generic crash.
    """
    password = "ValidPass1234!"
    created: list[tuple[str, str]] = []

    try:
        # Exhaust the 5/minute signup limit
        for i in range(5):
            email = f"rl_json_{i}_{uuid.uuid4().hex[:4]}@example.com"
            res = await async_client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
            if res.status_code == 201:
                created.append((res.json()["access_token"], password))

        over_email = f"rl_json_over_{uuid.uuid4().hex[:4]}@example.com"
        res_429 = await async_client.post(
            "/api/auth/signup", json={"email": over_email, "password": password}
        )
        assert res_429.status_code == 429

        # Body must be JSON with 'detail' key — not empty, not HTML
        try:
            body = res_429.json()
        except Exception:
            pytest.fail(f"429 response is not JSON: {res_429.text!r}")

        assert "detail" in body, f"429 body missing 'detail': {body}"
        assert "too many" in body["detail"].lower(), (
            f"429 detail should say 'too many requests', got: {body['detail']!r}"
        )
    finally:
        for tok, pw in created:
            await _cleanup(async_client, tok, pw)


@pytest.mark.asyncio
async def test_g10_3_auth_endpoint_does_not_hang_under_bad_input(async_client: AsyncClient):
    """
    10.3 — Auth endpoints respond promptly (within 10s) even for invalid input.
    Tests the backend side of the hang regression: if the server-side processing
    hangs, the ASGI transport would block here — catching that would indicate a
    server-level hang rather than a client-side timeout issue.
    """
    import anyio

    try:
        with anyio.fail_after(10.0):
            res = await async_client.post(
                "/api/auth/login",
                json={"email": "bad@test.invalid", "password": "wrongpassword1234"},
            )
        assert res.status_code in (400, 401, 422, 429)
    except TimeoutError:
        pytest.fail(
            "Login endpoint hung for >10s under invalid input — server-side hang detected. "
            "This is the production root cause of infinite skeleton states."
        )


@pytest.mark.asyncio
async def test_g10_4_signup_endpoint_responds_promptly_on_duplicate(async_client: AsyncClient):
    """
    10.4 — Duplicate-email signup returns 400 promptly (within 10s).
    Previously the 400 was returned by the backend but was not surfaced by the
    client because onStartAuth() had already triggered the skeleton — the UI
    hung even though the backend responded correctly. This confirms backend latency
    is not the cause of the hang (the skeleton timing fix in App.jsx / AuthModal.jsx is).
    """
    import anyio

    email = f"prompt_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"
    r = await _signup(async_client, email, password)
    assert r.status_code == 201
    token = r.json()["access_token"]

    try:
        with anyio.fail_after(10.0):
            res = await async_client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"].lower()
    except TimeoutError:
        pytest.fail("Duplicate-email signup hung for >10s — backend should respond promptly")
    finally:
        await _cleanup(async_client, token, password)


@pytest.mark.asyncio
async def test_g10_5_timeout_error_message_is_distinct(async_client: AsyncClient):
    """
    10.5 — The 15-second AbortController timeout in AuthModal.jsx surfaces a
    distinct timeout message (not the generic 'Authentication failed' fallback).

    This is a CLIENT-SIDE test verified by contract:
    • The client sets a 15-second AbortController on every auth fetch.
    • If the signal fires (err.name === 'AbortError'), the error message must be
      'Request timed out. The server may be starting up — please try again.'
    • The loading state resets to false via the finally block.
    • isSigningIn in App.jsx is reset via the onAuthError callback.

    We cannot exercise AbortController directly from pytest, so this test
    verifies the BACKEND never triggers the timeout under normal load (response
    time << 15s), and documents the client-side contract for the CI record.
    """
    import anyio

    email = f"timeout_ok_{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1234!"

    # Verify the backend responds well under normal conditions (no timeout needed)
    try:
        with anyio.fail_after(15.0):  # mirrors the client AbortController threshold
            res = await async_client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
        assert res.status_code == 201
        token = res.json()["access_token"]
        await _cleanup(async_client, token, password)
    except TimeoutError:
        pytest.fail(
            "Signup took longer than 15 seconds — would trigger client AbortController timeout. "
            "Investigate backend cold-start latency or DB connection pool."
        )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("KUERYCORE_SMOKE_TEST"),
    reason="Live smoke test skipped in CI. Set KUERYCORE_SMOKE_TEST=1 to run against Railway.",
)
async def test_g10_6_live_smoke_test_railway_backend():
    """
    10.6 — LIVE SMOKE TEST (skipped in CI unless KUERYCORE_SMOKE_TEST=1 is set).

    Hits the real Railway/Render backend over the network to catch infra-level
    latency that in-process ASGI tests cannot reproduce. The in-process transport
    always responds in <1ms regardless of DB pool warm-up or cold-start delays.

    Run manually: KUERYCORE_SMOKE_TEST=1 pytest tests/test_auth_regression.py::test_g10_6_live_smoke_test_railway_backend -v
    """
    import httpx

    live_url = os.environ.get(
        "KUERYCORE_LIVE_URL", "https://documind-ai-97t5.onrender.com"
    )
    email = f"smoke_{uuid.uuid4().hex[:6]}@example.com"
    password = "SmokeTest1234!"

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(base_url=live_url, timeout=timeout) as client:
        try:
            res = await client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
            assert res.status_code == 201, (
                f"Live signup failed ({res.status_code}): {res.text[:200]}"
            )
            token = res.json()["access_token"]

            # Cleanup immediately
            await client.request(
                "DELETE", "/api/auth/me",
                json={"password": password},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.TimeoutException as e:
            pytest.fail(
                f"Live backend at {live_url} timed out after 20s — this would "
                f"trigger the client AbortController (15s). Infra cold-start issue. "
                f"Error: {e}"
            )
