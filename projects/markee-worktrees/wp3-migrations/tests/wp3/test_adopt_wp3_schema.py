"""Contract tests for the offline, fail-closed WP3 structural classifier."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

import pytest

import scripts.adopt_wp3_schema as adoption
from scripts.drift_inventory import LiveInventory
from scripts.adopt_wp3_schema import (
    AdoptionError,
    AdoptionReason,
    build_reconciliation_plan,
)
from scripts.wp3_adoption_contract import (
    AdoptionVerdict,
    ContractError,
    ReasonCode,
    canonical_json,
    classify_structure,
    load_contract,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "scripts" / "contracts" / "wp3_002_structure.json"
MIGRATION_002_PATH = ROOT / "alembic" / "versions" / "002_data_infrastructure.py"
EXPECTED_CONTRACT_VERSION = 3
EXPECTED_PAYLOAD_SHA256 = "96fda452869da2d1d9107d1f2bc849c7363fb3b8b4f6381ebebc5721d84d7611"


def _tables(structure: dict) -> dict[str, dict]:
    return {f"{t['schema']}.{t['name']}": t for t in structure["tables"]}


def _remove_table(structure: dict, qualified: str) -> None:
    structure["tables"] = [
        table for table in structure["tables"]
        if f"{table['schema']}.{table['name']}" != qualified
    ]


@pytest.fixture
def contract():
    return load_contract(CONTRACT_PATH, source_root=ROOT)


@pytest.fixture
def canonical_structure(contract) -> dict:
    return deepcopy(contract.canonical)


@pytest.fixture
def known_restored_structure(contract, canonical_structure) -> dict:
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


def _assert_only(result, code: ReasonCode) -> None:
    assert result.verdict is AdoptionVerdict.UNKNOWN
    assert result.accepted is False
    assert [difference.code for difference in result.differences] == [code]


def test_known_restored_profile_is_adoptable(known_restored_structure, contract):
    result = classify_structure(known_restored_structure, contract)
    assert result.verdict is AdoptionVerdict.ADOPTABLE_RESTORED
    assert result.accepted is True
    assert result.differences == ()


def test_missing_required_column_is_rejected(known_restored_structure, contract):
    table = _tables(known_restored_structure)["core.trademarks"]
    table["columns"] = [c for c in table["columns"] if c["name"] != "jurisdiction"]
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.COLUMN_MISSING)


def test_changed_nullability_is_rejected(known_restored_structure, contract):
    column = next(c for c in _tables(known_restored_structure)["app.users"]["columns"] if c["name"] == "email")
    column["nullable"] = not column["nullable"]
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.COLUMN_NULLABILITY_MISMATCH)


def test_wrong_fk_target_schema_is_rejected(known_restored_structure, contract):
    fk = next(f for f in _tables(known_restored_structure)["events.lifecycle_events"]["foreign_keys"] if f["columns"] == ["trademark_id"])
    fk["target_schema"] = "public"
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.FOREIGN_KEY_MISMATCH)


def test_unknown_public_table_is_rejected(known_restored_structure, contract):
    unexpected = deepcopy(next(iter(contract.legacy_public_tables.values())))
    unexpected["name"] = "unapproved_clone_table"
    known_restored_structure["tables"].append(unexpected)
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.UNKNOWN_TABLE)


def test_unknown_index_on_expected_table_is_rejected(known_restored_structure, contract):
    table = _tables(known_restored_structure)["core.trademarks"]
    table["indexes"].append('{"include":[],"keys":[{"collation":null,"expr":"application_number","nulls":"last","opclass":null,"sort":"asc"}],"method":"hash","predicate":null,"unique":false}')
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.INDEX_UNEXPECTED)


def test_non_allowlisted_missing_index_is_rejected(known_restored_structure, contract):
    table = _tables(known_restored_structure)["core.source_runs"]
    table["indexes"].pop()
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.INDEX_REQUIRED_MISSING)


def test_partition_with_wrong_bounds_is_rejected(known_restored_structure, contract):
    partition = deepcopy(contract.allowed_missing_partitions["raw.api_responses_2026_07"])
    partition["partition_bounds"] = "FOR VALUES FROM ('2026-06-01') TO ('2026-07-01')"
    known_restored_structure["tables"].append(partition)
    result = classify_structure(known_restored_structure, contract)
    assert result.verdict is AdoptionVerdict.UNKNOWN
    assert ReasonCode.PARTITION_BOUNDS_MISMATCH in result.reasons
    assert ReasonCode.INDEX_REQUIRED_MISSING not in result.reasons


def _column(structure: dict, qualified: str, name: str) -> dict:
    return next(c for c in _tables(structure)[qualified]["columns"] if c["name"] == name)


def _assert_adoptable(result) -> None:
    assert result.verdict is AdoptionVerdict.ADOPTABLE_RESTORED
    assert result.accepted is True
    assert result.differences == ()


def test_observed_lowercase_now_equals_contract_uppercase_now(known_restored_structure, contract):
    column = _column(known_restored_structure, "app.users", "created_at")
    assert column["default"] == "NOW()"
    column["default"] = "now()"
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_observed_uppercase_now_equals_contract_lowercase_now(known_restored_structure, contract):
    column = _column(known_restored_structure, "raw.api_responses", "created_at")
    assert column["default"] == "now()"
    column["default"] = "NOW()"
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_mixed_case_standalone_now_variant_is_semantically_equal(known_restored_structure, contract):
    column = _column(known_restored_structure, "core.trademarks", "created_at")
    assert column["default"] == "NOW()"
    column["default"] = "Now()"
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_legacy_table_lowercase_now_equals_contract_uppercase_now(known_restored_structure, contract):
    column = _column(known_restored_structure, "public.users", "created_at")
    assert column["default"] == "NOW()"
    column["default"] = "now()"
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_pg16_lowercase_rendering_of_every_standalone_now_default_is_adoptable(
    known_restored_structure, contract
):
    flipped = 0
    for table in known_restored_structure["tables"]:
        for column in table["columns"]:
            if column.get("default") == "NOW()":
                column["default"] = "now()"
                flipped += 1
    assert flipped >= 33
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_partition_entry_with_flipped_now_case_remains_adoptable(known_restored_structure, contract):
    partition = deepcopy(contract.allowed_missing_partitions["raw.api_responses_2026_07"])
    column = next(c for c in partition["columns"] if c["name"] == "created_at")
    assert column["default"] == "now()"
    column["default"] = "NOW()"
    known_restored_structure["tables"].append(partition)
    _assert_adoptable(classify_structure(known_restored_structure, contract))


def test_semantic_now_equality_leaves_structural_fingerprint_untouched(
    known_restored_structure, contract
):
    pristine = classify_structure(deepcopy(known_restored_structure), contract)
    column = _column(known_restored_structure, "app.users", "created_at")
    column["default"] = "now()"
    flipped = classify_structure(known_restored_structure, contract)
    assert flipped.verdict is AdoptionVerdict.ADOPTABLE_RESTORED
    assert flipped.structural_fingerprint != pristine.structural_fingerprint


@pytest.mark.parametrize("observed_default", [
    "timezone('utc'::text, now())",
    "clock_timestamp()",
    "(now())",
    "now()::timestamp with time zone",
    "now() + '7 days'::interval",
    "NOW ()",
    "'now()'::text",
    "now",
    None,
])
def test_non_standalone_now_defaults_remain_mismatches(
    observed_default, known_restored_structure, contract
):
    column = _column(known_restored_structure, "app.users", "created_at")
    column["default"] = observed_default
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.COLUMN_DEFAULT_MISMATCH)


@pytest.mark.parametrize("observed_default", [
    "timezone('utc'::text, now())",
    "clock_timestamp()",
    "CURRENT_TIMESTAMP",
])
def test_contract_lowercase_now_never_matches_other_temporal_defaults(
    observed_default, known_restored_structure, contract
):
    column = _column(known_restored_structure, "raw.api_responses", "created_at")
    column["default"] = observed_default
    _assert_only(classify_structure(known_restored_structure, contract), ReasonCode.COLUMN_DEFAULT_MISMATCH)


def _write_contract_with_valid_payload_hash(path: Path, document: dict) -> None:
    document["integrity"]["payload_sha256"] = hashlib.sha256(
        canonical_json(document["payload"])
    ).hexdigest()
    path.write_text(json.dumps(document), encoding="utf-8")


def test_contract_artifact_integrity_hash_and_version(tmp_path):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert document["format_version"] == 1
    assert document["contract_version"] == EXPECTED_CONTRACT_VERSION
    assert document["integrity"]["payload_sha256"] == __import__("hashlib").sha256(canonical_json(document["payload"])).hexdigest()
    altered = deepcopy(document)
    altered["payload"]["canonical"]["tables"][0]["columns"][0]["nullable"] ^= True
    path = tmp_path / "altered.json"
    path.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ContractError, match="contract payload hash mismatch"):
        load_contract(path)
    for unsupported_version in (1, 4):
        altered = deepcopy(document)
        altered["contract_version"] = unsupported_version
        path.write_text(json.dumps(altered), encoding="utf-8")
        with pytest.raises(ContractError, match="contract version unsupported"):
            load_contract(path)


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda provenance: provenance.pop("canonical_revision"), "invalid provenance fields"),
        (lambda provenance: provenance.__setitem__("unexpected", "value"), "invalid provenance fields"),
        (lambda provenance: provenance.__setitem__("canonical_revision", 2), "invalid canonical revision"),
        (lambda provenance: provenance.__setitem__("derivation", ["review"]), "invalid provenance derivation"),
        (lambda provenance: provenance.__setitem__("migration_sha256", []), "invalid migration provenance"),
    ],
)
def test_contract_provenance_schema_is_exact_and_typed(tmp_path, mutate, reason):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(document["payload"]["provenance"])
    path = tmp_path / "mutated.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match=reason):
        load_contract(path)


def test_contract_canonical_revision_is_exact_with_valid_payload_hash(tmp_path):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["payload"]["provenance"]["canonical_revision"] = "001"
    path = tmp_path / "wrong-revision.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match="canonical revision unsupported"):
        load_contract(path)


def test_contract_derivation_is_exact_with_valid_payload_hash(tmp_path):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["payload"]["provenance"]["derivation"] = "arbitrary_static_review"
    path = tmp_path / "wrong-derivation.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match="provenance derivation unsupported"):
        load_contract(path)


def test_contract_extra_provenance_key_is_rejected_with_valid_payload_hash(tmp_path):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["payload"]["provenance"]["source_path"] = "alembic/versions"
    path = tmp_path / "extra-provenance-key.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match="invalid provenance fields"):
        load_contract(path)


@pytest.mark.parametrize(
    "migration_hashes",
    [
        {"001_initial_migration.py": "0" * 64},
        {
            "001_initial_migration.py": "A" * 64,
            "002_data_infrastructure.py": "f" * 64,
        },
        {
            "001_initial_migration.py": "0" * 64,
            "002_data_infrastructure.py": "f" * 64,
            "003_unapproved.py": "1" * 64,
        },
    ],
)
def test_contract_migration_hash_schema_and_values_are_exact(
    tmp_path, migration_hashes
):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["payload"]["provenance"]["migration_sha256"] = migration_hashes
    path = tmp_path / "wrong-migration-hashes.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match="invalid migration provenance"):
        load_contract(path)


def test_contract_migration_hashes_must_match_local_sources(tmp_path):
    source_root = tmp_path / "source"
    versions = source_root / "alembic" / "versions"
    versions.mkdir(parents=True)
    for name in ("001_initial_migration.py", "002_data_infrastructure.py"):
        content = (ROOT / "alembic" / "versions" / name).read_bytes()
        if name == "001_initial_migration.py":
            content += b"\n# mutation\n"
        (versions / name).write_bytes(content)

    with pytest.raises(
        ContractError,
        match="migration source hash mismatch: 001_initial_migration.py",
    ):
        load_contract(CONTRACT_PATH, source_root=source_root)


def test_contract_rejects_symlinked_migration_source_outside_source_root(tmp_path):
    source_root = tmp_path / "source"
    versions = source_root / "alembic" / "versions"
    versions.mkdir(parents=True)
    for name in ("001_initial_migration.py", "002_data_infrastructure.py"):
        (versions / name).symlink_to(ROOT / "alembic" / "versions" / name)

    with pytest.raises(
        ContractError,
        match="migration source path invalid: 001_initial_migration.py",
    ):
        load_contract(CONTRACT_PATH, source_root=source_root)


def test_corrected_contract_provenance_and_payload_digest_are_accepted():
    contract = load_contract(CONTRACT_PATH, source_root=ROOT)

    assert contract.contract_id == "markee-wp3-002-structure"
    assert contract.format_version == 1
    assert contract.contract_version == EXPECTED_CONTRACT_VERSION
    assert contract.payload_sha256 == EXPECTED_PAYLOAD_SHA256


def _canonical_contract_table(qualified: str) -> dict:
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return next(
        table for table in document["payload"]["canonical"]["tables"]
        if f"{table['schema']}.{table['name']}" == qualified
    )


def _migration_002_create_table_block(table_name: str) -> str:
    source = MIGRATION_002_PATH.read_text(encoding="utf-8")
    start = source.index(f'op.create_table(\n        "{table_name}",')
    depth = 0
    for position in range(start + len("op.create_table"), len(source)):
        char = source[position]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(f"unterminated create_table block for {table_name}")


def test_contract_trademark_holders_pk_matches_migration_002_truth():
    block = _migration_002_create_table_block("trademark_holders")
    assert 'sa.PrimaryKeyConstraint("trademark_id", "holder_id", "role")' in block

    table = _canonical_contract_table("core.trademark_holders")
    assert table["primary_key"] == ["trademark_id", "holder_id", "role"]
    assert table["unique"] == []


def test_contract_trademark_representatives_pk_matches_migration_002_truth():
    block = _migration_002_create_table_block("trademark_representatives")
    assert 'sa.PrimaryKeyConstraint("trademark_id", "representative_id")' in block

    table = _canonical_contract_table("core.trademark_representatives")
    assert table["primary_key"] == ["trademark_id", "representative_id"]
    assert table["unique"] == []


def test_contract_trademark_versions_unique_matches_migration_002_truth():
    block = _migration_002_create_table_block("trademark_versions")
    assert 'sa.UniqueConstraint("trademark_id", "version_number"' in block
    assert '"id", postgresql.UUID(as_uuid=True), primary_key=True' in block

    table = _canonical_contract_table("core.trademark_versions")
    assert table["primary_key"] == ["id"]
    assert table["unique"] == [["trademark_id", "version_number"]]


_MALFORMED_V1_CONSTRAINT_SHAPES = (
    ("core.trademark_holders", "primary_key", []),
    ("core.trademark_representatives", "primary_key", []),
    ("core.trademark_versions", "unique", [[]]),
)


def test_malformed_empty_link_constraints_in_structure_are_rejected(
    canonical_structure, contract
):
    tables = _tables(canonical_structure)
    for qualified, field, malformed in _MALFORMED_V1_CONSTRAINT_SHAPES:
        tables[qualified][field] = malformed

    result = classify_structure(canonical_structure, contract)

    assert result.verdict is AdoptionVerdict.UNKNOWN
    assert result.accepted is False
    assert {(d.code, d.path) for d in result.differences} == {
        (ReasonCode.PRIMARY_KEY_MISMATCH, "core.trademark_holders.primary_key"),
        (ReasonCode.PRIMARY_KEY_MISMATCH, "core.trademark_representatives.primary_key"),
        (ReasonCode.UNIQUE_MISMATCH, "core.trademark_versions.unique"),
    }


def test_migration_truth_structure_is_rejected_by_regressed_v1_constraint_shapes(
    tmp_path, canonical_structure
):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_tables = {
        f"{table['schema']}.{table['name']}": table
        for table in document["payload"]["canonical"]["tables"]
    }
    for qualified, field, malformed in _MALFORMED_V1_CONSTRAINT_SHAPES:
        contract_tables[qualified][field] = malformed
    path = tmp_path / "regressed.json"
    _write_contract_with_valid_payload_hash(path, document)
    regressed = load_contract(path)

    result = classify_structure(canonical_structure, regressed)

    assert result.verdict is AdoptionVerdict.UNKNOWN
    assert result.accepted is False
    assert {(d.code, d.path) for d in result.differences} == {
        (ReasonCode.PRIMARY_KEY_MISMATCH, "core.trademark_holders.primary_key"),
        (ReasonCode.PRIMARY_KEY_MISMATCH, "core.trademark_representatives.primary_key"),
        (ReasonCode.UNIQUE_MISMATCH, "core.trademark_versions.unique"),
    }


def test_loader_rejects_contract_version_one_after_v2_transition(tmp_path):
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    document["contract_version"] = 1
    path = tmp_path / "regressed-version.json"
    _write_contract_with_valid_payload_hash(path, document)

    with pytest.raises(ContractError, match="contract version unsupported"):
        load_contract(path)


def test_contract_team_members_preserves_migration_001_composite_unique():
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    team_members = next(
        table for table in document["payload"]["canonical"]["tables"]
        if (table["schema"], table["name"]) == ("app", "team_members")
    )

    assert team_members["primary_key"] == ["id"]
    assert team_members["unique"] == [["team_id", "user_id"]]
    assert team_members["indexes"] == []


def test_contract_artifact_contains_no_values_or_dsn():
    document = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    forbidden_keys = {"target", "dsn", "database_url", "host", "port", "user", "password", "credential", "secret", "token", "rows", "row_count", "sample", "value", "values"}
    def walk(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                assert key.lower() not in forbidden_keys, ".".join((*path, key))
                walk(child, (*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, (*path, str(index)))
        elif isinstance(value, str):
            assert "://" not in value
            assert "postgresql" not in value.lower()
    walk(document)


def test_canonical_final_profile_is_already_final(canonical_structure, contract):
    result = classify_structure(canonical_structure, contract)
    assert result.verdict is AdoptionVerdict.ALREADY_FINAL
    assert result.accepted is True
    assert result.reasons == (ReasonCode.CANONICAL_FINAL_STRUCTURE,)


def test_empty_profile_is_distinct_from_adoptable(contract):
    result = classify_structure({"schemas": ["public"], "extensions": ["pg_trgm"], "tables": []}, contract)
    assert result.verdict is AdoptionVerdict.EMPTY
    assert result.accepted is False
    assert result.reasons == (ReasonCode.EMPTY_APPLICATION_STRUCTURE,)


def test_partial_or_mixed_profile_is_unknown(known_restored_structure, contract):
    _remove_table(known_restored_structure, "core.sources")
    result = classify_structure(known_restored_structure, contract)
    assert result.verdict is AdoptionVerdict.UNKNOWN
    assert result.accepted is False
    assert ReasonCode.REQUIRED_TABLE_MISSING in result.reasons


EXPECTED_RECONCILIATION_OPERATIONS = (
    (
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
    ),
    (
        "partition:raw.api_responses_2026_07",
        """CREATE TABLE raw.api_responses_2026_07
PARTITION OF raw.api_responses
FOR VALUES FROM ('2026-07-01') TO ('2026-08-01')""",
    ),
    (
        "partition:raw.api_responses_2026_08",
        """CREATE TABLE raw.api_responses_2026_08
PARTITION OF raw.api_responses
FOR VALUES FROM ('2026-08-01') TO ('2026-09-01')""",
    ),
    ("index:app.alerts:user_id,is_dismissed,created_at", """CREATE INDEX idx_alerts_user_unread
ON app.alerts (user_id, is_dismissed, created_at)"""),
    ("index:app.alerts:watchlist_id,similarity_score", """CREATE INDEX idx_alerts_composite_score
ON app.alerts (watchlist_id, similarity_score)"""),
    ("index:app.deadlines:due_date,status", """CREATE INDEX idx_deadlines_due_date
ON app.deadlines (due_date, status)"""),
    ("index:app.prospection_opportunities:opportunity_type,score", """CREATE INDEX idx_prospection_score
ON app.prospection_opportunities (opportunity_type, score)"""),
    ("index:app.review_queue:status,created_at", """CREATE INDEX idx_review_queue_status
ON app.review_queue (status, created_at)"""),
    ("index:core.holders:name:gin_trgm_ops", """CREATE INDEX idx_holders_name_trgm
ON core.holders USING GIN (name gin_trgm_ops)"""),
    ("index:core.representatives:name:gin_trgm_ops", """CREATE INDEX idx_reps_name_trgm
ON core.representatives USING GIN (name gin_trgm_ops)"""),
    ("index:core.trademarks:word_mark:gin_trgm_ops", """CREATE INDEX idx_trademarks_wordmark
ON core.trademarks USING GIN (word_mark gin_trgm_ops)"""),
    ("index:events.lifecycle_events:trademark_id,event_date", """CREATE INDEX idx_lifecycle_events_trademark
ON events.lifecycle_events (trademark_id, event_date)"""),
    ("index:events.lifecycle_events:trademark_id,event_type", """CREATE INDEX idx_events_trademark_type
ON events.lifecycle_events (trademark_id, event_type)"""),
    ("index:raw.api_responses:source_id,created_at_desc", """CREATE INDEX idx_raw_source_created
ON raw.api_responses (source_id, created_at DESC)"""),
)


def test_contract_deltas_have_exact_static_operations(known_restored_structure, contract):
    plan = build_reconciliation_plan(known_restored_structure, contract)

    assert tuple((operation.key, operation.sql) for operation in plan) == EXPECTED_RECONCILIATION_OPERATIONS


def test_reconciliation_plan_contains_fourteen_ordered_operations_for_known_clone(
    known_restored_structure, contract
):
    plan = build_reconciliation_plan(known_restored_structure, contract)

    assert len(plan) == 14
    assert tuple(operation.key for operation in plan) == tuple(
        key for key, _sql in EXPECTED_RECONCILIATION_OPERATIONS
    )
    raw_index_position = next(
        index for index, operation in enumerate(plan)
        if operation.key == "index:raw.api_responses:source_id,created_at_desc"
    )
    assert all(
        next(index for index, operation in enumerate(plan) if operation.key == partition_key)
        < raw_index_position
        for partition_key in (
            "partition:raw.api_responses_2026_07",
            "partition:raw.api_responses_2026_08",
        )
    )


def test_reconciliation_plan_creates_exact_canonical_app_api_keys(
    known_restored_structure, contract
):
    operation = build_reconciliation_plan(known_restored_structure, contract)[0]
    expected_sql = EXPECTED_RECONCILIATION_OPERATIONS[0][1]

    assert operation.key == "table:app.api_keys"
    assert operation.sql == expected_sql
    assert "PRIMARY KEY (id)" in operation.sql
    assert "REFERENCES app.users (id)" in operation.sql
    assert "ON DELETE CASCADE" in operation.sql
    assert "UNIQUE (key_hash)" in operation.sql
    assert not re.search(r"\b(?:INSERT|SELECT)\b", operation.sql, re.IGNORECASE)
    assert "public.api_keys" not in operation.sql


def test_reconciliation_plan_is_empty_for_canonical_final_structure(
    canonical_structure, contract
):
    assert build_reconciliation_plan(canonical_structure, contract) == ()


@pytest.mark.parametrize("delta_kind", ["table", "index", "partition", "unexpected"])
def test_unmapped_contract_or_structural_delta_is_rejected(
    delta_kind, known_restored_structure, contract
):
    if delta_kind == "table":
        altered_contract = replace(
            contract,
            allowed_missing_tables=contract.allowed_missing_tables | {"app.users"},
        )
    elif delta_kind == "index":
        altered_indexes = dict(contract.allowed_missing_indexes)
        altered_indexes["app.users"] = frozenset({"unmapped-semantic-index"})
        altered_contract = replace(contract, allowed_missing_indexes=altered_indexes)
    elif delta_kind == "partition":
        altered_partitions = dict(contract.allowed_missing_partitions)
        altered_partitions["raw.api_responses_2026_09"] = deepcopy(
            next(iter(contract.allowed_missing_partitions.values()))
        )
        altered_contract = replace(contract, allowed_missing_partitions=altered_partitions)
    else:
        altered_contract = contract
        _tables(known_restored_structure)["core.source_runs"]["indexes"].pop()

    with pytest.raises(AdoptionError) as raised:
        build_reconciliation_plan(known_restored_structure, altered_contract)

    assert raised.value.reason is AdoptionReason.CONTRACT_DELTA_UNMAPPED


def test_sql_catalog_is_additive_static_unique_and_deterministic(
    known_restored_structure, contract
):
    first = build_reconciliation_plan(known_restored_structure, contract)
    reordered = deepcopy(known_restored_structure)
    reordered["tables"].reverse()
    second = build_reconciliation_plan(reordered, contract)
    forbidden = re.compile(
        r"(?:\bDROP\b|\bTRUNCATE\b|\bDELETE\s+FROM\b|\bUPDATE\s+[A-Za-z_]|\bINSERT\s+INTO\b|\bSELECT\b)",
        re.IGNORECASE,
    )

    assert first == second
    assert len({operation.key for operation in first}) == len(first)
    assert tuple(operation.key for operation in first) == tuple(
        key for key, _sql in EXPECTED_RECONCILIATION_OPERATIONS
    )
    assert all(not forbidden.search(operation.sql) for operation in first)
    assert all("IF NOT EXISTS" not in operation.sql.upper() for operation in first)
    assert all("{" not in operation.sql and "}" not in operation.sql for operation in first)
    assert all("%s" not in operation.sql and ":" not in operation.sql for operation in first)
    assert all("public.api_keys" not in operation.sql for operation in first)


class _Result:
    def __init__(self, rows=(), scalar=None):
        self._rows = list(rows)
        self._scalar = scalar

    def all(self):
        return list(self._rows)

    def scalar(self):
        return self._scalar


class _TransactionalConnection:
    def __init__(self, structure, *, versions=None, version_table=False):
        self.structure = deepcopy(structure)
        self.versions = list(versions or ())
        self.version_table = version_table
        self.sql: list[str] = []
        self.ddl: list[str] = []
        self.metadata_ddl: list[str] = []
        self.locks: list[str] = []
        self.fail_lock_at: int | None = None
        self.fail_ddl_at: int | None = None
        self.post_ddl_structure = None
        self.stamp_calls = 0

    def execute(self, statement):
        sql = str(statement).strip()
        self.sql.append(sql)
        upper = sql.upper()
        if "FROM INFORMATION_SCHEMA.TABLES" in upper:
            return _Result(scalar=1 if self.version_table else None)
        if "FROM PUBLIC.ALEMBIC_VERSION" in upper:
            return _Result([(version,) for version in sorted(self.versions)])
        if upper.startswith("LOCK TABLE"):
            self.locks.append(sql)
            if self.fail_lock_at == len(self.locks):
                raise RuntimeError("induced relation lock failure")
            return _Result()
        if upper.startswith("CREATE TABLE") or upper.startswith("CREATE INDEX"):
            self.ddl.append(sql)
            if self.fail_ddl_at == len(self.ddl):
                raise RuntimeError("induced reconciliation failure")
            if len(self.ddl) == 14 and self.post_ddl_structure is not None:
                self.structure = deepcopy(self.post_ddl_structure)
            return _Result()
        if upper.startswith("ALTER TABLE"):
            self.metadata_ddl.append(sql)
            return _Result()
        return _Result()

class _Begin:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        self.engine.begin_count += 1
        self.engine.snapshot = (
            deepcopy(self.engine.connection.structure),
            list(self.engine.connection.versions),
            self.engine.connection.version_table,
        )
        return self.engine.connection

    def __exit__(self, exc_type, _exc, _tb):
        if exc_type is None:
            self.engine.commits += 1
        else:
            self.engine.rollbacks += 1
            structure, versions, version_table = self.engine.snapshot
            self.engine.connection.structure = structure
            self.engine.connection.versions = versions
            self.engine.connection.version_table = version_table
        return False


class _Engine:
    def __init__(self, connection):
        self.connection = connection
        self.begin_count = 0
        self.commits = 0
        self.rollbacks = 0
        self.disposals = 0
        self.snapshot = None

    def begin(self):
        return _Begin(self)

    def dispose(self):
        self.disposals += 1


def _live(connection):
    structure = deepcopy(connection.structure)
    tables = tuple(
        (table["schema"], table["name"]) for table in structure.get("tables", ())
    )
    return LiveInventory(
        target="sanitised-target",
        schemas=tuple(structure.get("schemas", ())),
        tables=tables,
        indexes=(),
        extensions=tuple((name, "test") for name in structure.get("extensions", ())),
        alembic_version=connection.versions[0] if len(connection.versions) == 1 else None,
        fingerprint="catalog-fingerprint",
        structure=structure,
        structural_fingerprint=hashlib.sha256(canonical_json(structure)).hexdigest(),
    )


def _install_boundaries(monkeypatch, connection, *, head="002", stamp_version="002"):
    engine = _Engine(connection)
    calls = []

    def guard(_url):
        calls.append("guard")
        return type("Spec", (), {
            "host": "127.0.0.1", "port": 5441,
            "database": "markee_wp3_disposable", "user": "markee_wp3",
            "identity_verified": True,
        })()

    monkeypatch.setattr(adoption, "create_engine", lambda *_a, **_k: calls.append("engine") or engine)
    monkeypatch.setattr(adoption, "inventory_connection", lambda supplied, *, target: _live(supplied))
    # Default: legacy tests use partial synthetic inventories that predate the
    # metadata bridge; collapse the new module-level planner to an empty plan
    # so the existing 14-DDL contract is preserved. Bridge-specific tests
    # override this monkeypatch with a real or synthetic planner.
    monkeypatch.setattr(adoption, "build_metadata_plan", lambda *_a, **_k: ())
    script = type("Script", (), {"get_heads": lambda self: [head]})()
    monkeypatch.setattr(adoption.ScriptDirectory, "from_config", lambda _config: script)

    class Context:
        def stamp(self, supplied_script, revision):
            assert supplied_script is script
            assert revision == "002"
            assert configured[0] is connection
            assert engine.begin_count == 1 and engine.commits == 0
            connection.stamp_calls += 1
            connection.version_table = True
            connection.versions = [stamp_version]

    configured = []
    monkeypatch.setattr(
        adoption.MigrationContext,
        "configure",
        lambda supplied: configured.append(supplied) or Context(),
    )
    return engine, guard, calls, configured


def _adopt(monkeypatch, connection, *, head="002", stamp_version="002"):
    engine, guard, calls, configured = _install_boundaries(
        monkeypatch, connection, head=head, stamp_version=stamp_version
    )
    result = adoption.adopt_wp3_schema(
        "credential-bearing-test-dsn",
        guard=guard,
        contract_path=CONTRACT_PATH,
        source_root=ROOT,
    )
    return result, engine, calls, configured


def test_guard_runs_before_engine_creation_and_rejection_opens_nothing(monkeypatch):
    calls = []

    def reject(_url):
        calls.append("guard")
        raise RuntimeError("rejected")

    monkeypatch.setattr(adoption, "create_engine", lambda *_a, **_k: calls.append("engine"))
    with pytest.raises(RuntimeError, match="rejected"):
        adoption.adopt_wp3_schema(
            "test-dsn", guard=reject, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert calls == ["guard"]


def test_weak_textual_guard_is_rejected_before_scripts_or_engine(monkeypatch):
    calls = []
    monkeypatch.setattr(
        adoption.ScriptDirectory,
        "from_config",
        lambda _config: calls.append("script"),
    )
    monkeypatch.setattr(adoption, "create_engine", lambda *_a, **_k: calls.append("engine"))
    with pytest.raises(adoption.AdoptionError, match="attested Docker identity"):
        adoption.adopt_wp3_schema(
            "test-dsn",
            guard=lambda _url: adoption.TargetSpec(
                scheme="postgresql",
                host="127.0.0.1",
                port=5441,
                user="markee_wp3",
                database="markee_wp3_disposable",
            ),
            contract_path=CONTRACT_PATH,
            source_root=ROOT,
        )
    assert calls == []


@pytest.mark.parametrize("version_table", [False, True])
def test_unstamped_valid_adoptable_reaches_002_with_exact_operations(
    monkeypatch, known_restored_structure, canonical_structure, version_table
):
    final = deepcopy(canonical_structure)
    final["tables"].extend(
        deepcopy([table for table in known_restored_structure["tables"] if table["schema"] == "public"])
    )
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection = _TransactionalConnection(
        known_restored_structure, versions=[], version_table=version_table
    )
    connection.post_ddl_structure = final

    result, engine, calls, configured = _adopt(monkeypatch, connection)

    assert result.status is adoption.AdoptionStatus.ADOPTED
    assert result.reason is AdoptionReason.ADOPTED_TO_002
    assert result.operations == tuple(key for key, _sql in EXPECTED_RECONCILIATION_OPERATIONS)
    assert tuple(connection.ddl) == tuple(sql for _key, sql in EXPECTED_RECONCILIATION_OPERATIONS)
    assert connection.versions == ["002"]
    assert calls[:2] == ["guard", "engine"]
    assert configured == [connection]
    assert engine.begin_count == 1 and engine.commits == 1 and engine.rollbacks == 0
    assert engine.disposals == 1


def test_combined_legacy_shape_bridges_metadata_then_additive_in_one_txn(
    monkeypatch, known_restored_structure, canonical_structure
):
    """RED->GREEN: the real restored clone carries BOTH the 100 approved
    metadata deltas AND the 14 missing additive objects in one structure. A
    single adoption transaction must normalise metadata first, re-inventory,
    apply the additive plan, and stamp 002 only after a final zero-diff
    verification. This is the exact live blocker the separate-simulation
    dry-run masked (build_reconciliation_plan on the raw clone raised
    "delta outside the static catalogue"; the unstamped gate rejected it).
    """
    from scripts.wp3_reconcile_metadata import (
        ALL_OPS,
        OpKind,
        build_metadata_plan as real_build_metadata_plan,
    )

    normalized = deepcopy(known_restored_structure)
    canonical_final = deepcopy(canonical_structure)
    canonical_final["tables"].extend(
        deepcopy([t for t in known_restored_structure["tables"] if t["schema"] == "public"])
    )
    canonical_final["tables"].sort(key=lambda t: (t["schema"], t["name"]))

    # Build the true legacy clone: de-normalise exactly the 100 catalogue columns
    # so the real metadata planner emits all 67 SET DEFAULT + 33 DROP NOT NULL.
    legacy = deepcopy(known_restored_structure)
    legacy_tables = _tables(legacy)
    denormalised = 0
    for op in ALL_OPS:
        table = legacy_tables.get(f"{op.schema}.{op.table}")
        if table is None:
            continue
        column = next((c for c in table["columns"] if c["name"] == op.column), None)
        if column is None:
            continue
        if op.kind is OpKind.SET_DEFAULT:
            column["default"] = None          # differs from the canonical expression
        else:
            column["nullable"] = False         # DROP NOT NULL still required
        denormalised += 1
    assert denormalised == 100
    assert len(real_build_metadata_plan(legacy)) == 100          # 67 + 33
    assert real_build_metadata_plan(normalized) == ()            # normalized needs none

    class _CombinedConnection(_TransactionalConnection):
        def __init__(self, *, metadata_count):
            super().__init__(legacy, versions=[], version_table=False)
            self._metadata_count = metadata_count
            self.post_ddl_structure = canonical_final   # parent swaps after 14th CREATE

        def execute(self, statement):
            sql = str(statement).strip()
            if sql.upper().startswith("ALTER TABLE"):
                self.metadata_ddl.append(sql)
                if len(self.metadata_ddl) == self._metadata_count:
                    self.structure = deepcopy(normalized)
                return _Result()
            return super().execute(statement)

    connection = _CombinedConnection(metadata_count=100)
    engine, guard, calls, configured = _install_boundaries(monkeypatch, connection)
    # Override the default empty-plan stub with the real static metadata planner.
    monkeypatch.setattr(adoption, "build_metadata_plan", real_build_metadata_plan)

    result = adoption.adopt_wp3_schema(
        "credential-bearing-test-dsn",
        guard=guard,
        contract_path=CONTRACT_PATH,
        source_root=ROOT,
    )

    assert result.status is adoption.AdoptionStatus.ADOPTED
    assert result.reason is AdoptionReason.ADOPTED_TO_002
    assert len(connection.metadata_ddl) == 100                    # bridge applied FIRST
    assert result.operations == tuple(key for key, _sql in EXPECTED_RECONCILIATION_OPERATIONS)
    assert tuple(connection.ddl) == tuple(sql for _key, sql in EXPECTED_RECONCILIATION_OPERATIONS)
    assert connection.versions == ["002"]                         # stamped only after zero diff
    assert connection.stamp_calls == 1
    assert engine.begin_count == 1 and engine.commits == 1 and engine.rollbacks == 0
    assert engine.disposals == 1


@pytest.mark.parametrize(
    ("structure_fixture", "versions", "reason"),
    [
        ("empty", [], AdoptionReason.EMPTY_DATABASE),
        ("restored", ["001"], AdoptionReason.VERSION_001_REJECTED),
        ("restored", ["999"], AdoptionReason.VERSION_UNKNOWN),
        ("restored", ["001", "002"], AdoptionReason.VERSION_MULTIPLE),
    ],
)
def test_invalid_history_states_are_rejected(
    monkeypatch, request, known_restored_structure, contract,
    structure_fixture, versions, reason
):
    structure = (
        {"schemas": ["public"], "extensions": ["pg_trgm"], "tables": []}
        if structure_fixture == "empty" else known_restored_structure
    )
    connection = _TransactionalConnection(structure, versions=versions, version_table=bool(versions))
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert raised.value.reason is reason
    assert connection.ddl == [] and connection.stamp_calls == 0
    assert engine.rollbacks == 1


def test_already_002_final_validates_and_is_noop(monkeypatch, canonical_structure):
    connection = _TransactionalConnection(canonical_structure, versions=["002"], version_table=True)
    result, engine, _calls, configured = _adopt(monkeypatch, connection)
    assert result.status is adoption.AdoptionStatus.ALREADY_ADOPTED
    assert result.reason is AdoptionReason.ALREADY_002_NOOP
    assert result.operations == ()
    assert result.structural_fingerprint_before == result.structural_fingerprint_after
    assert connection.ddl == [] and connection.stamp_calls == 0 and configured == []
    assert engine.commits == 1


def test_already_002_with_drift_is_rejected(monkeypatch, canonical_structure):
    _remove_table(canonical_structure, "core.sources")
    connection = _TransactionalConnection(canonical_structure, versions=["002"], version_table=True)
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert raised.value.reason is AdoptionReason.ALREADY_002_DRIFT
    assert connection.ddl == [] and connection.stamp_calls == 0
    assert engine.rollbacks == 1


def test_unstamped_canonical_without_legacy_is_rejected(monkeypatch, canonical_structure):
    connection = _TransactionalConnection(canonical_structure)
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert raised.value.reason is AdoptionReason.UNSTAMPED_STRUCTURE_REJECTED
    assert connection.ddl == [] and connection.stamp_calls == 0 and engine.rollbacks == 1


def test_alembic_head_mismatch_is_rejected_before_engine(monkeypatch):
    calls = []
    monkeypatch.setattr(adoption.ScriptDirectory, "from_config", lambda _config: type("Script", (), {"get_heads": lambda self: ["001"]})())
    monkeypatch.setattr(adoption, "create_engine", lambda *_a, **_k: calls.append("engine"))
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn",
            guard=lambda _url: type("Spec", (), {"identity_verified": True})(),
            contract_path=CONTRACT_PATH,
            source_root=ROOT,
        )
    assert raised.value.reason is AdoptionReason.ALEMBIC_HEAD_MISMATCH
    assert calls == []


def test_mid_reconciliation_error_rolls_back_and_never_stamps(
    monkeypatch, known_restored_structure, canonical_structure
):
    connection = _TransactionalConnection(known_restored_structure)
    connection.post_ddl_structure = canonical_structure
    connection.fail_ddl_at = 7
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    with pytest.raises(AdoptionError):
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert engine.rollbacks == 1 and engine.commits == 0
    assert connection.stamp_calls == 0 and connection.versions == []
    assert canonical_json(connection.structure) == canonical_json(known_restored_structure)


def test_post_ddl_reinventory_drift_rolls_back_without_stamp(
    monkeypatch, known_restored_structure
):
    connection = _TransactionalConnection(known_restored_structure)
    drift = deepcopy(known_restored_structure)
    _remove_table(drift, "core.sources")
    connection.post_ddl_structure = drift
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert raised.value.reason is AdoptionReason.POST_RECONCILIATION_DRIFT
    assert engine.rollbacks == 1 and connection.stamp_calls == 0


def test_post_stamp_version_mismatch_rolls_back(
    monkeypatch, known_restored_structure, canonical_structure
):
    final = deepcopy(canonical_structure)
    final["tables"].extend(deepcopy([t for t in known_restored_structure["tables"] if t["schema"] == "public"]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection = _TransactionalConnection(known_restored_structure)
    connection.post_ddl_structure = final
    engine, guard, _calls, _configured = _install_boundaries(
        monkeypatch, connection, stamp_version="999"
    )
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )
    assert raised.value.reason is AdoptionReason.POST_STAMP_VERSION_MISMATCH
    assert engine.rollbacks == 1 and connection.versions == []
    assert connection.stamp_calls == 1


def test_second_adoption_is_noop(monkeypatch, known_restored_structure, canonical_structure):
    final = deepcopy(canonical_structure)
    final["tables"].extend(deepcopy([t for t in known_restored_structure["tables"] if t["schema"] == "public"]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection = _TransactionalConnection(known_restored_structure)
    connection.post_ddl_structure = final
    first, _engine, _calls, _configured = _adopt(monkeypatch, connection)
    connection.ddl.clear()
    second, _engine2, _calls2, configured2 = _adopt(monkeypatch, connection)
    assert first.status is adoption.AdoptionStatus.ADOPTED
    assert second.status is adoption.AdoptionStatus.ALREADY_ADOPTED
    assert connection.ddl == [] and connection.stamp_calls == 1 and configured2 == []


def test_executed_sql_never_reads_or_copies_legacy_identity_tables(
    monkeypatch, known_restored_structure, canonical_structure
):
    final = deepcopy(canonical_structure)
    final["tables"].extend(deepcopy([t for t in known_restored_structure["tables"] if t["schema"] == "public"]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection = _TransactionalConnection(known_restored_structure)
    connection.post_ddl_structure = final
    result, _engine, _calls, _configured = _adopt(monkeypatch, connection)
    executed_ddl = "\n".join(connection.ddl).upper()
    assert len(result.operations) == 14
    assert not re.search(
        r"(?:\bDROP\b|\bTRUNCATE\b|\bDELETE\s+FROM\b|\bUPDATE\s+[A-Z_]|"
        r"\bINSERT\s+INTO\b|\bSELECT\b)",
        executed_ddl,
    )
    assert "PUBLIC.USERS" not in executed_ddl
    assert "PUBLIC.API_KEYS" not in executed_ddl
    assert "credential-bearing-test-dsn" not in repr(result)


def _expected_relation_locks(structure, *, version_table=False):
    relations = {
        f"{table['schema']}.{table['name']}" for table in structure["tables"]
    }
    if version_table:
        relations.add("public.alembic_version")
    return tuple(
        f'LOCK TABLE "{schema}"."{name}" IN ACCESS SHARE MODE'
        for schema, name in (relation.split(".", 1) for relation in sorted(relations))
    )


def test_valid_adoption_locks_existing_approved_relations_in_static_sorted_order(
    monkeypatch, known_restored_structure, canonical_structure
):
    connection = _TransactionalConnection(
        known_restored_structure, version_table=True
    )
    final = deepcopy(canonical_structure)
    final["tables"].extend(
        deepcopy([t for t in known_restored_structure["tables"] if t["schema"] == "public"])
    )
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection.post_ddl_structure = final

    _adopt(monkeypatch, connection)

    assert tuple(connection.locks) == _expected_relation_locks(
        known_restored_structure, version_table=True
    )
    assert all("ACCESS SHARE MODE" in sql for sql in connection.locks)
    assert not any('"app"."api_keys"' in sql for sql in connection.locks)
    assert not any('"raw"."api_responses_2026_07"' in sql for sql in connection.locks)
    assert not any('"raw"."api_responses_2026_08"' in sql for sql in connection.locks)
    assert any('"public"."users"' in sql for sql in connection.locks)
    assert any('"public"."api_keys"' in sql for sql in connection.locks)


def test_advisory_lock_precedes_relation_locks_and_reinventory_precedes_ddl(
    monkeypatch, known_restored_structure, canonical_structure
):
    connection = _TransactionalConnection(known_restored_structure)
    connection.post_ddl_structure = canonical_structure
    inventory_positions = []
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)

    def inventory(supplied, *, target):
        assert supplied is connection
        inventory_positions.append(len(connection.sql))
        return _live(supplied)

    monkeypatch.setattr(adoption, "inventory_connection", inventory)
    adoption.adopt_wp3_schema(
        "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
    )

    advisory = next(i for i, sql in enumerate(connection.sql) if "PG_ADVISORY_XACT_LOCK" in sql.upper())
    first_lock = next(i for i, sql in enumerate(connection.sql) if sql.upper().startswith("LOCK TABLE"))
    first_ddl = next(i for i, sql in enumerate(connection.sql) if sql.upper().startswith("CREATE "))
    assert advisory < inventory_positions[0] < first_lock < inventory_positions[1] < first_ddl
    assert engine.begin_count == 1 and engine.commits == 1
    assert len(inventory_positions) == 4


def test_locked_revalidation_mutation_rejects_before_ddl_or_stamp(
    monkeypatch, known_restored_structure
):
    connection = _TransactionalConnection(known_restored_structure)
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)
    calls = 0

    def inventory(supplied, *, target):
        nonlocal calls
        calls += 1
        result = _live(supplied)
        if calls == 1:
            _remove_table(connection.structure, "core.sources")
        return result

    monkeypatch.setattr(adoption, "inventory_connection", inventory)
    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )

    assert raised.value.reason is AdoptionReason.LOCKED_REVALIDATION_DRIFT
    assert connection.ddl == [] and connection.stamp_calls == 0
    assert engine.rollbacks == 1


def test_relation_lock_failure_rolls_back_without_ddl_or_stamp(
    monkeypatch, known_restored_structure
):
    connection = _TransactionalConnection(known_restored_structure)
    connection.fail_lock_at = 3
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)

    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )

    assert raised.value.reason is AdoptionReason.RELATION_LOCK_FAILED
    assert connection.ddl == [] and connection.stamp_calls == 0
    assert engine.rollbacks == 1


def test_invalid_initial_profile_takes_no_relation_locks(monkeypatch, known_restored_structure):
    malicious = deepcopy(next(iter(known_restored_structure["tables"])))
    malicious["schema"] = 'evil"; DROP TABLE app.users; --'
    known_restored_structure["tables"].append(malicious)
    connection = _TransactionalConnection(known_restored_structure)
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)

    with pytest.raises(AdoptionError) as raised:
        adoption.adopt_wp3_schema(
            "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
        )

    assert raised.value.reason is AdoptionReason.UNSTAMPED_STRUCTURE_REJECTED
    assert connection.locks == [] and connection.ddl == [] and connection.stamp_calls == 0
    assert not any("DROP TABLE" in sql for sql in connection.sql)
    assert engine.rollbacks == 1


def test_already_002_locks_and_revalidates_before_noop(monkeypatch, canonical_structure):
    connection = _TransactionalConnection(
        canonical_structure, versions=["002"], version_table=True
    )
    inventory_connections = []
    engine, guard, _calls, _configured = _install_boundaries(monkeypatch, connection)

    def inventory(supplied, *, target):
        inventory_connections.append(supplied)
        return _live(supplied)

    monkeypatch.setattr(adoption, "inventory_connection", inventory)
    result = adoption.adopt_wp3_schema(
        "test-dsn", guard=guard, contract_path=CONTRACT_PATH, source_root=ROOT
    )

    assert result.status is adoption.AdoptionStatus.ALREADY_ADOPTED
    assert tuple(connection.locks) == _expected_relation_locks(
        canonical_structure, version_table=True
    )
    assert inventory_connections == [connection, connection]
    assert connection.ddl == [] and connection.stamp_calls == 0
    assert engine.begin_count == 1 and engine.commits == 1


def _alembic_version_table() -> dict:
    """The Alembic history relation exactly as the live inventory reports it."""
    return {
        "schema": "public",
        "name": "alembic_version",
        "columns": [{
            "name": "version_num", "type": "VARCHAR(32)", "nullable": False,
            "default": None, "identity": None, "generated": None,
        }],
        "primary_key": ["version_num"],
        "unique": [],
        "foreign_keys": [],
        "checks": [],
        "indexes": [],
        "partition_key": None,
        "parent_schema": None,
        "parent_table": None,
        "partition_bounds": None,
    }


def _with_alembic_version(structure: dict) -> dict:
    structure = deepcopy(structure)
    structure["tables"].append(_alembic_version_table())
    structure["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    return structure


def test_stamped_inventory_listing_alembic_version_is_already_adopted(
    monkeypatch, canonical_structure
):
    structure = _with_alembic_version(canonical_structure)
    connection = _TransactionalConnection(structure, versions=["002"], version_table=True)
    result, engine, _calls, configured = _adopt(monkeypatch, connection)
    assert result.status is adoption.AdoptionStatus.ALREADY_ADOPTED
    assert result.reason is AdoptionReason.ALREADY_002_NOOP
    assert connection.ddl == [] and connection.stamp_calls == 0 and configured == []
    assert connection.locks.count(
        'LOCK TABLE "public"."alembic_version" IN ACCESS SHARE MODE'
    ) == 1
    assert tuple(connection.locks) == _expected_relation_locks(
        structure, version_table=True
    )
    assert engine.begin_count == 1 and engine.commits == 1 and engine.rollbacks == 0


def test_approved_relations_accept_alembic_version_exactly_once(
    canonical_structure, contract
):
    relations = adoption._approved_existing_relations(
        _with_alembic_version(canonical_structure), contract, version_table_exists=True
    )
    assert relations.count("public.alembic_version") == 1
    assert relations == tuple(sorted(relations))


def test_unknown_relation_beside_alembic_version_stays_rejected(
    canonical_structure, contract
):
    structure = _with_alembic_version(canonical_structure)
    rogue = _alembic_version_table()
    rogue["name"] = "alembic_version_backup"
    structure["tables"].append(rogue)
    with pytest.raises(AdoptionError) as raised:
        adoption._approved_existing_relations(
            structure, contract, version_table_exists=True
        )
    assert raised.value.reason is AdoptionReason.LOCKED_REVALIDATION_DRIFT


def test_alembic_version_outside_public_schema_stays_rejected(
    canonical_structure, contract
):
    structure = deepcopy(canonical_structure)
    rogue = _alembic_version_table()
    rogue["schema"] = "app"
    structure["tables"].append(rogue)
    with pytest.raises(AdoptionError) as raised:
        adoption._approved_existing_relations(
            structure, contract, version_table_exists=True
        )
    assert raised.value.reason is AdoptionReason.LOCKED_REVALIDATION_DRIFT


def test_alembic_version_entry_without_catalog_confirmation_stays_rejected(
    canonical_structure, contract
):
    with pytest.raises(AdoptionError) as raised:
        adoption._approved_existing_relations(
            _with_alembic_version(canonical_structure), contract,
            version_table_exists=False,
        )
    assert raised.value.reason is AdoptionReason.LOCKED_REVALIDATION_DRIFT


def test_unstamped_inventory_listing_empty_alembic_version_table_adopts(
    monkeypatch, known_restored_structure, canonical_structure
):
    structure = _with_alembic_version(known_restored_structure)
    final = _with_alembic_version(canonical_structure)
    final["tables"].extend(
        deepcopy([
            table for table in known_restored_structure["tables"]
            if table["schema"] == "public"
        ])
    )
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))
    connection = _TransactionalConnection(structure, versions=[], version_table=True)
    connection.post_ddl_structure = final
    result, engine, _calls, _configured = _adopt(monkeypatch, connection)
    assert result.status is adoption.AdoptionStatus.ADOPTED
    assert result.reason is AdoptionReason.ADOPTED_TO_002
    assert len(result.operations) == 14
    assert connection.versions == ["002"]
    assert connection.locks.count(
        'LOCK TABLE "public"."alembic_version" IN ACCESS SHARE MODE'
    ) == 1
    assert tuple(connection.locks) == _expected_relation_locks(
        structure, version_table=True
    )
    assert engine.begin_count == 1 and engine.commits == 1 and engine.rollbacks == 0


# =============================================================================
# WP3 BRIDGE — metadata reconciliation tests (100 ops, dry-run + atomic apply)
# =============================================================================
#
# These tests pin the bridge between ``scripts.adopt_wp3_schema`` and the
# offline catalogue in ``scripts.wp3_reconcile_metadata``. They were authored
# first (RED) and drive the minimal bridge injection in ``adopt_wp3_schema``.
#
# All 100 metadata ops come from ``scripts.wp3_reconcile_metadata.ALL_OPS``
# (67 SET DEFAULT + 33 DROP NOT NULL). No data writes are introduced; the
# bridge only emits ALTER TABLE statements drawn from the closed allowlist.
# -----------------------------------------------------------------------------

from scripts.wp3_reconcile_metadata import (  # noqa: E402  -- isolated section
    ALL_OPS as _ALL_METADATA_OPS,
    build_metadata_plan,
    render_sql,
)


def _legacy_structure(contract) -> dict:
    """Build a structure that has every column the catalogue addresses but
    where every SET DEFAULT and every DROP NOT NULL is still pending.

    The legacy v1/v2 schema exposed the columns WITHOUT default expressions
    (default is None) and with NOT NULL on every catalogue column.  The
    result is that all 100 ops of the catalogue must be emitted, in the
    exact catalogue order, against this structure.
    """
    from copy import deepcopy
    structure = deepcopy(contract.canonical)
    catalogue_targets = {(op.schema, op.table) for op in _ALL_METADATA_OPS}
    for table in structure["tables"]:
        qualified = f"{table['schema']}.{table['name']}"
        if (table["schema"], table["name"]) not in catalogue_targets:
            continue
        # Match qualified keys for the catalogue — schema must be in {app, core, events, raw}.
        if qualified.split(".", 1)[0] not in {"app", "core", "events", "raw"}:
            continue
        for column in table.get("columns", ()):
            column_name = column.get("name")
            if any(op.column == column_name and (op.schema, op.table) == (table["schema"], table["name"])
                   for op in _ALL_METADATA_OPS):
                # Legacy: no default expression set on column, and NOT NULL.
                column["default"] = None
                column["nullable"] = False
    return structure


def _canonical_structure_with_defaults(contract) -> dict:
    """Build a structure that matches the catalogue exactly: every catalogue
    column carries the canonical default expression and is nullable.
    ``build_metadata_plan`` MUST return an empty tuple.
    """
    from copy import deepcopy
    structure = deepcopy(contract.canonical)
    for table in structure["tables"]:
        for column in table.get("columns", ()):
            for op in _ALL_METADATA_OPS:
                if (op.schema, op.table, op.column) == (
                    table["schema"], table["name"], column["name"]
                ):
                    if op.kind.value == "set_default":
                        column["default"] = op.expression
                    else:
                        column["nullable"] = True
                    break
    return structure


def test_legacy_inventory_yields_exactly_ordered_100_metadata_ops(contract):
    """build_metadata_plan against the legacy shape returns ALL_OPS in order."""
    structure = _legacy_structure(contract)
    plan = build_metadata_plan(structure)
    assert len(plan) == len(_ALL_METADATA_OPS) == 100
    assert tuple(op.key for op in plan) == tuple(op.key for op in _ALL_METADATA_OPS)


def test_existing_canonical_state_yields_zero_metadata_ops(contract):
    """When every catalogue column already matches, build_metadata_plan is empty."""
    structure = _canonical_structure_with_defaults(contract)
    plan = build_metadata_plan(structure)
    assert plan == ()


def test_render_sql_emits_exact_static_ddl_text(contract):
    """render_sql produces one canonical SQL statement per catalogue op,
    no string interpolation beyond the closed allowlist."""
    structure = _canonical_structure_with_defaults(contract)
    plan = build_metadata_plan(structure)
    assert plan == ()  # canonical state → no DDL produced
    # Spot-check the renderer against a known SET DEFAULT and DROP NOT NULL entry.
    sd_op = next(op for op in _ALL_METADATA_OPS if op.kind.value == "set_default")
    nn_op = next(op for op in _ALL_METADATA_OPS if op.kind.value == "drop_not_null")
    assert render_sql(sd_op) == (
        f'ALTER TABLE "{sd_op.schema}"."{sd_op.table}" '
        f'ALTER COLUMN "{sd_op.column}" SET DEFAULT {sd_op.expression};'
    )
    assert render_sql(nn_op) == (
        f'ALTER TABLE "{nn_op.schema}"."{nn_op.table}" '
        f'ALTER COLUMN "{nn_op.column}" DROP NOT NULL;'
    )


def test_adopt_metadata_apply_runs_inside_engine_begin_between_locks_and_stamp(
    monkeypatch, contract, canonical_structure, known_restored_structure
):
    """Atomic apply: metadata DDL is executed inside engine.begin(), AFTER
    relation locks and BEFORE the Alembic stamp. No extra commit, no extra
    transaction, no SET NOT NULL and no data writes.

    Strategy: structure starts as the *known_restored* (pre-DDL) inventory;
    after the 14 additive DDLs the mock flips structure to canonical, then
    metadata bridge runs 100 ALTER TABLEs (all already applied against the
    canonical structure, so plan must be empty in real use — we inject a
    fake plan to prove the call-site runs between locks and stamp).
    """
    structure = known_restored_structure
    final = _canonical_structure_with_defaults(contract)
    final["tables"].extend(deepcopy([
        table for table in known_restored_structure["tables"]
        if table["schema"] == "public"
    ]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))

    connection = _TransactionalConnection(structure, versions=[], version_table=True)
    connection.post_ddl_structure = final

    catalogue_sql = [render_sql(op) for op in _ALL_METADATA_OPS]

    def _fake_plan(_structure):
        return tuple(_ALL_METADATA_OPS)

    engine, guard, calls, configured = _install_boundaries(
        monkeypatch, connection, head="002", stamp_version="002",
    )
    monkeypatch.setattr(adoption, "build_metadata_plan", _fake_plan)

    result = adoption.adopt_wp3_schema(
        "credential-bearing-test-dsn",
        guard=guard,
        contract_path=CONTRACT_PATH,
        source_root=ROOT,
    )

    # All 100 catalogue SQL fragments must have been emitted as ALTER TABLE.
    assert len(connection.metadata_ddl) == 100
    assert tuple(connection.metadata_ddl) == tuple(catalogue_sql)
    # Ordering: last LOCK before first metadata ALTER.
    last_lock_idx = max(
        i for i, sql in enumerate(connection.sql) if sql.upper().startswith("LOCK TABLE")
    )
    first_metadata_idx = next(
        i for i, sql in enumerate(connection.sql)
        if sql.upper().startswith("ALTER TABLE")
    )
    assert last_lock_idx < first_metadata_idx
    # The 14 additive DDLs also ran (CREATE TABLE / CREATE INDEX) before
    # the metadata bridge.
    assert len(connection.ddl) == 14
    # Stamp fired on success path inside the same engine.begin() transaction.
    assert connection.versions == ["002"]
    assert connection.stamp_calls == 1
    assert engine.begin_count == 1 and engine.commits == 1 and engine.rollbacks == 0
    assert result.status is adoption.AdoptionStatus.ADOPTED
    assert result.reason is AdoptionReason.ADOPTED_TO_002


def test_adopt_metadata_plan_failure_aborts_before_stamp(
    monkeypatch, contract, canonical_structure, known_restored_structure
):
    """When build_metadata_plan raises ContractDeltaUnmapped (production
    lets it propagate, no try/except at the planner call site), the
    transaction rolls back and the Alembic stamp is NEVER reached."""
    from scripts.wp3_reconcile_metadata import ContractDeltaUnmapped

    structure = known_restored_structure
    final = _canonical_structure_with_defaults(contract)
    final["tables"].extend(deepcopy([
        table for table in known_restored_structure["tables"]
        if table["schema"] == "public"
    ]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))

    connection = _TransactionalConnection(structure, versions=[], version_table=True)
    connection.post_ddl_structure = final

    def _explode(_structure):
        raise ContractDeltaUnmapped("unapproved identifier: synthetic.delta")

    engine, guard, calls, configured = _install_boundaries(
        monkeypatch, connection, head="002", stamp_version="002",
    )
    monkeypatch.setattr(adoption, "build_metadata_plan", _explode)

    with pytest.raises(ContractDeltaUnmapped, match="synthetic.delta"):
        adoption.adopt_wp3_schema(
            "credential-bearing-test-dsn",
            guard=guard,
            contract_path=CONTRACT_PATH,
            source_root=ROOT,
        )
    # Stamp was never reached, no metadata DDL was emitted.
    assert connection.stamp_calls == 0
    assert connection.versions == []
    assert connection.metadata_ddl == []
    # engine.begin() never entered because the raise happens before the
    # bridge runs and connection.execute of the DDLs raises immediately
    # inside the same block. But the 14-DDL plan IS empty (canonical),
    # so no DDL loop runs; the planner call is the only thing that runs
    # in the bridge region, and its raise aborts before inventory re-read
    # and stamp.
    assert engine.commits == 0


def test_adopt_metadata_exception_rolls_back_transaction(
    monkeypatch, contract, canonical_structure, known_restored_structure
):
    """If metadata DDL execution raises mid-apply, the engine.begin() block
    rolls back (engine.rollbacks == 1) and the stamp is never emitted."""
    structure = known_restored_structure
    final = _canonical_structure_with_defaults(contract)
    final["tables"].extend(deepcopy([
        table for table in known_restored_structure["tables"]
        if table["schema"] == "public"
    ]))
    final["tables"].sort(key=lambda table: (table["schema"], table["name"]))

    connection = _TransactionalConnection(structure, versions=[], version_table=True)
    connection.structure = deepcopy(final)

    from scripts.wp3_reconcile_metadata import MetadataOp, OpKind
    synthetic_op = MetadataOp(
        "app.alert_deliveries.created_at.default",
        "app", "alert_deliveries", "created_at",
        OpKind.SET_DEFAULT, "NOW()",
    )

    def _fake_plan(_structure):
        return (synthetic_op,)

    # Pre-arm the connection mock so the synthetic SQL raises on execute.
    orig_execute = connection.execute
    def _raising_execute(stmt):
        sql = str(stmt).strip()
        if "FAIL HERE" in sql:
            raise RuntimeError("induced metadata execution failure")
        return orig_execute(stmt)
    connection.execute = _raising_execute  # type: ignore[method-assign]

    engine, guard, calls, configured = _install_boundaries(
        monkeypatch, connection, head="002", stamp_version="002",
    )
    monkeypatch.setattr(adoption, "build_metadata_plan", _fake_plan)
    monkeypatch.setattr(adoption, "render_sql", lambda _op: "ALTER TABLE x FAIL HERE;")

    try:
        with pytest.raises(AdoptionError) as excinfo:
            adoption.adopt_wp3_schema(
                "credential-bearing-test-dsn",
                guard=guard,
                contract_path=CONTRACT_PATH,
                source_root=ROOT,
            )
        assert excinfo.value.reason is AdoptionReason.RECONCILIATION_FAILED
        assert engine.rollbacks == 1
        assert engine.commits == 0
        assert connection.stamp_calls == 0
        assert connection.versions == []
    finally:
        connection.execute = orig_execute  # type: ignore[method-assign]


def test_dry_run_path_executes_zero_sql(contract):
    """The dry-run audit shape is read-only: calling build_metadata_plan
    against either the legacy or the canonical structure must NEVER touch
    any connection or execute any DDL.  The bridge must preserve this."""
    from scripts.wp3_reconcile_metadata import dry_run
    legacy = _legacy_structure(contract)
    canonical = _canonical_structure_with_defaults(contract)

    legacy_audit = dry_run(legacy)
    canonical_audit = dry_run(canonical)

    # Legacy: every catalogue op is pending → exactly 100 ops in catalogue
    # order, no skip and no blocked entries.
    assert len(legacy_audit["ops"]) == 100
    assert legacy_audit["skip"] == []
    assert legacy_audit["blocked"] == []
    assert [op["key"] for op in legacy_audit["ops"]] == [
        op.key for op in _ALL_METADATA_OPS
    ]
    # Canonical: everything already applied, no ops and no blocked.
    assert canonical_audit["ops"] == []
    assert canonical_audit["blocked"] == []
