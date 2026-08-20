"""Offline EUIPO Trademark Search API 1.1.0 client foundation."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
import email.utils
import random
import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class EUIPOEnvironment(str, Enum):
    """Supported EUIPO environments."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EUIPOSettings(BaseModel):
    """Explicit, fail-closed settings for the isolated client."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    environment: EUIPOEnvironment = EUIPOEnvironment.SANDBOX
    sandbox_client_id: str = ""
    sandbox_client_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    production_client_id: str = ""
    production_client_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 10.0
    pool_timeout: float = 10.0
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_base: float = Field(default=1.0, ge=0)
    backoff_jitter: float = Field(default=0.25, ge=0)
    overlap: timedelta = timedelta(days=1)
    token_skew: timedelta = timedelta(seconds=30)

    @property
    def client_id(self) -> str:
        """Return the client id belonging to the selected environment."""
        if self.environment is EUIPOEnvironment.SANDBOX:
            return self.sandbox_client_id
        return self.production_client_id

    @property
    def client_secret(self) -> SecretStr:
        """Return the secret belonging to the selected environment."""
        if self.environment is EUIPOEnvironment.SANDBOX:
            return self.sandbox_client_secret
        return self.production_client_secret

    @property
    def token_url(self) -> str:
        """Return the immutable official token URL for the selected environment."""
        if self.environment is EUIPOEnvironment.SANDBOX:
            return "https://auth-sandbox.euipo.europa.eu/oidc/accessToken"
        return "https://euipo.europa.eu/cas-server-webapp/oidc/accessToken"

    @property
    def api_base_url(self) -> str:
        """Return the immutable official API base for the selected environment."""
        if self.environment is EUIPOEnvironment.SANDBOX:
            return "https://api-sandbox.euipo.europa.eu/trademark-search"
        return "https://api.euipo.europa.eu/trademark-search"


@dataclass(frozen=True, slots=True)
class SearchPage:
    """Validated EUIPO page envelope."""

    trademarks: list[dict[str, Any]]
    size: int
    total_elements: int
    total_pages: int
    page: int


@dataclass(frozen=True, slots=True)
class IncrementalBatch:
    """Deduplicated incremental result and its next date cursor."""

    records: list[dict[str, Any]]
    next_cursor: date


class EUIPOClientError(RuntimeError):
    """Structured error which deliberately excludes request secrets and bodies."""

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        status_code: int | None = None,
        correlation_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.correlation_id = correlation_id
        self.retryable = retryable


Sleep = Callable[[float], Awaitable[None]]


class EUIPOClient:
    """Small async OAuth2 and search client with no application wiring."""

    def __init__(
        self,
        settings: EUIPOSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        random_source: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings
        self._sleep = sleep
        self._random = random_source
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(
                connect=settings.connect_timeout,
                read=settings.read_timeout,
                write=settings.write_timeout,
                pool=settings.pool_timeout,
            ),
            headers={"Accept": "application/json", "User-Agent": "Markee/0.1"},
        )

    async def __aenter__(self) -> EUIPOClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying connection pool."""
        await self._client.aclose()

    def _require_enabled(self) -> None:
        if not self.settings.enabled:
            raise EUIPOClientError("disabled", "EUIPO client is disabled")
        if not self.settings.client_id or not self.settings.client_secret.get_secret_value():
            raise EUIPOClientError("configuration", "EUIPO credentials are not configured")

    async def _access_token(self, *, force: bool = False) -> str:
        self._require_enabled()
        now = time.monotonic()
        if not force and self._token and now < self._token_expires_at:
            return self._token
        async with self._token_lock:
            now = time.monotonic()
            if not force and self._token and now < self._token_expires_at:
                return self._token
            try:
                response = await self._client.post(
                    self.settings.token_url,
                    data={
                        "grant_type": "client_credentials",
                        "scope": "uid",
                        "client_id": self.settings.client_id,
                        "client_secret": self.settings.client_secret.get_secret_value(),
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.HTTPError as exc:
                raise EUIPOClientError(
                    "auth_transport", "EUIPO authentication transport failed", retryable=True
                ) from exc
            if response.status_code >= 400:
                raise self._http_error(response, kind="authentication")
            try:
                payload = response.json()
                token = payload["access_token"]
                expires_in = float(payload.get("expires_in", 3600))
                if not isinstance(token, str) or not token:
                    raise (KeyError("access_token"))
            except (ValueError, TypeError, KeyError) as exc:
                raise EUIPOClientError(
                    "malformed_auth_payload", "EUIPO authentication returned a malformed payload"
                ) from exc
            skew = self.settings.token_skew.total_seconds()
            self._token = token
            self._token_expires_at = time.monotonic() + max(0.0, expires_in - skew)
            return token

    async def _request(self, params: dict[str, str | int]) -> httpx.Response:
        refreshed = False
        retry = 0
        while True:
            token = await self._access_token()
            try:
                response = await self._client.get(
                    f"{self.settings.api_base_url}/trademarks",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-IBM-Client-Id": self.settings.client_id,
                    },
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if retry >= self.settings.max_retries:
                    raise EUIPOClientError(
                        "transport", "EUIPO request transport failed", retryable=True
                    ) from exc
                await self._sleep(self._backoff_delay(retry))
                retry += 1
                continue

            if response.status_code == 401 and not refreshed:
                self._token = None
                self._token_expires_at = 0.0
                await self._access_token(force=True)
                refreshed = True
                continue
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if retry < self.settings.max_retries:
                    await self._sleep(self._retry_delay(response, retry))
                    retry += 1
                    continue
            if response.status_code >= 400:
                raise self._http_error(response)
            return response

    def _backoff_delay(self, retry: int) -> float:
        base = self.settings.backoff_base * (2**retry)
        return base + self.settings.backoff_jitter * self._random()

    def _retry_delay(self, response: httpx.Response, retry: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    parsed = email.utils.parsedate_to_datetime(value)
                    return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return self._backoff_delay(retry)

    @staticmethod
    def _http_error(response: httpx.Response, *, kind: str = "http") -> EUIPOClientError:
        correlation_id = response.headers.get("X-Correlation-Id")
        try:
            payload = response.json()
            if isinstance(payload, dict):
                raw_correlation = payload.get("correlationId")
                if isinstance(raw_correlation, str):
                    correlation_id = raw_correlation
        except ValueError:
            pass
        retryable = response.status_code == 429 or response.status_code >= 500
        return EUIPOClientError(
            kind,
            f"EUIPO request failed with HTTP {response.status_code}",
            status_code=response.status_code,
            correlation_id=correlation_id,
            retryable=retryable,
        )

    async def search(
        self,
        query: str,
        *,
        page: int = 0,
        size: int = 100,
        sort: str | None = None,
        fields: str | None = None,
    ) -> SearchPage:
        """Execute one 0-based RSQL search page, capped to the official size 100."""
        if page < 0:
            raise ValueError("page must be non-negative")
        capped_size = min(100, max(10, size))
        params: dict[str, str | int] = {"q": query, "page": page, "size": capped_size}
        if sort:
            params["sort"] = sort
        if fields:
            params["fields"] = fields
        response = await self._request(params)
        try:
            payload = response.json()
            trademarks = payload["trademarks"]
            page_size = payload["size"]
            total_elements = payload["totalElements"]
            total_pages = payload["totalPages"]
            page_number = payload["page"]
            if not isinstance(trademarks, list) or not all(
                isinstance(record, dict) for record in trademarks
            ):
                raise TypeError("trademarks")
            if not all(
                isinstance(value, int)
                for value in (page_size, total_elements, total_pages, page_number)
            ):
                raise TypeError("pagination")
        except (ValueError, KeyError, TypeError) as exc:
            raise EUIPOClientError(
                "malformed_payload",
                "EUIPO search returned a malformed payload",
                status_code=response.status_code,
            ) from exc
        return SearchPage(
            trademarks=trademarks,
            size=page_size,
            total_elements=total_elements,
            total_pages=total_pages,
            page=page_number,
        )

    async def paginate(
        self,
        query: str,
        *,
        size: int = 100,
        sort: str | None = None,
        fields: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield all records across the API's 0-based pages."""
        page_number = 0
        while True:
            result = await self.search(
                query, page=page_number, size=size, sort=sort, fields=fields
            )
            for record in result.trademarks:
                yield record
            page_number += 1
            if page_number >= result.total_pages:
                break

    async def fetch_incremental(
        self,
        cursor: date,
        *,
        query: str | None = None,
        overlap: timedelta | None = None,
        fields: str | None = None,
    ) -> IncrementalBatch:
        """Fetch an overlapped updateDate window and deterministically deduplicate it."""
        effective_overlap = self.settings.overlap if overlap is None else overlap
        lower_bound = cursor - effective_overlap
        clauses = [query] if query else []
        clauses.append(f"updateDate>={lower_bound.isoformat()}")
        rsql = ";".join(clauses)
        records = [
            record
            async for record in self.paginate(
                rsql, size=100, sort="updateDate:asc", fields=fields
            )
        ]

        selected: dict[str, tuple[date, int, dict[str, Any]]] = {}
        for index, record in enumerate(records):
            application_number = record.get("applicationNumber")
            update_date = record.get("updateDate")
            if not isinstance(application_number, str) or not isinstance(update_date, str):
                raise EUIPOClientError(
                    "malformed_payload", "EUIPO incremental record lacks cursor fields"
                )
            try:
                parsed_date = date.fromisoformat(update_date[:10])
            except ValueError as exc:
                raise EUIPOClientError(
                    "malformed_payload", "EUIPO incremental record has invalid updateDate"
                ) from exc
            previous = selected.get(application_number)
            candidate = (parsed_date, index, record)
            if previous is None or candidate[:2] > previous[:2]:
                selected[application_number] = candidate

        deduped = [
            selected[key][2]
            for key in sorted(
                selected,
                key=lambda application_number: (
                    selected[application_number][0], application_number
                ),
            )
        ]
        next_cursor = max((value[0] for value in selected.values()), default=cursor)
        return IncrementalBatch(records=deduped, next_cursor=max(cursor, next_cursor))
