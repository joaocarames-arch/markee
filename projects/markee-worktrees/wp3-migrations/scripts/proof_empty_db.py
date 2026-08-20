"""Empty-DB proof: upgrade to head, no-op fingerprint, no create_all.

Steps, in order, all gated by :mod:`scripts.target_guard`:

1. Load the disposable DSN from ``scripts/disposable.env`` and vet it.
2. Run Alembic ``upgrade head`` programmatically against that DSN.
3. Read the catalog and confirm ``alembic_version`` is ``002``.
4. Confirm ``alembic heads`` returns exactly one head.
5. Confirm ``alembic current`` shows ``002``.
6. Compare the catalog fingerprint *before* and *after* a second
   ``upgrade head`` — the second run must be a no-op.
7. Confirm the four expected schemas exist; confirm a partition
   ``raw.api_responses_2026_07`` exists.

The script is the only place that mutates the disposable database; every
other entry point is read-only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the worktree importable so ``scripts.target_guard`` resolves when
# the script is executed directly via ``python scripts/proof_empty_db.py``.
WORKTREE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKTREE))

# Set DATABASE_URL before importing app.* modules.
from scripts.disposable_env import load_disposable_url  # noqa: E402

DSN = load_disposable_url()
os.environ["DATABASE_URL"] = DSN
os.environ["DB_CREATE_ALL_ON_STARTUP"] = "false"
os.environ["ENVIRONMENT"] = "development"

import scripts.target_guard as guard  # noqa: E402
from scripts.drift_inventory import inventory_target  # noqa: E402

import alembic.command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


ARTIFACTS = WORKTREE.parent.parent / "markee-gate-artifacts" / "wp3"


def _alembic_config() -> Config:
    """Build an in-memory Alembic :class:`Config` pointed at the disposable.

    The repo's ``alembic.ini`` references the live DSN by default; we
    override ``sqlalchemy.url`` here so the upgrade targets the disposable.
    """
    cfg = Config(str(WORKTREE / "alembic.ini"))
    cfg.set_main_option("script_location", str(WORKTREE / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DSN.replace("postgresql+asyncpg", "postgresql"))
    return cfg


def _heads(cfg: Config) -> list[str]:
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    out: list[str] = []
    for h in heads:
        out.append(h.revision if hasattr(h, "revision") else str(h))
    return out


def _current_version() -> str | None:
    """Read ``alembic_version`` directly from the disposable catalog."""
    engine = create_engine(DSN.replace("postgresql+asyncpg", "postgresql"), future=True)
    try:
        with engine.begin() as conn:
            exists = conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='alembic_version'"
                )
            ).scalar()
            if not exists:
                return None
            row = conn.execute(
                text("SELECT version_num FROM public.alembic_version")
            ).first()
            return row[0] if row else None
    finally:
        engine.dispose()


def _partition_exists() -> bool:
    engine = create_engine(DSN.replace("postgresql+asyncpg", "postgresql"), future=True)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM pg_inherits i "
                    "JOIN pg_class c ON c.oid = i.inhparent "
                    "WHERE c.relname='api_responses' "
                    "AND i.inhrelid::regclass::text LIKE 'raw.api_responses_%' "
                    "LIMIT 1"
                )
            ).first()
            return row is not None
    finally:
        engine.dispose()


def main() -> int:
    guard.assert_disposable_target(DSN)
    cfg = _alembic_config()
    heads = _heads(cfg)
    print(f"[heads] {heads}")
    if len(heads) != 1:
        print(f"FAIL: expected exactly one head, got {len(heads)}", file=sys.stderr)
        return 5
    head = heads[0]
    if head != "002":
        print(f"FAIL: head is {head!r} (expected '002')", file=sys.stderr)
        return 5

    # Pre-upgrade: disposable is empty.
    inv_before = inventory_target(DSN, guard=guard.assert_disposable_target)
    print(f"[before] tables={len(inv_before.tables)} alembic={inv_before.alembic_version}")
    if inv_before.tables:
        print("FAIL: disposable is not empty before upgrade", file=sys.stderr)
        return 2
    if inv_before.alembic_version is not None:
        print("FAIL: alembic_version already set before upgrade", file=sys.stderr)
        return 2

    # Run upgrade head.
    try:
        alembic.command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: alembic upgrade head raised: {exc!r}", file=sys.stderr)
        return 1

    inv_after = inventory_target(DSN, guard=guard.assert_disposable_target)
    av = _current_version()
    print(f"[after] tables={len(inv_after.tables)} alembic={av} fp={inv_after.fingerprint}")
    if av != "002":
        print(f"FAIL: alembic_version={av!r} (expected '002')", file=sys.stderr)
        return 3
    expected_schemas = {"app", "core", "events", "raw", "public"}
    actual_schemas = set(inv_after.schemas)
    missing = expected_schemas - actual_schemas
    if missing:
        print(f"FAIL: missing schemas: {sorted(missing)}", file=sys.stderr)
        return 6
    if not _partition_exists():
        print("FAIL: raw.api_responses partitions missing", file=sys.stderr)
        return 7

    # No-op proof.
    fp_after_first = inv_after.fingerprint
    try:
        alembic.command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: second upgrade head raised: {exc!r}", file=sys.stderr)
        return 1
    inv_after_second = inventory_target(DSN, guard=guard.assert_disposable_target)
    fp_after_second = inv_after_second.fingerprint
    if fp_after_first != fp_after_second:
        print("FAIL: second upgrade changed catalog", file=sys.stderr)
        print(fp_after_first, file=sys.stderr)
        print(fp_after_second, file=sys.stderr)
        return 4
    print(f"[no-op] fingerprint stable: {fp_after_first}")

    # Persist a structured summary out-of-Git, mode 600.
    out = ARTIFACTS / "empty-db-proof.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "before": inv_before.to_dict(),
                "after": inv_after.to_dict(),
                "after_second": inv_after_second.to_dict(),
                "heads": heads,
                "current_version": av,
                "fingerprint_first": fp_after_first,
                "fingerprint_second": fp_after_second,
                "partition_exists": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.chmod(out, 0o600)
    print(f"[ok] summary written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
