"""Offline catalogue of 100 metadata-only DDL operations and the renderer.

The catalogue is statically derived from the v2 evidence (brief §3.1 + §3.2).
No entry is generated from runtime input. Every SQL fragment comes from this
file.  This module is import-only: it never opens a connection, never executes
DDL, never writes to the database.  All sequencing of metadata-only ops onto a
real connection lives in :mod:`scripts.adopt_wp3_schema`.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class OpKind(StrEnum):
    SET_DEFAULT = "set_default"
    DROP_NOT_NULL = "drop_not_null"


@dataclass(frozen=True)
class MetadataOp:
    """One statically approved metadata-only DDL operation.

    ``key`` matches the raw diff key prefix; ``schema``, ``table`` and
    ``column`` are taken verbatim from a closed allowlist and are never
    derived from runtime input.  ``expression`` is the literal text used in
    the DDL after the ``SET DEFAULT`` keyword (no quoting added at this
    layer; the renderer wraps the identifier parts and inlines the literal).
    """

    key: str
    schema: str
    table: str
    column: str
    kind: OpKind
    expression: str | None  # only for SET_DEFAULT


# ---------------------------------------------------------------------------
# 67 SET DEFAULT entries (alphabetic by schema.table; brief §3.1).
# Every literal here is fixed ASCII; nothing is derived from input.
# ---------------------------------------------------------------------------
_SET_DEFAULT: tuple[MetadataOp, ...] = (
    MetadataOp("app.alert_deliveries.created_at.default", "app", "alert_deliveries", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.alert_deliveries.id.default", "app", "alert_deliveries", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.alerts.created_at.default", "app", "alerts", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.alerts.id.default", "app", "alerts", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.client_portfolios.created_at.default", "app", "client_portfolios", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.client_portfolios.id.default", "app", "client_portfolios", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.deadlines.created_at.default", "app", "deadlines", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.deadlines.id.default", "app", "deadlines", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.deadlines.updated_at.default", "app", "deadlines", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.prospection_opportunities.created_at.default", "app", "prospection_opportunities", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.prospection_opportunities.id.default", "app", "prospection_opportunities", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.prospection_opportunities.updated_at.default", "app", "prospection_opportunities", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.review_queue.created_at.default", "app", "review_queue", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.review_queue.id.default", "app", "review_queue", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.review_queue.status.default", "app", "review_queue", "status", OpKind.SET_DEFAULT, "'pending'"),
    MetadataOp("app.subscriptions.created_at.default", "app", "subscriptions", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.subscriptions.id.default", "app", "subscriptions", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.subscriptions.updated_at.default", "app", "subscriptions", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.team_members.created_at.default", "app", "team_members", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.team_members.id.default", "app", "team_members", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.teams.created_at.default", "app", "teams", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.teams.id.default", "app", "teams", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.users.created_at.default", "app", "users", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.users.id.default", "app", "users", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.users.updated_at.default", "app", "users", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.watchlist_items.created_at.default", "app", "watchlist_items", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.watchlist_items.id.default", "app", "watchlist_items", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.watchlists.created_at.default", "app", "watchlists", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("app.watchlists.id.default", "app", "watchlists", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("app.watchlists.updated_at.default", "app", "watchlists", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.documents.created_at.default", "core", "documents", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.documents.id.default", "core", "documents", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.documents.language.default", "core", "documents", "language", OpKind.SET_DEFAULT, "'pt'"),
    MetadataOp("core.goods_services.created_at.default", "core", "goods_services", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.goods_services.id.default", "core", "goods_services", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.goods_services.language.default", "core", "goods_services", "language", OpKind.SET_DEFAULT, "'pt'"),
    MetadataOp("core.holders.created_at.default", "core", "holders", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.holders.id.default", "core", "holders", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.holders.updated_at.default", "core", "holders", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.nice_classes.created_at.default", "core", "nice_classes", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.nice_classes.id.default", "core", "nice_classes", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.representatives.created_at.default", "core", "representatives", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.representatives.id.default", "core", "representatives", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.representatives.updated_at.default", "core", "representatives", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.source_runs.created_at.default", "core", "source_runs", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.source_runs.id.default", "core", "source_runs", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.source_runs.items_failed.default", "core", "source_runs", "items_failed", OpKind.SET_DEFAULT, "0"),
    MetadataOp("core.source_runs.items_new.default", "core", "source_runs", "items_new", OpKind.SET_DEFAULT, "0"),
    MetadataOp("core.source_runs.items_processed.default", "core", "source_runs", "items_processed", OpKind.SET_DEFAULT, "0"),
    MetadataOp("core.source_runs.items_updated.default", "core", "source_runs", "items_updated", OpKind.SET_DEFAULT, "0"),
    MetadataOp("core.sources.created_at.default", "core", "sources", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.sources.id.default", "core", "sources", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.sources.is_enabled.default", "core", "sources", "is_enabled", OpKind.SET_DEFAULT, "true"),
    MetadataOp("core.sources.priority.default", "core", "sources", "priority", OpKind.SET_DEFAULT, "1"),
    MetadataOp("core.trademark_holders.created_at.default", "core", "trademark_holders", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.trademark_holders.role.default", "core", "trademark_holders", "role", OpKind.SET_DEFAULT, "'applicant'"),
    MetadataOp("core.trademark_representatives.created_at.default", "core", "trademark_representatives", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.trademark_representatives.role.default", "core", "trademark_representatives", "role", OpKind.SET_DEFAULT, "'representative'"),
    MetadataOp("core.trademark_versions.created_at.default", "core", "trademark_versions", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.trademark_versions.id.default", "core", "trademark_versions", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.trademarks.created_at.default", "core", "trademarks", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("core.trademarks.id.default", "core", "trademarks", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("core.trademarks.updated_at.default", "core", "trademarks", "updated_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("events.lifecycle_events.created_at.default", "events", "lifecycle_events", "created_at", OpKind.SET_DEFAULT, "NOW()"),
    MetadataOp("events.lifecycle_events.id.default", "events", "lifecycle_events", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
    MetadataOp("raw.api_responses.created_at.default", "raw", "api_responses", "created_at", OpKind.SET_DEFAULT, "now()"),
    MetadataOp("raw.api_responses.id.default", "raw", "api_responses", "id", OpKind.SET_DEFAULT, "gen_random_uuid()"),
)


# ---------------------------------------------------------------------------
# 33 DROP NOT NULL entries (alphabetic by schema.table; brief §3.2).
# ---------------------------------------------------------------------------
_DROP_NOT_NULL: tuple[MetadataOp, ...] = (
    MetadataOp("app.alert_deliveries.created_at.nullable", "app", "alert_deliveries", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.alerts.created_at.nullable", "app", "alerts", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.alerts.is_dismissed.nullable", "app", "alerts", "is_dismissed", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.alerts.is_read.nullable", "app", "alerts", "is_read", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.client_portfolios.created_at.nullable", "app", "client_portfolios", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.deadlines.created_at.nullable", "app", "deadlines", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.deadlines.updated_at.nullable", "app", "deadlines", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.prospection_opportunities.created_at.nullable", "app", "prospection_opportunities", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.prospection_opportunities.is_exported.nullable", "app", "prospection_opportunities", "is_exported", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.prospection_opportunities.updated_at.nullable", "app", "prospection_opportunities", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.subscriptions.created_at.nullable", "app", "subscriptions", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.subscriptions.features.nullable", "app", "subscriptions", "features", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.subscriptions.max_clients.nullable", "app", "subscriptions", "max_clients", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.subscriptions.updated_at.nullable", "app", "subscriptions", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.team_members.created_at.nullable", "app", "team_members", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.teams.created_at.nullable", "app", "teams", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.users.created_at.nullable", "app", "users", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.users.is_active.nullable", "app", "users", "is_active", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.users.is_superuser.nullable", "app", "users", "is_superuser", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.users.updated_at.nullable", "app", "users", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlist_items.created_at.nullable", "app", "watchlist_items", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlists.class_weight.nullable", "app", "watchlists", "class_weight", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlists.created_at.nullable", "app", "watchlists", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlists.is_active.nullable", "app", "watchlists", "is_active", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlists.phonetic_weight.nullable", "app", "watchlists", "phonetic_weight", OpKind.DROP_NOT_NULL, None),
    MetadataOp("app.watchlists.updated_at.nullable", "app", "watchlists", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.source_runs.items_failed.nullable", "core", "source_runs", "items_failed", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.source_runs.items_new.nullable", "core", "source_runs", "items_new", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.source_runs.items_processed.nullable", "core", "source_runs", "items_processed", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.source_runs.items_updated.nullable", "core", "source_runs", "items_updated", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.trademarks.created_at.nullable", "core", "trademarks", "created_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("core.trademarks.updated_at.nullable", "core", "trademarks", "updated_at", OpKind.DROP_NOT_NULL, None),
    MetadataOp("events.lifecycle_events.created_at.nullable", "events", "lifecycle_events", "created_at", OpKind.DROP_NOT_NULL, None),
)


# Static catalogue: 67 SET DEFAULT + 33 DROP NOT NULL = 100 ops.
ALL_OPS: tuple[MetadataOp, ...] = _SET_DEFAULT + _DROP_NOT_NULL

# Allowlist (closed set) of identifiers the renderer accepts. Every value
# in the catalogue must appear here. The renderer refuses anything else.
_CATALOGUE_IDENTIFIERS: frozenset[tuple[str, str, str]] = frozenset(
    (op.schema, op.table, op.column) for op in ALL_OPS
)


class ContractDeltaUnmapped(LookupError):
    """The inventory contains a column key that the catalogue does not own."""


# ---------------------------------------------------------------------------
# Renderer (safe composition against the closed allowlist).
# ---------------------------------------------------------------------------
def render_sql(op: MetadataOp) -> str:
    """Return the exact DDL text to emit for ``op``.

    Identifiers are wrapped in double quotes (PostgreSQL DDL is the only
    consumer; binds are impossible).  The literal default expression is
    taken verbatim from the catalogue — no quoting is added because every
    expression is a fixed ASCII fragment from the static allowlist.
    """
    if (op.schema, op.table, op.column) not in _CATALOGUE_IDENTIFIERS:
        raise ContractDeltaUnmapped(f"unapproved identifier: {op.key}")
    if op.kind is OpKind.SET_DEFAULT:
        if op.expression is None:
            raise ValueError(f"SET_DEFAULT requires expression: {op.key}")
        return (
            f'ALTER TABLE "{op.schema}"."{op.table}" '
            f'ALTER COLUMN "{op.column}" SET DEFAULT {op.expression};'
        )
    if op.expression is not None:
        raise ValueError(f"DROP_NOT_NULL must not carry expression: {op.key}")
    return (
        f'ALTER TABLE "{op.schema}"."{op.table}" '
        f'ALTER COLUMN "{op.column}" DROP NOT NULL;'
    )


def reverse_sql(op: MetadataOp) -> str:
    """Return the textual inverse of ``op`` for audit logs only.

    ``SET DEFAULT`` is reversed by ``DROP DEFAULT`` (trivially idempotent).
    ``DROP NOT NULL`` would be reversed by ``SET NOT NULL`` but that
    operation is forbidden by design (brief §1): a DROP NOT NULL must
    never be re-tightened on rollback.  The audit log receives a
    sentinel marker instead.  This function is never executed; only
    surfaced for transparency in the audit shape.
    """
    if op.kind is OpKind.SET_DEFAULT:
        return (
            f'ALTER TABLE "{op.schema}"."{op.table}" '
            f'ALTER COLUMN "{op.column}" DROP DEFAULT;'
        )
    return f"-- ROLLBACK-FORBIDDEN: {op.key} (drop_not_null is non-reversible by design)"


# ---------------------------------------------------------------------------
# Planner (fail-closed, idempotent).
# ---------------------------------------------------------------------------
def _lookup_column(structure: Mapping[str, Any], schema: str, table: str, column: str) -> Mapping[str, Any] | None:
    for entry in structure.get("tables", ()):
        if entry.get("schema") == schema and entry.get("name") == table:
            for col in entry.get("columns", ()) or ():
                if col.get("name") == column:
                    return col
            return None
    return None


def _comparable(value: Any) -> Any:
    """Canonicalise a single default for equality only (mirrors contract)."""
    if isinstance(value, str) and value.strip().lower() == "now()":
        return "now()"
    return value


def build_metadata_plan(
    structure: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> tuple[MetadataOp, ...]:
    """Map the static catalogue to the minimal DDL set still needed.

    ``structure`` is the inventory collected inside the same transaction
    (shape of ``LiveInventory.structure``).  ``contract`` is accepted for
    signature symmetry but not used — the catalogue is the only source of
    truth for which columns to address.  The function never mutates state
    and never inspects input strings for quoting; every name comes from the
    closed allowlist.
    """
    catalogue_columns = {(s, t, c) for s, t, c in _CATALOGUE_IDENTIFIERS}

    plan: list[MetadataOp] = []
    for op in ALL_OPS:
        if (op.schema, op.table, op.column) not in catalogue_columns:
            # Defensive: every op in ALL_OPS is in the allowlist by
            # construction. Reject anything that drifts in.
            raise ContractDeltaUnmapped(f"unapproved identifier: {op.key}")
        col = _lookup_column(structure, op.schema, op.table, op.column)
        if col is None:
            # Column absent in inventory: covered by the additive plan or
            # by legacy schema. Skip silently. Never invent an op.
            continue
        if op.kind is OpKind.SET_DEFAULT:
            if _comparable(col.get("default")) != _comparable(op.expression):
                plan.append(op)
        else:  # DROP_NOT_NULL
            if col.get("nullable") is False:
                plan.append(op)
    return tuple(plan)


# ---------------------------------------------------------------------------
# Dry-run (audit-shape, no SQL executed).
# ---------------------------------------------------------------------------
def dry_run(structure: Mapping[str, Any], contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return what would be executed, without executing anything.

    Shape::

        {
          "ops":    [{"key": ..., "schema": ..., "table": ...,
                      "column": ..., "kind": ..., "sql": ...,
                      "reverse_sql": ...}, ...],
          "skip":   [{"key": ..., "reason": "already_applied"}, ...],
          "blocked":[{"key": ..., "reason": "..."}, ...]
        }

    On ``ContractDeltaUnmapped`` the audit shape is preserved with a single
    ``blocked`` entry: nothing is executed and the reason is recorded.
    """
    try:
        planned = list(build_metadata_plan(structure, contract))
    except ContractDeltaUnmapped as exc:
        return {
            "ops": [],
            "skip": [],
            "blocked": [{"key": "<plan>", "reason": str(exc)}],
        }
    planned_keys = {op.key for op in planned}
    ops = [
        {
            "key": op.key,
            "schema": op.schema,
            "table": op.table,
            "column": op.column,
            "kind": op.kind.value,
            "sql": render_sql(op),
            "reverse_sql": reverse_sql(op),
        }
        for op in planned
    ]
    skip = [
        {"key": op.key, "reason": "already_applied"}
        for op in ALL_OPS if op.key not in planned_keys
    ]
    return {"ops": ops, "skip": skip, "blocked": []}


def normalize_metadata_in_memory(
    structure: Mapping[str, Any],
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deep copy of ``structure`` with the static metadata plan applied.

    Pure and side-effect free: it mirrors the column-level effect of the
    SET DEFAULT / DROP NOT NULL bridge DDL (:func:`build_metadata_plan`) so a
    caller can compute the additive reconciliation plan and classify the
    post-bridge shape without a second database round-trip.  Absent columns are
    skipped exactly as :func:`build_metadata_plan` skips them; no identifier or
    value is derived from runtime input beyond the closed catalogue.  The real
    adoption still verifies the *actual* post-DDL inventory before stamping, so
    this simulation only ever narrows what is planned — it never authorises a
    write on its own.
    """
    normalized = deepcopy(dict(structure))
    tables = {
        (table.get("schema"), table.get("name")): table
        for table in normalized.get("tables", ())
    }
    for op in build_metadata_plan(structure, contract):
        table = tables.get((op.schema, op.table))
        if table is None:
            continue
        for column in table.get("columns", ()) or ():
            if column.get("name") == op.column:
                if op.kind is OpKind.SET_DEFAULT:
                    column["default"] = op.expression
                else:
                    column["nullable"] = True
                break
    return normalized


__all__ = [
    "OpKind",
    "MetadataOp",
    "ALL_OPS",
    "ContractDeltaUnmapped",
    "render_sql",
    "reverse_sql",
    "build_metadata_plan",
    "dry_run",
    "normalize_metadata_in_memory",
]
