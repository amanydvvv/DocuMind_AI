"""
KueryCore AI — Auth Router
Authentication endpoints for user signup, login, token refresh, and user profile management.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.core.ratelimit import limiter
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_current_user,
    rotate_refresh_token,
)

import os
import logging
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from app.config import get_settings
from app.models import Document
from app.services.ingestion import _resolve_file_path
from app.services.query_cache import query_cache

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class DeleteAccountRequest(BaseModel):
    password: str


class UserSignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


async def _issue_tokens(
    db: AsyncSession, user: User, jti: Optional[str] = None
) -> AuthTokenResponse:
    """Issue a new access token plus a rotated refresh token, persisting its jti."""
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    if jti is None:
        jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(str(user.id), jti)
    user.refresh_token_jti = jti
    await db.commit()
    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
    )


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def signup(request: Request, body: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account and issue an access + refresh token pair."""
    email_clean = body.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address format.")
    if len(body.password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters long.")

    # Check existing user
    res = await db.execute(select(User).where(User.email == email_clean))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_pw = hash_password(body.password)
    user = User(email=email_clean, hashed_password=hashed_pw)
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # Race condition: two concurrent requests both passed the SELECT check above
        # and one of them won the INSERT race. Rollback and return the same 400 as the
        # pre-flight duplicate check so the client always gets a clean, non-500 response.
        await db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    return await _issue_tokens(db, user)


@router.post("/login", response_model=AuthTokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user credentials via JSON body and issue an access + refresh token pair."""
    email_clean = body.email.strip().lower()
    password_plain = body.password

    if not email_clean or not password_plain:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    res = await db.execute(select(User).where(User.email == email_clean))
    user = res.scalar_one_or_none()

    if not user or not verify_password(password_plain, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    return await _issue_tokens(db, user)


@router.post("/refresh", response_model=AuthTokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Rotate a refresh token via atomic compare-and-swap (no TOCTOU window)."""
    try:
        payload = decode_access_token(body.refresh_token)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token.")

    user_id = payload.get("sub")
    old_jti = payload.get("jti")
    if not user_id or not old_jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload.")

    new_jti = str(uuid.uuid4())
    swapped = await rotate_refresh_token(db, uuid.UUID(user_id), old_jti, new_jti)
    if not swapped:
        # Token already rotated by a concurrent request, account deactivated,
        # or user missing — reject without any further writes.
        await db.rollback()
        raise HTTPException(
            status_code=401,
            detail="Refresh token has already been used. Please log in again.",
        )

    # Post-CAS lookup is race-free: the jti swap has already been applied atomically.
    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        await db.rollback()
        raise HTTPException(status_code=401, detail="User account no longer exists.")

    return await _issue_tokens(db, user, jti=new_jti)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete the current user account, associated files, and cascaded data."""
    # 1. Re-authenticate password
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    user_id = current_user.id
    logger.info("Account deletion requested for user_id=%s", user_id)

    # 2. Best-effort physical on-disk file cleanup
    try:
        docs_res = await db.execute(
            select(Document).where(Document.user_id == current_user.id)
        )
        user_docs = docs_res.scalars().all()
        for doc in user_docs:
            try:
                file_path = Path(_resolve_file_path(doc))
                if file_path.exists():
                    os.remove(file_path)
            except Exception as file_exc:
                logger.warning(
                    "Failed to delete physical file %s for user %s: %s",
                    doc.id, user_id, file_exc
                )
    except Exception as docs_exc:
        logger.warning(
            "Error querying user documents during file cleanup (user %s): %s",
            user_id, docs_exc
        )

    # 3. Delete user row (PostgreSQL ON DELETE CASCADE purges all child tables)
    from sqlalchemy import delete
    await db.execute(delete(User).where(User.id == current_user.id))
    await db.commit()

    # Tenant no longer exists: drop its cached retrieval results immediately.
    query_cache.invalidate_user(user_id)

    logger.info("Account deletion completed for user_id=%s", user_id)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_token(raw: str) -> str:
    """SHA-256 hex digest of a raw reset token for safe at-rest storage."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# POST /api/auth/forgot-password
# ---------------------------------------------------------------------------

_FORGOT_GENERIC_MSG = (
    "If an account exists with this email, "
    "password reset instructions have been sent."
)


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Initiate a password reset flow.

    Security contract:
    - ALWAYS returns the same 200 + generic message immediately (<50ms)
      regardless of whether the email exists in the DB (prevents account enumeration).
    - If a matching, active user IS found:
        1. Any unused reset tokens for that user are deleted.
        2. A cryptographically random token is generated.
        3. Its SHA-256 hash + 30-min expiry are persisted.
        4. An email is dispatched asynchronously via BackgroundTasks.
    - Rate limited to 3 requests/minute per IP to prevent email-bombing.
    """
    from app.services.email import send_password_reset_email

    email_clean = body.email.strip().lower()

    # Always return the generic response; branching happens silently.
    res = await db.execute(select(User).where(User.email == email_clean))
    user = res.scalar_one_or_none()

    if user and user.is_active:
        # Delete any existing unused tokens for this user (only one live token
        # per user at any time — requesting again invalidates the previous one).
        from sqlalchemy import delete as sa_delete
        await db.execute(
            sa_delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )

        # Generate and persist a new token.
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        prt = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(prt)
        await db.commit()

        # Fire-and-forget email via background task — returns response instantly
        background_tasks.add_task(send_password_reset_email, to=user.email, raw_token=raw_token)

    return MessageResponse(message=_FORGOT_GENERIC_MSG)


# ---------------------------------------------------------------------------
# POST /api/auth/test-email (Diagnostic & Live Probe)
# ---------------------------------------------------------------------------

class TestEmailRequest(BaseModel):
    to: str
    admin_key: Optional[str] = None


@router.post("/test-email")
async def test_email_endpoint(body: TestEmailRequest) -> dict:
    """Live diagnostic probe to inspect exact provider response / errors."""
    from app.services.email import send_password_reset_email
    result = await send_password_reset_email(to=body.to.strip(), raw_token="diagnostic_test_token")
    return result


# ---------------------------------------------------------------------------
# POST /api/auth/reset-password
# ---------------------------------------------------------------------------

_RESET_ERROR = "Invalid or expired reset link."


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Complete a password reset using the token from the email link.

    On success:
    - Updates the user's hashed password.
    - Marks the token as used (single-use enforcement).
    - Clears the user's refresh_token_jti, invalidating all existing sessions
      on every device (standard practice after a credential change).

    On any failure (expired / used / not found / invalid):
    - Returns a generic 400 — does not reveal which specific condition failed.
    """
    # Validate new password before any DB lookup (fails fast, no timing side-channel).
    if len(body.new_password) < 12:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 12 characters long.",
        )

    token_hash = _hash_token(body.token)
    now = datetime.now(timezone.utc)

    # Look up a matching, unexpired, unused token.
    res = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
        )
    )
    prt = res.scalar_one_or_none()

    if prt is None or prt.used_at is not None or prt.expires_at <= now:
        # Generic error — don't reveal which specific condition failed.
        raise HTTPException(status_code=400, detail=_RESET_ERROR)

    # Fetch the associated user.
    user = await db.get(User, prt.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail=_RESET_ERROR)

    # Apply the password change.
    user.hashed_password = hash_password(body.new_password)

    # Invalidate ALL existing refresh tokens (force re-login on every device).
    user.refresh_token_jti = None

    # Mark token as used (single-use guarantee).
    prt.used_at = now

    await db.commit()
    logger.info("Password reset completed for user_id=%s", user.id)

    return MessageResponse(message="Password updated successfully. Please sign in with your new password.")
