"""Offline contract tests for the EUIPO Trademark Search 1.1.0 client."""
from __future__ import annotations

from datetime import date, timedelta
import logging

import httpx
import pytest

from app.core.config import Settings
from app.services.euipo_client import (
    EUIPOClient,
    EUIPOClientError,
    EUIPOEnvironment,
    EUIPOSettings,
)


def make_settings(environment: EUIPOEnvironment = EUIPOEnvironment.SANDBOX) -> EUIPOSettings:
    """Return enabled, non-secret test settings."""
    return EUIPOSettings(
        enabled=True,
        environment=environment,
        sandbox_client_id="sandbox-id",
        sandbox_client_secret="sandbox-secret",
        production_client_id="production-id",
        production_client_secret="production-secret",
        max_retries=2,
        backoff_base=0.01,
        backoff_jitter=0.0,
    )


def test_application_settings_keep_euipo_disabled_and_credentials_separate() -> None:
    settings = Settings(_env_file=None)

    assert settings.EUIPO_ENABLED is False
    assert settings.EUIPO_ENVIRONMENT == "sandbox"
    assert settings.EUIPO_CLIENT_ID_SANDBOX == ""
    assert settings.EUIPO_CLIENT_SECRET_SANDBOX == ""
    assert settings.EUIPO_CLIENT_ID_PROD == ""
    assert settings.EUIPO_CLIENT_SECRET_PROD == ""


def response(status: int, *, json: object | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    """Build a transport response."""
    if json is None:
        return httpx.Response(status, headers=headers)
    return httpx.Response(status, json=json, headers=headers)


@pytest.mark.asyncio
async def test_disabled_by_default_and_refuses_requests() -> None:
    settings = EUIPOSettings()
    assert settings.enabled is False
    client = EUIPOClient(settings, transport=httpx.MockTransport(lambda request: response(500)))

    with pytest.raises(EUIPOClientError, match="disabled"):
        await client.search("status==REGISTERED")


@pytest.mark.asyncio
async def test_sandbox_auth_uses_client_credentials_and_memory_only_token() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/accessToken"):
            assert request.url.host == "auth-sandbox.euipo.europa.eu"
            assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
            body = request.content.decode()
            assert "grant_type=client_credentials" in body
            assert "scope=uid" in body
            assert "client_id=sandbox-id" in body
            assert "client_secret=sandbox-secret" in body
            return response(200, json={"access_token": "memory-token", "expires_in": 3600})
        assert request.url.host == "api-sandbox.euipo.europa.eu"
        assert request.headers["authorization"] == "Bearer memory-token"
        assert request.headers["x-ibm-client-id"] == "sandbox-id"
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler))
    await client.search("status==REGISTERED")

    assert len(requests) == 2
    assert "memory-token" not in repr(client.settings)


@pytest.mark.asyncio
async def test_production_and_sandbox_endpoints_cannot_be_mixed() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host or "", request.content.decode()))
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    for environment in (EUIPOEnvironment.SANDBOX, EUIPOEnvironment.PRODUCTION):
        client = EUIPOClient(make_settings(environment), transport=httpx.MockTransport(handler))
        await client.search("status==REGISTERED")

    hosts = [host for host, _ in seen]
    assert hosts == [
        "auth-sandbox.euipo.europa.eu",
        "api-sandbox.euipo.europa.eu",
        "euipo.europa.eu",
        "api.euipo.europa.eu",
    ]
    assert "production-secret" not in seen[0][1]
    assert "sandbox-secret" not in seen[2][1]


@pytest.mark.asyncio
async def test_401_invalidates_token_and_reauthenticates_once() -> None:
    tokens = iter(["first-token", "second-token"])
    auth_calls = 0
    search_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls, search_calls
        if request.url.path.endswith("/accessToken"):
            auth_calls += 1
            return response(200, json={"access_token": next(tokens), "expires_in": 3600})
        search_calls += 1
        if search_calls == 1:
            return response(401, json={"title": "Unauthorized", "status": 401})
        assert request.headers["authorization"] == "Bearer second-token"
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler))
    await client.search("status==REGISTERED")

    assert auth_calls == 2
    assert search_calls == 2


@pytest.mark.asyncio
async def test_429_honours_retry_after_before_retrying() -> None:
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        calls += 1
        if calls == 1:
            return response(429, headers={"Retry-After": "2"})
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler), sleep=fake_sleep)
    await client.search("status==REGISTERED")

    assert calls == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_5xx_uses_exponential_backoff() -> None:
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        calls += 1
        if calls < 3:
            return response(503, json={"title": "Unavailable", "status": 503})
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler), sleep=fake_sleep)
    await client.search("status==REGISTERED")

    assert calls == 3
    assert sleeps == [0.01, 0.02]


@pytest.mark.asyncio
async def test_search_passes_rsql_sort_projection_and_caps_page_size() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        captured = request
        return response(
            200,
            json={"trademarks": [], "size": 100, "totalElements": 0, "totalPages": 0, "page": 2},
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler))
    page = await client.search(
        "status==REGISTERED;niceClasses=all=(25,28)",
        page=2,
        size=999,
        sort="updateDate:asc",
        fields="applicationNumber,updateDate",
    )

    assert captured is not None
    assert captured.url.params["q"] == "status==REGISTERED;niceClasses=all=(25,28)"
    assert captured.url.params["page"] == "2"
    assert captured.url.params["size"] == "100"
    assert captured.url.params["sort"] == "updateDate:asc"
    assert captured.url.params["fields"] == "applicationNumber,updateDate"
    assert page.page == 2


@pytest.mark.asyncio
async def test_paginate_reads_all_pages() -> None:
    pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        page = int(request.url.params["page"])
        pages.append(page)
        return response(
            200,
            json={
                "trademarks": [{"applicationNumber": str(page + 1), "updateDate": "2026-07-20"}],
                "size": 100,
                "totalElements": 2,
                "totalPages": 2,
                "page": page,
            },
        )

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler))
    records = [record async for record in client.paginate("status==REGISTERED")]

    assert pages == [0, 1]
    assert [record["applicationNumber"] for record in records] == ["1", "2"]


@pytest.mark.asyncio
async def test_incremental_overlap_and_deterministic_dedupe() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        queries.append(request.url.params["q"])
        return response(
            200,
            json={
                "trademarks": [
                    {"applicationNumber": "2", "updateDate": "2026-07-24", "status": "OLD"},
                    {"applicationNumber": "1", "updateDate": "2026-07-25", "status": "NEW"},
                    {"applicationNumber": "2", "updateDate": "2026-07-25", "status": "NEW"},
                ],
                "size": 100,
                "totalElements": 3,
                "totalPages": 1,
                "page": 0,
            },
        )

    settings = make_settings()
    settings.overlap = timedelta(days=2)
    client = EUIPOClient(settings, transport=httpx.MockTransport(handler))
    batch = await client.fetch_incremental(date(2026, 7, 25), query="status==REGISTERED")

    assert queries == ["status==REGISTERED;updateDate>=2026-07-23"]
    assert [record["applicationNumber"] for record in batch.records] == ["1", "2"]
    assert batch.records[1]["status"] == "NEW"
    assert batch.next_cursor == date(2026, 7, 25)


@pytest.mark.asyncio
async def test_malformed_payload_raises_structured_sanitized_error(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "super-secret-token", "expires_in": 3600})
        return response(200, json={"unexpected": ["super-secret-token"]})

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler))
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(EUIPOClientError) as raised:
            await client.search("status==REGISTERED")

    error = raised.value
    assert error.kind == "malformed_payload"
    assert error.status_code == 200
    assert "super-secret-token" not in str(error)
    assert "sandbox-secret" not in str(error)
    assert "super-secret-token" not in caplog.text
    assert "sandbox-secret" not in caplog.text


@pytest.mark.asyncio
async def test_token_refreshes_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    current_time = 0.0
    auth_calls = 0

    def fake_monotonic() -> float:
        return current_time

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls
        if request.url.path.endswith("/accessToken"):
            auth_calls += 1
            return response(
                200,
                json={"access_token": f"token-{auth_calls}", "expires_in": 1},
            )
        return response(
            200,
            json={"trademarks": [], "size": 10, "totalElements": 0, "totalPages": 0, "page": 0},
        )

    settings = make_settings()
    settings.token_skew = timedelta(0)
    monkeypatch.setattr("app.services.euipo_client.time.monotonic", fake_monotonic)
    client = EUIPOClient(settings, transport=httpx.MockTransport(handler))
    await client.search("status==REGISTERED")
    current_time = 2.0
    await client.search("status==REGISTERED")

    assert auth_calls == 2


@pytest.mark.asyncio
async def test_transport_timeout_retries_then_raises_sanitized_error() -> None:
    sleeps: list[float] = []
    calls = 0

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        if request.url.path.endswith("/accessToken"):
            return response(200, json={"access_token": "token", "expires_in": 3600})
        calls += 1
        raise httpx.ReadTimeout("response contained sandbox-secret", request=request)

    client = EUIPOClient(make_settings(), transport=httpx.MockTransport(handler), sleep=fake_sleep)
    with pytest.raises(EUIPOClientError) as raised:
        await client.search("status==REGISTERED")

    assert raised.value.kind == "transport"
    assert raised.value.retryable is True
    assert "sandbox-secret" not in str(raised.value)
    assert calls == 3
    assert sleeps == [0.01, 0.02]
