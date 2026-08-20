"""RED→GREEN tests for scripts/drift_inventory.

The module is the read-only inventory layer that powers the WP3 dry-run
report. It must be deterministic and free of secrets: every test either
builds a synthetic revisions/models/live set or stubs the guard so no
network or DSN leak is possible.
"""
from __future__ import annotations

import dataclasses
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import ARRAY, Date, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION

import scripts.drift_inventory as di
import scripts.target_guard as guard
from scripts.drift_inventory import (
    DriftReport,
    LiveInventory,
    ModelInfo,
    RevisionInfo,
    classify_drift,
    list_models,
    list_revisions,
    revision_graph,
)


VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


# --- list_revisions / revision_graph ---------------------------------------


def test_list_revisions_finds_001_and_002_in_order():
    """The canonical repository has exactly revisions 001 and 002 in order."""
    revs = list_revisions(VERSIONS_DIR)
    ids = [r.revision for r in revs]
    assert ids == ["001", "002"], ids
    assert revs[0].down_revision is None
    assert revs[1].down_revision == "001"


def test_revision_graph_has_exactly_one_head():
    revs = list_revisions(VERSIONS_DIR)
    graph = revision_graph(revs)
    assert graph["heads"] == ["002"], graph["heads"]
    assert graph["multiple_heads"] is False
    assert graph["cycle"] is False


def test_revision_graph_detects_multiple_heads():
    fake = [
        RevisionInfo(revision="001", down_revision=None, source_path="001.py"),
        RevisionInfo(revision="002", down_revision=None, source_path="002.py"),
    ]
    graph = revision_graph(fake)
    assert graph["multiple_heads"] is True
    assert sorted(graph["heads"]) == ["001", "002"]


def test_revision_graph_detects_cycle():
    fake = [
        RevisionInfo(revision="001", down_revision="002", source_path="001.py"),
        RevisionInfo(revision="002", down_revision="001", source_path="002.py"),
    ]
    graph = revision_graph(fake)
    assert graph["cycle"] is True


def test_revision_graph_is_linear_for_001_to_002():
    revs = list_revisions(VERSIONS_DIR)
    graph = revision_graph(revs)
    # 001 -> 002, no other children, no cycle.
    assert graph["child_map"] == {"001": ["002"], "002": []}


# --- list_models ------------------------------------------------------------


def test_list_models_returns_normalised_tuples():
    """Every ORM model produces a (schema, table) entry; partition flag set."""
    import app.models  # noqa: F401
    from app.models.database import Base

    models = list_models(Base.metadata)
    by_name = {m.name: m for m in models}
    assert "app.users" in by_name
    assert "core.trademarks" in by_name
    assert "events.lifecycle_events" in by_name
    assert "raw.api_responses" in by_name
    assert by_name["raw.api_responses"].has_partition is True
    assert by_name["app.users"].has_partition is False
    assert by_name["core.sources"].has_partition is False


# --- classify_drift ---------------------------------------------------------


def _fake_revisions() -> list[RevisionInfo]:
    return [
        RevisionInfo(revision="001", down_revision=None, source_path="001.py"),
        RevisionInfo(revision="002", down_revision="001", source_path="002.py"),
    ]


def _fake_models() -> list[ModelInfo]:
    return [
        ModelInfo(name="app.users", table="users", schema="app"),
        ModelInfo(name="core.trademarks", table="trademarks", schema="core"),
    ]


def _fake_live() -> LiveInventory:
    return LiveInventory(
        target="127.0.0.1:5441/markee_wp3_disposable as markee_wp3",
        schemas=("app", "core", "public"),
        tables=(
            ("app", "users"),
            ("core", "trademarks"),
            ("public", "alembic_version"),
            ("public", "users"),  # legacy drift
        ),
        indexes=(("app", "users", "users_pkey"),),
        extensions=(("pg_trgm", "1.6"),),
        alembic_version="001",
        fingerprint="abc",
    )


def test_classify_drift_identifies_model_not_in_live_and_live_not_in_model():
    report = classify_drift(_fake_revisions(), _fake_models(), _fake_live())
    assert "public.users" in report.live_not_in_model
    assert "app.users" not in report.model_not_in_live
    # core.trademarks exists on both sides, so it should not appear.
    assert "core.trademarks" not in report.model_not_in_live
    # model not in live: nothing in this fixture.
    assert report.model_not_in_live == ()
    assert report.code_revisions["multiple_heads"] is False
    assert report.code_revisions["cycle"] is False


def test_classify_drift_serialises_to_dict_without_secrets():
    report = classify_drift(_fake_revisions(), _fake_models(), _fake_live())
    blob = report.to_dict()
    assert "code_revisions" in blob
    assert "model_tables" in blob
    assert "live" in blob
    serialised = str(blob)
    for needle in ("markee_dev", "secret", "password", "token"):
        assert needle not in serialised.lower(), needle


# --- inventory_target: guard-before-connect contract ------------------------


def test_inventory_target_calls_guard_first(monkeypatch):
    """``inventory_target`` must run the guard before any engine connection."""
    calls: list[str] = []

    def fake_guard(dsn):
        calls.append(("guard", dsn))
        return SimpleNamespace(host="127.0.0.1", port=5441, user="markee_wp3", database="markee_wp3_disposable")

    def fake_create_engine(*a, **k):
        calls.append(("engine", a, k))
        raise RuntimeError("engine must not be created before guard")

    monkeypatch.setattr(di, "create_engine", fake_create_engine)
    monkeypatch.setattr(di, "inspect", lambda *a, **k: calls.append(("inspect", a)) or SimpleNamespace())
    with pytest.raises(RuntimeError, match="engine must not be created"):
        di.inventory_target(
            "postgresql+asyncpg://markee_wp3:x@127.0.0.1:5441/markee_wp3_disposable",
            guard=fake_guard,
        )
    assert calls and calls[0][0] == "guard"


def test_inventory_target_aborts_when_guard_rejects(monkeypatch):
    """If the guard raises ``GuardError``, no engine is created."""
    def fake_guard(dsn):
        raise guard.GuardError("refused")

    def fake_create_engine(*a, **k):
        raise RuntimeError("engine must not be created after guard error")

    monkeypatch.setattr(di, "create_engine", fake_create_engine)
    with pytest.raises(guard.GuardError, match="refused"):
        di.inventory_target("any-dsn", guard=fake_guard)


def test_inventory_target_strips_asyncpg_scheme(monkeypatch):
    """The helper converts asyncpg URLs to plain postgresql for ``inspect``."""
    captured: list[str] = []

    def fake_create_engine(dsn, **k):
        captured.append(dsn)

        class _Result:
            def all(self_inner):
                return []

            def scalar(self_inner):
                return None

        class _Conn:
            def execute(self_inner, *a, **k):
                return _Result()

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

        eng = SimpleNamespace(
            begin=lambda: _Conn(),
            connect=lambda: _Conn(),
            dispose=lambda: None,
        )
        return eng

    monkeypatch.setattr(di, "create_engine", fake_create_engine)
    monkeypatch.setattr(
        di, "inspect", lambda engine: SimpleNamespace(
            get_schema_names=lambda: ["public"],
            get_table_names=lambda schema=None: ["alembic_version"],
            get_indexes=lambda t, schema=None: [],
        )
    )

    def fake_guard(dsn):
        return SimpleNamespace(host="127.0.0.1", port=5441, user="markee_wp3", database="markee_wp3_disposable")

    di.inventory_target(
        "postgresql+asyncpg://markee_wp3:x@127.0.0.1:5441/markee_wp3_disposable",
        guard=fake_guard,
    )
    assert captured == ["postgresql://markee_wp3:x@127.0.0.1:5441/markee_wp3_disposable"]


# --- Stable hash (no-op proof) ---------------------------------------------


def test_fingerprint_changes_when_alembic_version_changes():
    from scripts.drift_inventory import _fingerprint

    schemas: tuple[str, ...] = ("app", "core", "public")
    tables: tuple[tuple[str, str], ...] = (
        ("app", "users"),
        ("core", "trademarks"),
        ("public", "alembic_version"),
        ("public", "users"),
    )
    indexes: tuple[tuple[str, str, str], ...] = (("app", "users", "users_pkey"),)
    extensions: tuple[tuple[str, str], ...] = (("pg_trgm", "1.6"),)
    fp_001 = _fingerprint(schemas, tables, indexes, extensions, "001")
    fp_002 = _fingerprint(schemas, tables, indexes, extensions, "002")
    assert fp_001 != fp_002


def test_fingerprint_stable_for_same_inputs():
    from scripts.drift_inventory import _fingerprint

    schemas: tuple[str, ...] = ("app", "core", "public")
    tables: tuple[tuple[str, str], ...] = (("app", "users"), ("core", "trademarks"))
    indexes: tuple[tuple[str, str, str], ...] = (("app", "users", "users_pkey"),)
    extensions: tuple[tuple[str, str], ...] = (("pg_trgm", "1.6"),)
    a = _fingerprint(schemas, tables, indexes, extensions, "001")
    b = _fingerprint(schemas, tables, indexes, extensions, "001")
    assert a == b


# --- Structural fingerprint (adoption Option B, cycle 1) --------------------


def _structure(alembic_version: str | None = "001") -> dict:
    """A synthetic normalised structural snapshot with every element class.

    Mirrors what the inventory can observe today: schemas, tables with
    columns (type/default/nullability), PK, unique, FK targets, checks,
    semantic index entries and partition key/bounds. No row values.
    """
    return {
        "alembic_version": alembic_version,
        "schemas": ["app", "core", "public", "raw"],
        "tables": [
            {
                "schema": "app",
                "name": "users",
                "columns": [
                    {"name": "id", "type": "uuid", "nullable": False, "default": "gen_random_uuid()"},
                    {"name": "email", "type": "varchar(255)", "nullable": False, "default": None},
                ],
                "primary_key": ["id"],
                "unique": [["email"]],
                "foreign_keys": [],
                "checks": ["char_length(email) > 3"],
                "indexes": [
                    {
                        "name": "users_email_key",
                        "unique": True,
                        "method": "btree",
                        "keys": [
                            {
                                "expr": "email",
                                "opclass": None,
                                "collation": None,
                                "sort": "asc",
                                "nulls": None,
                            }
                        ],
                        "include": [],
                        "predicate": None,
                    }
                ],
                "partition_key": None,
                "partition_bounds": None,
            },
            {
                "schema": "core",
                "name": "trademarks",
                "columns": [
                    {"name": "id", "type": "uuid", "nullable": False, "default": None},
                    {"name": "owner_id", "type": "uuid", "nullable": True, "default": None},
                ],
                "primary_key": ["id"],
                "unique": [],
                "foreign_keys": [
                    {
                        "columns": ["owner_id"],
                        "target_schema": "app",
                        "target_table": "users",
                        "target_columns": ["id"],
                    }
                ],
                "checks": [],
                "indexes": [],
                "partition_key": None,
                "partition_bounds": None,
            },
            {
                "schema": "raw",
                "name": "api_responses_2026_01",
                "columns": [
                    {"name": "id", "type": "bigint", "nullable": False, "default": None},
                    {"name": "fetched_at", "type": "timestamptz", "nullable": False, "default": None},
                ],
                "primary_key": ["id", "fetched_at"],
                "unique": [],
                "foreign_keys": [],
                "checks": [],
                "indexes": [],
                "partition_key": "RANGE (fetched_at)",
                "partition_bounds": "FOR VALUES FROM ('2026-01-01') TO ('2026-02-01')",
            },
        ],
    }


def _index(name: str = "ix_word_mark_trgm", opclass: str | None = "gin_trgm_ops") -> dict:
    return {
        "name": name,
        "unique": False,
        "method": "gin",
        "keys": [
            {
                "expr": "word_mark",
                "opclass": opclass,
                "collation": None,
                "sort": None,
                "nulls": None,
            }
        ],
        "include": [],
        "predicate": None,
    }


def test_structural_fingerprint_ignores_alembic_version():
    """Structure is invariant under stamp state: only DDL shape matters."""
    fp_001 = di.structural_fingerprint(_structure(alembic_version="001"))
    fp_002 = di.structural_fingerprint(_structure(alembic_version="002"))
    fp_none = di.structural_fingerprint(_structure(alembic_version=None))
    assert fp_001 == fp_002 == fp_none


def test_catalog_fingerprint_changes_with_alembic_version():
    """The catalog fingerprint keeps its pre-existing stamp sensitivity."""
    schemas: tuple[str, ...] = ("app", "core", "public")
    tables: tuple[tuple[str, str], ...] = (("app", "users"), ("public", "alembic_version"))
    indexes: tuple[tuple[str, str, str], ...] = (("app", "users", "users_pkey"),)
    extensions: tuple[tuple[str, str], ...] = (("pg_trgm", "1.6"),)
    fp_001 = di.catalog_fingerprint(schemas, tables, indexes, extensions, "001")
    fp_002 = di.catalog_fingerprint(schemas, tables, indexes, extensions, "002")
    assert fp_001 != fp_002
    # And it must agree with the private helper already used by the report.
    assert fp_001 == di._fingerprint(schemas, tables, indexes, extensions, "001")


def test_index_signature_ignores_name_but_not_opclass():
    """Two indexes differing only in name are the same object; opclass is not."""
    renamed = di.index_signature(_index(name="ix_restored_random_suffix_ab12"))
    original = di.index_signature(_index(name="ix_word_mark_trgm"))
    assert renamed == original
    other_opclass = di.index_signature(_index(opclass="gin_trgm_ops_v2"))
    assert other_opclass != original


def test_partition_bounds_are_part_of_structural_fingerprint():
    base = _structure()
    moved = _structure()
    moved["tables"][2]["partition_bounds"] = (
        "FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')"
    )
    assert di.structural_fingerprint(base) != di.structural_fingerprint(moved)


def test_fk_target_schema_is_part_of_structural_fingerprint():
    base = _structure()
    retargeted = _structure()
    retargeted["tables"][1]["foreign_keys"][0]["target_schema"] = "public"
    assert di.structural_fingerprint(base) != di.structural_fingerprint(retargeted)


# --- PostgreSQL column type normalisation (Cycle A) -------------------------


@pytest.mark.parametrize(
    ("type_object", "expected"),
    [
        pytest.param(
            DateTime(timezone=True),
            "timestamp with time zone",
            id="timestamp-with-time-zone",
        ),
        pytest.param(
            DateTime(timezone=False),
            "timestamp without time zone",
            id="timestamp-without-time-zone-remains-distinct",
        ),
    ],
)
def test_postgresql_timestamp_types_preserve_timezone_semantics(type_object, expected):
    assert di._normalise_column_type(type_object) == expected


@pytest.mark.parametrize(
    ("type_object", "expected"),
    [
        pytest.param(Float(), "float", id="sqlalchemy-float"),
        pytest.param(DOUBLE_PRECISION(), "float", id="postgresql-double-precision"),
        pytest.param(ARRAY(Integer()), "integer[]", id="integer-array"),
        pytest.param(ARRAY(Date()), "date[]", id="date-array"),
        pytest.param(ARRAY(String()), "varchar[]", id="unbounded-varchar-array"),
        pytest.param(ARRAY(String(100)), "varchar(100)[]", id="bounded-varchar-array"),
    ],
)
def test_postgresql_reflected_types_use_migration_vocabulary(type_object, expected):
    assert di._normalise_column_type(type_object) == expected


def test_type_normalisation_retains_real_drift_distinctions():
    representations = {
        "timestamp_without_tz": di._normalise_column_type(DateTime(timezone=False)),
        "timestamp_with_tz": di._normalise_column_type(DateTime(timezone=True)),
        "numeric": di._normalise_column_type(Numeric()),
        "float": di._normalise_column_type(Float()),
        "text_array": di._normalise_column_type(ARRAY(Text())),
        "integer_array": di._normalise_column_type(ARRAY(Integer())),
        "bounded_varchar_array": di._normalise_column_type(ARRAY(String(100))),
    }
    assert representations["timestamp_without_tz"] != representations["timestamp_with_tz"]
    assert representations["numeric"] != representations["float"]
    assert len({
        representations["text_array"],
        representations["integer_array"],
        representations["bounded_varchar_array"],
    }) == 3


@pytest.mark.parametrize("raw", ["NOW()"] * 33 + ["now()"])
def test_default_normalisation_canonicalises_now_spellings(raw):
    assert di._normalise_column_default(raw, column_type="timestamp with time zone") == "now()"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("'pending'::character varying", "'pending'"),
        ("'pt'::character varying", "'pt'"),
        ("'pt'::character varying(8)", "'pt'"),
        ("'applicant'::varchar", "'applicant'"),
        ("'representative'::varchar(32)", "'representative'"),
    ],
)
def test_default_normalisation_removes_five_redundant_varchar_cast_forms(raw, expected):
    assert di._normalise_column_default(raw, column_type="varchar(32)") == expected


@pytest.mark.parametrize(
    "raw",
    [
        "timezone('utc', now())",
        "clock_timestamp()",
        "'pending'::text",
        "'pending'::status",
    ],
)
def test_default_normalisation_preserves_materially_different_defaults(raw):
    assert di._normalise_column_default(raw, column_type="varchar(32)") == raw


# --- Live structural inventory correction ----------------------------------


class _FakeResult:
    def __init__(self, *, rows=(), scalar=None):
        self._rows = list(rows)
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar

    def mappings(self):
        return self


class _FakeConnection:
    def __init__(self):
        self.statements: list[str] = []

    def execute(self, statement):
        sql = str(statement)
        self.statements.append(sql)
        if "drift_inventory:indexes" in sql:
            return _FakeResult(rows=[{
                "schema": "app",
                "table": "users",
                "unique": True,
                "method": "btree",
                "keys": [{
                    "expr": "email",
                    "opclass": None,
                    "collation": None,
                    "sort": "asc",
                    "nulls": "last",
                }],
                "include": [],
                "predicate": None,
            }])
        if "drift_inventory:partitions" in sql:
            return _FakeResult(rows=[{
                "schema": "raw",
                "table": "api_responses",
                "partition_key": "RANGE (fetched_at)",
                "parent_schema": None,
                "parent_table": None,
                "partition_bounds": None,
            }, {
                "schema": "raw",
                "table": "api_responses_2026_07",
                "partition_key": None,
                "parent_schema": "raw",
                "parent_table": "api_responses",
                "partition_bounds": "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')",
            }])
        if "FROM pg_extension" in sql:
            return _FakeResult(rows=[("pg_trgm", "1.6")])
        if "information_schema.tables" in sql:
            return _FakeResult(scalar=True)
        if "public.alembic_version" in sql:
            return _FakeResult(rows=[("001",)])
        raise AssertionError(f"unexpected inventory SQL: {sql}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeEngine:
    def begin(self):
        return _FakeConnection()

    def connect(self):
        return _FakeConnection()

    def dispose(self):
        pass


class _FakeInspector:
    def get_schema_names(self):
        return ["public", "app", "raw"]

    def get_table_names(self, schema=None):
        return {
            "public": ["alembic_version"],
            "app": ["users"],
            "raw": ["api_responses", "api_responses_2026_07"],
        }[schema]

    def get_columns(self, table, schema=None):
        if (schema, table) == ("app", "users"):
            return [{
                "name": "id",
                "type": "UUID",
                "nullable": False,
                "default": "gen_random_uuid()",
                "identity": {"always": False, "start": 1},
                "computed": None,
            }, {
                "name": "email",
                "type": "VARCHAR(255)",
                "nullable": False,
                "default": None,
            }]
        return [{
            "name": "fetched_at",
            "type": "TIMESTAMP WITH TIME ZONE",
            "nullable": False,
            "default": None,
            "computed": {"sqltext": "timezone('utc', now())", "persisted": True},
        }]

    def get_pk_constraint(self, table, schema=None):
        return {"constrained_columns": ["id"] if table == "users" else ["fetched_at"]}

    def get_unique_constraints(self, table, schema=None):
        return [{"column_names": ["email"]}] if table == "users" else []

    def get_foreign_keys(self, table, schema=None):
        if table != "api_responses_2026_07":
            return []
        return [{
            "constrained_columns": ["fetched_at"],
            "referred_schema": "app",
            "referred_table": "users",
            "referred_columns": ["id"],
            "options": {
                "ondelete": "CASCADE",
                "onupdate": "RESTRICT",
                "deferrable": True,
                "initially": "DEFERRED",
            },
        }]

    def get_check_constraints(self, table, schema=None):
        return [{"sqltext": "fetched_at IS NOT NULL"}] if table.startswith("api_responses") else []


def _catalog_index(
    schema: str,
    table: str,
    indexname: str,
    *,
    expr: str,
    unique: bool = False,
    method: str = "btree",
    opclass: str | None = None,
    predicate: str | None = None,
) -> dict:
    return {
        "schema": schema,
        "table": table,
        "indexname": indexname,
        "unique": unique,
        "method": method,
        "keys": [{
            "expr": expr,
            "opclass": opclass,
            "collation": None,
            "sort": "asc",
            "nulls": "last",
        }],
        "include": [],
        "predicate": predicate,
    }


class _PostgresRealisticConnection(_FakeConnection):
    """Emulate the rows PostgreSQL returns before/after semantic SQL filters."""

    def execute(self, statement):
        sql = str(statement)
        if "drift_inventory:indexes" not in sql:
            return super().execute(statement)
        self.statements.append(sql)
        semantic = [
            _catalog_index("app", "users", "ix_users_email", expr="email"),
            _catalog_index(
                "app", "users", "ux_users_external_ref", expr="external_ref", unique=True
            ),
            _catalog_index(
                "app", "users", "ix_users_email_lower", expr="lower((email)::text)"
            ),
            _catalog_index(
                "app", "users", "ix_users_email_pattern", expr="email",
                opclass="text_pattern_ops",
            ),
            _catalog_index(
                "app", "users", "ix_users_active_email", expr="email",
                predicate="is_active",
            ),
            _catalog_index(
                "app", "users", "ix_users_email_trgm", expr="email", method="gin",
                opclass="gin_trgm_ops",
            ),
            _catalog_index(
                "raw", "api_responses", "ix_raw_source_created", expr="source_id"
            ),
        ]
        backing_or_child = [
            _catalog_index("app", "users", "users_pkey", expr="id", unique=True),
            _catalog_index("app", "users", "users_email_key", expr="email", unique=True),
            _catalog_index(
                "raw", "api_responses_2026_07", "api_responses_2026_07_source_id_idx",
                expr="source_id",
            ),
        ]
        has_postgresql_semantic_filters = all(fragment in sql for fragment in (
            "NOT i.indisprimary",
            "con.conindid = i.indexrelid",
            "index_inh.inhrelid = i.indexrelid",
        ))
        return _FakeResult(rows=semantic if has_postgresql_semantic_filters else semantic + backing_or_child)


def _inventory_from_fakes(monkeypatch) -> LiveInventory:
    monkeypatch.setattr(di, "create_engine", lambda *a, **k: _FakeEngine())
    monkeypatch.setattr(di, "inspect", lambda engine: _FakeInspector())
    return di.inventory_target(
        "postgresql+asyncpg://markee_wp3:x@127.0.0.1:5441/markee_wp3_disposable",
        guard=lambda dsn: SimpleNamespace(
            host="127.0.0.1", port=5441, user="markee_wp3", database="markee_wp3_disposable"
        ),
    )


def test_inventory_connection_uses_supplied_connection_only(monkeypatch):
    connection = _FakeConnection()
    inspected: list[object] = []
    monkeypatch.setattr(
        di,
        "create_engine",
        lambda *args, **kwargs: pytest.fail("inventory_connection must not create an engine"),
    )
    monkeypatch.setattr(
        di,
        "inspect",
        lambda candidate: inspected.append(candidate) or _FakeInspector(),
    )

    live = di.inventory_connection(connection, target="supplied transaction")

    assert inspected == [connection]
    assert live.target == "supplied transaction"
    assert len(connection.statements) == 5
    assert all(isinstance(statement, str) for statement in connection.statements)


def test_catalog_index_query_uses_postgresql_semantic_index_filters(monkeypatch):
    connection = _PostgresRealisticConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _FakeInspector())

    di.inventory_connection(connection, target="postgresql catalog fixture")

    sql = next(statement for statement in connection.statements if "drift_inventory:indexes" in statement)
    assert "NOT i.indisprimary" in sql
    assert "NOT EXISTS" in sql
    assert "FROM pg_constraint AS con" in sql
    assert "con.conindid = i.indexrelid" in sql
    assert "FROM pg_inherits AS index_inh" in sql
    assert "index_inh.inhrelid = i.indexrelid" in sql
    assert "index_inh.inhparent" not in sql


def test_catalog_index_query_casts_bigint_ordinality_without_changing_index_semantics():
    connection = _FakeConnection()

    di._catalog_indexes(connection)

    sql = " ".join(connection.statements[0].split())
    rendered_key = "pg_get_indexdef(i.indexrelid, key.ordinality::integer, true)"
    assert sql.count(rendered_key) == 2
    assert (
        "jsonb_agg(jsonb_build_object( "
        f"'expr', {rendered_key}, "
        "'opclass', CASE WHEN opc.opcdefault THEN NULL ELSE opc.opcname END, "
        "'collation', CASE WHEN coll.oid = 0 THEN NULL ELSE coll.collname END, "
        "'collation_inherited', COALESCE(att.attcollation = coll.oid, false), "
        "'sort', CASE WHEN (key.option & 1) = 1 THEN 'desc' ELSE 'asc' END, "
        "'nulls', CASE WHEN (key.option & 2) = 2 THEN 'first' ELSE 'last' END "
        ") ORDER BY key.ordinality) "
        "FILTER (WHERE key.ordinality <= i.indnkeyatts) AS keys"
    ) in sql
    assert (
        f"array_agg({rendered_key} ORDER BY key.ordinality) "
        "FILTER (WHERE key.ordinality > i.indnkeyatts) AS include"
    ) in sql


def test_inventory_excludes_backing_and_child_indexes_without_losing_semantics(monkeypatch):
    connection = _PostgresRealisticConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _FakeInspector())

    live = di.inventory_connection(connection, target="postgresql catalog fixture")

    names = {name for _schema, _table, name in live.indexes}
    assert names == {
        "ix_users_email",
        "ux_users_external_ref",
        "ix_users_email_lower",
        "ix_users_email_pattern",
        "ix_users_active_email",
        "ix_users_email_trgm",
        "ix_raw_source_created",
    }
    assert names.isdisjoint({
        "users_pkey",
        "users_email_key",
        "api_responses_2026_07_source_id_idx",
    })
    tables = {
        (table["schema"], table["name"]): table for table in live.structure["tables"]
    }
    users = tables[("app", "users")]
    assert users["primary_key"] == ["id"]
    assert users["unique"] == [["email"]]
    assert users["indexes"] == [
        {
            "unique": False,
            "method": "btree",
            "keys": [{
                "expr": "email", "opclass": None, "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": None,
        },
        {
            "unique": True,
            "method": "btree",
            "keys": [{
                "expr": "external_ref", "opclass": None, "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": None,
        },
        {
            "unique": False,
            "method": "btree",
            "keys": [{
                "expr": "lower((email)::text)", "opclass": None, "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": None,
        },
        {
            "unique": False,
            "method": "btree",
            "keys": [{
                "expr": "email", "opclass": "text_pattern_ops", "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": None,
        },
        {
            "unique": False,
            "method": "btree",
            "keys": [{
                "expr": "email", "opclass": None, "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": "is_active",
        },
        {
            "unique": False,
            "method": "gin",
            "keys": [{
                "expr": "email", "opclass": "gin_trgm_ops", "collation": None,
                "sort": "asc", "nulls": "last",
            }],
            "include": [],
            "predicate": None,
        },
    ]
    assert len(users["primary_key"]) + len(users["unique"]) == 2
    assert tables[("raw", "api_responses")]["indexes"] != []
    assert tables[("raw", "api_responses_2026_07")]["indexes"] == []


def test_inventory_target_delegates_to_inventory_connection(monkeypatch):
    calls: list[object] = []
    connection = _FakeConnection()

    class _ConnectionContext:
        def __enter__(self):
            calls.append("enter")
            return connection

        def __exit__(self, *exc):
            calls.append("exit")
            return False

    class _Engine:
        def connect(self):
            calls.append("connect")
            return _ConnectionContext()

        def dispose(self):
            calls.append("dispose")

    def fake_guard(dsn):
        calls.append("guard")
        return SimpleNamespace(
            host="127.0.0.1", port=5441, user="markee_wp3", database="markee_wp3_disposable"
        )

    monkeypatch.setattr(di, "create_engine", lambda *args, **kwargs: calls.append("engine") or _Engine())
    monkeypatch.setattr(
        di,
        "inventory_connection",
        lambda candidate, *, target: (
            calls.append(("inventory_connection", candidate, target))
            or (_ for _ in ()).throw(RuntimeError("inventory failed"))
        ),
        raising=False,
    )

    with pytest.raises(RuntimeError, match="inventory failed"):
        di.inventory_target("postgresql://example", guard=fake_guard)

    assert calls == [
        "guard",
        "engine",
        "connect",
        "enter",
        (
            "inventory_connection",
            connection,
            "127.0.0.1:5441/markee_wp3_disposable as markee_wp3",
        ),
        "exit",
        "dispose",
    ]


def test_inventory_connection_preserves_normalized_structure(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _FakeInspector())
    target = "127.0.0.1:5441/markee_wp3_disposable as markee_wp3"

    live = di.inventory_connection(connection, target=target)
    target_live = _inventory_from_fakes(monkeypatch)

    assert isinstance(live, LiveInventory)
    assert live == target_live
    assert live.schemas == ("app", "public", "raw")
    assert live.tables == (
        ("app", "users"),
        ("public", "alembic_version"),
        ("raw", "api_responses"),
        ("raw", "api_responses_2026_07"),
    )
    assert live.indexes == (("app", "users", ""),)
    assert live.extensions == (("pg_trgm", "1.6"),)
    assert live.alembic_version == "001"
    assert live.fingerprint == di.catalog_fingerprint(
        live.schemas, live.tables, live.indexes, live.extensions, live.alembic_version
    )
    assert live.structural_fingerprint == di.structural_fingerprint(live.structure)


def test_inventory_target_attaches_complete_live_structural_fingerprint(monkeypatch):
    live = _inventory_from_fakes(monkeypatch)
    assert live.structural_fingerprint == di.structural_fingerprint(live.structure)
    assert live.to_dict()["structural_fingerprint"] == live.structural_fingerprint
    users = next(t for t in live.structure["tables"] if (t["schema"], t["name"]) == ("app", "users"))
    child = next(
        t for t in live.structure["tables"]
        if (t["schema"], t["name"]) == ("raw", "api_responses_2026_07")
    )
    assert users["columns"][0]["identity"] == {"always": False, "start": 1}
    assert users["indexes"][0]["method"] == "btree"
    assert child["columns"][0]["generated"]["persisted"] is True
    assert child["foreign_keys"][0]["ondelete"] == "CASCADE"
    assert child["foreign_keys"][0]["initially"] == "DEFERRED"
    assert child["parent_schema"] == "raw"
    assert child["parent_table"] == "api_responses"
    assert child["partition_bounds"].startswith("FOR VALUES FROM")
    assert live.structure["extensions"] == ["pg_trgm"]


def test_required_extension_name_affects_structural_fingerprint():
    with_extension = _structure()
    with_extension["extensions"] = ["pg_trgm"]
    without_extension = _structure()
    without_extension["extensions"] = []
    assert di.structural_fingerprint(with_extension) != di.structural_fingerprint(without_extension)


def test_fk_actions_and_deferrability_affect_structural_fingerprint():
    base = _structure()
    base["tables"][1]["foreign_keys"][0].update({
        "ondelete": "CASCADE", "onupdate": "RESTRICT", "deferrable": True, "initially": "DEFERRED"
    })
    for field, value in (
        ("ondelete", "SET NULL"),
        ("onupdate", "CASCADE"),
        ("deferrable", False),
        ("initially", "IMMEDIATE"),
    ):
        changed = _structure()
        changed["tables"][1]["foreign_keys"][0].update(
            {"ondelete": "CASCADE", "onupdate": "RESTRICT", "deferrable": True, "initially": "DEFERRED"}
        )
        changed["tables"][1]["foreign_keys"][0][field] = value
        assert di.structural_fingerprint(base) != di.structural_fingerprint(changed), field


def test_identity_and_generated_semantics_affect_column_signature():
    base = _structure()
    base["tables"][0]["columns"][0]["identity"] = {"always": False, "start": 1}
    base["tables"][0]["columns"][1]["generated"] = {"sqltext": "lower(email)", "persisted": True}
    changed_identity = _structure()
    changed_identity["tables"][0]["columns"][0]["identity"] = {"always": True, "start": 1}
    changed_identity["tables"][0]["columns"][1]["generated"] = {"sqltext": "lower(email)", "persisted": True}
    changed_generated = _structure()
    changed_generated["tables"][0]["columns"][0]["identity"] = {"always": False, "start": 1}
    changed_generated["tables"][0]["columns"][1]["generated"] = {"sqltext": "upper(email)", "persisted": True}
    assert di.structural_fingerprint(base) != di.structural_fingerprint(changed_identity)
    assert di.structural_fingerprint(base) != di.structural_fingerprint(changed_generated)


def test_partition_parent_relation_key_and_bounds_affect_signature():
    base = _structure()
    child = base["tables"][2]
    child.update({"parent_schema": "raw", "parent_table": "api_responses"})
    for field, value in (
        ("parent_schema", "public"),
        ("parent_table", "other_parent"),
        ("partition_key", "HASH (fetched_at)"),
        ("partition_bounds", "FOR VALUES FROM ('2026-02-01') TO ('2026-03-01')"),
    ):
        changed = _structure()
        changed["tables"][2].update({"parent_schema": "raw", "parent_table": "api_responses"})
        changed["tables"][2][field] = value
        assert di.structural_fingerprint(base) != di.structural_fingerprint(changed), field


def test_unique_constraint_and_equivalent_unique_btree_index_normalise_equally():
    constrained = _structure()
    constrained["tables"][0]["indexes"] = []
    indexed = _structure()
    indexed["tables"][0]["unique"] = []
    assert di.structural_fingerprint(constrained) == di.structural_fingerprint(indexed)


# --- Cycle B, category 1: implicit index collation --------------------------
#
# Evidence (/tmp/markee-wp3-canonical-diff.json): 13 index_required_missing /
# index_unexpected pairs whose only delta is one direct-column key reported by
# the catalog with collation "default" where the contract says null. The
# catalog query must carry whether the key collation is merely inherited from
# the column, and only that inherited "default" may be nulled.


def _semantic_key(
    expr: str,
    *,
    opclass: str | None = None,
    collation: str | None = None,
    inherited: bool | None = None,
) -> dict:
    key = {
        "expr": expr,
        "opclass": opclass,
        "collation": collation,
        "sort": "asc",
        "nulls": "last",
    }
    if inherited is not None:
        key["collation_inherited"] = inherited
    return key


def _semantic_index(keys: list[dict], *, method: str = "btree") -> dict:
    return {
        "unique": False,
        "method": method,
        "keys": keys,
        "include": [],
        "predicate": None,
    }


# The 13 real pairs: (object, method, [(expr, opclass, catalog collation)]).
# Catalog collation "default" is inherited from the column in every case.
_EVIDENCE_COLLATION_PAIRS = [
    ("app.deadlines", "btree", [("due_date", None, None), ("status", None, "default")]),
    ("app.prospection_opportunities", "btree", [("opportunity_type", None, "default"), ("score", None, None)]),
    ("app.review_queue", "btree", [("status", None, "default"), ("created_at", None, None)]),
    ("core.documents", "btree", [("file_hash", None, "default")]),
    ("core.holders", "gin", [("name", "gin_trgm_ops", "default")]),
    ("core.holders", "btree", [("source_id", None, "default")]),
    ("core.representatives", "gin", [("name", "gin_trgm_ops", "default")]),
    ("core.representatives", "btree", [("source_id", None, "default")]),
    ("core.source_runs", "btree", [("status", None, "default")]),
    ("core.trademarks", "btree", [("jurisdiction", None, "default")]),
    ("core.trademarks", "gin", [("word_mark", "gin_trgm_ops", "default")]),
    ("events.lifecycle_events", "btree", [("event_type", None, "default")]),
    ("events.lifecycle_events", "btree", [("trademark_id", None, None), ("event_type", None, "default")]),
]


def _evidence_pair(spec) -> tuple[dict, dict]:
    """Return (catalog form with inheritance flags, contract form) for a pair."""
    _object, method, keys = spec
    catalog = _semantic_index(
        [
            _semantic_key(
                expr,
                opclass=opclass,
                collation=collation,
                inherited=collation == "default",
            )
            for expr, opclass, collation in keys
        ],
        method=method,
    )
    contract = _semantic_index(
        [_semantic_key(expr, opclass=opclass) for expr, opclass, _collation in keys],
        method=method,
    )
    return catalog, contract


@pytest.mark.parametrize(
    "spec",
    _EVIDENCE_COLLATION_PAIRS,
    ids=[f"{obj}:{'+'.join(e for e, _o, _c in keys)}" for obj, _m, keys in _EVIDENCE_COLLATION_PAIRS],
)
def test_index_collation_evidence_pairs_normalise_to_contract_keys(spec):
    """Each real pair is one semantic index once the inherited default is nulled."""
    catalog, contract = _evidence_pair(spec)
    assert [di._normalise_index_key(key) for key in catalog["keys"]] == contract["keys"]


@pytest.mark.parametrize(
    "spec",
    _EVIDENCE_COLLATION_PAIRS,
    ids=[f"{obj}:{'+'.join(e for e, _o, _c in keys)}" for obj, _m, keys in _EVIDENCE_COLLATION_PAIRS],
)
def test_index_collation_evidence_pairs_share_one_signature(spec):
    catalog, contract = _evidence_pair(spec)
    assert di.index_signature(catalog) == di.index_signature(contract)


def test_index_key_normalisation_strips_helper_flag_only():
    """The helper flag never leaks into the semantic key shape."""
    normalised = di._normalise_index_key(
        _semantic_key("status", collation="default", inherited=True)
    )
    assert set(normalised) == {"expr", "opclass", "collation", "sort", "nulls"}
    assert normalised["collation"] is None


@pytest.mark.parametrize(
    ("key", "expected_collation"),
    [
        pytest.param(
            _semantic_key("lower((name)::text)", collation="default", inherited=False),
            "default",
            id="expression-key-keeps-default",
        ),
        pytest.param(
            _semantic_key("status", collation="default"),
            "default",
            id="missing-inheritance-flag-is-conservative",
        ),
        pytest.param(
            _semantic_key("status", collation="C", inherited=True),
            "C",
            id="non-default-collation-survives-even-if-inherited",
        ),
        pytest.param(
            _semantic_key("status", collation="pt-PT-x-icu", inherited=False),
            "pt-PT-x-icu",
            id="explicit-custom-collation-survives",
        ),
        pytest.param(
            _semantic_key("due_date", collation=None, inherited=False),
            None,
            id="uncollatable-key-stays-null",
        ),
    ],
)
def test_index_key_normalisation_preserves_meaningful_collations(key, expected_collation):
    assert di._normalise_index_key(key)["collation"] == expected_collation


def test_index_signature_still_distinguishes_meaningful_collations():
    base = di.index_signature(_semantic_index([_semantic_key("status")]))
    explicit_c = di.index_signature(
        _semantic_index([_semantic_key("status", collation="C", inherited=False)])
    )
    unproven_default = di.index_signature(
        _semantic_index([_semantic_key("lower((status)::text)", collation="default", inherited=False)])
    )
    assert explicit_c != base
    assert unproven_default != di.index_signature(
        _semantic_index([_semantic_key("lower((status)::text)")])
    )


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("unique", True),
        ("method", "hash"),
        ("include", ["created_at"]),
        ("predicate", "is_active"),
    ],
)
def test_index_signature_stays_sensitive_outside_collation(mutation, value):
    catalog, contract = _evidence_pair(_EVIDENCE_COLLATION_PAIRS[0])
    mutated = dict(catalog)
    mutated[mutation] = value
    assert di.index_signature(mutated) != di.index_signature(contract)


@pytest.mark.parametrize(("field", "value"), [("sort", "desc"), ("nulls", "first"), ("opclass", "text_pattern_ops")])
def test_index_signature_stays_sensitive_to_key_options(field, value):
    catalog, contract = _evidence_pair(_EVIDENCE_COLLATION_PAIRS[0])
    mutated_key = dict(catalog["keys"][1])
    mutated_key[field] = value
    mutated = _semantic_index([catalog["keys"][0], mutated_key])
    assert di.index_signature(mutated) != di.index_signature(contract)


def test_structural_fingerprint_uses_index_key_normalisation():
    catalog, contract = _evidence_pair(_EVIDENCE_COLLATION_PAIRS[0])
    with_catalog_key = _structure()
    with_catalog_key["tables"][0]["indexes"] = [catalog]
    with_contract_key = _structure()
    with_contract_key["tables"][0]["indexes"] = [contract]
    assert di.structural_fingerprint(with_catalog_key) == di.structural_fingerprint(with_contract_key)
    with_explicit_c = _structure()
    with_explicit_c["tables"][0]["indexes"] = [
        _semantic_index([_semantic_key("due_date"), _semantic_key("status", collation="C", inherited=False)])
    ]
    assert di.structural_fingerprint(with_explicit_c) != di.structural_fingerprint(with_contract_key)


def test_catalog_index_query_carries_column_collation_inheritance():
    connection = _FakeConnection()

    di._catalog_indexes(connection)

    sql = " ".join(connection.statements[0].split())
    assert "LEFT JOIN pg_attribute AS att" in sql
    assert "att.attrelid = i.indrelid" in sql
    assert "att.attnum = i.indkey[key.ordinality::integer - 1]" in sql
    assert "'collation_inherited', COALESCE(att.attcollation = coll.oid, false)" in sql


class _CollationAwareConnection(_FakeConnection):
    """Emulate catalog rows for the inheritance-aware index query.

    Older query shapes (no pg_attribute join) can only report the collation
    name, so they get keys with a bare "default"; the inheritance-aware query
    also reports whether the key collation is inherited from the column.
    """

    def execute(self, statement):
        sql = str(statement)
        if "drift_inventory:indexes" not in sql:
            return super().execute(statement)
        self.statements.append(sql)
        aware = "collation_inherited" in sql and "pg_attribute" in sql
        keys = [
            {
                "expr": "due_date", "opclass": None, "collation": None,
                "sort": "asc", "nulls": "last",
                **({"collation_inherited": False} if aware else {}),
            },
            {
                "expr": "status", "opclass": None, "collation": "default",
                "sort": "asc", "nulls": "last",
                **({"collation_inherited": True} if aware else {}),
            },
            {
                "expr": "lower((notes)::text)", "opclass": None, "collation": "default",
                "sort": "asc", "nulls": "last",
                **({"collation_inherited": False} if aware else {}),
            },
            {
                "expr": "status", "opclass": None, "collation": "C",
                "sort": "asc", "nulls": "last",
                **({"collation_inherited": False} if aware else {}),
            },
        ]
        return _FakeResult(rows=[{
            "schema": "app",
            "table": "users",
            "indexname": "ix_users_mixed_collations",
            "unique": False,
            "method": "btree",
            "keys": keys,
            "include": [],
            "predicate": None,
        }])


def test_inventory_nulls_only_inherited_default_collation(monkeypatch):
    connection = _CollationAwareConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _FakeInspector())

    live = di.inventory_connection(connection, target="collation fixture")

    users = next(
        table for table in live.structure["tables"]
        if (table["schema"], table["name"]) == ("app", "users")
    )
    keys = users["indexes"][0]["keys"]
    assert [key["collation"] for key in keys] == [None, None, "default", "C"]
    assert all(set(key) == {"expr", "opclass", "collation", "sort", "nulls"} for key in keys)


# --- Cycle B, category 2: CHECK IN-set canonicalisation ----------------------
#
# Evidence: exactly two check_mismatch rows where PostgreSQL rewrote the
# migrations' ``col IN (...)`` into ``col::text = ANY (ARRAY[...]::text[])``.
# Only that structural pair (IN_SET of string literals over one identifier,
# with the varchar→text casts PostgreSQL itself adds) may canonicalise.

_EVIDENCE_CHECK_PAIRS = [
    pytest.param(
        "type::text = ANY (ARRAY['natural'::character varying, "
        "'legal'::character varying]::text[])",
        "type IN ('natural', 'legal')",
        id="core.holders",
    ),
    pytest.param(
        "type::text = ANY (ARRAY['natural'::character varying, "
        "'legal'::character varying, 'association'::character varying]::text[])",
        "type IN ('natural', 'legal', 'association')",
        id="core.representatives",
    ),
]


@pytest.mark.parametrize(("catalog_form", "contract_form"), _EVIDENCE_CHECK_PAIRS)
def test_check_canonicaliser_reduces_postgresql_in_expansion(catalog_form, contract_form):
    assert di._normalise_check(catalog_form) == contract_form


@pytest.mark.parametrize(("_catalog_form", "contract_form"), _EVIDENCE_CHECK_PAIRS)
def test_check_canonicaliser_is_idempotent_on_contract_form(_catalog_form, contract_form):
    assert di._normalise_check(contract_form) == contract_form


@pytest.mark.parametrize(
    "check",
    [
        pytest.param(
            "NOT (type::text = ANY (ARRAY['natural'::character varying]::text[]))",
            id="negated-membership",
        ),
        pytest.param(
            "type::text <> ALL (ARRAY['natural'::character varying]::text[])",
            id="different-operator",
        ),
        pytest.param(
            "type::holder_kind = ANY (ARRAY['natural'::character varying]::text[])",
            id="unauthorised-identifier-cast",
        ),
        pytest.param(
            "type::text = ANY (ARRAY['natural'::holder_kind]::text[])",
            id="unauthorised-element-cast",
        ),
        pytest.param(
            "type::text = ANY (ARRAY['natural'::character varying]::holder_kind[])",
            id="unauthorised-array-cast",
        ),
        pytest.param(
            "code::text = ANY (ARRAY[1, 2]::text[])",
            id="non-textual-literal",
        ),
        pytest.param(
            "type::text = ANY (ARRAY['natural'::character varying]::text[]) "
            "AND char_length(type::text) > 2",
            id="extra-conjunction",
        ),
        pytest.param("char_length(email) > 3", id="unrelated-check"),
        pytest.param(
            "lower(type)::text = ANY (ARRAY['natural'::character varying]::text[])",
            id="expression-not-identifier",
        ),
    ],
)
def test_check_canonicaliser_passes_through_everything_else(check):
    assert di._normalise_check(check) == check


def test_check_canonicaliser_keeps_none():
    assert di._normalise_check(None) is None


@pytest.mark.parametrize(
    ("catalog_form", "contract_form"),
    [
        pytest.param(
            "type::text = ANY (ARRAY['natural'::character varying]::text[])",
            "type IN ('natural', 'legal')",
            id="member-removed",
        ),
        pytest.param(
            "type::text = ANY (ARRAY['natural'::character varying, "
            "'legal'::character varying, 'estate'::character varying]::text[])",
            "type IN ('natural', 'legal')",
            id="member-added",
        ),
        pytest.param(
            "type::text = ANY (ARRAY['natural'::character varying, "
            "'juridical'::character varying]::text[])",
            "type IN ('natural', 'legal')",
            id="member-changed",
        ),
        pytest.param(
            "status::text = ANY (ARRAY['natural'::character varying, "
            "'legal'::character varying]::text[])",
            "type IN ('natural', 'legal')",
            id="different-column",
        ),
    ],
)
def test_check_canonicaliser_never_hides_material_set_drift(catalog_form, contract_form):
    assert di._normalise_check(catalog_form) != di._normalise_check(contract_form)


def test_live_table_structure_canonicalises_checks(monkeypatch):
    class _CheckInspector(_FakeInspector):
        def get_check_constraints(self, table, schema=None):
            if (schema, table) != ("app", "users"):
                return []
            return [
                {
                    "sqltext": "type::text = ANY (ARRAY['natural'::character varying,\n"
                               "  'legal'::character varying]::text[])",
                },
                {"sqltext": "char_length(email) > 3"},
            ]

    connection = _FakeConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _CheckInspector())

    live = di.inventory_connection(connection, target="check fixture")

    users = next(
        table for table in live.structure["tables"]
        if (table["schema"], table["name"]) == ("app", "users")
    )
    assert users["checks"] == ["type IN ('natural', 'legal')", "char_length(email) > 3"]


def test_structural_fingerprint_uses_check_canonicalisation():
    catalog_side = _structure()
    catalog_side["tables"][0]["checks"] = [
        "type::text = ANY (ARRAY['natural'::character varying, "
        "'legal'::character varying]::text[])"
    ]
    contract_side = _structure()
    contract_side["tables"][0]["checks"] = ["type IN ('natural', 'legal')"]
    assert di.structural_fingerprint(catalog_side) == di.structural_fingerprint(contract_side)
    drifted = _structure()
    drifted["tables"][0]["checks"] = [
        "type::text = ANY (ARRAY['natural'::character varying]::text[])"
    ]
    assert di.structural_fingerprint(drifted) != di.structural_fingerprint(contract_side)


# --- Cycle B, category 3: partition bound midnight-UTC reduction ------------
#
# Evidence: exactly two partition_bounds_mismatch rows where the migrations
# wrote plain dates and the catalog renders the same instants as midnight-UTC
# timestamps. Only a valid ISO date at exactly 00:00:00 with an explicit +00
# offset may reduce to the date; everything else keeps its rendering.

_EVIDENCE_BOUNDS_PAIRS = [
    pytest.param(
        "FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00')",
        "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')",
        id="raw.api_responses_2026_07",
    ),
    pytest.param(
        "FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00')",
        "FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')",
        id="raw.api_responses_2026_08",
    ),
]


@pytest.mark.parametrize(("catalog_form", "contract_form"), _EVIDENCE_BOUNDS_PAIRS)
def test_partition_bounds_reduce_midnight_utc_to_contract_dates(catalog_form, contract_form):
    assert di._normalise_partition_bounds(catalog_form) == contract_form


@pytest.mark.parametrize(("_catalog_form", "contract_form"), _EVIDENCE_BOUNDS_PAIRS)
def test_partition_bounds_reduction_is_idempotent_on_contract_form(_catalog_form, contract_form):
    assert di._normalise_partition_bounds(contract_form) == contract_form


def test_partition_bounds_reduction_keeps_none():
    assert di._normalise_partition_bounds(None) is None


@pytest.mark.parametrize(
    "bounds",
    [
        pytest.param(
            "FOR VALUES FROM ('2026-07-01 00:30:00+00') TO ('2026-08-01 00:30:00+00')",
            id="non-midnight-time",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-07-01 00:00:00+01') TO ('2026-08-01 00:00:00+01')",
            id="non-utc-offset",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-07-01 00:00:00') TO ('2026-08-01 00:00:00')",
            id="offset-missing-not-provably-utc",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-07-01 00:00:00.000001+00') TO ('2026-08-01 00:00:00.000001+00')",
            id="fractional-second",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-13-01 00:00:00+00') TO ('2026-14-01 00:00:00+00')",
            id="invalid-iso-date",
        ),
        pytest.param(
            "FOR VALUES FROM (MINVALUE) TO (MAXVALUE)",
            id="open-range-sentinels",
        ),
        pytest.param(
            "FOR VALUES IN ('2026-07-01 00:00:00+00')",
            id="list-partition-form",
        ),
        pytest.param(
            "FOR VALUES WITH (modulus 4, remainder 1)",
            id="hash-partition-form",
        ),
    ],
)
def test_partition_bounds_reduction_passes_through_everything_else(bounds):
    assert di._normalise_partition_bounds(bounds) == bounds


@pytest.mark.parametrize(
    "lower_literal",
    [
        pytest.param("'2026-07-01 00:30:00+00'", id="non-midnight-time"),
        pytest.param("'2026-07-01 00:00:00+01'", id="non-utc-offset"),
        pytest.param("'2026-07-01 00:00:00.000001+00'", id="fractional-second"),
    ],
)
def test_partition_bounds_mixed_reduction_keeps_material_literal_verbatim(lower_literal):
    """A non-qualifying instant survives verbatim even next to a reducible one."""
    reduced = di._normalise_partition_bounds(
        f"FOR VALUES FROM ({lower_literal}) TO ('2026-08-01 00:00:00+00')"
    )
    assert reduced == f"FOR VALUES FROM ({lower_literal}) TO ('2026-08-01')"
    assert reduced != "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')"


def test_partition_bounds_reduction_is_per_value_and_keeps_sentinels():
    """A reducible instant next to MINVALUE/MAXVALUE reduces alone."""
    assert di._normalise_partition_bounds(
        "FOR VALUES FROM (MINVALUE) TO ('2026-08-01 00:00:00+00')"
    ) == "FOR VALUES FROM (MINVALUE) TO ('2026-08-01')"


def test_partition_bounds_reduction_preserves_from_to_order():
    """The FROM/TO structure (bound inclusivity) is never rearranged."""
    reduced = di._normalise_partition_bounds(
        "FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-07-01 00:00:00+00')"
    )
    assert reduced == "FOR VALUES FROM ('2026-08-01') TO ('2026-07-01')"


@pytest.mark.parametrize(
    ("catalog_form", "contract_form"),
    [
        pytest.param(
            "FOR VALUES FROM ('2026-07-02 00:00:00+00') TO ('2026-08-01 00:00:00+00')",
            "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')",
            id="different-day",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-06-01 00:00:00+00') TO ('2026-08-01 00:00:00+00')",
            "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')",
            id="different-month",
        ),
        pytest.param(
            "FOR VALUES FROM ('2026-07-01 12:00:00+00') TO ('2026-08-01 00:00:00+00')",
            "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')",
            id="different-instant-same-day",
        ),
    ],
)
def test_partition_bounds_reduction_never_hides_material_drift(catalog_form, contract_form):
    assert di._normalise_partition_bounds(catalog_form) != di._normalise_partition_bounds(contract_form)


def test_live_table_structure_canonicalises_partition_bounds(monkeypatch):
    class _MidnightUtcConnection(_FakeConnection):
        def execute(self, statement):
            sql = str(statement)
            if "drift_inventory:partitions" not in sql:
                return super().execute(statement)
            self.statements.append(sql)
            return _FakeResult(rows=[{
                "schema": "raw",
                "table": "api_responses",
                "partition_key": "RANGE (fetched_at)",
                "parent_schema": None,
                "parent_table": None,
                "partition_bounds": None,
            }, {
                "schema": "raw",
                "table": "api_responses_2026_07",
                "partition_key": None,
                "parent_schema": "raw",
                "parent_table": "api_responses",
                "partition_bounds": "FOR VALUES FROM ('2026-07-01 00:00:00+00') "
                                    "TO ('2026-08-01 00:00:00+00')",
            }])

    connection = _MidnightUtcConnection()
    monkeypatch.setattr(di, "inspect", lambda candidate: _FakeInspector())

    live = di.inventory_connection(connection, target="partition fixture")

    child = next(
        table for table in live.structure["tables"]
        if (table["schema"], table["name"]) == ("raw", "api_responses_2026_07")
    )
    assert child["partition_bounds"] == "FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')"
    assert child["parent_schema"] == "raw"
    assert child["parent_table"] == "api_responses"


def test_structural_fingerprint_uses_partition_bound_reduction():
    catalog_side = _structure()
    catalog_side["tables"][2]["partition_bounds"] = (
        "FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-02-01 00:00:00+00')"
    )
    contract_side = _structure()
    assert di.structural_fingerprint(catalog_side) == di.structural_fingerprint(contract_side)
    drifted = _structure()
    drifted["tables"][2]["partition_bounds"] = (
        "FOR VALUES FROM ('2026-01-01 06:00:00+00') TO ('2026-02-01 00:00:00+00')"
    )
    assert di.structural_fingerprint(drifted) != di.structural_fingerprint(contract_side)


# --- Smoke: importable, no globals, no DSN baked in -------------------------


def test_drift_inventory_has_no_baked_dsn():
    """The module must not embed any DSN in its source."""
    src = Path(di.__file__).read_text(encoding="utf-8")
    for needle in (
        "postgresql+asyncpg://markee:",
        "postgresql://markee:",
        "markee_dev",
        "markee_wp3_local_only",
    ):
        assert needle not in src, f"baked credential {needle!r} in drift_inventory"
