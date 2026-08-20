"""Email verification token service.

Tokens are random 32-byte secrets, base64url-encoded (~43 chars). Only the
SHA-256 hash is persisted. The service revokes any outstanding tokens for the
same ``(user, purpose)`` pair when a new one is issued, enforces a configurable
TTL, and stamps ``used_at`` upon successful verification.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select, update

from app.core.config import Settings
from app.models.email_verification import EmailVerificationToken


PURPOSE_REGISTER = "register"
PURPOSE_EMAIL_CHANGE = "email_change"


class EmailVerificationError(Exception):
    """Failure to verify a token.

    The ``code`` attribute is suitable for an end-user response; the message
    intentionally stays generic to avoid leaking the token's lifecycle state.
    """

    def __init__(self, code: str, message: str = "Token inválido ou expirado") -> None:
        super().__init__(message)
        self.code = code


def generate_token() -> str:
    """Return a fresh, URL-safe random token (43 chars)."""
    return secrets.token_urlsafe(32)


def hash_token(plaintext: str) -> str:
    """Return the SHA-256 hex digest of a token."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class VerifyResult:
    """Payload returned from a successful verification."""

    user_id: uuid.UUID
    email: str
    purpose: str


class TokenService:
    """Stateless helper around the verification token table."""

    def __init__(self, session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def _revoke_outstanding(
        self, user_id: uuid.UUID, purpose: str
    ) -> None:
        """Mark every previous outstanding token as revoked."""
        now = _utcnow()
        await self._session.execute(
            update(EmailVerificationToken)
            .where(
                and_(
                    EmailVerificationToken.user_id == user_id,
                    EmailVerificationToken.purpose == purpose,
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.revoked_at.is_(None),
                )
            )
            .values(revoked_at=now)
        )

    async def _count_recent(self, user_id: uuid.UUID, purpose: str) -> int:
        """Count tokens issued for this user/purpose in the last hour."""
        since = _utcnow() - timedelta(hours=1)
        result = await self._session.execute(
            select(EmailVerificationToken).where(
                and_(
                    EmailVerificationToken.user_id == user_id,
                    EmailVerificationToken.purpose == purpose,
                    EmailVerificationToken.created_at >= since,
                )
            )
        )
        return len(list(result.scalars().all()))

    async def issue(
        self,
        user_id: uuid.UUID,
        email: str,
        *,
        purpose: str = PURPOSE_REGISTER,
    ) -> str:
        """Revoke any old tokens, persist a new hash, return the plaintext.

        Raises:
            EmailVerificationError: When the per-hour rate limit is exceeded.
        """
        recent = await self._count_recent(user_id, purpose)
        if recent >= self._settings.EMAIL_VERIFY_RATE_LIMIT_PER_HOUR:
            raise EmailVerificationError(
                code="rate_limited",
                message="Demasiados pedidos de verificação; tente mais tarde.",
            )

        await self._revoke_outstanding(user_id, purpose)

        plaintext = generate_token()
        token = EmailVerificationToken(
            user_id=user_id,
            email=email,
            purpose=purpose,
            token_hash=hash_token(plaintext),
            expires_at=_utcnow()
            + timedelta(minutes=self._settings.EMAIL_VERIFY_TTL_MINUTES),
        )
        self._session.add(token)
        await self._session.commit()
        return plaintext

    async def verify(self, plaintext: str) -> VerifyResult:
        """Look up a token by hash, validate it, mark it used, return payload.

        Raises:
            EmailVerificationError: When the token is unknown, expired, used
                or revoked.
        """
        if not plaintext:
            raise EmailVerificationError(code="invalid")

        token_hash = hash_token(plaintext)
        result = await self._session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            ).with_for_update()
        )
        token = result.scalar_one_or_none()
        if token is None:
            raise EmailVerificationError(code="invalid")
        if token.revoked_at is not None:
            # Same response as unknown to avoid leaking which tokens were
            # issued and revoked.
            raise EmailVerificationError(code="revoked")
        if token.used_at is not None:
            raise EmailVerificationError(code="used")
        if token.expires_at <= _utcnow():
            raise EmailVerificationError(code="expired")

        token.used_at = _utcnow()
        await self._session.commit()
        return VerifyResult(
            user_id=token.user_id, email=token.email, purpose=token.purpose
        )

    async def count_recent(
        self, user_id: uuid.UUID, purpose: str = PURPOSE_REGISTER
    ) -> int:
        """Public helper for tests and for the resend endpoint."""
        return await self._count_recent(user_id, purpose)
