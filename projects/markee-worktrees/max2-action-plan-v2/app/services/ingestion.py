"""Ingestion orchestrator: raw source data → normalised core entities.

Responsibilities:

- normalise raw API/PDF records into the canonical trademark shape;
- versioning per ADR 0002 (append-only ``core.trademark_versions`` + current
  state in ``core.trademarks``) — re-running with identical data is a no-op;
- upsert holders/representatives and their N:M links;
- sync per-class goods/services terms;
- confidence scoring, routing uncertain results to ``app.review_queue``;
- source registry (``core.sources``) and run tracking (``core.source_runs``).
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holder import Holder, TrademarkHolder
from app.models.lifecycle import LifecycleEvent
from app.models.nice_class import NiceClass
from app.models.goods_services import GoodsServices
from app.models.representative import Representative, TrademarkRepresentative
from app.models.review_queue import ReviewQueueItem
from app.models.source import Source, SourceRun
from app.models.trademark import Trademark
from app.models.trademark_version import TrademarkVersion
from app.services.confidence import (
    REVIEW_THRESHOLD,
    RecordConfidence,
    score_bpi_event,
    score_trademark_record,
)
from app.utils import parse_date

logger = logging.getLogger(__name__)

# Trademark fields tracked in version snapshots and diffs.
TRACKED_FIELDS: tuple[str, ...] = (
    "source_id",
    "application_number",
    "application_date",
    "registration_number",
    "registration_date",
    "word_mark",
    "figurative_mark_url",
    "status",
    "renewal_status",
    "nice_classes",
    "applicants",
    "representatives",
    "goods_services",
    "jurisdiction",
)

# Registry defaults mirroring config/sources.yaml (kept dependency-free).
SOURCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "euipo_api": {
        "source_type": "api_rest",
        "base_url": "https://api.euipo.europa.eu",
        "auth_method": "oauth2_client_credentials",
        "priority": 1,
    },
    "inpi_bpi": {
        "source_type": "pdf_bulletin",
        "base_url": "https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin",
        "auth_method": "none",
        "priority": 2,
    },
}

_RE_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Build a stable lowercase key fragment from arbitrary text."""
    return _RE_NON_ALNUM.sub("-", value.strip().lower()).strip("-")


def _first(record: dict[str, Any], *keys: str) -> Any:
    """Return the first non-``None`` value among ``keys`` in ``record``."""
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def normalize_trademark_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw source record into the canonical trademark shape.

    Accepts both already-normalised dicts (snake_case, e.g. from the EUIPO
    mock mode) and camelCase records as returned by the EUIPO REST API.

    Args:
        record: The raw record.

    Returns:
        A dict with the canonical fields (``None`` when absent).
    """
    jurisdiction = _first(record, "jurisdiction", "office") or "EUIPO"
    application_number = _first(record, "application_number", "applicationNumber")
    source_id = _first(record, "source_id", "sourceId")
    if not source_id and application_number:
        source_id = f"{jurisdiction}-{application_number}"

    nice_classes = _first(record, "nice_classes", "niceClasses", "niceClass")
    if isinstance(nice_classes, (int, str)):
        nice_classes = [int(nice_classes)]
    elif nice_classes is not None:
        nice_classes = [int(c) for c in nice_classes]

    update_date_raw = _first(record, "update_date", "updateDate")
    update_date: datetime | None = None
    if isinstance(update_date_raw, datetime):
        update_date = update_date_raw
    elif isinstance(update_date_raw, str) and update_date_raw:
        try:
            update_date = datetime.fromisoformat(update_date_raw.replace("Z", "+00:00"))
        except ValueError:
            update_date = None
    if update_date is not None and update_date.tzinfo is None:
        update_date = update_date.replace(tzinfo=timezone.utc)

    goods_services = _first(record, "goods_services", "goodsServices")
    goods_services_list = _first(record, "goods_services_list", "gsList")
    if isinstance(goods_services, list):
        goods_services_list = goods_services_list or goods_services
        goods_services = None

    return {
        "source_id": source_id,
        "application_number": application_number,
        "application_date": parse_date(_first(record, "application_date", "applicationDate")),
        "registration_number": _first(record, "registration_number", "registrationNumber"),
        "registration_date": parse_date(
            _first(record, "registration_date", "registrationDate")
        ),
        "word_mark": _first(record, "word_mark", "wordMark", "markVerbalElementText"),
        "figurative_mark_url": _first(
            record, "figurative_mark_url", "markImageURI", "markImageUrl"
        ),
        "status": _first(record, "status", "markCurrentStatusCode"),
        "renewal_status": _first(record, "renewal_status", "renewalStatus"),
        "nice_classes": nice_classes,
        "applicants": _first(record, "applicants", "applicantReferences") or [],
        "representatives": _first(record, "representatives", "representativeReferences")
        or [],
        "goods_services": goods_services,
        "goods_services_list": goods_services_list,
        "jurisdiction": jurisdiction,
        "update_date": update_date,
        "raw_data": record,
    }


def snapshot_of(trademark: Trademark) -> dict[str, Any]:
    """Build a JSON-serialisable snapshot of a trademark's tracked fields.

    Args:
        trademark: The ORM row.

    Returns:
        A dict keyed by :data:`TRACKED_FIELDS` with ISO strings for dates.
    """
    snapshot: dict[str, Any] = {}
    for name in TRACKED_FIELDS:
        value = getattr(trademark, name)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        snapshot[name] = value
    return snapshot


def compute_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Compute a human-readable diff between two snapshots.

    Args:
        old: The previous snapshot.
        new: The new snapshot.

    Returns:
        ``{"added": {...}, "removed": {...}, "changed": {field: {"old", "new"}}}``
        with empty sections omitted; ``{}`` means no change.
    """
    added: dict[str, Any] = {}
    removed: dict[str, Any] = {}
    changed: dict[str, Any] = {}
    for key in set(old) | set(new):
        old_value = old.get(key)
        new_value = new.get(key)
        if old_value == new_value:
            continue
        if old_value in (None, [], {}) and new_value not in (None, [], {}):
            added[key] = new_value
        elif new_value in (None, [], {}) and old_value not in (None, [], {}):
            removed[key] = old_value
        else:
            changed[key] = {"old": old_value, "new": new_value}
    diff: dict[str, Any] = {}
    if added:
        diff["added"] = added
    if removed:
        diff["removed"] = removed
    if changed:
        diff["changed"] = changed
    return diff


def classify_change(diff: dict[str, Any]) -> str:
    """Classify a snapshot diff into a version ``change_type``.

    Args:
        diff: A diff produced by :func:`compute_diff`.

    Returns:
        One of ``status_change``, ``owner_change``, ``classification_change``,
        ``renewal`` or ``update``.
    """
    touched: set[str] = set()
    for section in ("added", "removed", "changed"):
        touched.update(diff.get(section, {}).keys())
    if "status" in touched:
        return "status_change"
    if "applicants" in touched:
        return "owner_change"
    if "renewal_status" in touched:
        return "renewal"
    if "nice_classes" in touched or "goods_services" in touched:
        return "classification_change"
    return "update"


def add_months(day: date, months: int) -> date:
    """Return ``day`` shifted by ``months`` calendar months (clamped to month end).

    Args:
        day: The starting date.
        months: Number of months to add.

    Returns:
        The shifted date.
    """
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp the day to the target month's length (e.g. 31 Jan + 1m → 28 Feb).
    for candidate in (day.day, 30, 29, 28):
        try:
            return date(year, month, candidate)
        except ValueError:
            continue
    raise ValueError(f"Cannot shift {day} by {months} months")


async def get_or_create_source(
    session: AsyncSession, name: str, **overrides: Any
) -> Source:
    """Fetch a registered source by name, creating it from defaults if missing.

    Args:
        session: An active async session.
        name: The source name (e.g. ``euipo_api``, ``inpi_bpi``).
        **overrides: Column overrides applied on creation.

    Returns:
        The persistent :class:`Source` row.
    """
    source = (
        await session.execute(select(Source).where(Source.name == name))
    ).scalar_one_or_none()
    if source is not None:
        return source
    defaults: dict[str, Any] = {
        "source_type": "api_rest",
        "priority": 1,
        **SOURCE_DEFAULTS.get(name, {}),
        **overrides,
    }
    source = Source(name=name, **defaults)
    session.add(source)
    await session.flush()
    return source


async def start_run(
    session: AsyncSession, source: Source, run_type: str
) -> SourceRun:
    """Open a new ``core.source_runs`` row in ``running`` state.

    Args:
        session: An active async session.
        source: The source being executed.
        run_type: ``incremental_poll``, ``full_backfill`` or ``daily_parse``.

    Returns:
        The flushed :class:`SourceRun` row.
    """
    run = SourceRun(
        source_id=source.id,
        run_type=run_type,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()
    return run


def finish_run(
    run: SourceRun,
    *,
    status: str,
    error_message: str | None = None,
    cursor_value: str | None = None,
) -> None:
    """Mark a run as finished, recording status, error and resume cursor.

    Args:
        run: The run to finalise.
        status: ``completed``, ``failed`` or ``partial``.
        error_message: Optional error description.
        cursor_value: Optional cursor for the next run.
    """
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    if error_message:
        run.error_message = error_message[:2000]
    if cursor_value:
        run.cursor_value = cursor_value[:128]


@dataclass
class IngestionResult:
    """Outcome of ingesting a single trademark record."""

    status: str  # created | updated | unchanged | skipped
    trademark_id: uuid.UUID | None = None
    version_number: int | None = None
    confidence: float | None = None
    queued_for_review: bool = False
    error: str | None = None


@dataclass
class BPIIngestSummary:
    """Outcome of ingesting a batch of BPI events."""

    created: int = 0
    duplicates: int = 0
    queued_for_review: int = 0
    unmatched: int = 0
    errors: list[str] = field(default_factory=list)


class IngestionService:
    """Writes normalised source data into the core/events schemas."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the service.

        Args:
            session: An active async session; the caller owns the transaction.
        """
        self.session = session
        self._nice_class_cache: dict[int, NiceClass] = {}

    # ── Trademarks ──────────────────────────────────────────────────────────

    async def ingest_trademark(
        self,
        record: dict[str, Any],
        *,
        change_source: str = "euipo_poll",
        source: Source | None = None,
        raw_response_id: uuid.UUID | None = None,
    ) -> IngestionResult:
        """Ingest one raw trademark record (create, version or no-op).

        Idempotent: re-ingesting an identical record produces no new version
        and no duplicate related rows.

        Args:
            record: The raw record (normalised internally).
            change_source: Version provenance (``euipo_poll``, ``bpi_parse``, ...).
            source: Optional registered source, stored on the trademark row.
            raw_response_id: Optional ``raw.api_responses`` id for provenance.

        Returns:
            An :class:`IngestionResult` describing what happened.
        """
        normalized = normalize_trademark_record(record)
        if not normalized["source_id"]:
            return IngestionResult(status="skipped", error="missing source_id")

        confidence = score_trademark_record(normalized)

        trademark = (
            await self.session.execute(
                select(Trademark).where(Trademark.source_id == normalized["source_id"])
            )
        ).scalar_one_or_none()

        if trademark is None:
            result = await self._create_trademark(
                normalized, confidence, change_source, source, raw_response_id
            )
        else:
            result = await self._update_trademark(
                trademark, normalized, confidence, change_source, source, raw_response_id
            )

        if confidence.needs_review and result.status in ("created", "updated"):
            await self._queue_trademark_review(normalized, confidence, result.trademark_id)
            result.queued_for_review = True
        return result

    async def _create_trademark(
        self,
        normalized: dict[str, Any],
        confidence: RecordConfidence,
        change_source: str,
        source: Source | None,
        raw_response_id: uuid.UUID | None,
    ) -> IngestionResult:
        """Insert a brand-new trademark plus its version 1 and relations."""
        trademark = Trademark(
            source_id=normalized["source_id"],
            application_number=normalized["application_number"],
            application_date=normalized["application_date"],
            registration_number=normalized["registration_number"],
            registration_date=normalized["registration_date"],
            word_mark=normalized["word_mark"],
            figurative_mark_url=normalized["figurative_mark_url"],
            status=normalized["status"],
            renewal_status=normalized["renewal_status"],
            nice_classes=normalized["nice_classes"],
            applicants=normalized["applicants"],
            representatives=normalized["representatives"],
            goods_services=normalized["goods_services"],
            jurisdiction=normalized["jurisdiction"],
            raw_data=normalized["raw_data"],
            update_date=normalized["update_date"],
            confidence_score=confidence.overall,
            ingest_source_id=source.id if source else None,
        )
        self.session.add(trademark)
        await self.session.flush()

        self.session.add(
            TrademarkVersion(
                trademark_id=trademark.id,
                version_number=1,
                snapshot=snapshot_of(trademark),
                diff_from_previous=None,
                change_source=change_source,
                change_type="created",
                raw_response_id=raw_response_id,
            )
        )
        await self._sync_relations(trademark, normalized)
        await self.session.flush()
        return IngestionResult(
            status="created",
            trademark_id=trademark.id,
            version_number=1,
            confidence=confidence.overall,
        )

    async def _update_trademark(
        self,
        trademark: Trademark,
        normalized: dict[str, Any],
        confidence: RecordConfidence,
        change_source: str,
        source: Source | None,
        raw_response_id: uuid.UUID | None,
    ) -> IngestionResult:
        """Apply changes to an existing trademark, versioning when needed."""
        old_snapshot = snapshot_of(trademark)

        # Only non-None incoming values overwrite; a partial record must not
        # wipe fields the source simply omitted this time.
        for name in TRACKED_FIELDS:
            value = normalized.get(name)
            if value is not None and value != []:
                setattr(trademark, name, value)

        new_snapshot = snapshot_of(trademark)
        diff = compute_diff(old_snapshot, new_snapshot)
        if not diff:
            # Identical payload: keep metadata fresh but create no version.
            if normalized["update_date"] is not None:
                trademark.update_date = normalized["update_date"]
            return IngestionResult(
                status="unchanged",
                trademark_id=trademark.id,
                confidence=confidence.overall,
            )

        max_version = (
            await self.session.execute(
                select(func.max(TrademarkVersion.version_number)).where(
                    TrademarkVersion.trademark_id == trademark.id
                )
            )
        ).scalar_one() or 0
        version_number = max_version + 1

        self.session.add(
            TrademarkVersion(
                trademark_id=trademark.id,
                version_number=version_number,
                snapshot=new_snapshot,
                diff_from_previous=diff,
                change_source=change_source,
                change_type=classify_change(diff),
                raw_response_id=raw_response_id,
            )
        )
        trademark.raw_data = normalized["raw_data"]
        if normalized["update_date"] is not None:
            trademark.update_date = normalized["update_date"]
        trademark.confidence_score = confidence.overall
        if source is not None:
            trademark.ingest_source_id = source.id

        await self._sync_relations(trademark, normalized)
        await self.session.flush()
        return IngestionResult(
            status="updated",
            trademark_id=trademark.id,
            version_number=version_number,
            confidence=confidence.overall,
        )

    async def _sync_relations(
        self, trademark: Trademark, normalized: dict[str, Any]
    ) -> None:
        """Sync holders, representatives and goods/services for one trademark."""
        await self._sync_holders(trademark, normalized.get("applicants") or [])
        await self._sync_representatives(trademark, normalized.get("representatives") or [])
        await self._sync_goods_services(trademark, normalized)

    # ── Holders / representatives ──────────────────────────────────────────

    @staticmethod
    def _party_source_key(party: dict[str, Any]) -> str | None:
        """Derive a stable source key for an applicant/representative dict."""
        identifier = party.get("id") or party.get("identifier")
        if identifier:
            return str(identifier)[:64]
        name = party.get("name")
        if not name:
            return None
        country = party.get("country") or ""
        return f"name:{_slugify(str(name))}:{_slugify(str(country))}"[:64]

    async def _upsert_holder(self, party: dict[str, Any]) -> Holder | None:
        """Insert or update one holder, keyed by its derived source key."""
        key = self._party_source_key(party)
        if key is None:
            return None
        holder = (
            await self.session.execute(select(Holder).where(Holder.source_id == key))
        ).scalar_one_or_none()
        if holder is None:
            holder = Holder(source_id=key, name=str(party.get("name"))[:512])
            self.session.add(holder)
        holder.name = str(party.get("name"))[:512]
        holder.address = party.get("address")
        holder.country = (party.get("country") or None) and str(party["country"])[:2]
        holder.type = party.get("type") if party.get("type") in ("natural", "legal") else None
        holder.raw_data = party
        await self.session.flush()
        return holder

    async def _sync_holders(
        self, trademark: Trademark, applicants: list[dict[str, Any]]
    ) -> None:
        """Upsert holders and make trademark↔holder links match ``applicants``."""
        desired: dict[uuid.UUID, Holder] = {}
        for party in applicants:
            if not isinstance(party, dict) or not party.get("name"):
                continue
            holder = await self._upsert_holder(party)
            if holder is not None:
                desired[holder.id] = holder

        existing_links = (
            await self.session.execute(
                select(TrademarkHolder).where(
                    TrademarkHolder.trademark_id == trademark.id,
                    TrademarkHolder.role == "applicant",
                )
            )
        ).scalars().all()
        existing_ids = {link.holder_id for link in existing_links}

        for link in existing_links:
            if link.holder_id not in desired:
                await self.session.delete(link)
        for holder_id in desired:
            if holder_id not in existing_ids:
                self.session.add(
                    TrademarkHolder(
                        trademark_id=trademark.id,
                        holder_id=holder_id,
                        role="applicant",
                        since_date=trademark.application_date,
                    )
                )
        await self.session.flush()

    async def _upsert_representative(self, party: dict[str, Any]) -> Representative | None:
        """Insert or update one representative, keyed by its derived source key."""
        key = self._party_source_key(party)
        if key is None:
            return None
        rep = (
            await self.session.execute(
                select(Representative).where(Representative.source_id == key)
            )
        ).scalar_one_or_none()
        if rep is None:
            rep = Representative(source_id=key, name=str(party.get("name"))[:512])
            self.session.add(rep)
        rep.name = str(party.get("name"))[:512]
        rep.address = party.get("address")
        rep.country = (party.get("country") or None) and str(party["country"])[:2]
        rep.type = (
            party.get("type")
            if party.get("type") in ("natural", "legal", "association")
            else None
        )
        rep.raw_data = party
        await self.session.flush()
        return rep

    async def _sync_representatives(
        self, trademark: Trademark, representatives: list[dict[str, Any]]
    ) -> None:
        """Upsert representatives and sync the N:M links."""
        desired: dict[uuid.UUID, Representative] = {}
        for party in representatives:
            if not isinstance(party, dict) or not party.get("name"):
                continue
            rep = await self._upsert_representative(party)
            if rep is not None:
                desired[rep.id] = rep

        existing_links = (
            await self.session.execute(
                select(TrademarkRepresentative).where(
                    TrademarkRepresentative.trademark_id == trademark.id
                )
            )
        ).scalars().all()
        existing_ids = {link.representative_id for link in existing_links}

        for link in existing_links:
            if link.representative_id not in desired:
                await self.session.delete(link)
        for rep_id in desired:
            if rep_id not in existing_ids:
                self.session.add(
                    TrademarkRepresentative(
                        trademark_id=trademark.id,
                        representative_id=rep_id,
                        role="representative",
                    )
                )
        await self.session.flush()

    # ── Goods & services ────────────────────────────────────────────────────

    async def _get_or_create_nice_class(self, class_number: int) -> NiceClass:
        """Fetch a Nice class row by number, creating it on first sight."""
        cached = self._nice_class_cache.get(class_number)
        if cached is not None:
            return cached
        nice = (
            await self.session.execute(
                select(NiceClass).where(NiceClass.class_number == class_number)
            )
        ).scalar_one_or_none()
        if nice is None:
            nice = NiceClass(class_number=class_number)
            self.session.add(nice)
            await self.session.flush()
        self._nice_class_cache[class_number] = nice
        return nice

    def _desired_terms(
        self, normalized: dict[str, Any]
    ) -> list[tuple[int, str, str]]:
        """Build the desired (class_number, term, language) tuples for a record."""
        desired: list[tuple[int, str, str]] = []
        gs_list = normalized.get("goods_services_list")
        if gs_list:
            for entry in gs_list:
                if not isinstance(entry, dict):
                    continue
                class_number = entry.get("nice_class") or entry.get("classNumber")
                if class_number is None:
                    continue
                language = str(entry.get("language") or "pt")[:8]
                terms = entry.get("terms") or entry.get("goodsServicesDescription") or []
                if isinstance(terms, str):
                    terms = [t.strip() for t in terms.split(";") if t.strip()]
                for term in terms:
                    desired.append((int(class_number), str(term), language))
            return desired

        text = normalized.get("goods_services")
        classes = normalized.get("nice_classes") or []
        if not text or not classes:
            return desired
        terms = [t.strip() for t in str(text).split(";") if t.strip()]
        if len(terms) == len(classes):
            # Positional pairing when the source aligns terms with classes.
            desired = [(int(c), t, "pt") for c, t in zip(classes, terms)]
        else:
            desired = [(int(c), str(text).strip(), "pt") for c in classes]
        return desired

    async def _sync_goods_services(
        self, trademark: Trademark, normalized: dict[str, Any]
    ) -> None:
        """Make ``core.goods_services`` rows match the record (idempotent)."""
        desired = self._desired_terms(normalized)
        if not desired and not normalized.get("goods_services") and not normalized.get(
            "goods_services_list"
        ):
            return  # record carries no G&S info — leave existing rows alone

        desired_keys: set[tuple[int, str, str]] = set(desired)
        for class_number in {c for c, _, _ in desired_keys if 1 <= c <= 45}:
            await self._get_or_create_nice_class(class_number)

        existing = (
            await self.session.execute(
                select(GoodsServices, NiceClass)
                .join(NiceClass, GoodsServices.nice_class_id == NiceClass.id)
                .where(GoodsServices.trademark_id == trademark.id)
            )
        ).all()
        existing_by_key = {
            (nice.class_number, gs.term, gs.language): gs for gs, nice in existing
        }

        for key, gs in existing_by_key.items():
            if key not in desired_keys:
                await self.session.delete(gs)
        for class_number, term, language in desired_keys:
            if not 1 <= class_number <= 45:
                continue
            if (class_number, term, language) in existing_by_key:
                continue
            nice = await self._get_or_create_nice_class(class_number)
            self.session.add(
                GoodsServices(
                    trademark_id=trademark.id,
                    nice_class_id=nice.id,
                    term=term,
                    language=language,
                )
            )
        await self.session.flush()

    # ── Review queue ────────────────────────────────────────────────────────

    async def _queue_trademark_review(
        self,
        normalized: dict[str, Any],
        confidence: RecordConfidence,
        trademark_id: uuid.UUID | None,
    ) -> None:
        """Queue a low-confidence trademark record for human review."""
        weak_fields = ", ".join(confidence.issues) or "vários campos"
        payload = {
            key: value
            for key, value in normalized.items()
            if key not in ("raw_data",)
        }
        payload = _jsonable_payload(payload)
        self.session.add(
            ReviewQueueItem(
                source="euipo_api",
                item_type="trademark_record",
                payload=payload,
                reason=f"Extração com baixa confiança (campos: {weak_fields}).",
                confidence_score=confidence.overall,
                trademark_id=trademark_id,
            )
        )
        await self.session.flush()

    # ── BPI lifecycle events ───────────────────────────────────────────────

    async def ingest_bpi_events(
        self,
        events: list[Any],
        *,
        document_id: uuid.UUID | None = None,
        change_source: str = "bpi_parse",
    ) -> BPIIngestSummary:
        """Persist BPI-extracted events, queueing uncertain/unmatched ones.

        Deduplicates on (trademark, event type, event date, source), so
        re-parsing the same bulletin is idempotent.

        Args:
            events: :class:`~app.services.bpi_parser.BPIEvent` objects.
            document_id: The ``core.documents`` id of the parsed bulletin.
            change_source: Provenance label (kept for symmetry/logging).

        Returns:
            A :class:`BPIIngestSummary` with per-outcome counts.
        """
        summary = BPIIngestSummary()
        for event in events:
            app_number = (event.application_number or "").strip()
            confidence = getattr(event, "confidence_score", None)
            if confidence is None:
                confidence = score_bpi_event(
                    event.event_type,
                    app_number or None,
                    getattr(event, "source_excerpt", "") or event.description,
                    event.event_date is not None,
                )

            if not app_number:
                await self._queue_bpi_review(
                    event,
                    confidence,
                    document_id,
                    reason="Evento sem número de pedido identificável.",
                )
                summary.queued_for_review += 1
                continue

            trademark = (
                await self.session.execute(
                    select(Trademark).where(Trademark.application_number == app_number)
                )
            ).scalar_one_or_none()

            if trademark is None:
                await self._queue_bpi_review(
                    event,
                    confidence,
                    document_id,
                    reason=f"Marca com pedido {app_number} não encontrada no sistema.",
                )
                summary.unmatched += 1
                continue

            if confidence < REVIEW_THRESHOLD:
                await self._queue_bpi_review(
                    event,
                    confidence,
                    document_id,
                    trademark_id=trademark.id,
                    reason="Extração com confiança abaixo do limiar de revisão.",
                )
                summary.queued_for_review += 1
                continue

            duplicate = (
                await self.session.execute(
                    select(LifecycleEvent.id).where(
                        LifecycleEvent.trademark_id == trademark.id,
                        LifecycleEvent.event_type == event.event_type,
                        LifecycleEvent.event_date == event.event_date,
                        LifecycleEvent.source == event.source,
                    )
                )
            ).first()
            if duplicate is not None:
                summary.duplicates += 1
                continue

            deadline_date: date | None = None
            if event.event_type == "publication" and event.event_date is not None:
                # PT opposition window: 2 months from BPI publication.
                deadline_date = add_months(event.event_date, 2)

            self.session.add(
                LifecycleEvent(
                    trademark_id=trademark.id,
                    event_type=event.event_type,
                    event_date=event.event_date,
                    deadline_date=deadline_date,
                    description=event.description,
                    source=event.source,
                    source_reference=app_number[:128],
                    page_number=getattr(event, "page_number", None),
                    source_excerpt=getattr(event, "source_excerpt", None) or None,
                    confidence_score=confidence,
                    raw_data={"text": event.raw_text, "change_source": change_source},
                )
            )
            summary.created += 1

        await self.session.flush()
        return summary

    async def _queue_bpi_review(
        self,
        event: Any,
        confidence: float,
        document_id: uuid.UUID | None,
        *,
        trademark_id: uuid.UUID | None = None,
        reason: str,
    ) -> None:
        """Queue one BPI event for human review."""
        if hasattr(event, "__dataclass_fields__"):
            payload = asdict(event)
        else:
            payload = dict(vars(event))
        payload = _jsonable_payload(payload)
        self.session.add(
            ReviewQueueItem(
                source="inpi_bpi",
                item_type="lifecycle_event",
                payload=payload,
                reason=reason,
                confidence_score=confidence,
                trademark_id=trademark_id,
                document_id=document_id,
            )
        )
        await self.session.flush()


def _jsonable_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert dates/datetimes in a payload dict into ISO strings."""
    converted: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (date, datetime)):
            converted[key] = value.isoformat()
        else:
            converted[key] = value
    return converted
