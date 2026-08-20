"""Behavioral tests for the transactional notification outbox.

Covers transaction neutrality, atomic claim semantics, lease ownership,
terminal-state protection, retry scheduling and DB-level invariants.
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, insert, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable

import app.models
from app.models.notification import NotificationOutbox
from app.services.notifications import NotificationOutboxService, retry_delay_seconds

NOW = datetime(2026, 7, 26, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        execution_options={"schema_translate_map": {"app": None}},
    )

    # Standard recipe so SAVEPOINT works under the sqlite driver's
    # legacy transaction handling.
    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_connect(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def _sqlite_begin(conn):
        conn.exec_driver_sql("BEGIN")

    async with engine.begin() as conn:
        await conn.run_sync(lambda c: NotificationOutbox.__table__.create(c))
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        yield db
    await engine.dispose()


async def _enqueue(service: NotificationOutboxService, key: str) -> NotificationOutbox:
    return await service.enqueue(key, "a@example.com", "Alerta", "texto", "<p>texto</p>")


def _row_values(key: str, **overrides) -> dict:
    values = {
        "dedupe_key": key,
        "event_type": "similar_filing",
        "event_version": 1,
        "aggregate_id": uuid.uuid5(uuid.NAMESPACE_URL, key),
        "recipient": "a@example.com",
        "channel": "email",
        "template_key": "alert",
        "template_version": "1",
        "payload": {"title": "s", "body": "t"},
        "status": "pending",
        "attempts": 0,
    }
    values.update(overrides)
    return values


# ---------------------------------------------------------------------------
# Transaction neutrality
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enqueue_is_deduplicated(session):
    service = NotificationOutboxService(session)
    key = "markee:v1:alert:1:email:alert/v1"
    first = await _enqueue(service, key)
    second = await _enqueue(service, key)
    assert first.id == second.id
    assert len((await session.scalars(select(NotificationOutbox))).all()) == 1


@pytest.mark.asyncio
async def test_outer_rollback_discards_enqueue(session):
    service = NotificationOutboxService(session)
    await _enqueue(service, "k-rollback")
    await session.rollback()
    assert (await session.scalars(select(NotificationOutbox))).all() == []


@pytest.mark.asyncio
async def test_dedupe_does_not_destroy_outer_transaction(session):
    service = NotificationOutboxService(session)
    first = await _enqueue(service, "k1")
    await _enqueue(service, "k2")
    duplicate = await _enqueue(service, "k1")
    assert duplicate.id == first.id
    # Both uncommitted rows must still be visible: dedupe handling must not
    # have rolled back the caller's transaction.
    assert len((await session.scalars(select(NotificationOutbox))).all()) == 2
    await session.rollback()
    # The caller still controls the transaction boundary.
    assert (await session.scalars(select(NotificationOutbox))).all() == []


# ---------------------------------------------------------------------------
# Claim semantics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claim_respects_next_attempt_at(session):
    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-backoff")
    item.next_attempt_at = datetime.now(UTC) + timedelta(hours=1)
    await session.flush()
    assert await service.claim_batch("w1", 10) == []
    item.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.flush()
    claimed = await service.claim_batch("w1", 10)
    assert [row.id for row in claimed] == [item.id]
    assert claimed[0].status == "sending"
    assert claimed[0].lease_owner == "w1"
    assert claimed[0].attempts == 1


@pytest.mark.asyncio
async def test_claim_recovers_only_expired_sending_lease(session):
    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-lease")
    claimed = await service.claim_batch("w1", 10, lease_seconds=300, now=NOW)
    assert [row.id for row in claimed] == [item.id]
    # Lease still valid: another worker must not steal the row.
    assert await service.claim_batch("w2", 10, now=NOW + timedelta(seconds=10)) == []
    # Lease expired: recovery is allowed, ownership moves, attempts grow.
    recovered = await service.claim_batch("w2", 10, now=NOW + timedelta(seconds=400))
    assert [row.id for row in recovered] == [item.id]
    assert recovered[0].lease_owner == "w2"
    assert recovered[0].status == "sending"
    assert recovered[0].attempts == 2


@pytest.mark.asyncio
async def test_claim_never_touches_sent_or_dead(session):
    await session.execute(
        insert(NotificationOutbox).values(
            _row_values("k-sent", status="sent", sent_at=NOW)
        )
    )
    await session.execute(
        insert(NotificationOutbox).values(
            _row_values("k-dead", status="dead", failed_at=NOW, attempts=5)
        )
    )
    service = NotificationOutboxService(session)
    assert await service.claim_batch("w1", 10, now=NOW + timedelta(days=365)) == []


@pytest.mark.asyncio
async def test_sent_row_is_never_reopened_by_lifecycle(session):
    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-final")
    await service.claim_batch("w1", 10, now=NOW)
    await service.mark_sent(item.id, "provider-1", worker_id="w1", now=NOW)
    assert await service.claim_batch("w2", 10, now=NOW + timedelta(days=30)) == []
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "sent"


# ---------------------------------------------------------------------------
# Completion guards (owner + lease)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_sent_rejects_wrong_owner(session):
    from app.services.notifications import StaleLeaseError

    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-owner")
    await service.claim_batch("w1", 10, now=NOW)
    with pytest.raises(StaleLeaseError):
        await service.mark_sent(item.id, "provider-x", worker_id="w2", now=NOW)
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "sending"
    assert row.lease_owner == "w1"
    assert row.provider_message_id is None


@pytest.mark.asyncio
async def test_mark_sent_rejects_expired_lease(session):
    from app.services.notifications import StaleLeaseError

    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-stale")
    await service.claim_batch("w1", 10, lease_seconds=300, now=NOW)
    with pytest.raises(StaleLeaseError):
        await service.mark_sent(
            item.id, "provider-x", worker_id="w1", now=NOW + timedelta(seconds=301)
        )
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "sending"
    assert row.sent_at is None


@pytest.mark.asyncio
async def test_mark_sent_rejects_non_sending_row(session):
    from app.services.notifications import StaleLeaseError

    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-pending")
    with pytest.raises(StaleLeaseError):
        await service.mark_sent(item.id, "provider-x", worker_id="w1", now=NOW)


@pytest.mark.asyncio
async def test_mark_failure_rejects_wrong_owner_and_expired_lease(session):
    from app.services.notifications import StaleLeaseError

    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-fail-guard")
    await service.claim_batch("w1", 10, lease_seconds=300, now=NOW)
    with pytest.raises(StaleLeaseError):
        await service.mark_failure(item.id, "smtp_450", worker_id="w2", now=NOW)
    with pytest.raises(StaleLeaseError):
        await service.mark_failure(
            item.id, "smtp_450", worker_id="w1", now=NOW + timedelta(seconds=301)
        )
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "sending"
    assert row.last_error_code is None


@pytest.mark.asyncio
async def test_stale_worker_cannot_overwrite_recovered_row(session):
    from app.services.notifications import StaleLeaseError

    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-race")
    await service.claim_batch("w1", 10, lease_seconds=300, now=NOW)
    # w2 recovers after w1's lease expires.
    recovered = await service.claim_batch("w2", 10, now=NOW + timedelta(seconds=400))
    assert recovered[0].lease_owner == "w2"
    # The original worker wakes up late and must be rejected.
    with pytest.raises(StaleLeaseError):
        await service.mark_sent(
            item.id, "provider-late", worker_id="w1", now=NOW + timedelta(seconds=410)
        )
    row = await session.get(NotificationOutbox, item.id)
    assert row.lease_owner == "w2"
    assert row.status == "sending"


# ---------------------------------------------------------------------------
# Transitions clear lease / retry scheduling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_sent_clears_lease_and_sets_sent_at(session):
    service = NotificationOutboxService(session)
    item = await _enqueue(service, "k-sent-clean")
    await service.claim_batch("w1", 10, now=NOW)
    await service.mark_sent(item.id, "provider-1", worker_id="w1", now=NOW)
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "sent"
    assert row.provider_message_id == "provider-1"
    assert row.sent_at is not None
    assert row.lease_owner is None
    assert row.lease_expires_at is None
    assert row.next_attempt_at is None


@pytest.mark.asyncio
async def test_retry_failure_clears_lease_and_schedules_backoff(session):
    service = NotificationOutboxService(session, max_attempts=5)
    item = await _enqueue(service, "k-retry")
    await service.claim_batch("w1", 10, now=NOW)
    await service.mark_failure(item.id, "smtp_450", worker_id="w1", retryable=True, now=NOW)
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "pending"
    assert row.lease_owner is None
    assert row.lease_expires_at is None
    assert row.last_error_code == "smtp_450"
    assert row.next_attempt_at is not None
    assert row.next_attempt_at > NOW
    # Not claimable before the scheduled retry time.
    assert await service.claim_batch("w1", 10, now=NOW + timedelta(seconds=1)) == []
    # Claimable once due.
    assert len(await service.claim_batch("w1", 10, now=NOW + timedelta(hours=2))) == 1


@pytest.mark.asyncio
async def test_final_failure_goes_dead_and_clears_lease(session):
    service = NotificationOutboxService(session, max_attempts=2)
    item = await _enqueue(service, "k-dead-path")
    await service.claim_batch("w1", 10, now=NOW)
    await service.mark_failure(item.id, "smtp_450", worker_id="w1", retryable=True, now=NOW)
    t1 = NOW + timedelta(hours=2)
    await service.claim_batch("w1", 10, now=t1)
    await service.mark_failure(item.id, "smtp_550", worker_id="w1", retryable=True, now=t1)
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "dead"
    assert row.failed_at is not None
    assert row.lease_owner is None
    assert row.lease_expires_at is None
    assert row.next_attempt_at is None
    # Dead rows stay dead.
    assert await service.claim_batch("w1", 10, now=t1 + timedelta(days=30)) == []


@pytest.mark.asyncio
async def test_non_retryable_failure_goes_dead_immediately(session):
    service = NotificationOutboxService(session, max_attempts=5)
    item = await _enqueue(service, "k-hard-fail")
    await service.claim_batch("w1", 10, now=NOW)
    await service.mark_failure(item.id, "smtp_550", worker_id="w1", retryable=False, now=NOW)
    row = await session.get(NotificationOutbox, item.id)
    assert row.status == "dead"
    assert row.failed_at is not None
    assert row.lease_owner is None


# ---------------------------------------------------------------------------
# DB invariants (CHECK constraints)
# ---------------------------------------------------------------------------

INVALID_ROWS = [
    ("bad-status", {"status": "weird"}),
    ("negative-attempts", {"attempts": -1}),
    ("pending-with-lease", {"lease_owner": "w1", "lease_expires_at": NOW}),
    ("sending-without-lease", {"status": "sending", "attempts": 1}),
    ("sent-without-sent-at", {"status": "sent"}),
    (
        "sent-with-lease",
        {
            "status": "sent",
            "sent_at": NOW,
            "lease_owner": "w1",
            "lease_expires_at": NOW,
        },
    ),
    ("dead-without-failed-at", {"status": "dead", "attempts": 5}),
    (
        "sent-with-next-attempt",
        {"status": "sent", "sent_at": NOW, "next_attempt_at": NOW},
    ),
    (
        "dead-with-next-attempt",
        {
            "status": "dead",
            "failed_at": NOW,
            "attempts": 5,
            "next_attempt_at": NOW,
        },
    ),
    ("non-sent-with-sent-at", {"status": "pending", "sent_at": NOW}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("label,overrides", INVALID_ROWS, ids=[c[0] for c in INVALID_ROWS])
async def test_invalid_rows_are_rejected_by_constraints(session, label, overrides):
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.execute(
                insert(NotificationOutbox).values(_row_values(f"k-{label}", **overrides))
            )


@pytest.mark.asyncio
async def test_valid_lifecycle_rows_pass_constraints(session):
    valid = [
        _row_values("v-pending"),
        _row_values(
            "v-sending",
            status="sending",
            attempts=1,
            lease_owner="w1",
            lease_expires_at=NOW,
        ),
        _row_values("v-sent", status="sent", attempts=1, sent_at=NOW),
        _row_values("v-dead", status="dead", attempts=5, failed_at=NOW),
    ]
    for values in valid:
        await session.execute(insert(NotificationOutbox).values(values))
    assert len((await session.scalars(select(NotificationOutbox))).all()) == 4


def test_model_ddl_declares_invariants():
    ddl = str(
        CreateTable(NotificationOutbox.__table__).compile(dialect=postgresql.dialect())
    )
    for name in (
        "ck_notification_outbox_channel_valid",
        "ck_notification_outbox_event_version_positive",
        "ck_notification_outbox_status_valid",
        "ck_notification_outbox_attempts_nonneg",
        "ck_notification_outbox_lease_coherent",
        "ck_notification_outbox_sent_at_coherent",
        "ck_notification_outbox_dead_failed_at",
        "ck_notification_outbox_terminal_no_retry",
    ):
        assert name in ddl
    assert "'pending'" in ddl and "'sending'" in ddl and "'sent'" in ddl and "'dead'" in ddl


# ---------------------------------------------------------------------------
# PostgreSQL concurrency semantics (compiled SQL)
# ---------------------------------------------------------------------------

def test_claim_sql_uses_postgres_row_locking():
    from app.services.notifications import build_claim_statement

    stmt = build_claim_statement("w1", limit=5, lease_seconds=300, now=NOW)
    sql = str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "next_attempt_at" in sql
    assert "lease_expires_at" in sql
    assert "'pending'" in sql
    assert "'sending'" in sql
    assert "'sent'" not in sql  # terminal states never appear as claimable
    assert "RETURNING" in sql


# ---------------------------------------------------------------------------
# Backoff and service configuration
# ---------------------------------------------------------------------------

def test_backoff_is_bounded_and_deterministic():
    assert retry_delay_seconds(3, jitter_seed="x") == retry_delay_seconds(3, jitter_seed="x")
    assert 0 <= retry_delay_seconds(99, jitter_seed="x") <= 3600


def test_backoff_envelope_per_attempt():
    for attempt in range(11):
        delay = retry_delay_seconds(attempt, jitter_seed="seed")
        assert min(3600, 2**attempt) <= delay <= min(3600, 2**attempt + 30)


def test_backoff_rejects_negative_attempt():
    with pytest.raises(ValueError):
        retry_delay_seconds(-1)


@pytest.mark.asyncio
async def test_service_rejects_non_positive_max_attempts(session):
    with pytest.raises(ValueError):
        NotificationOutboxService(session, max_attempts=0)
    with pytest.raises(ValueError):
        NotificationOutboxService(session, max_attempts=-1)


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

def test_notification_outbox_is_exported():
    assert "NotificationOutbox" in app.models.__all__
    assert app.models.NotificationOutbox is NotificationOutbox
