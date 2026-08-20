"""Helpers for the markee frontend behavioural tests.

All helpers are pure stdlib so the suite runs in the project venv without
extra installs. The tests assert behaviour of files committed under
``frontend/``, ``assets/`` and ``app/`` — they never start the FastAPI
server, never touch the network and never rely on a browser.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LANDING_HTML = REPO_ROOT / "frontend" / "landing" / "index.html"
LANDING_CSS = REPO_ROOT / "frontend" / "landing" / "styles.css"
LANDING_JS = REPO_ROOT / "frontend" / "landing" / "script.js"
DASHBOARD_HTML = REPO_ROOT / "frontend" / "dashboard" / "index.html"
DASHBOARD_CSS = REPO_ROOT / "frontend" / "dashboard" / "styles.css"
DASHBOARD_JS = REPO_ROOT / "frontend" / "dashboard" / "app.js"
BRAND_V2_LOGOS = REPO_ROOT / "assets" / "brand-v2" / "logos"
BRAND_V2_TOKENS_CSS = REPO_ROOT / "assets" / "brand-v2" / "tokens" / "css-variables.css"
BRAND_V2_TOKENS_JSON = REPO_ROOT / "assets" / "brand-v2" / "tokens" / "tokens.json"
LEGACY_FAVICONS = (
    REPO_ROOT / "assets" / "logos" / "markee_logo_1_favicon_16.svg",
    REPO_ROOT / "assets" / "logos" / "markee_logo_1_favicon_32.svg",
)
ALERTS_SERVICE = REPO_ROOT / "app" / "services" / "alerts.py"

# Files we consider production surface for the brand integration audit.
LANDING_SOURCE_FILES = (LANDING_HTML, LANDING_CSS, LANDING_JS)
DASHBOARD_SOURCE_FILES = (DASHBOARD_HTML, DASHBOARD_CSS, DASHBOARD_JS)

# Every file that paints the accent on a surface a visitor can actually
# reach: the two apps FastAPI serves, the canonical Brand v2 tokens and
# wordmarks, the favicon referenced from the landing <head>, and the HTML
# email template. Drafts, candidates, evidence bundles and the unmounted
# ``frontend/landing/assets/logos`` duplicates are historical records and
# stay untouched.
ACTIVE_BRAND_SURFACES = (
    LANDING_SOURCE_FILES
    + DASHBOARD_SOURCE_FILES
    + (
        BRAND_V2_TOKENS_CSS,
        BRAND_V2_TOKENS_JSON,
        BRAND_V2_LOGOS / "markee-wordmark-dark.svg",
        BRAND_V2_LOGOS / "markee-wordmark-light.svg",
        BRAND_V2_LOGOS / "markee-wordmark-mono-white.svg",
        BRAND_V2_LOGOS / "markee-wordmark-mono-black.svg",
        BRAND_V2_LOGOS / "markee-brand-sheet.svg",
        ALERTS_SERVICE,
    )
    + LEGACY_FAVICONS
)


def read_text(path: Path) -> str:
    """Return the file content or an empty string if it does not exist.

    Tests use this so a missing optional file fails gracefully with a
    clearer error than FileNotFoundError leaking from the assertion.
    """
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def all_texts() -> dict[str, str]:
    """Bundle every production frontend file into a dict for combined scans."""
    out: dict[str, str] = {}
    for path in LANDING_SOURCE_FILES + DASHBOARD_SOURCE_FILES:
        out[str(path.relative_to(REPO_ROOT))] = read_text(path)
    return out


def slugify(name: str) -> str:
    """Stable slug for use in test IDs and parametrize IDs."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def assert_file_exists(path: Path, label: str) -> None:
    """Assert that a tracked file is present on disk."""
    assert path.is_file(), f"missing required file: {label} ({path})"


def is_git_tracked(path: Path) -> bool:
    """Return whether ``path`` is tracked in the project git index."""
    rel = path.resolve().relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel.as_posix()],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def load_tokens() -> dict:
    """Return the canonical DTCG tokens from Brand v2."""
    with BRAND_V2_TOKENS_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)