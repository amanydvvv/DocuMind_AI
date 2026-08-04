"""
DocuMind AI — Auth Router
Authentication endpoints for user signup, login, token refresh, and user profile management.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
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

router = APIRouter(prefix="/api/auth", tags=["Auth"])


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
    await db.flush()

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
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

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
