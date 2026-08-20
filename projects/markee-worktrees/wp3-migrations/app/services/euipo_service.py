"""EUIPO / TMview REST API client with OAuth2 and RSQL queries.

When credentials are not configured the client transparently falls back to a
mock mode that returns synthetic data, so the application is fully usable in
development and tests without external access.

When constructed with an :class:`~sqlalchemy.ext.asyncio.AsyncSession`, every
HTTP interaction (including mock-mode calls) is preserved in
``raw.api_responses`` and imports are tracked in ``core.source_runs``.
"""
from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.source import Source, SourceRun
from app.services import ingestion
from app.services.raw_responses import record_api_response

SOURCE_NAME = "euipo_api"


class EUIPOService:
    """Client for the EUIPO/TMview REST API (INPI is reachable via TMview)."""

    BASE_URL = "https://api.euipo.europa.eu"
    AUTH_URL = "https://api.euipo.europa.eu/oauth2/token"
    SEARCH_URL = f"{BASE_URL}/search/api/v1/search"
    DETAILS_URL = f"{BASE_URL}/tmview/api/tradeMark"

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        session: AsyncSession | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            client_id: OAuth2 client id (falls back to settings/env).
            client_secret: OAuth2 client secret (falls back to settings/env).
            session: Optional async session; when provided, raw responses are
                preserved in ``raw.api_responses`` and runs are tracked.
        """
        self.client_id = client_id or settings.EUIPO_API_CLIENT_ID
        self.client_secret = client_secret or settings.EUIPO_API_CLIENT_SECRET
        self.session = session
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self._mock_mode = not (self.client_id and self.client_secret)
        self._source: Source | None = None
        self._run_id: uuid.UUID | None = None

    @property
    def mock_mode(self) -> bool:
        """Whether the client is operating without real credentials."""
        return self._mock_mode

    async def _ensure_source(self) -> Source | None:
        """Return the registered ``core.sources`` row (requires a session)."""
        if self.session is None:
            return None
        if self._source is None:
            self._source = await ingestion.get_or_create_source(
                self.session, SOURCE_NAME
            )
        return self._source

    async def _record(
        self,
        endpoint: str,
        params: dict[str, Any] | None,
        *,
        status: int | None = None,
        body: Any | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> uuid.UUID | None:
        """Persist one raw interaction when a session is attached."""
        source = await self._ensure_source()
        if source is None or self.session is None:
            return None
        row = await record_api_response(
            self.session,
            source_id=source.id,
            source_run_id=self._run_id,
            endpoint=endpoint,
            request_params=params,
            response_status=status,
            response_body=body,
            duration_ms=duration_ms,
            error_message=error,
        )
        return row.id

    async def authenticate(self) -> str:
        """Obtain an OAuth2 access token from EUIPO.

        Returns:
            The bearer access token (a placeholder string in mock mode).
        """
        if self._mock_mode:
            self._token = "mock-token"
            self._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "trademark",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return self._token

    async def _get_auth_header(self) -> dict[str, str]:
        """Return the Authorization header, refreshing the token if needed."""
        if self._mock_mode:
            return {}
        expired = self._token_expires and datetime.now(timezone.utc) >= self._token_expires
        if not self._token or expired:
            await self.authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    @staticmethod
    def _unwrap_results(data: Any) -> list[dict[str, Any]]:
        """Normalise an API response into a list of result dicts."""
        if isinstance(data, dict):
            return data.get("results", [])
        if isinstance(data, list):
            return data
        return []

    async def _get_json(
        self, url: str, params: dict[str, Any] | None = None, timeout: float = 60.0
    ) -> tuple[Any, uuid.UUID | None]:
        """GET a JSON endpoint, timing and preserving the raw interaction.

        Args:
            url: The endpoint URL.
            params: Query parameters.
            timeout: Request timeout in seconds.

        Returns:
            A tuple of (parsed JSON, raw.api_responses id or None).

        Raises:
            httpx.HTTPStatusError: On non-2xx responses (recorded before raising).
        """
        headers = await self._get_auth_header()
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
            except httpx.HTTPError as exc:
                duration = int((time.monotonic() - started) * 1000)
                await self._record(
                    url, params, duration_ms=duration, error=str(exc)
                )
                raise
            duration = int((time.monotonic() - started) * 1000)
            body: Any | None
            try:
                body = response.json()
            except ValueError:
                body = None
            raw_id = await self._record(
                url,
                params,
                status=response.status_code,
                body=body,
                duration_ms=duration,
            )
            response.raise_for_status()
            return body, raw_id

    async def search_trademarks(
        self,
        query: str,
        jurisdiction: str | None = None,
        nice_classes: list[int] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search trademarks via an RSQL query.

        Args:
            query: Free-text query matched against the word mark.
            jurisdiction: Optional jurisdiction filter.
            nice_classes: Optional list of Nice classes to filter by.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            A list of raw trademark records.
        """
        if self._mock_mode:
            results = self._mock_search(query, limit)
            await self._record(
                "mock://euipo/search", {"q": query, "limit": limit}, status=200, body=results
            )
            return results

        rsql_parts = [f"wordMark==*{query}*"]
        if jurisdiction:
            rsql_parts.append(f"jurisdiction=={jurisdiction}")
        if nice_classes:
            classes_filter = ",".join(str(c) for c in nice_classes)
            rsql_parts.append(f"niceClass=in=({classes_filter})")
        rsql = ";".join(rsql_parts)

        params = {"q": rsql, "limit": limit, "offset": offset}
        data, _ = await self._get_json(self.SEARCH_URL, params)
        return self._unwrap_results(data)

    async def get_trademark_details(self, application_number: str) -> dict[str, Any]:
        """Fetch full details for a single trademark.

        Args:
            application_number: The application number to look up.

        Returns:
            The trademark detail record (may be empty if not found in mock mode).
        """
        if self._mock_mode:
            details = self._mock_details(application_number)
            await self._record(
                f"mock://euipo/tradeMark/{application_number}", None, status=200, body=details
            )
            return details

        data, _ = await self._get_json(
            f"{self.DETAILS_URL}/{application_number}", timeout=30.0
        )
        return data if isinstance(data, dict) else {}

    async def poll_recent_changes(
        self, since: datetime, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Poll incremental updates via an ``updateDate`` RSQL filter.

        Args:
            since: Only return records updated on or after this timestamp.
            limit: Maximum number of results.

        Returns:
            A list of changed trademark records.
        """
        if self._mock_mode:
            return self._mock_poll(limit)

        since_iso = since.strftime("%Y-%m-%dT%H:%M:%S")
        rsql = f"updateDate=ge={since_iso}"
        params = {"q": rsql, "limit": limit, "offset": 0}
        data, _ = await self._get_json(self.SEARCH_URL, params)
        return self._unwrap_results(data)

    async def poll_incremental(
        self,
        since_date: datetime | date,
        *,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> list[dict[str, Any]]:
        """Poll all records changed since ``since_date``, paginating by page.

        Uses the source's ``updateDate`` field as the incremental cursor
        (see config/sources.yaml). Each fetched page is preserved in
        ``raw.api_responses`` when a session is attached; every returned
        record carries a private ``_raw_response_id`` key linking it to the
        raw page it came from (consumed by :meth:`import_batch`).

        Args:
            since_date: Lower bound (inclusive) for ``updateDate``.
            page_size: Records per page.
            max_pages: Safety cap on the number of pages fetched.

        Returns:
            The accumulated list of changed records.
        """
        if isinstance(since_date, datetime):
            since_iso = since_date.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            since_iso = since_date.strftime("%Y-%m-%dT00:00:00")

        if self._mock_mode:
            records = self._mock_poll(page_size)
            raw_id = await self._record(
                "mock://euipo/search",
                {"q": f"updateDate=ge={since_iso}", "limit": page_size},
                status=200,
                body=records,
            )
            for record in records:
                record["_raw_response_id"] = str(raw_id) if raw_id else None
            return records

        rsql = f"updateDate=ge={since_iso}"
        collected: list[dict[str, Any]] = []
        for page in range(max_pages):
            params = {"q": rsql, "limit": page_size, "offset": page * page_size}
            data, raw_id = await self._get_json(self.SEARCH_URL, params)
            results = self._unwrap_results(data)
            for record in results:
                record["_raw_response_id"] = str(raw_id) if raw_id else None
            collected.extend(results)
            if len(results) < page_size:
                break
        return collected

    async def import_batch(
        self,
        records: list[dict[str, Any]],
        session: AsyncSession | None = None,
        *,
        run: SourceRun | None = None,
        change_source: str = "euipo_poll",
    ) -> dict[str, int]:
        """Feed a batch of raw records through the ingestion service.

        Args:
            records: Raw records (as returned by :meth:`poll_incremental`).
            session: Session to write with (defaults to the bound session).
            run: Optional run whose counters are updated in place.
            change_source: Version provenance label.

        Returns:
            Counts: ``{"processed", "new", "updated", "unchanged", "failed"}``.

        Raises:
            ValueError: If no session is available.
        """
        db = session or self.session
        if db is None:
            raise ValueError("import_batch requires a database session")

        source = await ingestion.get_or_create_source(db, SOURCE_NAME)
        service = ingestion.IngestionService(db)
        counts = {"processed": 0, "new": 0, "updated": 0, "unchanged": 0, "failed": 0}

        for record in records:
            raw_ref = record.pop("_raw_response_id", None)
            raw_response_id = uuid.UUID(raw_ref) if raw_ref else None
            counts["processed"] += 1
            try:
                result = await service.ingest_trademark(
                    record,
                    change_source=change_source,
                    source=source,
                    raw_response_id=raw_response_id,
                )
            except Exception:  # noqa: BLE001 - one bad record must not sink the batch
                counts["failed"] += 1
                continue
            if result.status == "created":
                counts["new"] += 1
            elif result.status == "updated":
                counts["updated"] += 1
            elif result.status == "unchanged":
                counts["unchanged"] += 1
            else:
                counts["failed"] += 1

        if run is not None:
            run.items_processed += counts["processed"]
            run.items_new += counts["new"]
            run.items_updated += counts["updated"]
            run.items_failed += counts["failed"]
        return counts

    async def run_incremental_import(
        self,
        since_date: datetime | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Full incremental pipeline: poll → preserve raw → ingest → track run.

        The ``since`` cursor defaults to the last completed run's cursor with a
        one-hour overlap (see config/sources.yaml ``lookback_hours``), or six
        hours ago on the first ever run.

        Args:
            since_date: Optional explicit lower bound for ``updateDate``.
            session: Session to use (defaults to the bound session).

        Returns:
            A summary dict with run id, status and item counts.

        Raises:
            ValueError: If no session is available.
        """
        db = session or self.session
        if db is None:
            raise ValueError("run_incremental_import requires a database session")
        self.session = db

        source = await ingestion.get_or_create_source(db, SOURCE_NAME)
        self._source = source

        if since_date is None:
            since_date = await self._resolve_cursor(db, source)

        run = await ingestion.start_run(db, source, "incremental_poll")
        self._run_id = run.id
        try:
            records = await self.poll_incremental(since_date)
            counts = await self.import_batch(records, db, run=run)
        except Exception as exc:  # noqa: BLE001 - the run row must record failures
            ingestion.finish_run(run, status="failed", error_message=str(exc))
            await db.commit()
            raise
        finally:
            self._run_id = None

        cursor = self._max_update_date(records) or datetime.now(timezone.utc)
        status = "completed" if counts["failed"] == 0 else "partial"
        ingestion.finish_run(run, status=status, cursor_value=cursor.isoformat())
        await db.commit()
        return {"run_id": str(run.id), "status": status, "since": since_date.isoformat(), **counts}

    @staticmethod
    def _max_update_date(records: list[dict[str, Any]]) -> datetime | None:
        """Return the maximum ``update_date`` across a batch of records."""
        best: datetime | None = None
        for record in records:
            normalized = ingestion.normalize_trademark_record(record)
            value = normalized["update_date"]
            if value is not None and (best is None or value > best):
                best = value
        return best

    @staticmethod
    async def _resolve_cursor(db: AsyncSession, source: Source) -> datetime:
        """Derive the polling lower bound from the last completed run."""
        from sqlalchemy import select

        last_cursor = (
            await db.execute(
                select(SourceRun.cursor_value)
                .where(
                    SourceRun.source_id == source.id,
                    SourceRun.status.in_(("completed", "partial")),
                    SourceRun.cursor_value.is_not(None),
                )
                .order_by(SourceRun.started_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_cursor:
            try:
                cursor = datetime.fromisoformat(last_cursor)
                # One-hour overlap to catch records updated around the cursor.
                return cursor - timedelta(hours=1)
            except ValueError:
                pass
        return datetime.now(timezone.utc) - timedelta(hours=6)

    def _mock_poll(self, limit: int) -> list[dict[str, Any]]:
        """Return synthetic changed records with an ``update_date`` stamp."""
        now_iso = datetime.now(timezone.utc).isoformat()
        records = self._mock_search("", limit)
        for record in records:
            record.setdefault("update_date", now_iso)
        return records

    def _mock_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Return synthetic trademark data for development and tests.

        Args:
            query: The search query (case-insensitive substring match).
            limit: Maximum number of results.

        Returns:
            A list of synthetic trademark records. Falls back to the full
            sample set when the query matches nothing, so fallback code paths
            always have data to work with.
        """
        base: list[dict[str, Any]] = [
            {
                "source_id": "EUIPO-018765432",
                "application_number": "018765432",
                "application_date": "2024-01-15",
                "registration_number": "018765432",
                "registration_date": "2024-06-01",
                "word_mark": "ACME TECH",
                "status": "Registered",
                "renewal_status": "Active",
                "nice_classes": [9, 42],
                "applicants": [{"name": "Acme Corp", "address": "Lisbon"}],
                "representatives": [{"name": "Agente Silva"}],
                "goods_services": "Software; IT services",
                "jurisdiction": "EUIPO",
            },
            {
                "source_id": "INPI-N-123456",
                "application_number": "N-123456",
                "application_date": "2023-11-20",
                "registration_number": "564738",
                "registration_date": "2024-03-10",
                "word_mark": "MARCA LUSA",
                "status": "Registered",
                "renewal_status": "Active",
                "nice_classes": [25, 35],
                "applicants": [{"name": "Lusa Moda Lda", "address": "Porto"}],
                "representatives": [],
                "goods_services": "Vestuário; Comércio",
                "jurisdiction": "INPI",
            },
            {
                "source_id": "EUIPO-019876543",
                "application_number": "019876543",
                "application_date": "2024-03-01",
                "registration_number": "019876543",
                "registration_date": "2024-08-15",
                "word_mark": "SOLARIS",
                "status": "Published",
                "renewal_status": "Pending",
                "nice_classes": [11, 37],
                "applicants": [{"name": "Solaris Energia SA", "address": "Lisbon"}],
                "representatives": [{"name": "Advogado João"}],
                "goods_services": "Painéis solares; Instalação",
                "jurisdiction": "EUIPO",
            },
        ]
        if not query:
            return base[:limit]
        filtered = [
            m
            for m in base
            if query.lower() in (m.get("word_mark") or "").lower()
            or query.lower() in (m.get("application_number") or "").lower()
        ]
        # Fall back to the full sample set so fallback tests always get data.
        return (filtered or base)[:limit]

    def _mock_details(self, application_number: str) -> dict[str, Any]:
        """Return synthetic details for a single application number.

        Args:
            application_number: The application number to look up.

        Returns:
            The matching mock record with a ``raw_data`` marker, or ``{}``.
        """
        for m in self._mock_search("", 100):
            if m.get("application_number") == application_number:
                return {**m, "raw_data": {"mock": True}}
        return {}


def get_euipo_service() -> EUIPOService:
    """Return a ready-to-use :class:`EUIPOService` instance.

    Returns:
        A new EUIPO service configured from application settings.
    """
    return EUIPOService()
