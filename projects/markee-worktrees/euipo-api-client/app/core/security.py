"""Password hashing and JWT helpers.

Centralises the cryptographic primitives used by the authentication layer so
they can be reused by routers, tasks and tests without circular imports.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against its stored hash.

    Args:
        plain_password: The password supplied by the user.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    if not hashed_password:
        return False
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The resulting bcrypt hash as a string.
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data: Claims to embed in the token (must include ``sub``).
        expires_delta: Optional custom lifetime; defaults to the configured
            ``ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        The encoded JWT as a string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT.

    Returns:
        The decoded claims, or ``None`` if the token is invalid or expired.
    """
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None