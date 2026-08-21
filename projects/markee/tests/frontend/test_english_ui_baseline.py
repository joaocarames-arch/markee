"""English-first UI baseline for currently reachable Markee surfaces.

The product direction is now English-first. These tests deliberately avoid
network/browser dependencies and assert the committed public/professional UI
source no longer defaults to Portuguese in the main journeys.
"""
from __future__ import annotations

import re

from . import _helpers as H

PT_ACCENTS = "áàâãçéêíóôõúÁÀÂÃÇÉÊÍÓÔÕÚ"
PT_UI_TERMS = re.compile(
    r"\b(?:"
    r"monitorização|vigilância|vigília|funcionalidades|preços|entrar|registar|"
    r"pesquisa|prazos|definições|painel|marca|marcas|avaliação|jurídico|"
    r"palavra-passe|credenciais|plano inválido|começar|conteúdo|rodapé"
    r")\b",
    re.IGNORECASE,
)


def _visible_sources() -> dict[str, str]:
    root = H.REPO_ROOT
    return {
        "frontend/landing/index.html": H.read_text(H.LANDING_HTML),
        "frontend/landing/script.js": H.read_text(H.LANDING_JS),
        "frontend/dashboard/index.html": H.read_text(H.DASHBOARD_HTML),
        "frontend/dashboard/app.js": H.read_text(H.DASHBOARD_JS),
        "app/main.py": H.read_text(root / "app" / "main.py"),
        "app/api/auth.py": H.read_text(root / "app" / "api" / "auth.py"),
        "app/api/billing.py": H.read_text(root / "app" / "api" / "billing.py"),
        "app/services/assessment.py": H.read_text(root / "app" / "services" / "assessment.py"),
    }


def _strip_optional_pt_dictionary(path: str, text: str) -> str:
    if path == "frontend/landing/script.js" and '"pt": {' in text and '"en": {' in text:
        return text.split('"pt": {', 1)[0] + '"pt": {},' + text.split('"en": {', 1)[1]
    return text


def _strip_allowed_official_terms(text: str) -> str:
    """Keep official registry/source labels out of the Portuguese leak scan."""
    allowed = (
        "INPI", "EUIPO", "Portugal", "Lisboa", "Portuguese", "PT",
        "Boletim da Propriedade Industrial",  # official source name
    )
    for term in allowed:
        text = text.replace(term, "")
    return text


def test_landing_defaults_to_english_first():
    html = H.read_text(H.LANDING_HTML)
    js = H.read_text(H.LANDING_JS)

    assert re.search(r"<html[^>]*lang=\"en\"", html)
    assert 'data-default-lang="en"' in html
    en_button = re.search(r"<button[^>]*data-lang-option=\"en\"[^>]*>", html)
    pt_button = re.search(r"<button[^>]*data-lang-option=\"pt\"[^>]*>", html)
    assert en_button and 'aria-pressed="true"' in en_button.group(0)
    assert pt_button and 'aria-pressed="false"' in pt_button.group(0)
    assert "EU trademark protection, made simpler." in html
    assert "Explore our services" in html
    assert "Check your trademark" in html
    assert "professional EU trademark services firm" in js


def test_dashboard_shell_defaults_to_english_first():
    html = H.read_text(H.DASHBOARD_HTML)
    js = H.read_text(H.DASHBOARD_JS)

    assert re.search(r"<html[^>]*lang=\"en\"", html)
    assert 'technology-driven EU trademark platform' in html
    assert 'Dashboard' in js
    assert 'Trademark check' in js
    assert 'Settings' in js
    assert 'Não foi possível' not in js
    assert 'Painel' not in js


def test_user_facing_backend_messages_are_english():
    sources = _visible_sources()
    joined = "\n".join(sources.values())

    assert "Invalid credentials" in joined
    assert "Email already registered" in joined
    assert "This automated assessment is for information only" in joined
    assert "Professional review" in joined


def test_no_obvious_portuguese_ui_remains_in_main_sources():
    offenders: dict[str, list[str]] = {}
    for path, text in _visible_sources().items():
        scan = _strip_allowed_official_terms(_strip_optional_pt_dictionary(path, text))
        matches = sorted(set(PT_UI_TERMS.findall(scan)))
        accented_lines = [
            line.strip()
            for line in scan.splitlines()
            if any(ch in PT_ACCENTS for ch in line)
        ]
        if matches or accented_lines:
            offenders[path] = matches + accented_lines[:8]

    assert not offenders, offenders
