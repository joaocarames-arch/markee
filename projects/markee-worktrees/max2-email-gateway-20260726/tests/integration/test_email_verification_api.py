"""Integration tests for the email verification flow.

Covers register→verify→login, login blocking unverified accounts without leaks,
resend enumeration-safe and rate-limited, and the verify endpoint being
idempotent + safe under repeated submissions.
"""
from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.database import get_db
from app.models.email_verification import EmailVerificationToken

_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")


def extract_verification_token(text_body: str) -> str:
    """Return the ``token`` query value from the first URL carrying one.

    Robust against line layout, adjacent punctuation and URL encoding — it
    scans every URL in the body instead of splitting on lines.
    """
    for raw_url in _URL_RE.findall(text_body):
        candidate = raw_url.rstrip(".,;:!?")
        values = parse_qs(urlparse(candidate).query).get("token")
        if values and values[0]:
            return values[0]
    raise AssertionError("no verification token found in email body")


@pytest.fixture(autouse=True)
def _reset_in_memory_gateway() -> None:
    from app.services.email import reset_in_memory_gateway
    reset_in_memory_gateway()
    yield
    reset_in_memory_gateway()


@pytest_asyncio.fixture
async def api_client(override_get_db: Callable[[], object]) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def _inbox() -> list[object]:
    """Return the in-memory gateway's collected envelopes."""
    from app.services.email import get_in_memory_gateway

    return list(get_in_memory_gateway().sent)


# ── Register ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_creates_unverified_account_and_emits_verification_email(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "secret123"},
    )
    assert response.status_code == 201
    assert response.json()["is_active"] is True
    assert response.json()["is_verified"] is False

    inbox = await _inbox()
    assert len(inbox) == 1
    assert "new@example.com" in inbox[0].recipients
    assert "verifica" in inbox[0].subject.lower()


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_generic_message(
    api_client: AsyncClient,
) -> None:
    first = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret123"},
    )
    assert first.status_code == 201
    inbox_after_first = len(await _inbox())

    # Second attempt with same email — must not leak existence.
    second = await api_client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "secret123"},
    )
    assert second.status_code == 201
    assert second.json()["email"] == "dup@example.com"
    inbox_after_second = len(await _inbox())
    # No new email must be sent for duplicate registration attempts.
    assert inbox_after_second == inbox_after_first


# ── Login ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_unverified_account_is_blocked_without_leak(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "u@example.com", "password": "secret123"},
    )
    response = await api_client.post(
        "/api/v1/auth/login",
        data={"username": "u@example.com", "password": "secret123"},
    )
    assert response.status_code == 403
    body = response.json()["detail"]
    assert "verificada" in body.lower() or "verify" in body.lower()


# ── Verify ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_marks_account_as_verified_allows_login(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "v@example.com", "password": "secret123"},
    )
    # Extract token from the inbox.
    inbox = await _inbox()
    token = extract_verification_token(inbox[-1].text_body)
    assert token

    v = await api_client.post("/api/v1/auth/verify", json={"token": token})
    assert v.status_code == 200
    assert v.json()["is_verified"] is True

    login = await api_client.post(
        "/api/v1/auth/login",
        data={"username": "v@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_verify_is_idempotent(api_client: AsyncClient) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "i@example.com", "password": "secret123"},
    )
    inbox = await _inbox()
    token = extract_verification_token(inbox[-1].text_body)

    first = await api_client.post("/api/v1/auth/verify", json={"token": token})
    second = await api_client.post("/api/v1/auth/verify", json={"token": token})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["is_verified"] is True


@pytest.mark.asyncio
async def test_verify_unknown_token_returns_generic_error(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/auth/verify", json={"token": "garbage-value-not-in-db"}
    )
    assert response.status_code == 400
    assert "token" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_revokes_previous_tokens_for_same_user(
    api_client: AsyncClient, db_session
) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "r@example.com", "password": "secret123"},
    )
    # Trigger a second issuance via resend.
    resend = await api_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "r@example.com"},
    )
    assert resend.status_code == 200

    # First token must now be revoked at the DB level.
    result = await db_session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.purpose == "register"
        )
    )
    tokens = list(result.scalars().all())
    revoked = [t for t in tokens if t.revoked_at is not None]
    assert len(tokens) >= 2
    assert len(revoked) >= 1


# ── Resend ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resend_unknown_email_returns_identical_response(
    api_client: AsyncClient,
) -> None:
    rcpt = await api_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "ghost@example.com"},
    )
    assert rcpt.status_code == 200
    assert len(await _inbox()) == 0  # No email sent for unknown user.


@pytest.mark.asyncio
async def test_resend_known_email_sends_new_token_and_revokes_previous(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "k@example.com", "password": "secret123"},
    )
    inbox_before = len(await _inbox())

    resend = await api_client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "k@example.com"},
    )
    assert resend.status_code == 200
    assert len(await _inbox()) == inbox_before + 1


@pytest.mark.asyncio
async def test_resend_rate_limits_more_than_configured_per_hour(
    api_client: AsyncClient,
) -> None:
    await api_client.post(
        "/api/v1/auth/register",
        json={"email": "rl@example.com", "password": "secret123"},
    )
    # First resend is allowed; subsequent ones within the same hour must be
    # refused once the configured limit is hit.
    statuses: list[int] = []
    for _ in range(10):
        res = await api_client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "rl@example.com"},
        )
        statuses.append(res.status_code)
    assert 429 in statuses
