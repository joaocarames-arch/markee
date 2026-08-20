"""Offline, fail-closed structural classification for WP3 schema adoption.

This module only compares an already collected catalog structure with a signed
contract.  It never opens a connection, emits SQL, executes DDL, or inspects an
Alembic stamp.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from scripts.drift_inventory import LiveInventory, index_signature

DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parent / "contracts" / "wp3_002_structure.json"
_EXPECTED_ID = "markee-wp3-002-structure"
_EXPECTED_FORMAT_VERSION = 1
_EXPECTED_CONTRACT_VERSION = 3
_EXPECTED_CANONICAL_REVISION = "002"
_EXPECTED_DERIVATION = "empty_database_alembic_upgrade_001_to_002_static_review"
_PROVENANCE_FIELDS = {"canonical_revision", "derivation", "migration_sha256"}
_MIGRATION_PATHS = {
    "001_initial_migration.py": ("alembic", "versions", "001_initial_migration.py"),
    "002_data_infrastructure.py": ("alembic", "versions", "002_data_infrastructure.py"),
}
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}")
_SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast"}


class ContractError(ValueError):
    """Invalid, unsupported or tampered adoption contract."""


class AdoptionVerdict(StrEnum):
    ADOPTABLE_RESTORED = "adoptable_restored"
    ALREADY_FINAL = "already_final"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class ReasonCode(StrEnum):
    KNOWN_RESTORED_PROFILE = "known_restored_profile"
    CANONICAL_FINAL_STRUCTURE = "canonical_final_structure"
    EMPTY_APPLICATION_STRUCTURE = "empty_application_structure"
    CONTRACT_INTEGRITY_FAILURE = "contract_integrity_failure"
    CONTRACT_VERSION_UNSUPPORTED = "contract_version_unsupported"
    REQUIRED_SCHEMA_MISSING = "required_schema_missing"
    UNKNOWN_SCHEMA = "unknown_schema"
    REQUIRED_EXTENSION_MISSING = "required_extension_missing"
    UNKNOWN_EXTENSION = "unknown_extension"
    REQUIRED_TABLE_MISSING = "required_table_missing"
    UNKNOWN_TABLE = "unknown_table"
    LEGACY_TABLE_MISSING = "legacy_table_missing"
    TABLE_SIGNATURE_MISMATCH = "table_signature_mismatch"
    COLUMN_MISSING = "column_missing"
    COLUMN_UNEXPECTED = "column_unexpected"
    COLUMN_TYPE_MISMATCH = "column_type_mismatch"
    COLUMN_NULLABILITY_MISMATCH = "column_nullability_mismatch"
    COLUMN_DEFAULT_MISMATCH = "column_default_mismatch"
    PRIMARY_KEY_MISMATCH = "primary_key_mismatch"
    UNIQUE_MISMATCH = "unique_mismatch"
    CHECK_MISMATCH = "check_mismatch"
    FOREIGN_KEY_MISMATCH = "foreign_key_mismatch"
    INDEX_REQUIRED_MISSING = "index_required_missing"
    INDEX_UNEXPECTED = "index_unexpected"
    PARTITION_KEY_MISMATCH = "partition_key_mismatch"
    PARTITION_PARENT_MISMATCH = "partition_parent_mismatch"
    PARTITION_BOUNDS_MISMATCH = "partition_bounds_mismatch"


@dataclass(frozen=True)
class Difference:
    code: ReasonCode
    path: str
    expected: Any = None
    observed: Any = None


@dataclass(frozen=True)
class AdoptionContract:
    format_version: int
    contract_id: str
    contract_version: int
    payload_sha256: str
    canonical: Mapping[str, Any]
    required_extensions: frozenset[str]
    optional_extensions: frozenset[str]
    legacy_public_tables: Mapping[str, Mapping[str, Any]]
    allowed_missing_tables: frozenset[str]
    allowed_missing_indexes: Mapping[str, frozenset[str]]
    allowed_extra_indexes: Mapping[str, frozenset[str]]
    allowed_missing_partitions: Mapping[str, Mapping[str, Any]]


@dataclass(frozen=True)
class Classification:
    verdict: AdoptionVerdict
    reasons: tuple[ReasonCode, ...]
    differences: tuple[Difference, ...]
    structural_fingerprint: str
    contract_id: str
    contract_version: int
    contract_payload_sha256: str

    @property
    def accepted(self) -> bool:
        return self.verdict in {AdoptionVerdict.ADOPTABLE_RESTORED, AdoptionVerdict.ALREADY_FINAL}


def canonical_json(value: Any) -> bytes:
    """Return deterministic ASCII JSON used for contract integrity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _require_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        raise ContractError(f"invalid {where} fields")


def _validate_provenance(value: Any, source_root: Path | None) -> None:
    if not isinstance(value, dict):
        raise ContractError("invalid provenance object")
    _require_keys(value, _PROVENANCE_FIELDS, "provenance")
    revision = value["canonical_revision"]
    if not isinstance(revision, str):
        raise ContractError("invalid canonical revision")
    if revision != _EXPECTED_CANONICAL_REVISION:
        raise ContractError("canonical revision unsupported")
    derivation = value["derivation"]
    if not isinstance(derivation, str):
        raise ContractError("invalid provenance derivation")
    if derivation != _EXPECTED_DERIVATION:
        raise ContractError("provenance derivation unsupported")
    expected_hashes = value["migration_sha256"]
    if not isinstance(expected_hashes, dict) or set(expected_hashes) != set(_MIGRATION_PATHS):
        raise ContractError("invalid migration provenance")
    if any(
        not isinstance(digest, str) or _LOWER_SHA256.fullmatch(digest) is None
        for digest in expected_hashes.values()
    ):
        raise ContractError("invalid migration provenance")
    if source_root is None:
        return
    try:
        root = Path(source_root).resolve(strict=True)
    except OSError as exc:
        raise ContractError("migration source root unavailable") from exc
    for name, relative_parts in _MIGRATION_PATHS.items():
        source_path = root.joinpath(*relative_parts)
        current = root
        try:
            for part in relative_parts:
                current = current / part
                if current.is_symlink():
                    raise ContractError(f"migration source path invalid: {name}")
            resolved_source = source_path.resolve(strict=True)
            resolved_source.relative_to(root)
        except ContractError:
            raise
        except (OSError, ValueError) as exc:
            raise ContractError(f"migration source path invalid: {name}") from exc
        try:
            source_hash = hashlib.sha256(resolved_source.read_bytes()).hexdigest()
        except OSError as exc:
            raise ContractError(f"migration source unavailable: {name}") from exc
        if source_hash != expected_hashes[name]:
            raise ContractError(f"migration source hash mismatch: {name}")


def load_contract(path: Path = DEFAULT_CONTRACT_PATH, *, source_root: Path | None = None) -> AdoptionContract:
    """Load and validate contract schema, version, integrity and provenance."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("invalid contract document") from exc
    if not isinstance(document, dict):
        raise ContractError("invalid contract document")
    _require_keys(document, {"format_version", "contract_id", "contract_version", "payload", "integrity"}, "top-level")
    if type(document["format_version"]) is not int or document["format_version"] != _EXPECTED_FORMAT_VERSION:
        raise ContractError("contract format version unsupported")
    if document["contract_id"] != _EXPECTED_ID:
        raise ContractError("contract id unsupported")
    if type(document["contract_version"]) is not int or document["contract_version"] != _EXPECTED_CONTRACT_VERSION:
        raise ContractError("contract version unsupported")
    integrity = document["integrity"]
    if not isinstance(integrity, dict):
        raise ContractError("invalid contract integrity")
    _require_keys(integrity, {"algorithm", "payload_sha256"}, "integrity")
    if integrity["algorithm"] != "sha256":
        raise ContractError("contract integrity algorithm unsupported")
    actual_hash = hashlib.sha256(canonical_json(document["payload"])).hexdigest()
    if actual_hash != integrity["payload_sha256"]:
        raise ContractError("contract payload hash mismatch")
    payload = document["payload"]
    if not isinstance(payload, dict):
        raise ContractError("invalid contract payload")
    _require_keys(payload, {"provenance", "extensions", "canonical", "legacy_public_tables", "adoptable_restored_profile"}, "payload")
    _validate_provenance(payload["provenance"], source_root)
    profile = payload["adoptable_restored_profile"]
    _require_keys(profile, {"allowed_missing_tables", "allowed_missing_indexes", "allowed_extra_indexes", "allowed_missing_partitions", "reconciliation_operations"}, "restored profile")
    if profile["allowed_missing_tables"] != ["app.api_keys"] or profile["reconciliation_operations"] != {"app.api_keys": "create_empty_canonical_table_preserve_public_api_keys"}:
        raise ContractError("invalid app.api_keys reconciliation rule")

    extensions = payload["extensions"]
    canonical = payload["canonical"]
    legacy = payload["legacy_public_tables"]
    if len(legacy) != 14 or set(legacy) != {
        "public.alert_deliveries", "public.alerts", "public.api_keys", "public.client_portfolios",
        "public.deadlines", "public.lifecycle_events", "public.prospection_opportunities",
        "public.subscriptions", "public.team_members", "public.teams", "public.trademarks",
        "public.users", "public.watchlist_items", "public.watchlists",
    }:
        raise ContractError("invalid legacy public table allowlist")
    return AdoptionContract(
        format_version=_EXPECTED_FORMAT_VERSION, contract_id=_EXPECTED_ID,
        contract_version=_EXPECTED_CONTRACT_VERSION,
        payload_sha256=actual_hash, canonical=canonical,
        required_extensions=frozenset(extensions["required"]),
        optional_extensions=frozenset(extensions["optional"]),
        legacy_public_tables=legacy,
        allowed_missing_tables=frozenset(profile["allowed_missing_tables"]),
        allowed_missing_indexes={k: frozenset(v) for k, v in profile["allowed_missing_indexes"].items()},
        allowed_extra_indexes={k: frozenset(v) for k, v in profile["allowed_extra_indexes"].items()},
        allowed_missing_partitions=profile["allowed_missing_partitions"],
    )


def _qualified(table: Mapping[str, Any]) -> str:
    return f"{table.get('schema')}.{table.get('name')}"


def _normalise_table(table: Mapping[str, Any]) -> dict[str, Any]:
    """Whitelist table metadata and turn index mappings into semantic hashes."""
    indexes = []
    for index in table.get("indexes", ()):
        indexes.append(index if isinstance(index, str) else index_signature(index))
    foreign_keys = []
    for fk in table.get("foreign_keys", ()):
        foreign_keys.append({
            "columns": list(fk.get("columns", ())), "target_schema": fk.get("target_schema"),
            "target_table": fk.get("target_table"), "target_columns": list(fk.get("target_columns", ())),
            "ondelete": fk.get("ondelete"), "onupdate": fk.get("onupdate"),
            "deferrable": bool(fk.get("deferrable", False)), "initially": fk.get("initially"),
        })
    deduped = _dedupe_unique_indexes({**table, "indexes": indexes})
    return {
        "schema": table.get("schema"), "name": table.get("name"),
        "columns": [{
            "name": c.get("name"), "type": c.get("type"), "nullable": bool(c.get("nullable", True)),
            "default": c.get("default"), "identity": c.get("identity"),
            "generated": c.get("generated", c.get("computed")),
        } for c in table.get("columns", ())],
        "primary_key": list(table.get("primary_key", ())),
        "unique": deduped["unique"],
        "foreign_keys": sorted(foreign_keys, key=canonical_json),
        "checks": sorted([
            _normalise_check(check) or check
            for check in table.get("checks", ())
        ]),
        "indexes": deduped["indexes"],
        "partition_key": table.get("partition_key"), "parent_schema": table.get("parent_schema"),
        "parent_table": table.get("parent_table"), "partition_bounds": table.get("partition_bounds"),
    }


def _difference(code: ReasonCode, path: str, expected: Any, observed: Any) -> Difference:
    return Difference(code=code, path=path, expected=expected, observed=observed)


_STANDALONE_NOW = re.compile(r"now\(\)", re.IGNORECASE)

# --- WP3 reconciliation: canonicalisations (v3) -------------------------------
# PostgreSQL semantically rewrites `col IN (...)` as
# `col::text = ANY (ARRAY['x'::character varying, ...]::text[])`. The two
# renderings are equivalent; the classifier must accept both without DDL.
_SQL_STRING_LITERAL = r"'(?:[^']|'')*'"
_SQL_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_CHECK_IN_FORM = re.compile(rf"({_SQL_IDENTIFIER}) IN \((.+)\)")
# The clone renders the IN(...) rewrite as either of two shapes:
#   - ``col::text = ANY (ARRAY[<x>::character varying::text, ...])``
#     (this is what the WP3 evidence emits in /tmp/markee-wp3-restored-clone-v2).
#   - ``col::text = ANY (ARRAY[<x>::character varying, ...]::text[])``
#     (the alternative PG16 sometimes produces). Both must canonicalise to
#     the same ``<col> IN (<literals>)`` form. The trailing cast after
#     ``]`` is optional; the inner ``::character varying(<n>)::text`` cast
#     on each literal is also optional (some literals may omit it).
_CHECK_ANY_FORM = re.compile(
    rf"({_SQL_IDENTIFIER})::text = ANY \(ARRAY\[(.+?)\](?:::[\w\[\]]+)?\)"
)
_IN_SET_LITERAL = re.compile(rf"({_SQL_STRING_LITERAL})")
# A literal in the ARRAY is either ``'x'::character varying``,
# ``'x'::character varying(<n>)``, ``'x'::character varying::text``,
# ``'x'::character varying(<n>)::text``, or just ``'x'``. We strip every
# legal cast suffix to expose the raw string literal.
_ANY_SET_LITERAL = re.compile(
    rf"({_SQL_STRING_LITERAL})(?:::(?:character varying(?:\(\d+\))?(?:::\w+)?|text))?"
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
    ``col::text = ANY (ARRAY['a'::character varying, ...]::text[])``. Both
    reduce to the ``IN`` rendering with member order preserved. Only the
    exact casts of that expansion are accepted; anything else passes through
    untouched and keeps producing drift.
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


_INDEX_KEY_FIELDS = ("expr", "opclass", "collation", "sort", "nulls")


def _normalise_index_key(key: Mapping) -> dict:
    """Reduce a catalog index key to its contract shape."""
    return {name: key.get(name) for name in _INDEX_KEY_FIELDS}


def _plain_unique_columns(index: Mapping) -> tuple[str, ...] | None:
    """Return columns when an index exactly matches plain UNIQUE semantics."""
    if not index.get("unique") or (index.get("method") or "btree") != "btree":
        return None
    if index.get("predicate") is not None or list(index.get("include", ())) != []:
        return None
    columns: list[str] = []
    for key in index.get("keys", ()):
        if (
            key.get("opclass") is not None
            or key.get("collation") is not None
            or key.get("sort") not in (None, "asc")
            or key.get("nulls") not in (None, "last")
        ):
            return None
        expression = key.get("expr")
        if not isinstance(expression, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
            return None
        columns.append(expression)
    return tuple(columns) if columns else None


def _dedupe_unique_indexes(table: Mapping[str, Any]) -> dict[str, Any]:
    """Subtract from ``indexes`` those that are equivalent to a unique set.

    The contract declares a table's unique set separately from its extra
    indexes; the clone often materialises a plain unique constraint as an
    implicit unique btree index. Merging those into the unique set in BOTH
    sides (expected and observed) lets the structural classifier compare
    apples to apples without DDL.
    """
    uniqueness = {tuple(columns) for columns in table.get("unique", ())}
    semantic_indexes: list[str] = []
    for index in table.get("indexes", ()):
        if isinstance(index, str):
            try:
                index = json.loads(index)
            except json.JSONDecodeError:
                semantic_indexes.append(index)
                continue
        if not isinstance(index, Mapping):
            continue
        normalised_index: dict[str, Any] = {
            "unique": bool(index.get("unique")),
            "method": index.get("method") or "btree",
            "keys": [_normalise_index_key(key) for key in index.get("keys", ())],
            "include": list(index.get("include", ())),
            "predicate": index.get("predicate"),
        }
        equivalent_unique = _plain_unique_columns(normalised_index)
        if equivalent_unique is None:
            semantic_indexes.append(
                json.dumps(normalised_index, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            )
        else:
            uniqueness.add(equivalent_unique)
    return {
        "unique": sorted([list(columns) for columns in uniqueness]),
        "indexes": sorted(set(semantic_indexes)),
    }


def _comparable_default(value: Any) -> Any:
    """Canonicalise standalone NOW()/now() case variants for equality only.

    PostgreSQL renders ``NOW()`` written in DDL back as ``now()``; the contract
    legitimately carries both spellings. Anything beyond a bare case variant —
    ``timezone(...)``, ``clock_timestamp()``, casts, wrapping parentheses or
    larger expressions — is left untouched and still compares raw.
    """
    if isinstance(value, str) and _STANDALONE_NOW.fullmatch(value):
        return "now()"
    return value


def _compare_table(expected: Mapping[str, Any], observed: Mapping[str, Any], qualified: str, *, missing_indexes: frozenset[str] = frozenset(), extra_indexes: frozenset[str] = frozenset()) -> list[Difference]:
    expected = _normalise_table(expected); observed = _normalise_table(observed); out: list[Difference] = []
    ec = {c["name"]: c for c in expected["columns"]}; oc = {c["name"]: c for c in observed["columns"]}
    for name in sorted(ec.keys() - oc.keys()): out.append(_difference(ReasonCode.COLUMN_MISSING, f"{qualified}.columns.{name}", ec[name], None))
    for name in sorted(oc.keys() - ec.keys()): out.append(_difference(ReasonCode.COLUMN_UNEXPECTED, f"{qualified}.columns.{name}", None, oc[name]))
    for name in sorted(ec.keys() & oc.keys()):
        for field, code in (("type", ReasonCode.COLUMN_TYPE_MISMATCH), ("nullable", ReasonCode.COLUMN_NULLABILITY_MISMATCH), ("default", ReasonCode.COLUMN_DEFAULT_MISMATCH)):
            left, right = ec[name][field], oc[name][field]
            if field == "default": left, right = _comparable_default(left), _comparable_default(right)
            if left != right: out.append(_difference(code, f"{qualified}.columns.{name}.{field}", ec[name][field], oc[name][field]))
        if ec[name]["identity"] != oc[name]["identity"] or ec[name]["generated"] != oc[name]["generated"]:
            out.append(_difference(ReasonCode.TABLE_SIGNATURE_MISMATCH, f"{qualified}.columns.{name}.generation", {"identity": ec[name]["identity"], "generated": ec[name]["generated"]}, {"identity": oc[name]["identity"], "generated": oc[name]["generated"]}))
    for field, code in (("primary_key", ReasonCode.PRIMARY_KEY_MISMATCH), ("unique", ReasonCode.UNIQUE_MISMATCH), ("checks", ReasonCode.CHECK_MISMATCH), ("foreign_keys", ReasonCode.FOREIGN_KEY_MISMATCH)):
        if expected[field] != observed[field]: out.append(_difference(code, f"{qualified}.{field}", expected[field], observed[field]))
    expected_indexes=set(expected["indexes"]); observed_indexes=set(observed["indexes"])
    for signature in sorted((expected_indexes-observed_indexes)-set(missing_indexes)):
        out.append(_difference(ReasonCode.INDEX_REQUIRED_MISSING, f"{qualified}.indexes", signature, None))
    for signature in sorted((observed_indexes-expected_indexes)-set(extra_indexes)):
        out.append(_difference(ReasonCode.INDEX_UNEXPECTED, f"{qualified}.indexes", None, signature))
    if expected["partition_key"] != observed["partition_key"]: out.append(_difference(ReasonCode.PARTITION_KEY_MISMATCH, f"{qualified}.partition_key", expected["partition_key"], observed["partition_key"]))
    if (expected["parent_schema"], expected["parent_table"]) != (observed["parent_schema"], observed["parent_table"]): out.append(_difference(ReasonCode.PARTITION_PARENT_MISMATCH, f"{qualified}.parent", [expected["parent_schema"], expected["parent_table"]], [observed["parent_schema"], observed["parent_table"]]))
    if expected["partition_bounds"] != observed["partition_bounds"]: out.append(_difference(ReasonCode.PARTITION_BOUNDS_MISMATCH, f"{qualified}.partition_bounds", expected["partition_bounds"], observed["partition_bounds"]))
    return out


def classify_structure(structure: Mapping[str, Any], contract: AdoptionContract) -> Classification:
    """Classify an already collected structure without any external access."""
    raw_tables = structure.get("tables", ())
    observed = {_qualified(t): t for t in raw_tables if _qualified(t) != "public.alembic_version"}
    canonical = {_qualified(t): t for t in contract.canonical.get("tables", ())}
    legacy_names = set(contract.legacy_public_tables)
    application_names = set(observed) - {"public.alembic_version"}
    fp_structure = {
        "schemas": sorted(structure.get("schemas", ())),
        "extensions": sorted(structure.get("extensions", ())),
        "tables": sorted((_normalise_table(t) for t in raw_tables), key=lambda t: (t["schema"] or "", t["name"] or "")),
    }
    fingerprint = hashlib.sha256(canonical_json(fp_structure)).hexdigest()
    def result(verdict, reasons, differences=()):
        ordered=tuple(sorted(differences,key=lambda d:(d.code.value,d.path,canonical_json(d.expected),canonical_json(d.observed))))
        return Classification(verdict, tuple(reasons), ordered, fingerprint, contract.contract_id, contract.contract_version, contract.payload_sha256)
    if not application_names:
        unknown_public = [n for n in observed if n.startswith("public.")]
        if not unknown_public:
            return result(AdoptionVerdict.EMPTY, (ReasonCode.EMPTY_APPLICATION_STRUCTURE,))
    restored = bool(set(observed) & legacy_names)
    differences: list[Difference] = []
    required_schemas=set(contract.canonical.get("schemas", ())); schemas=set(structure.get("schemas", ())) - _SYSTEM_SCHEMAS
    for schema in sorted(required_schemas-schemas): differences.append(_difference(ReasonCode.REQUIRED_SCHEMA_MISSING, f"schemas.{schema}", schema, None))
    for schema in sorted(schemas-required_schemas): differences.append(_difference(ReasonCode.UNKNOWN_SCHEMA, f"schemas.{schema}", None, schema))
    extensions=set(structure.get("extensions", ()))
    for ext in sorted(contract.required_extensions-extensions): differences.append(_difference(ReasonCode.REQUIRED_EXTENSION_MISSING, f"extensions.{ext}", ext, None))
    for ext in sorted(extensions-contract.required_extensions-contract.optional_extensions): differences.append(_difference(ReasonCode.UNKNOWN_EXTENSION, f"extensions.{ext}", None, ext))
    expected_names=set(canonical)
    allowed_absent=set(contract.allowed_missing_tables) | set(contract.allowed_missing_partitions) if restored else set()
    for name in sorted(expected_names-set(observed)):
        if name not in allowed_absent: differences.append(_difference(ReasonCode.REQUIRED_TABLE_MISSING, name, canonical[name], None))
    allowed_names=expected_names | (legacy_names if restored else set())
    for name in sorted(set(observed)-allowed_names): differences.append(_difference(ReasonCode.UNKNOWN_TABLE, name, None, observed[name]))
    if restored:
        for name in sorted(legacy_names-set(observed)): differences.append(_difference(ReasonCode.LEGACY_TABLE_MISSING, name, contract.legacy_public_tables[name], None))
    for name in sorted(expected_names & set(observed)):
        differences.extend(_compare_table(canonical[name], observed[name], name, missing_indexes=contract.allowed_missing_indexes.get(name, frozenset()) if restored else frozenset(), extra_indexes=contract.allowed_extra_indexes.get(name, frozenset()) if restored else frozenset()))
    if restored:
        for name in sorted(legacy_names & set(observed)):
            differences.extend(_compare_table(contract.legacy_public_tables[name], observed[name], name))
    if differences:
        ordered=sorted(differences,key=lambda d:(d.code.value,d.path,canonical_json(d.expected),canonical_json(d.observed)))
        return result(AdoptionVerdict.UNKNOWN, tuple(dict.fromkeys(d.code for d in ordered)), ordered)
    if restored:
        return result(AdoptionVerdict.ADOPTABLE_RESTORED, (ReasonCode.KNOWN_RESTORED_PROFILE,))
    return result(AdoptionVerdict.ALREADY_FINAL, (ReasonCode.CANONICAL_FINAL_STRUCTURE,))


def classify_inventory(inventory: LiveInventory, contract: AdoptionContract | None = None) -> Classification:
    """Classify exclusively through ``inventory.structure``."""
    return classify_structure(inventory.structure, contract or load_contract())


__all__ = ["DEFAULT_CONTRACT_PATH", "ContractError", "AdoptionVerdict", "ReasonCode", "Difference", "AdoptionContract", "Classification", "canonical_json", "load_contract", "classify_structure", "classify_inventory"]
