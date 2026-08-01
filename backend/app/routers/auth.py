"""
DocuMind AI — Auth Router
Authentication endpoints for user signup, login, and user profile management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class UserSignupRequest(BaseModel):
    email: str
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account and issue an access token."""
    email_clean = body.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address format.")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # Check existing user
    res = await db.execute(select(User).where(User.email == email_clean))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_pw = hash_password(body.password)
    user = User(email=email_clean, hashed_password=hashed_pw)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user credentials via JSON body or Form data and issue an access token."""
    email_clean = ""
    password_plain = ""

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            data = await request.json()
            email_clean = (data.get("email") or data.get("username") or "").strip().lower()
            password_plain = data.get("password") or ""
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload.")
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email_clean = (form.get("username") or form.get("email") or "").strip().lower()
        password_plain = form.get("password") or ""
    else:
        # Default try parsing JSON
        try:
            data = await request.json()
            email_clean = (data.get("email") or data.get("username") or "").strip().lower()
            password_plain = data.get("password") or ""
        except Exception:
            raise HTTPException(status_code=400, detail="Unsupported Content-Type for authentication.")

    if not email_clean or not password_plain:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    res = await db.execute(select(User).where(User.email == email_clean))
    user = res.scalar_one_or_none()

    if not user or not verify_password(password_plain, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )
