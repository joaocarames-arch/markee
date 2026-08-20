"""Password hashing and JWT helpers.

Centralises the cryptographic primitives used by the authentication layer so
they can be reused by routers, tasks and tests without circular imports.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return the shared async Redis client for auth flows (lazy singleton).

    Returns:
        The process-wide :class:`Redis` client bound to ``settings.REDIS_URL``.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


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
    expire = datetime.now(UTC) + (
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


def _token_blocklist_key(token: str) -> str:
    """Return the Redis blocklist key for a token (SHA-256, never the raw value)."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"auth:token_blocklist:{digest}"


async def blocklist_token(token: str) -> None:
    """Invalidate a token server-side until its natural expiry.

    Stores a SHA-256 fingerprint of the token in Redis with a TTL matching the
    remaining token lifetime. Fails open (logs a warning) when Redis is
    unavailable, matching the project's service resilience conventions.

    Args:
        token: The encoded JWT to invalidate. Already-expired or invalid
            tokens are ignored — they are rejected by decoding anyway.
    """
    payload = decode_access_token(token)
    if payload is None:
        return
    exp = payload.get("exp")
    if exp is None:
        return
    ttl = int(exp - datetime.now(UTC).timestamp())
    if ttl <= 0:
        return
    try:
        await get_redis().setex(_token_blocklist_key(token), ttl, "1")
    except Exception:  # noqa: BLE001 - fail open on any Redis failure
        logger.warning(
            "Redis unavailable — logout not persisted to the token blocklist"
        )


async def is_token_blocklisted(token: str) -> bool:
    """Check whether a token has been invalidated by logout.

    Fails open (returns ``False`` with a warning) when Redis is unavailable.

    Args:
        token: The encoded JWT to check.

    Returns:
        ``True`` if the token is present in the blocklist.
    """
    try:
        return bool(await get_redis().exists(_token_blocklist_key(token)))
    except Exception:  # noqa: BLE001 - fail open on any Redis failure
        logger.warning("Redis unavailable — skipping token blocklist check")
        return False


def login_rate_limit_key(identifier: str, client_ip: str | None) -> str:
    """Build the deterministic Redis key for login attempt counting.

    The identity is stored as a SHA-256 digest so no raw email or client IP
    (PII) ever reaches Redis key space.

    Args:
        identifier: The login identifier (email); normalised to lowercase.
        client_ip: The client IP, or ``None`` when unavailable — the digest
            then covers the identifier alone.

    Returns:
        The Redis key scoping the failed-attempt counter, in the form
        ``auth:login_attempts:v1:<sha256-hex>``.
    """
    normalized = identifier.strip().lower()
    material = f"{normalized}|{client_ip}" if client_ip else normalized
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"auth:login_attempts:v1:{digest}"


async def get_login_retry_after(key: str) -> int | None:
    """Return the seconds to wait when a login key is blocked, else ``None``.

    Fails open (``None`` with a warning) when Redis is unavailable.

    Args:
        key: The rate-limit key from :func:`login_rate_limit_key`.

    Returns:
        Remaining block time in seconds, or ``None`` when not blocked.
    """
    try:
        redis = get_redis()
        count = await redis.get(key)
        if count is None or int(count) < settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
            return None
        return max(int(await redis.ttl(key)), 1)
    except Exception:  # noqa: BLE001 - fail open on any Redis failure
        logger.warning("Redis unavailable — skipping login rate limit check")
        return None


async def register_failed_login(key: str) -> None:
    """Count one failed login attempt, opening the window on the first.

    Fails open (logs a warning) when Redis is unavailable.

    Args:
        key: The rate-limit key from :func:`login_rate_limit_key`.
    """
    try:
        redis = get_redis()
        attempts = await redis.incr(key)
        if attempts == 1:
            await redis.expire(key, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    except Exception:  # noqa: BLE001 - fail open on any Redis failure
        logger.warning("Redis unavailable — failed login attempt not recorded")


async def reset_login_attempts(key: str) -> None:
    """Clear the failed-attempt counter after a successful login.

    Fails open (logs a warning) when Redis is unavailable.

    Args:
        key: The rate-limit key from :func:`login_rate_limit_key`.
    """
    try:
        await get_redis().delete(key)
    except Exception:  # noqa: BLE001 - fail open on any Redis failure
        logger.warning("Redis unavailable — login attempt counter not reset")