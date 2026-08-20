"""Authentication router — registration, JWT login and current-user lookup."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import ORMModel, StrId
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserCreate(BaseModel):
    """Payload for registering a new user."""

    email: EmailStr
    password: str
    full_name: str | None = None
    company_name: str | None = None


class UserLogin(BaseModel):
    """Payload for logging in with email and password."""

    email: EmailStr
    password: str


class UserOut(ORMModel):
    """Public representation of a user."""

    id: StrId
    email: str
    full_name: str | None = None
    company_name: str | None = None
    is_active: bool
    created_at: datetime | None = None


class Token(BaseModel):
    """A bearer access token response."""

    access_token: str
    token_type: str


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer token.

    Args:
        token: The JWT bearer token.
        db: Database session.

    Returns:
        The authenticated :class:`User`.

    Raises:
        HTTPException: 401 if the token is missing, invalid, or the user is
            unknown.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        parsed_id = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise credentials_exception from exc

    result = await db.execute(select(User).where(User.id == parsed_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        # A token issued before deactivation must stop working immediately.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa",
        )
    return user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new user account.

    Args:
        payload: The registration data.
        db: Database session.

    Returns:
        The newly created user.

    Raises:
        HTTPException: 400 if the email is already registered.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        company_name=payload.company_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate a user and return a JWT access token.

    Args:
        form_data: OAuth2 password form (``username`` is the email).
        db: Database session.

    Returns:
        A :class:`Token` with the signed access token.

    Raises:
        HTTPException: 401 if the credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa",
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user.

    Args:
        current_user: The authenticated user (injected).

    Returns:
        The current user.
    """
    return current_user
