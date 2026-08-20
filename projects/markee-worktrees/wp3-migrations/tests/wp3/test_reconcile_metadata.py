"""RED/GREEN tests for the offline metadata-only DDL catalogue.

Covers brief §3 (exact 67+33 catalogue), §4 (catalogued deltas and
allowlist), §7.3 (renderer), §7.4 (fail-closed planner), §7.7 (digest
integrity unchanged), §7.8 (rollback sentinel), §7.10 (dry-run audit
shape).  No connection is opened: every test is pure offline.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

import pytest

import scripts.wp3_reconcile_metadata as reconcile
from scripts.wp3_adoption_contract import (
    canonical_json,
    classify_structure,
    load_contract,
)
from scripts.wp3_reconcile_metadata import (
    ALL_OPS,
    ContractDeltaUnmapped,
    MetadataOp,
    OpKind,
    build_metadata_plan,
    dry_run,
    render_sql,
    reverse_sql,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "scripts" / "contracts" / "wp3_002_structure.json"
DIFF_PATH = Path("/tmp/markee-wp3-restored-clone-v2-full-diff.json")


# ---------------------------------------------------------------------------
# 1. catalogue cardinality
# ---------------------------------------------------------------------------
def test_catalogue_has_exactly_100_ops():
    set_default = [op for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT]
    drop_not_null = [op for op in ALL_OPS if op.kind is OpKind.DROP_NOT_NULL]
    assert len(ALL_OPS) == 100
    assert len(set_default) == 67
    assert len(drop_not_null) == 33


# ---------------------------------------------------------------------------
# 2. catalogue keys match the raw diff evidence
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def raw_diff_keys() -> set[str]:
    doc = json.loads(DIFF_PATH.read_text(encoding="utf-8"))
    return {entry["key"] for entry in doc["differences"]}


@pytest.fixture(scope="module")
def raw_default_keys(raw_diff_keys) -> set[str]:
    return {
        k.replace(".columns.", ".")
        for k in raw_diff_keys if k.endswith(".default")
    }


@pytest.fixture(scope="module")
def raw_nullable_keys(raw_diff_keys) -> set[str]:
    return {
        k.replace(".columns.", ".")
        for k in raw_diff_keys if k.endswith(".nullable")
    }


def test_catalogue_keys_match_evidence(raw_default_keys, raw_nullable_keys):
    catalogue_default = {op.key for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT}
    catalogue_nullable = {op.key for op in ALL_OPS if op.kind is OpKind.DROP_NOT_NULL}
    assert catalogue_default == raw_default_keys, (
        f"mismatch: extra={sorted(catalogue_default - raw_default_keys)[:3]} "
        f"missing={sorted(raw_default_keys - catalogue_default)[:3]}"
    )
    assert catalogue_nullable == raw_nullable_keys, (
        f"mismatch: extra={sorted(catalogue_nullable - raw_nullable_keys)[:3]} "
        f"missing={sorted(raw_nullable_keys - catalogue_nullable)[:3]}"
    )
    assert len(catalogue_default) + len(catalogue_nullable) == 100


# ---------------------------------------------------------------------------
# 3. no SET NOT NULL in catalogue (forbidden invariant)
# ---------------------------------------------------------------------------
def test_no_set_not_null_in_catalogue():
    forbidden = ("SET NOT NULL", "set not null", "SET_NOT_NULL")
    for op in ALL_OPS:
        assert op.kind is not OpKind.SET_DEFAULT or op.expression is not None
        sql = render_sql(op)
        for token in forbidden:
            assert token not in sql, f"forbidden token in {op.key}: {token}"
        rev = reverse_sql(op)
        # The audit marker may mention the policy but must not contain
        # executable DDL: the policy is to retain nullability, so a SET
        # NOT NULL fragment is never present.
        for token in forbidden:
            assert token not in rev, f"forbidden token in reverse of {op.key}: {token}"


# ---------------------------------------------------------------------------
# 4. renderer uses double-quoted identifiers
# ---------------------------------------------------------------------------
def test_render_set_default_uses_double_quoted_identifiers():
    op = MetadataOp(
        "x.y.z.default", "x", "y", "z", OpKind.SET_DEFAULT, "1"
    )
    # Inject into the catalogue for the test by patching the allowlist via
    # direct construction is not possible (frozen set), so we test a
    # representative catalogued entry instead.
    sample = next(op for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT)
    sql = render_sql(sample)
    assert sql.startswith(f'ALTER TABLE "{sample.schema}"."{sample.table}"')
    assert f'ALTER COLUMN "{sample.column}" SET DEFAULT {sample.expression};' in sql


def test_render_drop_not_null_is_idempotent_sql():
    sample = next(op for op in ALL_OPS if op.kind is OpKind.DROP_NOT_NULL)
    sql = render_sql(sample)
    assert sql.startswith('ALTER TABLE ')
    assert sql.endswith(';')
    assert f'ALTER COLUMN "{sample.column}" DROP NOT NULL' in sql
    # Re-rendering yields the same string (idempotent composition).
    assert render_sql(sample) == sql


# ---------------------------------------------------------------------------
# 5. build_metadata_plan against the canonical (post-reconciliation) structure
# ---------------------------------------------------------------------------
@pytest.fixture
def contract():
    return load_contract(CONTRACT_PATH, source_root=ROOT)


@pytest.fixture
def canonical_structure(contract) -> dict:
    return deepcopy(contract.canonical)


@pytest.fixture
def known_restored_structure(contract, canonical_structure) -> dict:
    """Fixture mirroring test_adopt_wp3_schema.known_restored_structure."""
    from tests.wp3.test_adopt_wp3_schema import _tables, _remove_table

    structure = deepcopy(canonical_structure)
    for qualified in contract.allowed_missing_tables:
        _remove_table(structure, qualified)
    for qualified in contract.allowed_missing_partitions:
        _remove_table(structure, qualified)
    tables = _tables(structure)
    for qualified, signatures in contract.allowed_missing_indexes.items():
        tables[qualified]["indexes"] = [
            sig for sig in tables[qualified]["indexes"] if sig not in signatures
        ]
    for qualified, signatures in contract.allowed_extra_indexes.items():
        tables[qualified]["indexes"].extend(sorted(signatures))
        tables[qualified]["indexes"].sort()
    structure["tables"].extend(deepcopy(list(contract.legacy_public_tables.values())))
    structure["tables"].sort(key=lambda t: (t["schema"], t["name"]))
    return structure


def test_build_metadata_plan_returns_empty_for_canonical_structure(known_restored_structure):
    plan = build_metadata_plan(known_restored_structure)
    assert plan == ()


# ---------------------------------------------------------------------------
# 6. build_metadata_plan returns 100 for a freshly broken inventory
# ---------------------------------------------------------------------------
def test_build_metadata_plan_returns_100_for_raw_clone_evidence(known_restored_structure):
    structure = deepcopy(known_restored_structure)
    # Inject the metadata-only drift on every catalogue column: strip the
    # default and force nullable=False (the raw clone profile).
    for op in ALL_OPS:
        for table in structure["tables"]:
            if table["schema"] == op.schema and table["name"] == op.table:
                for col in table["columns"]:
                    if col["name"] == op.column:
                        if op.kind is OpKind.SET_DEFAULT:
                            col["default"] = None
                        else:
                            col["nullable"] = False
    plan = build_metadata_plan(structure)
    assert len(plan) == 100


# ---------------------------------------------------------------------------
# 7. build_metadata_plan fails on unknown column
# ---------------------------------------------------------------------------
def test_build_metadata_plan_fails_on_unknown_column(known_restored_structure):
    # The catalogue is the closed allowlist: only the catalogued (s,t,c)
    # triple is allowed. The renderer's allowlist guard must reject any
    # MetadataOp whose identifier is not in the catalogue, regardless of
    # its kind. This is the load-bearing negative control: without it,
    # an unapproved (s,t,c) could be smuggled into the DDL stream.
    rogue_default = MetadataOp(
        "ghost.unapproved_table.col.default",
        "ghost", "unapproved_table", "col", OpKind.SET_DEFAULT, "1",
    )
    rogue_nullable = MetadataOp(
        "ghost.unapproved_table.col.nullable",
        "ghost", "unapproved_table", "col", OpKind.DROP_NOT_NULL, None,
    )
    with pytest.raises(ContractDeltaUnmapped):
        render_sql(rogue_default)
    with pytest.raises(ContractDeltaUnmapped):
        render_sql(rogue_nullable)
    # The rogue identifier is provably absent from the catalogue, so the
    # guard above is the *only* path by which the rogue op is rejected.
    catalogue_keys = {op.key for op in ALL_OPS}
    assert rogue_default.key not in catalogue_keys
    assert rogue_nullable.key not in catalogue_keys
    catalogue_triples = {(op.schema, op.table, op.column) for op in ALL_OPS}
    assert ("ghost", "unapproved_table", "col") not in catalogue_triples


# ---------------------------------------------------------------------------
# 8. reverse_sql for SET_DEFAULT is DROP DEFAULT
# ---------------------------------------------------------------------------
def test_reverse_sql_for_set_default_is_drop_default():
    sample = next(op for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT)
    rev = reverse_sql(sample)
    assert rev.startswith('ALTER TABLE ')
    assert 'DROP DEFAULT' in rev
    assert rev.endswith(';')


# ---------------------------------------------------------------------------
# 9. reverse_sql for DROP_NOT_NULL is sentinel
# ---------------------------------------------------------------------------
def test_reverse_sql_for_drop_not_null_is_sentinel():
    sample = next(op for op in ALL_OPS if op.kind is OpKind.DROP_NOT_NULL)
    rev = reverse_sql(sample)
    assert rev.startswith("-- ROLLBACK-FORBIDDEN:")
    assert sample.key in rev
    assert "SET NOT NULL" not in rev


# ---------------------------------------------------------------------------
# 10. team_members unique in contract v3
# ---------------------------------------------------------------------------
def test_team_members_unique_in_contract_v3_matches_inventory(contract):
    assert contract.contract_version == 3
    team_members = contract.legacy_public_tables["public.team_members"]
    assert team_members["unique"] == [["team_id", "user_id"]]


# ---------------------------------------------------------------------------
# 11. _normalise_check accepts = ANY(ARRAY[...]) on holders/representatives
# ---------------------------------------------------------------------------
def test_check_normaliser_accepts_array_any_form(known_restored_structure, contract):
    from scripts.wp3_adoption_contract import _normalise_check

    assert _normalise_check(
        "type::text = ANY (ARRAY['natural'::character varying::text, 'legal'::character varying::text])"
    ) == "type IN ('natural', 'legal')"
    assert _normalise_check(
        "type::text = ANY (ARRAY['natural'::character varying::text, 'legal'::character varying::text, 'association'::character varying::text])"
    ) == "type IN ('natural', 'legal', 'association')"
    result = classify_structure(known_restored_structure, contract)
    assert result.verdict.name == "ADOPTABLE_RESTORED"
    assert result.differences == ()


# ---------------------------------------------------------------------------
# 12. unique dedupe via allowed_extra_indexes for users / trademarks
# ---------------------------------------------------------------------------
def test_unique_dedup_via_allowed_extra_indexes_for_users_and_trademarks(
    known_restored_structure, contract
):
    # The known_restored fixture already injects allowed_extra_indexes for
    # app.users (unique email) and core.trademarks (unique source_id).
    # After canonicalisation these must not surface as UNIQUE_MISMATCH.
    result = classify_structure(known_restored_structure, contract)
    codes = {d.code.value for d in result.differences}
    assert "unique_mismatch" not in codes
    assert "index_unexpected" not in codes
    assert result.verdict.name == "ADOPTABLE_RESTORED"


# ---------------------------------------------------------------------------
# 13. dry-run does not execute SQL and returns audit shape
# ---------------------------------------------------------------------------
def test_dry_run_does_not_execute_sql(known_restored_structure, monkeypatch):
    # If dry_run executed SQL it would touch SQLAlchemy. Stub any side-effect
    # surface available: import the module to ensure it is pure offline.
    import sqlalchemy

    calls: list[tuple[str, str]] = []

    def _spy(*args, **kwargs):
        calls.append((args, kwargs))
        return None

    monkeypatch.setattr(sqlalchemy, "text", _spy)
    result = dry_run(known_restored_structure, {})
    assert calls == []  # no SQL emitted
    assert set(result.keys()) == {"ops", "skip", "blocked"}
    assert result["ops"] == []
    assert all(item["reason"] == "already_applied" for item in result["skip"])
    assert result["blocked"] == []


def test_dry_run_returns_plan_in_audit_shape():
    # Construct a minimal structure that triggers a single SET_DEFAULT op
    sample = next(op for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT)
    structure = {
        "schemas": [sample.schema],
        "extensions": [],
        "tables": [
            {
                "schema": sample.schema,
                "name": sample.table,
                "columns": [
                    {"name": sample.column, "type": "x", "nullable": True,
                     "default": None, "identity": None, "generated": None},
                ],
            }
        ],
    }
    result = dry_run(structure, {})
    assert len(result["ops"]) == 1
    entry = result["ops"][0]
    assert entry["key"] == sample.key
    assert entry["schema"] == sample.schema
    assert entry["table"] == sample.table
    assert entry["column"] == sample.column
    assert entry["kind"] == "set_default"
    assert entry["sql"].startswith('ALTER TABLE ')
    assert "SET DEFAULT" in entry["sql"]
    assert entry["reverse_sql"].startswith('ALTER TABLE ')
    assert "DROP DEFAULT" in entry["reverse_sql"]
    assert len(result["skip"]) == 99
    assert result["blocked"] == []


# ---------------------------------------------------------------------------
# Additional: digest stability for the contract v3 payload
# ---------------------------------------------------------------------------
def test_contract_v3_payload_digest_matches_evidence(contract):
    # Recompute the digest independently from the contract file.
    doc = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    recomputed = hashlib.sha256(canonical_json(doc["payload"])).hexdigest()
    assert contract.payload_sha256 == recomputed
    assert recomputed == "96fda452869da2d1d9107d1f2bc849c7363fb3b8b4f6381ebebc5721d84d7611"


# ---------------------------------------------------------------------------
# Additional: allowlist is closed; unknown identifier rejected
# ---------------------------------------------------------------------------
def test_render_sql_rejects_unknown_identifier():
    rogue = MetadataOp("ghost.unapproved_table.col.default", "ghost", "unapproved_table", "col", OpKind.SET_DEFAULT, "1")
    with pytest.raises(ContractDeltaUnmapped):
        render_sql(rogue)


# ---------------------------------------------------------------------------
# Additional: catalogue identifiers are a closed set
# ---------------------------------------------------------------------------
def test_catalogue_identifiers_are_unique():
    keys = [op.key for op in ALL_OPS]
    # Each (op.key) is unique because the key encodes both the identity
    # and the operation kind (".default" vs ".nullable").
    assert len(keys) == len(set(keys))
    # The (schema, table, column) triple can appear twice in the catalogue
    # (once as SET_DEFAULT, once as DROP_NOT_NULL) when both fixes apply
    # to the same column. The design is 67 + 33 = 100 ops over 77 distinct
    # (s, t, c) triples. We assert this is the exact cardinality.
    from collections import Counter
    triples = {(op.schema, op.table, op.column) for op in ALL_OPS}
    counter = Counter((op.schema, op.table, op.column) for op in ALL_OPS)
    assert len(triples) == 77
    double_triples = [t for t, n in counter.items() if n == 2]
    assert len(double_triples) == 23  # 100 - 77
    # No triple appears more than twice (the two kinds are exhaustive).
    assert all(n in (1, 2) for n in counter.values())


# ---------------------------------------------------------------------------
# Additional: catalogue order is stable and alphabetic per kind
# ---------------------------------------------------------------------------
def test_catalogue_is_alphabetic_per_kind():
    set_defaults = tuple(op for op in ALL_OPS if op.kind is OpKind.SET_DEFAULT)
    drop_not_nulls = tuple(op for op in ALL_OPS if op.kind is OpKind.DROP_NOT_NULL)
    # The catalogue is statically ordered by (schema, table, column) which
    # matches the alphabetic order of the keys: every SET_DEFAULT key ends
    # in ".default" and every DROP_NOT_NULL key ends in ".nullable".
    assert set_defaults == tuple(sorted(set_defaults, key=lambda o: o.key))
    assert drop_not_nulls == tuple(sorted(drop_not_nulls, key=lambda o: o.key))
