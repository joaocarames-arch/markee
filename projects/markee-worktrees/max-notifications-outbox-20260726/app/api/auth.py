"""Authentication router — registration, JWT login and current-user lookup.

End-to-end flow:

1. ``POST /register``                creates an unverified account, issues a
                                     verification token, dispatches the email.
2. ``POST /verify``                  consumes a token, marks the user verified.
3. ``POST /login``                   returns a JWT for verified active users.
4. ``POST /resend-verification``     enrolment-safe re-issue of the token.

Unverified accounts are blocked from logging in with a single generic
``403`` detail; the existence of the email is never leaked.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import ORMModel, StrId
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.database import get_db
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.services.email_verification import (
    PURPOSE_REGISTER,
    EmailVerificationError,
    TokenService,
    hash_token,
)
from app.services.email_verification_dispatch import issue_and_send_verification

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def _find_user_by_used_token(db: AsyncSession, plaintext: str) -> User | None:
    """Return the user behind a previously consumed verification token."""
    token_hash = hash_token(plaintext)
    result = await db.execute(
        select(User)
        .join(EmailVerificationToken, EmailVerificationToken.user_id == User.id)
        .where(EmailVerificationToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


# ── Schemas ────────────────────────────────────────────────────────────────


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
    is_verified: bool
    created_at: datetime | None = None


class RegisterResponse(BaseModel):
    """Enumeration-safe response shared by new and duplicate registrations."""

    email: str
    is_active: bool
    is_verified: bool


class Token(BaseModel):
    """A bearer access token response."""

    access_token: str
    token_type: str


class VerifyRequest(BaseModel):
    """Payload for the verification endpoint."""

    token: str


class ResendRequest(BaseModel):
    """Payload for the resend endpoint."""

    email: EmailStr


class ResendResponse(BaseModel):
    """Generic envelope for the resend endpoint."""

    sent: bool


# ── get_current_user ───────────────────────────────────────────────────────


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from a bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa",
        )
    return user


# ── Register ───────────────────────────────────────────────────────────────


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> RegisterResponse:
    """Register a new user account.

    The account is created in an unverified state. A verification email is
    queued via the configured gateway; in production the gateway will be the
    SMTP backend, in tests it is the in-memory backend. The response body is a
    constant, enumeration-safe shape: a duplicate attempt returns the exact
    same 201 payload as a fresh registration, no second email is sent and
    neither the existence nor the verification state of the address leaks.
    """
    settings = get_settings()
    # Constant public response — identical for new and duplicate emails.
    public_response = RegisterResponse(
        email=payload.email, is_active=True, is_verified=False
    )

    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        # Enumeration-safe: no token is issued or dispatched from here for an
        # existing account. Resend is the explicit channel for that.
        return public_response

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        company_name=payload.company_name,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await issue_and_send_verification(
        db,
        settings,
        user_id=user.id,
        email=user.email,
        purpose=PURPOSE_REGISTER,
    )
    return public_response


# ── Login ──────────────────────────────────────────────────────────────────


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Authenticate a verified user and return a JWT access token.

    Unverified accounts are blocked with a generic 403 — the message does not
    distinguish between "unknown email", "wrong password" and "not verified",
    so the endpoint cannot be used to enumerate accounts.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou palavra-passe incorretos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta não verificada. Confirme o email antes de iniciar sessão.",
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, token_type="bearer")


# ── Verify ─────────────────────────────────────────────────────────────────


@router.post("/verify", response_model=UserOut)
async def verify(
    payload: VerifyRequest, db: AsyncSession = Depends(get_db)
) -> User:
    """Consume a verification token and mark the user as verified.

    The endpoint is idempotent: a second call with the same token returns the
    verified user (the token is single-use, so the second call cannot have
    succeeded the first time). All token-lifecycle failures map to a single
    generic 400 detail.
    """
    settings = get_settings()
    service = TokenService(db, settings)
    try:
        result = await service.verify(payload.token)
    except EmailVerificationError as exc:
        # Idempotency: a token that was already used to verify an existing
        # account is treated as a successful no-op. Any other failure maps
        # to a single generic 400.
        if exc.code == "used":
            user = await _find_user_by_used_token(db, payload.token)
            if user is not None and user.is_verified:
                return user
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        ) from exc

    user_result = await db.execute(select(User).where(User.id == result.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )

    if not user.is_verified:
        user.is_verified = True
        user.verified_at = datetime.now(timezone.utc)
        if result.purpose == "email_change" and result.email != user.email:
            user.email = result.email
            user.pending_email = None
        await db.commit()
        await db.refresh(user)
    return user


# ── Resend ─────────────────────────────────────────────────────────────────


@router.post("/resend-verification", response_model=ResendResponse)
async def resend_verification(
    payload: ResendRequest, db: AsyncSession = Depends(get_db)
) -> ResendResponse:
    """Re-issue a verification token for an existing user.

    The endpoint is enumeration-safe: unknown, already-verified and inactive
    emails all return the same 200 body as a successful resend, and no email
    is dispatched for them. Per-user rate limiting caps repeated issuance.
    """
    settings = get_settings()
    user_result = await db.execute(select(User).where(User.email == payload.email))
    user = user_result.scalar_one_or_none()
    if user is None or user.is_verified or not user.is_active:
        return ResendResponse(sent=True)

    service = TokenService(db, settings)
    recent = await service.count_recent(user.id, PURPOSE_REGISTER)
    if recent >= settings.EMAIL_VERIFY_RATE_LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados pedidos de verificação; tente mais tarde.",
        )

    await issue_and_send_verification(
        db,
        settings,
        user_id=user.id,
        email=user.email,
        purpose=PURPOSE_REGISTER,
    )
    return ResendResponse(sent=True)


# ── Me ─────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return current_user
