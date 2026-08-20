"""Pytest configuration for the WP3 dry-run tests.

Adds the worktree root to ``sys.path`` so ``import scripts.target_guard``
works without an install step. Keeps the change scoped to this worktree:
the canonical ``tests/conftest.py`` is untouched.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
