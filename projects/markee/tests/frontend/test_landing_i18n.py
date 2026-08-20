"""Landing language switching contract.

The public landing must remain Portuguese by default while offering a real
English version without duplicating the page or breaking static routing.
"""
from __future__ import annotations

import re

from . import _helpers as H


def test_landing_exposes_accessible_pt_en_language_switcher():
    html = H.read_text(H.LANDING_HTML)

    assert 'data-language-switcher' in html
    assert 'aria-label="Escolher idioma"' in html
    assert 'data-lang-option="pt"' in html
    assert 'data-lang-option="en"' in html
    assert 'aria-pressed="true"' in html


def test_landing_declares_translatable_copy_and_metadata():
    html = H.read_text(H.LANDING_HTML)
    js = H.read_text(H.LANDING_JS)

    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    assert "meta.title" in keys
    assert "hero.title" in keys
    assert "pricing.title" in keys
    assert "footer.rights" in keys
    assert len(keys) >= 70

    for key in keys:
        assert f"'{key}'" in js or f'"{key}"' in js, f"missing JS translation key: {key}"


def test_landing_english_dictionary_contains_real_english_copy():
    js = H.read_text(H.LANDING_JS)

    assert "Your brand," in js
    assert "under absolute watch" in js
    assert "Explore features" in js
    assert "Choose the intensity" in js
    assert "Made in Lisbon" in js
    english_block = js.split('"en":', 1)[-1]
    assert "A sua marca," not in english_block


def test_landing_language_switch_persists_choice_and_updates_document_language():
    js = H.read_text(H.LANDING_JS)

    assert "localStorage.getItem('markee-language')" in js
    assert "localStorage.setItem('markee-language'" in js
    assert "document.documentElement.lang" in js
    assert "document.title" in js
    assert "meta[name=\"description\"]" in js
