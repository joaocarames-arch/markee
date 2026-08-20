"""Regression tests for interpreter/module resolution used by WP3 tooling.

The WP3 proof pipeline imports ``alembic.command`` with the repository root
on ``sys.path`` (scripts insert it explicitly, and running from the repo cwd
adds it implicitly). A tracked ``alembic/__init__.py`` in the worktree turns
the migration-scripts directory into a regular Python package that shadows
the installed Alembic distribution, so ``alembic.command`` stops resolving.
These tests pin the required behaviour: from the repository root, ``import
alembic.command`` must resolve to the installed distribution in
``site-packages``, never to ``<repo>/alembic``.

The checks run in a subprocess with ``sys.executable`` so they exercise the
same interpreter and cwd conditions as the real tooling, without inheriting
this test process's already-imported modules.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_PROBE = (
    "import alembic.command, alembic; "
    "print(alembic.command.__file__); "
    "print(alembic.__file__)"
)


def _run_probe() -> subprocess.CompletedProcess[str]:
    """Import ``alembic.command`` in a clean subprocess at the repo root."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-B", "-c", _PROBE],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_alembic_command_imports_from_repo_root():
    """``import alembic.command`` must succeed with the repo as cwd."""
    result = _run_probe()
    assert result.returncode == 0, (
        "import alembic.command failed from the repository root "
        f"(local alembic/ shadowing?):\n{result.stderr}"
    )


def test_alembic_resolves_to_installed_distribution_not_worktree():
    """The imported package must live in site-packages, not ``<repo>/alembic``."""
    result = _run_probe()
    assert result.returncode == 0, result.stderr
    command_file, package_file = result.stdout.strip().splitlines()
    for origin in (command_file, package_file):
        path = Path(origin).resolve()
        assert "site-packages" in path.parts, (
            f"alembic resolved outside site-packages: {origin}"
        )
        assert REPO_ROOT not in path.parents, (
            f"alembic resolved inside the worktree: {origin}"
        )
