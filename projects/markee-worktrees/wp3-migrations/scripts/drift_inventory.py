"""Normalised drift inventory for the WP3 migration dry-run.

The inventory answers three questions, all of which must be derived from
deterministic probes so the dry-run report can be reproduced from the
artifacts alone:

1. **Code migration graph** — which Alembic revisions exist, in which order,
   whether the graph has a single head, whether the chain is linear.
2. **Code/model parity** — for every model registered on ``Base.metadata``,
   what is the expected table name and schema, and does an Alembic
   operation create that exact object in the right schema?
3. **Live drift** — what tables, schemas, indexes and extensions exist on a
   target, and what is the binary ``alembic_version``.

The module is read-only with respect to any database: it only connects to
verify a target is the disposable one (via :mod:`scripts.target_guard`) and
then issues ``SELECT``/catalog queries.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Mapping

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.sqltypes import ARRAY, DateTime, Float


# --- Code-side inventory ----------------------------------------------------


@dataclass(frozen=True)
class RevisionInfo:
    """A single Alembic revision discovered on disk."""

    revision: str
    down_revision: str | None
    source_path: str

    def is_linear(self, other: "RevisionInfo") -> bool:
        """True when ``other`` immediately follows this revision in the chain."""
        return other.down_revision == self.revision


def list_revisions(versions_dir) -> list[RevisionInfo]:
    """Return every revision file in ``versions_dir`` sorted by filename.

    Alembic does not guarantee numeric ordering when revisions use non-numeric
    ids (``001``, ``002``, ``...``); we sort lexicographically as a stable,
    deterministic order.
    """
    versions_dir = str(versions_dir)
    revs: list[RevisionInfo] = []
    for path in sorted(_iter_python_files(versions_dir)):
        text_ = path.read_text(encoding="utf-8")
        rev_match = re.search(r'^revision:\s*str\s*=\s*"([^"]+)"', text_, re.M)
        down_match = re.search(
            r'^down_revision:\s*Union\[str,\s*None\]\s*=\s*("[^"]*"|None)',
            text_,
            re.M,
        )
        if not rev_match or not down_match:
            continue
        rev = rev_match.group(1)
        down_raw = down_match.group(1)
        down = None if down_raw == "None" else down_raw.strip('"')
        revs.append(RevisionInfo(revision=rev, down_revision=down, source_path=str(path)))
    return revs


def _iter_python_files(versions_dir: str):
    from pathlib import Path

    base = Path(versions_dir)
    for p in sorted(base.glob("*.py")):
        if p.name == "__init__.py":
            continue
        yield p


def revision_graph(revisions: list[RevisionInfo]) -> dict:
    """Return a deterministic, JSON-serialisable summary of the revision graph.

    A *head* is a revision that no other revision descends from. The *root*
    is a revision whose ``down_revision`` is None. With a linear chain
    ``001 -> 002``, 001 is the root and 002 is the head.

    The summary flags two failure conditions the dry-run report must surface:

    * ``multiple_heads`` — more than one revision has no incoming edge.
    * ``cycle`` — a chain revisits a revision.
    """
    by_rev: dict[str, RevisionInfo] = {r.revision: r for r in revisions}
    incoming: dict[str, list[str]] = {r.revision: [] for r in revisions}
    for r in revisions:
        if r.down_revision and r.down_revision in incoming:
            incoming[r.down_revision].append(r.revision)
    roots = [r.revision for r in revisions if r.down_revision is None]
    heads = sorted(r for r, incoming_edges in incoming.items() if not incoming_edges)
    multi_head = len(heads) > 1
    # Cycle detection: walk any chain and look for repeats.
    cycle = False
    for start in list(by_rev):
        seen: set[str] = set()
        cur: str | None = start
        while cur is not None:
            if cur in seen:
                cycle = True
                break
            seen.add(cur)
            cur = by_rev[cur].down_revision if cur in by_rev else None
        if cycle:
            break
    return {
        "revisions": [
            {
                "revision": r.revision,
                "down_revision": r.down_revision,
                "source_path": r.source_path,
            }
            for r in revisions
        ],
        "roots": roots,
        "heads": heads,
        "multiple_heads": multi_head,
        "cycle": cycle,
        "child_map": {r: incoming[r] for r in incoming},
    }


# --- Code/model parity ------------------------------------------------------


@dataclass(frozen=True)
class ModelInfo:
    """The ``__tablename__`` and schema for one ORM model."""

    name: str
    table: str
    schema: str | None
    has_partition: bool = False


def list_models(metadata) -> list[ModelInfo]:
    """Return a normalised :class:`ModelInfo` for every table in ``metadata``."""
    out: list[ModelInfo] = []
    for tbl in sorted(metadata.sorted_tables, key=lambda t: (t.schema or "", t.name)):
        schema = tbl.schema
        partition = bool(tbl.dialect_options.get("postgresql", {}).get("partition_by"))
        out.append(
            ModelInfo(
                name=f"{schema or 'public'}.{tbl.name}",
                table=tbl.name,
                schema=schema,
                has_partition=partition,
            )
        )
    return out


# --- Live target inventory -------------------------------------------------


@dataclass(frozen=True)
class LiveInventory:
    """Read-only snapshot of a target PostgreSQL database catalog."""

    target: str
    schemas: tuple[str, ...]
    tables: tuple[tuple[str, str], ...]  # (schema, table)
    indexes: tuple[tuple[str, str, str], ...]  # (schema, table, indexname)
    extensions: tuple[tuple[str, str], ...]  # (extname, version)
    alembic_version: str | None
    fingerprint: str
    structure: Mapping = field(default_factory=dict)
    structural_fingerprint: str = ""

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "schemas": list(self.schemas),
            "tables": [list(t) for t in self.tables],
            "indexes": [list(i) for i in self.indexes],
            "extensions": [list(e) for e in self.extensions],
            "alembic_version": self.alembic_version,
            "fingerprint": self.fingerprint,
            "structure": self.structure,
            "structural_fingerprint": self.structural_fingerprint,
        }


def _sync_dsn(async_dsn: str) -> str:
    """Convert an asyncpg SQLAlchemy URL to its psycopg2/psycopg equivalent.

    ``inspect`` needs a sync engine; we keep the async URL the source of
    truth elsewhere.
    """
    if async_dsn.startswith("postgresql+asyncpg://"):
        return "postgresql://" + async_dsn[len("postgresql+asyncpg://"):]
    return async_dsn


def _normalise_sql(value) -> str | None:
    """Collapse insignificant whitespace in catalog-rendered SQL fragments."""
    if value is None:
        return None
    return " ".join(str(value).split())


def _normalise_column_type(type_object) -> str:
    """Render a reflected type in the migration contract vocabulary.

    PostgreSQL reflects ``Float`` as ``DOUBLE PRECISION`` and renders an
    ``ARRAY`` itself as just ``ARRAY``.  The semantic element type is carried
    by ``item_type``, so arrays must be normalised recursively.
    """
    if isinstance(type_object, DateTime):
        return (
            "timestamp with time zone"
            if bool(type_object.timezone)
            else "timestamp without time zone"
        )
    if isinstance(type_object, ARRAY):
        return f"{_normalise_column_type(type_object.item_type)}[]"
    if isinstance(type_object, Float):
        return "float"
    return (_normalise_sql(str(type_object)) or "").lower()


_REDUNDANT_VARCHAR_CAST = re.compile(
    r"^('(?:[^']|'')*')::(?:character varying|varchar)(?:\(\d+\))?$"
)


def _normalise_column_default(default: str | None, *, column_type: str) -> str | None:
    """Canonicalise a reflected column default without hiding real drift.

    PostgreSQL renders ``NOW()`` written in DDL back as ``now()`` and decorates
    string literals on varchar columns with a redundant self-cast
    (``'pending'::character varying``). Both spellings are the same default,
    so they must hash identically. Anything else — ``timezone(...)``,
    ``clock_timestamp()``, ``::text`` or custom-type casts, non-literal
    expressions — is materially different and passes through untouched.
    """
    if default is None:
        return None
    normalised = _normalise_sql(default) or ""
    if normalised.lower() == "now()":
        return "now()"
    literal = _REDUNDANT_VARCHAR_CAST.fullmatch(normalised)
    if literal:
        return literal.group(1)
    return default


_SQL_STRING_LITERAL = r"'(?:[^']|'')*'"
_SQL_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"

_CHECK_IN_FORM = re.compile(rf"({_SQL_IDENTIFIER}) IN \((.+)\)")
_CHECK_ANY_FORM = re.compile(
    rf"({_SQL_IDENTIFIER})::text = ANY \(ARRAY\[(.+)\]::text\[\]\)"
)
_IN_SET_LITERAL = re.compile(rf"({_SQL_STRING_LITERAL})")
_ANY_SET_LITERAL = re.compile(
    rf"({_SQL_STRING_LITERAL})::character varying(?:\(\d+\))?"
)


def _parse_literal_set(payload: str, item: re.Pattern) -> list[str] | None:
    """Parse an ordered ``, ``-separated list of string literals, or None."""
    literals: list[str] = []
    position = 0
    while True:
        match = item.match(payload, position)
        if not match:
            return None
        literals.append(match.group(1))
        position = match.end()
        if position == len(payload):
            return literals
        if not payload.startswith(", ", position):
            return None
        position += 2


def _normalise_check(check: str | None) -> str | None:
    """Canonicalise the one CHECK shape PostgreSQL is proven to rewrite.

    The migrations write ``col IN ('a', 'b')``; PostgreSQL stores it back as
    ``col::text = ANY (ARRAY['a'::character varying, ...]::text[])``. Both are
    the same IN_SET(identifier, string literals) predicate, so both reduce to
    the ``IN`` rendering with member order preserved. Only the exact casts of
    that expansion (identifier ``::text``, element ``::character varying``,
    array ``::text[]``) are accepted; any other operator, cast, literal kind
    or extra clause passes through untouched and keeps producing drift.
    """
    if check is None:
        return None
    for form, item in ((_CHECK_IN_FORM, _IN_SET_LITERAL), (_CHECK_ANY_FORM, _ANY_SET_LITERAL)):
        match = form.fullmatch(check)
        if not match:
            continue
        literals = _parse_literal_set(match.group(2), item)
        if literals is not None:
            return f"{match.group(1)} IN ({', '.join(literals)})"
    return check


_RANGE_PARTITION_BOUNDS = re.compile(r"FOR VALUES FROM \((.+)\) TO \((.+)\)")
_MIDNIGHT_UTC_LITERAL = re.compile(r"'(\d{4}-\d{2}-\d{2}) 00:00:00\+00(?::00)?'")


def _reduce_bound_values(payload: str) -> str:
    """Reduce each midnight-UTC timestamp literal in a bound list to its date.

    Only a literal that is a valid ISO date at exactly ``00:00:00`` with an
    explicit ``+00`` offset denotes the same instant as the plain date the
    migrations wrote. Any other value — different time, missing or non-UTC
    offset, fractional seconds, ``MINVALUE``/``MAXVALUE``, invalid date —
    is kept verbatim, so the round-trip is lossless for non-matches.
    """
    values = []
    for value in payload.split(", "):
        match = _MIDNIGHT_UTC_LITERAL.fullmatch(value)
        if match:
            try:
                date.fromisoformat(match.group(1))
            except ValueError:
                values.append(value)
                continue
            values.append(f"'{match.group(1)}'")
        else:
            values.append(value)
    return ", ".join(values)


def _normalise_partition_bounds(bounds: str | None) -> str | None:
    """Canonicalise RANGE partition bounds without touching their structure.

    The FROM/TO order (and therefore inclusivity) is preserved; only the
    rendering of individual midnight-UTC instants is reduced. LIST and HASH
    bound forms pass through untouched.
    """
    if bounds is None:
        return None
    match = _RANGE_PARTITION_BOUNDS.fullmatch(bounds)
    if not match:
        return bounds
    lower = _reduce_bound_values(match.group(1))
    upper = _reduce_bound_values(match.group(2))
    return f"FOR VALUES FROM ({lower}) TO ({upper})"


_INDEX_KEY_FIELDS = ("expr", "opclass", "collation", "sort", "nulls")


def _normalise_index_key(key: Mapping) -> dict:
    """Reduce a catalog index key to its contract shape.

    The catalog names the collation of every collatable key even when it is
    just the one the column already carries; the contract writes ``null``
    there. Only that case — collation ``default`` proven inherited from the
    underlying column by the catalog query — is nulled. Explicit or custom
    collations, expression keys and keys lacking the inheritance proof keep
    their reported collation.
    """
    normalised = {name: key.get(name) for name in _INDEX_KEY_FIELDS}
    if normalised["collation"] == "default" and key.get("collation_inherited") is True:
        normalised["collation"] = None
    return normalised


def _result_mappings(result) -> list[dict]:
    """Materialise mapping rows; tolerate minimal empty-result test doubles."""
    mappings = getattr(result, "mappings", None)
    rows = mappings().all() if mappings else result.all()
    return [dict(row) for row in rows]


def _catalog_indexes(conn) -> list[dict]:
    """Return complete PostgreSQL index semantics in one bounded catalog query."""
    return _result_mappings(conn.execute(text("""
        /* drift_inventory:indexes */
        SELECT ns.nspname AS schema, tbl.relname AS table,
               idx.relname AS indexname, i.indisunique AS unique,
               am.amname AS method,
               jsonb_agg(jsonb_build_object(
                   'expr', pg_get_indexdef(i.indexrelid, key.ordinality::integer, true),
                   'opclass', CASE WHEN opc.opcdefault THEN NULL ELSE opc.opcname END,
                   'collation', CASE WHEN coll.oid = 0 THEN NULL ELSE coll.collname END,
                   'collation_inherited', COALESCE(att.attcollation = coll.oid, false),
                   'sort', CASE WHEN (key.option & 1) = 1 THEN 'desc' ELSE 'asc' END,
                   'nulls', CASE WHEN (key.option & 2) = 2 THEN 'first' ELSE 'last' END
               ) ORDER BY key.ordinality)
                   FILTER (WHERE key.ordinality <= i.indnkeyatts) AS keys,
               array_agg(pg_get_indexdef(i.indexrelid, key.ordinality::integer, true)
                         ORDER BY key.ordinality)
                   FILTER (WHERE key.ordinality > i.indnkeyatts) AS include,
               pg_get_expr(i.indpred, i.indrelid, true) AS predicate
        FROM pg_index AS i
        JOIN pg_class AS idx ON idx.oid = i.indexrelid
        JOIN pg_class AS tbl ON tbl.oid = i.indrelid
        JOIN pg_namespace AS ns ON ns.oid = tbl.relnamespace
        JOIN pg_am AS am ON am.oid = idx.relam
        JOIN LATERAL unnest(i.indclass, i.indcollation, i.indoption)
             WITH ORDINALITY AS key(opclass_oid, collation_oid, option, ordinality)
             ON true
        JOIN pg_opclass AS opc ON opc.oid = key.opclass_oid
        LEFT JOIN pg_collation AS coll ON coll.oid = key.collation_oid
        LEFT JOIN pg_attribute AS att
             ON att.attrelid = i.indrelid
            AND att.attnum = i.indkey[key.ordinality::integer - 1]
        WHERE ns.nspname NOT IN ('pg_catalog', 'information_schema')
          AND NOT i.indisprimary
          AND NOT EXISTS (
              SELECT 1
              FROM pg_constraint AS con
              WHERE con.conindid = i.indexrelid
          )
          AND NOT EXISTS (
              SELECT 1
              FROM pg_inherits AS index_inh
              WHERE index_inh.inhrelid = i.indexrelid
          )
        GROUP BY ns.nspname, tbl.relname, idx.relname, i.indexrelid,
                 i.indisunique, am.amname, i.indpred, i.indrelid
        ORDER BY ns.nspname, tbl.relname, idx.relname
    """)))


def _catalog_partitions(conn) -> list[dict]:
    """Return parent keys and child parent/bounds in one bounded catalog query."""
    return _result_mappings(conn.execute(text("""
        /* drift_inventory:partitions */
        SELECT ns.nspname AS schema, rel.relname AS table,
               CASE WHEN rel.relkind = 'p'
                    THEN pg_get_partkeydef(rel.oid) END AS partition_key,
               pns.nspname AS parent_schema, parent.relname AS parent_table,
               CASE WHEN parent.oid IS NOT NULL
                    THEN pg_get_expr(rel.relpartbound, rel.oid, true) END
                    AS partition_bounds
        FROM pg_class AS rel
        JOIN pg_namespace AS ns ON ns.oid = rel.relnamespace
        LEFT JOIN pg_inherits AS inh ON inh.inhrelid = rel.oid
        LEFT JOIN pg_class AS parent ON parent.oid = inh.inhparent
        LEFT JOIN pg_namespace AS pns ON pns.oid = parent.relnamespace
        WHERE rel.relkind IN ('r', 'p')
          AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
          AND (rel.relkind = 'p' OR parent.oid IS NOT NULL)
        ORDER BY ns.nspname, rel.relname
    """)))


def _inspector_call(insp, method: str, table: str, schema: str, fallback):
    """Call a SQLAlchemy inspector method while supporting narrow test fakes."""
    callback = getattr(insp, method, None)
    return callback(table, schema=schema) if callback else fallback


def _live_table_structure(insp, schema: str, table: str, *, indexes, partitions) -> dict:
    columns = []
    for column in _inspector_call(insp, "get_columns", table, schema, []):
        column_type = _normalise_column_type(column.get("type"))
        columns.append({
            "name": column.get("name"),
            "type": column_type,
            "nullable": bool(column.get("nullable", True)),
            "default": _normalise_column_default(
                _normalise_sql(column.get("default")), column_type=column_type
            ),
            "identity": column.get("identity"),
            "generated": column.get("computed") or column.get("generated"),
        })
    pk = _inspector_call(insp, "get_pk_constraint", table, schema, {})
    unique = _inspector_call(insp, "get_unique_constraints", table, schema, [])
    foreign_keys = []
    for fk in _inspector_call(insp, "get_foreign_keys", table, schema, []):
        options = fk.get("options") or {}
        foreign_keys.append({
            "columns": list(fk.get("constrained_columns") or ()),
            "target_schema": fk.get("referred_schema") or schema,
            "target_table": fk.get("referred_table"),
            "target_columns": list(fk.get("referred_columns") or ()),
            "ondelete": options.get("ondelete"),
            "onupdate": options.get("onupdate"),
            "deferrable": options.get("deferrable"),
            "initially": options.get("initially"),
        })
    checks = _inspector_call(insp, "get_check_constraints", table, schema, [])
    partition = partitions.get((schema, table), {})
    return {
        "schema": schema,
        "name": table,
        "columns": columns,
        "primary_key": list(pk.get("constrained_columns") or ()),
        "unique": [list(item.get("column_names") or ()) for item in unique],
        "foreign_keys": foreign_keys,
        "checks": [_normalise_check(_normalise_sql(item.get("sqltext"))) for item in checks],
        "indexes": indexes.get((schema, table), []),
        "partition_key": _normalise_sql(partition.get("partition_key")),
        "parent_schema": partition.get("parent_schema"),
        "parent_table": partition.get("parent_table"),
        "partition_bounds": _normalise_partition_bounds(
            _normalise_sql(partition.get("partition_bounds"))
        ),
    }


def inventory_connection(connection: Connection, *, target: str) -> LiveInventory:
    """Inventory a PostgreSQL catalog through the supplied connection only."""
    insp = inspect(connection)
    schemas = tuple(sorted(s for s in insp.get_schema_names() if s not in {"information_schema"}))
    tables: list[tuple[str, str]] = []
    indexes: list[tuple[str, str, str]] = []
    extensions = tuple(
        (row[0], row[1])
        for row in connection.execute(
            text(
                "SELECT extname, extversion FROM pg_extension "
                "WHERE extname NOT IN ('plpgsql') ORDER BY extname"
            )
        ).all()
    )
    catalog_indexes = _catalog_indexes(connection)
    catalog_partitions = _catalog_partitions(connection)
    av_rows = []
    exists = connection.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='alembic_version'"
        )
    ).scalar()
    if exists:
        av_rows = connection.execute(
            text(
                "SELECT version_num FROM public.alembic_version "
                "WHERE version_num IS NOT NULL"
            )
        ).all()
    alembic_version = av_rows[0][0] if av_rows else None
    indexes_by_table: dict[tuple[str, str], list[dict]] = {}
    for item in catalog_indexes:
        schema_table = (item["schema"], item["table"])
        semantic = {
            "unique": bool(item.get("unique")),
            "method": item.get("method") or "btree",
            "keys": [_normalise_index_key(key) for key in (item.get("keys") or ())],
            "include": list(item.get("include") or ()),
            "predicate": _normalise_sql(item.get("predicate")),
        }
        indexes_by_table.setdefault(schema_table, []).append(semantic)
        indexes.append((item["schema"], item["table"], item.get("indexname") or ""))
    partitions_by_table = {
        (item["schema"], item["table"]): item for item in catalog_partitions
    }
    live_tables = []
    for schema in schemas:
        for table_name in sorted(insp.get_table_names(schema=schema)):
            tables.append((schema, table_name))
            live_tables.append(_live_table_structure(
                insp,
                schema,
                table_name,
                indexes=indexes_by_table,
                partitions=partitions_by_table,
            ))
    structure = {
        "schemas": list(schemas),
        "tables": live_tables,
        "extensions": sorted(name for name, _version in extensions),
    }
    fingerprint = _fingerprint(schemas, tables, indexes, extensions, alembic_version)
    return LiveInventory(
        target=target,
        schemas=schemas,
        tables=tuple(tables),
        indexes=tuple(indexes),
        extensions=extensions,
        alembic_version=alembic_version,
        fingerprint=fingerprint,
        structure=structure,
        structural_fingerprint=structural_fingerprint(structure),
    )


def inventory_target(database_url: str, *, guard) -> LiveInventory:
    """Read the live catalog after the disposable-target guard accepts it."""
    spec = guard(database_url)
    target = f"{spec.host}:{spec.port}/{spec.database} as {spec.user}"
    engine = create_engine(_sync_dsn(database_url), future=True)
    try:
        with engine.connect() as connection:
            return inventory_connection(connection, target=target)
    finally:
        engine.dispose()


def _fingerprint(
    schemas: Iterable[str],
    tables: Iterable[tuple[str, str]],
    indexes: Iterable[tuple[str, str, str]],
    extensions: Iterable[tuple[str, str]],
    alembic_version: str | None,
) -> str:
    """Stable hash of the catalog, used to prove no-op and pre/post identity."""
    payload = "|".join(
        [
            "s=" + ",".join(sorted(schemas)),
            "t=" + ",".join(sorted(f"{s}.{t}" for s, t in tables)),
            "i=" + ",".join(sorted(f"{s}.{t}.{i}" for s, t, i in indexes)),
            "e=" + ",".join(sorted(f"{n}@{v}" for n, v in extensions)),
            f"av={alembic_version or 'none'}",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_fingerprint(
    schemas: Iterable[str],
    tables: Iterable[tuple[str, str]],
    indexes: Iterable[tuple[str, str, str]],
    extensions: Iterable[tuple[str, str]],
    alembic_version: str | None,
) -> str:
    """Public name for the catalog hash: sensitive to the Alembic stamp.

    This is the no-op/pre-post identity proof used by the dry-run report;
    it deliberately *includes* ``alembic_version`` (and index names), unlike
    :func:`structural_fingerprint`.
    """
    return _fingerprint(schemas, tables, indexes, extensions, alembic_version)


# --- Structural fingerprint (adoption Option B) ------------------------------


def _canonical_json(value) -> str:
    """Deterministic JSON encoding: sorted keys, no whitespace, ASCII only."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def index_signature(index: Mapping) -> str:
    """Canonical semantic identity of an index, ignoring its arbitrary name.

    A dump/restore (or a hand-created equivalent index) may change the index
    *name* without changing what the index does. Everything that changes
    behaviour is retained: uniqueness, access method, the ordered key
    expressions with their opclass/collation/sort/nulls, INCLUDE columns and
    the partial-index predicate.
    """
    payload = {
        "unique": bool(index.get("unique", False)),
        "method": index.get("method") or "btree",
        "keys": [_normalise_index_key(key) for key in index.get("keys", ())],
        "include": list(index.get("include", ())),
        "predicate": index.get("predicate"),
    }
    return _canonical_json(payload)


def _plain_unique_columns(index: Mapping) -> tuple[str, ...] | None:
    """Return columns when an index exactly matches plain UNIQUE semantics."""
    if not index.get("unique") or (index.get("method") or "btree") != "btree":
        return None
    if index.get("predicate") is not None or list(index.get("include", ())) != []:
        return None
    columns = []
    for key in index.get("keys", ()):
        if (
            key.get("opclass") is not None
            or key.get("collation") is not None
            or key.get("sort") not in (None, "asc")
            or key.get("nulls") not in (None, "last")
        ):
            return None
        expression = key.get("expr")
        if not isinstance(expression, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', expression):
            return None
        columns.append(expression)
    return tuple(columns) if columns else None


def _normalise_table(table: Mapping) -> dict:
    """Whitelist and canonicalise the complete DDL shape of one table."""
    uniqueness = {tuple(columns) for columns in table.get("unique", ())}
    semantic_indexes = []
    for index in table.get("indexes", ()):
        equivalent_unique = _plain_unique_columns(index)
        if equivalent_unique is None:
            semantic_indexes.append(index_signature(index))
        else:
            uniqueness.add(equivalent_unique)
    return {
        "schema": table.get("schema"),
        "name": table.get("name"),
        "columns": [
            {
                "name": col.get("name"),
                "type": col.get("type"),
                "nullable": bool(col.get("nullable", True)),
                "default": col.get("default"),
                "identity": col.get("identity"),
                "generated": col.get("generated", col.get("computed")),
            }
            for col in table.get("columns", ())
        ],
        "primary_key": list(table.get("primary_key", ())),
        "unique": sorted([list(columns) for columns in uniqueness]),
        "foreign_keys": sorted(
            (
                {
                    "columns": list(fk.get("columns", ())),
                    "target_schema": fk.get("target_schema"),
                    "target_table": fk.get("target_table"),
                    "target_columns": list(fk.get("target_columns", ())),
                    "ondelete": fk.get("ondelete"),
                    "onupdate": fk.get("onupdate"),
                    "deferrable": bool(fk.get("deferrable", False)),
                    "initially": fk.get("initially"),
                }
                for fk in table.get("foreign_keys", ())
            ),
            key=_canonical_json,
        ),
        "checks": sorted(
            _normalise_check(check) if isinstance(check, str) else check
            for check in table.get("checks", ())
        ),
        "indexes": sorted(semantic_indexes),
        "partition_key": table.get("partition_key"),
        "parent_schema": table.get("parent_schema"),
        "parent_table": table.get("parent_table"),
        "partition_bounds": _normalise_partition_bounds(table.get("partition_bounds"))
        if isinstance(table.get("partition_bounds"), str)
        else table.get("partition_bounds"),
    }


def structural_fingerprint(structure: Mapping) -> str:
    """Stable hash of the DDL shape of a database, blind to the Alembic stamp.

    Two databases with identical schemas/tables/columns/constraints/indexes
    (by semantics, not by index name) and identical partition layout hash to
    the same value regardless of ``alembic_version`` content. Used to decide
    whether a restored target is structurally adoptable.
    """
    payload = {
        "schemas": sorted(structure.get("schemas", ())),
        "extensions": sorted(structure.get("extensions", ())),
        "tables": sorted(
            (_normalise_table(t) for t in structure.get("tables", ())),
            key=lambda t: (t["schema"] or "", t["name"] or ""),
        ),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


# --- Drift classification ---------------------------------------------------


@dataclass(frozen=True)
class DriftReport:
    """The combined view of code/model/live drift."""

    code_revisions: dict
    model_tables: tuple[ModelInfo, ...]
    live: LiveInventory
    code_vs_model: dict
    live_vs_code: dict
    model_not_in_live: tuple[str, ...]
    live_not_in_model: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "code_revisions": self.code_revisions,
            "model_tables": [
                {"name": m.name, "table": m.table, "schema": m.schema, "has_partition": m.has_partition}
                for m in self.model_tables
            ],
            "live": self.live.to_dict(),
            "code_vs_model": self.code_vs_model,
            "live_vs_code": self.live_vs_code,
            "model_not_in_live": list(self.model_not_in_live),
            "live_not_in_model": list(self.live_not_in_model),
        }


def classify_drift(
    revisions: list[RevisionInfo],
    models: list[ModelInfo],
    live: LiveInventory,
) -> DriftReport:
    """Build the :class:`DriftReport` from raw observations.

    The report is intentionally explicit about *which side* of the drift is
    affected (code/model vs live), so the dry-run report can recommend a
    migration *or* a documentation update.
    """
    graph = revision_graph(revisions)
    model_set = {(m.schema, m.table) for m in models}
    live_set = {(s, t) for s, t in live.tables if s != "public" or t != "alembic_version"}
    code_vs_model = {
        "head_revision": graph["heads"][-1] if graph["heads"] else None,
        "model_count": len(models),
    }
    live_vs_code = {
        "alembic_version": live.alembic_version,
        "schema_count": len(live.schemas),
        "table_count": len(live.tables),
    }
    return DriftReport(
        code_revisions=graph,
        model_tables=tuple(models),
        live=live,
        code_vs_model=code_vs_model,
        live_vs_code=live_vs_code,
        model_not_in_live=tuple(
            sorted(f"{s or 'public'}.{t}" for s, t in (model_set - live_set))
        ),
        live_not_in_model=tuple(
            sorted(f"{s}.{t}" for s, t in (live_set - model_set))
        ),
    )


__all__ = [
    "RevisionInfo",
    "ModelInfo",
    "LiveInventory",
    "DriftReport",
    "list_revisions",
    "revision_graph",
    "list_models",
    "inventory_connection",
    "inventory_target",
    "classify_drift",
    "catalog_fingerprint",
    "index_signature",
    "structural_fingerprint",
]
