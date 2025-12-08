"""
Authentication endpoints for Identity Service.
"""

from datetime import datetime, timedelta
from typing import Optional

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token_type,
)
from app.config import settings
from fastapi import APIRouter, Depends, HTTPException, status
from infrastructure.db.database import get_db
from infrastructure.db.models import RefreshToken, User
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    name: str = Field(..., min_length=1, description="User full name")
    wallet_address: Optional[str] = Field(None, description="User's wallet address")


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """User information response."""

    id: int
    email: str
    name: str
    role: str
    wallet_address: Optional[str]
    identity_address: Optional[str]
    is_verified: bool
    created_at: datetime


# Helper Functions
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, email: str, password: str, name: str, wallet_address: Optional[str] = None
) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(password)

    user = User(
        email=email,
        hashed_password=hashed_password,
        name=name,
        wallet_address=wallet_address,
        role="user",  # Default role
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def save_refresh_token(db: AsyncSession, user_id: int, token: str, expires_in_days: int = 7):
    """Save refresh token to database."""
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
    )

    db.add(refresh_token)
    await db.commit()


async def get_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    """Get refresh token from database."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow(),
        )
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: str):
    """Revoke a refresh token."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    refresh_token = result.scalar_one_or_none()

    if refresh_token:
        refresh_token.revoked = True
        refresh_token.revoked_at = datetime.utcnow()
        await db.commit()


# Endpoints
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.

    Creates a new user account with email and password.
    """
    # Check if user already exists
    existing_user = await get_user_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = await create_user(
        db,
        email=request.email,
        password=request.password,
        name=request.name,
        wallet_address=request.wallet_address,
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        wallet_address=user.wallet_address,
        identity_address=user.identity_address,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    User login.

    Authenticates user and returns access and refresh tokens.
    """
    # Get user by email
    user = await get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Create tokens
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Save refresh token
    await save_refresh_token(db, user.id, refresh_token, settings.refresh_token_expire_days)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token.

    Exchanges a valid refresh token for a new access token.
    """
    # Decode and verify refresh token
    payload = decode_token(request.refresh_token)
    if not payload or not verify_token_type(payload, "refresh"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check if refresh token exists and is valid
    db_token = await get_refresh_token(db, request.refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or expired",
        )

    # Get user
    user_id = int(payload.get("sub"))
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new access token
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)

    # Optionally create new refresh token (token rotation)
    new_refresh_token = create_refresh_token(token_data)
    await revoke_refresh_token(db, request.refresh_token)  # Revoke old token
    await save_refresh_token(db, user.id, new_refresh_token, settings.refresh_token_expire_days)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    User logout.

    Revokes the refresh token.
    """
    await revoke_refresh_token(db, request.refresh_token)

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(lambda: None)):
    """
    Get current user information.

    Requires valid access token in Authorization header.
    """
    # This endpoint needs proper auth dependency
    # For now, returning a placeholder response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Endpoint requires auth middleware"
    )
