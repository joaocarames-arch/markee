"""Unit tests for the email verification token service.

Tokens are random, stored only as hashes, time-limited, single-use, and the
service revokes any prior outstanding token for the same (user, purpose) pair.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.services.email_verification import (
    PURPOSE_EMAIL_CHANGE,
    PURPOSE_REGISTER,
    EmailVerificationError,
    TokenService,
    generate_token,
    hash_token,
)


# ── Token primitives ───────────────────────────────────────────────────────


def test_generate_token_returns_strong_random_string() -> None:
    t1 = generate_token()
    t2 = generate_token()
    assert isinstance(t1, str)
    assert len(t1) >= 32
    assert t1 != t2


def test_hash_token_is_deterministic_and_does_not_equal_plaintext() -> None:
    t = generate_token()
    h1 = hash_token(t)
    h2 = hash_token(t)
    assert h1 == h2
    assert h1 != t
    assert len(h1) >= 64  # sha256 hex


# ── Service: behaviour with a fake session ─────────────────────────────────


class _FakeListResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> "_FakeListResult":
        return self

    def all(self) -> list[object]:
        return list(self._values)


class _FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalars(self) -> "_FakeScalarResult":
        return self

    def all(self) -> list[object]:
        return [] if self._value is None else [self._value]


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.tokens: dict[str, object] = {}

    async def execute(self, query: object) -> _FakeScalarResult:
        # Find a token by raw plaintext (would look up by hash in real code).
        return _FakeScalarResult(None)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: object) -> None:
        setattr(obj, "id", uuid.uuid4())
        now = datetime.now(timezone.utc)
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            setattr(obj, "created_at", now)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ENVIRONMENT="development",
        EMAIL_VERIFY_TTL_MINUTES=60,
        EMAIL_VERIFY_RATE_LIMIT_PER_HOUR=5,
    )


@pytest.mark.asyncio
async def test_issue_returns_plaintext_and_persists_hash_only(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)
    user_id = uuid.uuid4()
    email = "user@example.com"

    plaintext = await service.issue(user_id, email, purpose=PURPOSE_REGISTER)

    assert isinstance(plaintext, str)
    assert len(plaintext) >= 32
    persisted = session.added[0]
    assert getattr(persisted, "token_hash", None) != plaintext
    assert hash_token(plaintext) == persisted.token_hash
    assert persisted.purpose == PURPOSE_REGISTER
    assert persisted.used_at is None
    assert persisted.revoked_at is None
    assert persisted.email == email
    assert persisted.user_id == user_id


@pytest.mark.asyncio
async def test_verify_rejects_unknown_token(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)
    with pytest.raises(EmailVerificationError) as exc:
        await service.verify("not-a-real-token")
    assert exc.value.code == "invalid"


@pytest.mark.asyncio
async def test_verify_rejects_expired_token(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)

    class _Stored:
        token_hash = hash_token("old-plaintext")
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        used_at = None
        revoked_at = None
        user_id = uuid.uuid4()
        email = "user@example.com"
        purpose = PURPOSE_REGISTER

    async def _execute(query: object) -> _FakeScalarResult:
        return _FakeScalarResult(_Stored())

    session.execute = _execute  # type: ignore[assignment]

    with pytest.raises(EmailVerificationError) as exc:
        await service.verify("old-plaintext")
    assert exc.value.code == "expired"


@pytest.mark.asyncio
async def test_verify_rejects_revoked_token(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)

    class _Stored:
        token_hash = hash_token("tok")
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        used_at = None
        revoked_at = datetime.now(timezone.utc)
        user_id = uuid.uuid4()
        email = "user@example.com"
        purpose = PURPOSE_REGISTER

    async def _execute(query: object) -> _FakeScalarResult:
        return _FakeScalarResult(_Stored())

    session.execute = _execute  # type: ignore[assignment]

    with pytest.raises(EmailVerificationError) as exc:
        await service.verify("tok")
    assert exc.value.code == "revoked"


@pytest.mark.asyncio
async def test_verify_rejects_used_token(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)

    class _Stored:
        token_hash = hash_token("tok")
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        used_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        revoked_at = None
        user_id = uuid.uuid4()
        email = "user@example.com"
        purpose = PURPOSE_REGISTER

    async def _execute(query: object) -> _FakeScalarResult:
        return _FakeScalarResult(_Stored())

    session.execute = _execute  # type: ignore[assignment]

    with pytest.raises(EmailVerificationError) as exc:
        await service.verify("tok")
    assert exc.value.code == "used"


@pytest.mark.asyncio
async def test_verify_marks_used_and_returns_payload(settings: Settings) -> None:
    session = _FakeSession()
    service = TokenService(session, settings)

    stored = type(
        "Stored",
        (),
        {
            "token_hash": hash_token("tok"),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
            "used_at": None,
            "revoked_at": None,
            "user_id": uuid.uuid4(),
            "email": "user@example.com",
            "purpose": PURPOSE_REGISTER,
        },
    )()

    async def _execute(query: object) -> _FakeScalarResult:
        return _FakeScalarResult(stored)

    session.execute = _execute  # type: ignore[assignment]

    payload = await service.verify("tok")
    assert payload.user_id == stored.user_id
    assert payload.email == stored.email
    assert payload.purpose == PURPOSE_REGISTER
    assert stored.used_at is not None


def test_rate_limit_constants() -> None:
    s = Settings(ENVIRONMENT="development")
    assert s.EMAIL_VERIFY_RATE_LIMIT_PER_HOUR >= 1
    assert s.EMAIL_VERIFY_TTL_MINUTES >= 1


def test_purpose_constants() -> None:
    assert PURPOSE_REGISTER == "register"
    assert PURPOSE_EMAIL_CHANGE == "email_change"
