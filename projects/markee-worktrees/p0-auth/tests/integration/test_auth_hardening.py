"""Integration tests for P0-S1 auth hardening.

Cobre:
- Logout com invalidação server-side do token (blocklist em Redis).
- Guarda de autenticação nos endpoints de marcas.
- Rate limiting no login (5 falhas / 15 min, fail-open sem Redis).

Usa TestClient com BD mockada (padrão de ``test_api.py``) e um Redis falso
injetado via monkeypatch — nenhum teste depende de um Redis real.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.database import get_db

client = TestClient(app)


class FakeRedis:
    """In-memory stand-in for the async Redis client used in auth flows."""

    def __init__(self):
        self.store: dict[str, object] = {}
        self.ttls: dict[str, int] = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = int(ttl)
        return True

    async def exists(self, *keys):
        return sum(1 for key in keys if key in self.store)

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key):
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = value
        return value

    async def expire(self, key, ttl):
        self.ttls[key] = int(ttl)
        return True

    async def ttl(self, key):
        return self.ttls.get(key, -2)

    async def delete(self, *keys):
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
            self.ttls.pop(key, None)
        return removed


class BrokenRedis:
    """Redis stand-in whose every operation fails (connection down)."""

    def __getattr__(self, name):
        async def _fail(*args, **kwargs):
            raise ConnectionError("redis indisponível (simulado)")

        return _fail


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(security, "get_redis", lambda: fake, raising=False)
    return fake


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture(autouse=True)
def override_db_dependency(mock_db_session):
    async def _get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


def _make_user(email: str = "user@ex.pt", password: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.email = email
    user.full_name = "Test User"
    user.company_name = None
    user.is_active = True
    user.created_at = datetime.now(UTC)
    user.hashed_password = get_password_hash(password) if password else "irrelevante"
    return user


def _db_returns_user(mock_db_session, user) -> None:
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    mock_db_session.execute.return_value = result_mock


class TestLogout:
    """POST /api/v1/auth/logout — invalidação server-side idempotente."""

    def test_logout_invalidates_token(self, mock_db_session, fake_redis):
        user = _make_user()
        _db_returns_user(mock_db_session, user)
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 204

        rejected = client.get("/api/v1/auth/me", headers=headers)
        assert rejected.status_code == 401

    def test_logout_is_idempotent(self, mock_db_session, fake_redis):
        user = _make_user()
        _db_returns_user(mock_db_session, user)
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204

    def test_logout_rejects_missing_token(self, fake_redis):
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_logout_rejects_malformed_token(self, fake_redis):
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer nao-e-um-jwt"},
        )
        assert response.status_code == 401

    def test_blocklist_never_stores_raw_token(self, mock_db_session, fake_redis):
        user = _make_user()
        _db_returns_user(mock_db_session, user)
        token = create_access_token({"sub": str(user.id)})

        response = client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 204
        assert fake_redis.store, "logout deve registar o token na blocklist"
        assert all(token not in key for key in fake_redis.store)


def _make_trademark_row() -> MagicMock:
    row = MagicMock()
    row.id = str(uuid4())
    row.source_id = "N.123456"
    row.application_number = "N.123456"
    row.application_date = None
    row.registration_number = None
    row.registration_date = None
    row.word_mark = "MARKEE"
    row.status = "active"
    row.nice_classes = [9, 42]
    row.jurisdiction = "EUIPO"
    row.applicants = None
    row.goods_services = None
    return row


class TestTrademarkAuthGuard:
    """Endpoints de marcas exigem autenticação Bearer."""

    def test_list_requires_auth(self):
        response = client.get("/api/v1/trademarks")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_detail_requires_auth(self):
        response = client.get("/api/v1/trademarks/N.123456")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_list_with_token_preserves_response_shape(
        self, mock_db_session, fake_redis
    ):
        user = _make_user()
        row = _make_trademark_row()
        result_mock = MagicMock()
        # A mesma sessão serve o lookup do utilizador e a query de marcas.
        result_mock.scalar_one_or_none.return_value = user
        result_mock.scalars.return_value.all.return_value = [row]
        mock_db_session.execute.return_value = result_mock

        token = create_access_token({"sub": str(user.id)})
        response = client.get(
            "/api/v1/trademarks?q=MARKEE&limit=10&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["word_mark"] == "MARKEE"
        assert data[0]["jurisdiction"] == "EUIPO"
        assert data[0]["nice_classes"] == [9, 42]

    def test_detail_with_token_preserves_response_shape(
        self, mock_db_session, fake_redis
    ):
        user = _make_user()
        row = _make_trademark_row()
        result_mock = MagicMock()
        # 1ª chamada resolve o utilizador (dependência), 2ª a marca.
        result_mock.scalar_one_or_none.side_effect = [user, row]
        mock_db_session.execute.return_value = result_mock

        token = create_access_token({"sub": str(user.id)})
        response = client.get(
            "/api/v1/trademarks/N.123456",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["application_number"] == "N.123456"
        assert data["word_mark"] == "MARKEE"


def _login(email: str, password: str):
    return client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )


class TestLoginRateLimit:
    """POST /api/v1/auth/login — 5 falhas por janela de 15 minutos."""

    def test_sixth_failed_login_returns_429_with_retry_after(
        self, mock_db_session, fake_redis
    ):
        _db_returns_user(mock_db_session, None)

        for _ in range(5):
            assert _login("alice@ex.pt", "errada").status_code == 401

        blocked = _login("alice@ex.pt", "errada")
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0

    def test_successful_login_resets_counter(self, mock_db_session, fake_redis):
        user = _make_user(email="alice@ex.pt", password="correta123")
        _db_returns_user(mock_db_session, user)

        for _ in range(4):
            assert _login("alice@ex.pt", "errada").status_code == 401

        assert _login("alice@ex.pt", "correta123").status_code == 200

        # Sem o reset, a 2ª falha abaixo seria a 6ª da janela e daria 429.
        assert _login("alice@ex.pt", "errada").status_code == 401
        assert _login("alice@ex.pt", "errada").status_code == 401

    def test_rate_limit_isolated_per_identifier(self, mock_db_session, fake_redis):
        _db_returns_user(mock_db_session, None)

        for _ in range(5):
            assert _login("alice@ex.pt", "errada").status_code == 401
        assert _login("alice@ex.pt", "errada").status_code == 429

        assert _login("bob@ex.pt", "errada").status_code == 401

    def test_login_fails_open_when_redis_unavailable(
        self, mock_db_session, monkeypatch
    ):
        monkeypatch.setattr(
            security, "get_redis", lambda: BrokenRedis(), raising=False
        )
        user = _make_user(email="alice@ex.pt", password="correta123")
        _db_returns_user(mock_db_session, user)

        response = _login("alice@ex.pt", "correta123")
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_rate_limit_key_is_deterministic_and_normalized(self):
        import hashlib
        import re

        from app.core.security import login_rate_limit_key

        key = login_rate_limit_key("Alice@EX.pt", "1.2.3.4")
        # Versioned key with a 64-char hex SHA-256 digest, no raw PII.
        assert re.fullmatch(r"auth:login_attempts:v1:[0-9a-f]{64}", key)
        assert "alice@ex.pt" not in key
        assert "1.2.3.4" not in key
        expected = hashlib.sha256(b"alice@ex.pt|1.2.3.4").hexdigest()
        assert key == f"auth:login_attempts:v1:{expected}"

        # Deterministic across calls and identifier casing/whitespace.
        assert key == login_rate_limit_key("alice@ex.pt", "1.2.3.4")
        assert key == login_rate_limit_key("  ALICE@ex.PT  ", "1.2.3.4")

        # Distinct email/IP combinations map to distinct keys.
        assert key != login_rate_limit_key("bob@ex.pt", "1.2.3.4")
        assert key != login_rate_limit_key("alice@ex.pt", "5.6.7.8")
        assert login_rate_limit_key("bob@ex.pt", "1.2.3.4") != (
            login_rate_limit_key("alice@ex.pt", "5.6.7.8")
        )

        # Without a client IP the digest covers the email alone.
        key_no_ip = login_rate_limit_key("Alice@EX.pt", None)
        expected_no_ip = hashlib.sha256(b"alice@ex.pt").hexdigest()
        assert key_no_ip == f"auth:login_attempts:v1:{expected_no_ip}"
        assert key_no_ip != key
        assert "alice@ex.pt" not in key_no_ip
