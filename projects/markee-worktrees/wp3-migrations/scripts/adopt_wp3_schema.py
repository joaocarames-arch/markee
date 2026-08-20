"""Transactional, fail-closed WP3 schema adoption through Alembic revision 002."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
from typing import Any, Mapping

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from scripts.drift_inventory import inventory_connection, index_signature
from scripts.target_guard import TargetSpec, assert_wp3_adoption_target
from scripts.wp3_adoption_contract import (
    DEFAULT_CONTRACT_PATH,
    AdoptionContract,
    AdoptionVerdict,
    ContractError,
    classify_structure,
    load_contract,
)
from scripts.wp3_reconcile_metadata import (
    build_metadata_plan,
    normalize_metadata_in_memory,
    render_sql,
)


WORKTREE = Path(__file__).resolve().parents[1]


class AdoptionStatus(StrEnum):
    """Successful terminal states of the future adoption workflow."""

    ADOPTED = "adopted"
    ALREADY_ADOPTED = "already_adopted"


class AdoptionReason(StrEnum):
    """Stable reason codes for adoption outcomes and failures."""

    ADOPTED_TO_002 = "adopted_to_002"
    ALREADY_002_NOOP = "already_002_noop"
    ALEMBIC_HEAD_MISMATCH = "alembic_head_mismatch"
    EMPTY_DATABASE = "empty_database"
    VERSION_001_REJECTED = "version_001_rejected"
    VERSION_UNKNOWN = "version_unknown"
    VERSION_MULTIPLE = "version_multiple"
    UNSTAMPED_STRUCTURE_REJECTED = "unstamped_structure_rejected"
    ALREADY_002_DRIFT = "already_002_drift"
    CONTRACT_DELTA_UNMAPPED = "contract_delta_unmapped"
    POST_RECONCILIATION_DRIFT = "post_reconciliation_drift"
    POST_STAMP_VERSION_MISMATCH = "post_stamp_version_mismatch"
    CONTRACT_INVALID = "contract_invalid"
    RECONCILIATION_FAILED = "reconciliation_failed"
    RELATION_LOCK_FAILED = "relation_lock_failed"
    LOCKED_REVALIDATION_DRIFT = "locked_revalidation_drift"
    TARGET_IDENTITY_UNVERIFIED = "target_identity_unverified"


class AdoptionError(RuntimeError):
    """Fail-closed adoption failure with a stable machine-readable reason."""

    def __init__(self, reason: AdoptionReason, message: str) -> None:
        self.reason = reason
        super().__init__(message)


@dataclass(frozen=True)
class ReconciliationOperation:
    """One statically approved additive DDL operation."""

    key: str
    sql: str


@dataclass(frozen=True)
class AdoptionResult:
    """Audit-safe result shape reserved for the transaction cycle."""

    status: AdoptionStatus
    reason: AdoptionReason
    revision: str
    operations: tuple[str, ...]
    structural_fingerprint_before: str
    structural_fingerprint_after: str
    contract_id: str
    contract_version: int
    contract_payload_sha256: str


_API_KEYS = ReconciliationOperation(
    "table:app.api_keys",
    """CREATE TABLE app.api_keys (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    scopes VARCHAR(100)[],
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT api_keys_pkey PRIMARY KEY (id),
    CONSTRAINT api_keys_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES app.users (id)
        ON DELETE CASCADE,
    CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash)
)""",
)

_PARTITION_2026_07 = ReconciliationOperation(
    "partition:raw.api_responses_2026_07",
    """CREATE TABLE raw.api_responses_2026_07
PARTITION OF raw.api_responses
FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')""",
)

_PARTITION_2026_08 = ReconciliationOperation(
    "partition:raw.api_responses_2026_08",
    """CREATE TABLE raw.api_responses_2026_08
PARTITION OF raw.api_responses
FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')""",
)

_INDEX_OPERATIONS = (
    (
        "app.alerts",
        {"keys": [{"expr": "user_id", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "is_dismissed", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "created_at", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:app.alerts:user_id,is_dismissed,created_at", """CREATE INDEX idx_alerts_user_unread
ON app.alerts (user_id, is_dismissed, created_at)"""),
    ),
    (
        "app.alerts",
        {"keys": [{"expr": "watchlist_id", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "similarity_score", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:app.alerts:watchlist_id,similarity_score", """CREATE INDEX idx_alerts_composite_score
ON app.alerts (watchlist_id, similarity_score)"""),
    ),
    (
        "app.deadlines",
        {"keys": [{"expr": "due_date", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "status", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:app.deadlines:due_date,status", """CREATE INDEX idx_deadlines_due_date
ON app.deadlines (due_date, status)"""),
    ),
    (
        "app.prospection_opportunities",
        {"keys": [{"expr": "opportunity_type", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "score", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:app.prospection_opportunities:opportunity_type,score", """CREATE INDEX idx_prospection_score
ON app.prospection_opportunities (opportunity_type, score)"""),
    ),
    (
        "app.review_queue",
        {"keys": [{"expr": "status", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "created_at", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:app.review_queue:status,created_at", """CREATE INDEX idx_review_queue_status
ON app.review_queue (status, created_at)"""),
    ),
    (
        "core.holders",
        {"method": "gin", "keys": [{"expr": "name", "opclass": "gin_trgm_ops", "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:core.holders:name:gin_trgm_ops", """CREATE INDEX idx_holders_name_trgm
ON core.holders USING GIN (name gin_trgm_ops)"""),
    ),
    (
        "core.representatives",
        {"method": "gin", "keys": [{"expr": "name", "opclass": "gin_trgm_ops", "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:core.representatives:name:gin_trgm_ops", """CREATE INDEX idx_reps_name_trgm
ON core.representatives USING GIN (name gin_trgm_ops)"""),
    ),
    (
        "core.trademarks",
        {"method": "gin", "keys": [{"expr": "word_mark", "opclass": "gin_trgm_ops", "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:core.trademarks:word_mark:gin_trgm_ops", """CREATE INDEX idx_trademarks_wordmark
ON core.trademarks USING GIN (word_mark gin_trgm_ops)"""),
    ),
    (
        "events.lifecycle_events",
        {"keys": [{"expr": "trademark_id", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "event_date", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:events.lifecycle_events:trademark_id,event_date", """CREATE INDEX idx_lifecycle_events_trademark
ON events.lifecycle_events (trademark_id, event_date)"""),
    ),
    (
        "events.lifecycle_events",
        {"keys": [{"expr": "trademark_id", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "event_type", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}]},
        ReconciliationOperation("index:events.lifecycle_events:trademark_id,event_type", """CREATE INDEX idx_events_trademark_type
ON events.lifecycle_events (trademark_id, event_type)"""),
    ),
    (
        "raw.api_responses",
        {"keys": [{"expr": "source_id", "opclass": None, "collation": None, "sort": "asc", "nulls": "last"}, {"expr": "created_at", "opclass": None, "collation": None, "sort": "desc", "nulls": "first"}]},
        ReconciliationOperation("index:raw.api_responses:source_id,created_at_desc", """CREATE INDEX idx_raw_source_created
ON raw.api_responses (source_id, created_at DESC)"""),
    ),
)

_STATIC_INDEX_SIGNATURES = tuple(
    (table, index_signature(index), operation)
    for table, index, operation in _INDEX_OPERATIONS
)
_STATIC_MISSING_INDEXES: dict[str, frozenset[str]] = {}
for _table, _signature, _operation in _STATIC_INDEX_SIGNATURES:
    _STATIC_MISSING_INDEXES[_table] = _STATIC_MISSING_INDEXES.get(_table, frozenset()) | {_signature}


def _unmapped(message: str) -> AdoptionError:
    return AdoptionError(AdoptionReason.CONTRACT_DELTA_UNMAPPED, message)


def _validate_contract_catalogue(contract: AdoptionContract) -> None:
    if contract.allowed_missing_tables != frozenset({"app.api_keys"}):
        raise _unmapped("contract missing-table set has no exact static mapping")
    if dict(contract.allowed_missing_indexes) != _STATIC_MISSING_INDEXES:
        raise _unmapped("contract missing-index set has no exact static mapping")
    if set(contract.allowed_missing_partitions) != {
        "raw.api_responses_2026_07",
        "raw.api_responses_2026_08",
    }:
        raise _unmapped("contract missing-partition set has no exact static mapping")


def _observed_index_signatures(table: Mapping[str, Any]) -> set[str]:
    return {
        index if isinstance(index, str) else index_signature(index)
        for index in table.get("indexes", ())
    }


def build_reconciliation_plan(
    structure: Mapping[str, Any],
    contract: AdoptionContract,
) -> tuple[ReconciliationOperation, ...]:
    """Map only contract-approved missing objects to ordered static DDL.

    The real classifier closes the input shape first. Any structural drift or
    contract delta outside the exact static catalogue fails with one stable
    reason; no identifier or SQL fragment is generated from input data.
    """
    _validate_contract_catalogue(contract)
    classification = classify_structure(structure, contract)
    if not classification.accepted or classification.differences:
        raise _unmapped("structure contains a delta outside the static catalogue")

    tables = {
        f"{table.get('schema')}.{table.get('name')}": table
        for table in structure.get("tables", ())
    }
    plan: list[ReconciliationOperation] = []
    if "app.api_keys" not in tables:
        plan.append(_API_KEYS)
    if "raw.api_responses_2026_07" not in tables:
        plan.append(_PARTITION_2026_07)
    if "raw.api_responses_2026_08" not in tables:
        plan.append(_PARTITION_2026_08)
    for table_name, signature, operation in _STATIC_INDEX_SIGNATURES:
        if signature not in _observed_index_signatures(tables[table_name]):
            plan.append(operation)
    return tuple(plan)


def _sync_dsn(database_url: str) -> str:
    prefix = "postgresql+asyncpg://"
    return "postgresql://" + database_url[len(prefix):] if database_url.startswith(prefix) else database_url


def _script_directory(source_root: Path) -> ScriptDirectory:
    config = Config(str(source_root / "alembic.ini"))
    config.set_main_option("script_location", str(source_root / "alembic"))
    return ScriptDirectory.from_config(config)


def _version_rows(connection) -> tuple[str, ...]:
    exists = connection.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='alembic_version'"
    )).scalar()
    if not exists:
        return ()
    rows = connection.execute(text(
        "SELECT version_num FROM public.alembic_version ORDER BY version_num"
    )).all()
    return tuple(str(row[0]) for row in rows)


_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def _approved_existing_relations(
    structure: Mapping[str, Any],
    contract: AdoptionContract,
    *,
    version_table_exists: bool,
) -> tuple[str, ...]:
    """Return existing relations from the exact, statically approved catalogue."""
    approved = {
        f"{table['schema']}.{table['name']}"
        for table in contract.canonical.get("tables", ())
    } | set(contract.legacy_public_tables)
    if version_table_exists:
        # The Alembic history relation is the one approved relation that
        # lives outside the structural contract catalogue.
        approved.add("public.alembic_version")
    observed: set[str] = set()
    for table in structure.get("tables", ()):
        schema = table.get("schema")
        name = table.get("name")
        if not isinstance(schema, str) or not isinstance(name, str):
            raise AdoptionError(
                AdoptionReason.LOCKED_REVALIDATION_DRIFT,
                "observed relation has an invalid identifier",
            )
        qualified = f"{schema}.{name}"
        if (
            qualified not in approved
            or not _SAFE_IDENTIFIER.fullmatch(schema)
            or not _SAFE_IDENTIFIER.fullmatch(name)
        ):
            raise AdoptionError(
                AdoptionReason.LOCKED_REVALIDATION_DRIFT,
                "observed relation is outside the static lock catalogue",
            )
        observed.add(qualified)
    if version_table_exists:
        observed.add("public.alembic_version")
    return tuple(sorted(observed))


def _lock_existing_relations(
    connection,
    structure: Mapping[str, Any],
    contract: AdoptionContract,
    *,
    version_table_exists: bool,
) -> None:
    """Acquire deterministic DDL-blocking locks without blocking ordinary DML."""
    relations = _approved_existing_relations(
        structure, contract, version_table_exists=version_table_exists
    )
    try:
        for qualified in relations:
            schema, name = qualified.split(".", 1)
            connection.execute(text(
                f'LOCK TABLE "{schema}"."{name}" IN ACCESS SHARE MODE'
            ))
    except AdoptionError:
        raise
    except Exception as exc:
        raise AdoptionError(
            AdoptionReason.RELATION_LOCK_FAILED,
            "failed to acquire the static relation lock set",
        ) from exc


def _version_table_exists(connection) -> bool:
    return bool(connection.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name='alembic_version'"
    )).scalar())


def _result(
    *,
    status: AdoptionStatus,
    reason: AdoptionReason,
    operations: tuple[str, ...],
    before: str,
    after: str,
    contract: AdoptionContract,
) -> AdoptionResult:
    return AdoptionResult(
        status=status,
        reason=reason,
        revision="002",
        operations=operations,
        structural_fingerprint_before=before,
        structural_fingerprint_after=after,
        contract_id=contract.contract_id,
        contract_version=contract.contract_version,
        contract_payload_sha256=contract.payload_sha256,
    )


def _require_final(structure: Mapping[str, Any], contract: AdoptionContract) -> None:
    classification = classify_structure(structure, contract)
    try:
        plan = build_reconciliation_plan(structure, contract)
    except AdoptionError as exc:
        raise AdoptionError(
            AdoptionReason.POST_RECONCILIATION_DRIFT,
            "reconciled structure is outside the approved contract",
        ) from exc
    if (
        not classification.accepted
        or classification.differences
        or plan
        or classification.verdict not in {
            AdoptionVerdict.ADOPTABLE_RESTORED,
            AdoptionVerdict.ALREADY_FINAL,
        }
    ):
        raise AdoptionError(
            AdoptionReason.POST_RECONCILIATION_DRIFT,
            "reconciled structure is not canonical "
            f"(verdict={classification.verdict}, differences={len(classification.differences)}, "
            f"remaining_operations={len(plan)})",
        )


def adopt_wp3_schema(
    database_url: str,
    *,
    guard: Callable[[str], TargetSpec] = assert_wp3_adoption_target,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    source_root: Path = WORKTREE,
) -> AdoptionResult:
    """Validate, reconcile and stamp an approved restored WP3 schema atomically."""
    spec = guard(database_url)
    if getattr(spec, "identity_verified", False) is not True:
        raise AdoptionError(
            AdoptionReason.TARGET_IDENTITY_UNVERIFIED,
            "mutable adoption requires an attested Docker identity",
        )
    try:
        contract = load_contract(contract_path, source_root=source_root)
        script = _script_directory(source_root)
    except ContractError as exc:
        raise AdoptionError(AdoptionReason.CONTRACT_INVALID, "adoption contract rejected") from exc
    except AdoptionError:
        raise
    except Exception as exc:
        raise AdoptionError(AdoptionReason.ALEMBIC_HEAD_MISMATCH, "Alembic scripts unavailable") from exc
    if tuple(script.get_heads()) != ("002",):
        raise AdoptionError(
            AdoptionReason.ALEMBIC_HEAD_MISMATCH,
            "Alembic must have exactly revision 002 as its head",
        )

    target = f"{spec.host}:{spec.port}/{spec.database} as {spec.user}"
    engine = create_engine(_sync_dsn(database_url), future=True)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "SELECT pg_advisory_xact_lock("
                "hashtextextended('markee:wp3:schema-adoption', 0))"
            ))
            before_inventory = inventory_connection(connection, target=target)
            versions = _version_rows(connection)
            if len(versions) > 1:
                raise AdoptionError(AdoptionReason.VERSION_MULTIPLE, "multiple Alembic versions rejected")

            classification = classify_structure(before_inventory.structure, contract)
            if versions == ("001",):
                raise AdoptionError(AdoptionReason.VERSION_001_REJECTED, "revision 001 cannot be adopted")
            if versions and versions != ("002",):
                raise AdoptionError(AdoptionReason.VERSION_UNKNOWN, "unknown Alembic revision rejected")

            if versions == ("002",):
                if (
                    classification.verdict not in {
                        AdoptionVerdict.ADOPTABLE_RESTORED,
                        AdoptionVerdict.ALREADY_FINAL,
                    }
                    or not classification.accepted
                    or classification.differences
                ):
                    raise AdoptionError(
                        AdoptionReason.ALREADY_002_DRIFT,
                        "revision 002 structure does not match its contract",
                    )
            else:
                if classification.verdict is AdoptionVerdict.EMPTY:
                    raise AdoptionError(
                        AdoptionReason.EMPTY_DATABASE,
                        "empty database must use alembic upgrade head",
                    )
                # The unstamped restored clone still carries the 100 approved
                # metadata deltas (SET DEFAULT / DROP NOT NULL), so it does not
                # yet classify as ADOPTABLE_RESTORED. Preview the exact static
                # metadata bridge in-memory (no SQL) and require the normalized
                # shape to be the approved restored profile. This fails closed
                # early — before any relation lock, DDL or stamp — for a
                # non-restored/canonical structure or any non-catalogue delta,
                # while admitting the genuine metadata-dirty restored clone.
                preview = classify_structure(
                    normalize_metadata_in_memory(before_inventory.structure), contract
                )
                if (
                    preview.verdict is not AdoptionVerdict.ADOPTABLE_RESTORED
                    or not preview.accepted
                    or preview.differences
                ):
                    raise AdoptionError(
                        AdoptionReason.UNSTAMPED_STRUCTURE_REJECTED,
                        "unstamped structure is not the approved restored profile",
                    )

            version_table_exists = _version_table_exists(connection)
            _lock_existing_relations(
                connection,
                before_inventory.structure,
                contract,
                version_table_exists=version_table_exists,
            )
            locked_inventory = inventory_connection(connection, target=target)
            locked_versions = _version_rows(connection)
            locked_version_table_exists = _version_table_exists(connection)
            locked_classification = classify_structure(locked_inventory.structure, contract)
            if (
                locked_inventory.structural_fingerprint
                != before_inventory.structural_fingerprint
                or locked_versions != versions
                or locked_version_table_exists != version_table_exists
                or locked_classification != classification
            ):
                raise AdoptionError(
                    AdoptionReason.LOCKED_REVALIDATION_DRIFT,
                    "inventory, version or classification changed while acquiring relation locks",
                )

            if versions == ("002",):
                # Already stamped: the structure must already be canonical. Any
                # residual reconciliation delta is drift, not adoption.
                try:
                    plan = build_reconciliation_plan(locked_inventory.structure, contract)
                except AdoptionError as exc:
                    raise AdoptionError(
                        AdoptionReason.ALREADY_002_DRIFT,
                        "locked structure failed exact contract validation",
                    ) from exc
                if plan:
                    raise AdoptionError(
                        AdoptionReason.ALREADY_002_DRIFT,
                        "revision 002 structure requires reconciliation",
                    )
                return _result(
                    status=AdoptionStatus.ALREADY_ADOPTED,
                    reason=AdoptionReason.ALREADY_002_NOOP,
                    operations=(),
                    before=before_inventory.structural_fingerprint,
                    after=locked_inventory.structural_fingerprint,
                    contract=contract,
                )

            # --- WP3 metadata bridge FIRST, additive reconciliation SECOND ---
            # The unstamped restored clone still carries the approved metadata
            # deltas, so the exact-14 additive plan must be planned against the
            # metadata-normalized shape. The static metadata plan
            # (build_metadata_plan) and its in-memory normalization
            # (normalize_metadata_in_memory) mirror the SET DEFAULT / DROP NOT
            # NULL bridge exactly — the additive objects are table/index
            # existence deltas untouched by column normalization — so the plan
            # is derived without a second inventory round-trip. Both plans run
            # inside this same engine.begin() transaction, metadata first; the
            # real post-DDL inventory below (after_ddl) is the authoritative
            # zero-diff gate before the stamp. Every op comes from the closed
            # catalogue (absent columns skipped): no heap rewrite, no data write.
            # Any failure aborts before the stamp and rolls the schema back.
            metadata_plan = build_metadata_plan(locked_inventory.structure)
            normalized_structure = normalize_metadata_in_memory(locked_inventory.structure)
            try:
                plan = build_reconciliation_plan(normalized_structure, contract)
            except AdoptionError as exc:
                raise AdoptionError(
                    AdoptionReason.UNSTAMPED_STRUCTURE_REJECTED,
                    "unstamped structure is not the approved restored profile",
                ) from exc

            try:
                for op in metadata_plan:
                    connection.execute(text(render_sql(op)))
            except Exception as exc:
                raise AdoptionError(
                    AdoptionReason.RECONCILIATION_FAILED,
                    "static metadata reconciliation operation failed",
                ) from exc
            try:
                for operation in plan:
                    connection.execute(text(operation.sql))
            except Exception as exc:
                raise AdoptionError(
                    AdoptionReason.RECONCILIATION_FAILED,
                    "static reconciliation operation failed",
                ) from exc

            after_ddl = inventory_connection(connection, target=target)
            _require_final(after_ddl.structure, contract)
            MigrationContext.configure(connection).stamp(script, "002")
            if _version_rows(connection) != ("002",):
                raise AdoptionError(
                    AdoptionReason.POST_STAMP_VERSION_MISMATCH,
                    "Alembic stamp did not produce exactly revision 002",
                )
            final_inventory = inventory_connection(connection, target=target)
            try:
                _require_final(final_inventory.structure, contract)
            except AdoptionError as exc:
                raise AdoptionError(
                    AdoptionReason.POST_RECONCILIATION_DRIFT,
                    "post-stamp structure no longer matches the contract",
                ) from exc
            return _result(
                status=AdoptionStatus.ADOPTED,
                reason=AdoptionReason.ADOPTED_TO_002,
                operations=tuple(operation.key for operation in plan),
                before=before_inventory.structural_fingerprint,
                after=final_inventory.structural_fingerprint,
                contract=contract,
            )
    finally:
        engine.dispose()


__all__ = [
    "AdoptionStatus",
    "AdoptionReason",
    "AdoptionError",
    "ReconciliationOperation",
    "AdoptionResult",
    "build_reconciliation_plan",
    "adopt_wp3_schema",
]
