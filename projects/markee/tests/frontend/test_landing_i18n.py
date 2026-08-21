"""Landing language switching contract.

The public landing must be English by default while keeping a real
Portuguese version without duplicating the page or breaking static routing.

These tests fail when:
* a ``data-i18n`` key used in the HTML is missing from either dictionary,
* the EN dictionary leaks Portuguese words or accented characters,
* important visible Portuguese copy sits outside translatable markup
  (element text or translatable attributes without ``data-i18n``),
* the language switch would break the split-line / split-word animations.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

from . import _helpers as H


PT_ACCENTS = "áàâãçéêíóôõúÁÀÂÃÇÉÊÍÓÔÕÚ"

# Obvious Portuguese words that must never appear in the EN dictionary or in
# visible copy outside translatable markup. Kept lowercase; matching is
# case-insensitive and word-bounded to avoid false positives ("markee").
PT_WORDS = (
    "marca",
    "marcas",
    "sua",
    "vigilância",
    "funcionalidades",
    "preços",
    "começar",
    "entrar",
    "prazos",
    "pedido",
    "alertas",
    "conteúdo",
    "mês",
    "rodapé",
    "saltar",
    "escolher",
)
PT_WORDS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in PT_WORDS) + r")\b", re.IGNORECASE
)

# Attributes whose values are user-visible (read by assistive tech or shown
# by the browser) and therefore must be translated when they hold copy.
VISIBLE_ATTRS = ("aria-label", "alt", "title", "placeholder", "content")


def _extract_dictionaries() -> tuple[dict[str, str], dict[str, str]]:
    """Parse the pt/en dictionaries out of the i18n object in script.js."""
    js = H.read_text(H.LANDING_JS)
    assert '"pt": {' in js and '"en": {' in js, "i18n dictionaries not found"
    pt_block = js.split('"pt": {', 1)[1].split('"en": {', 1)[0]
    en_block = js.split('"en": {', 1)[1].split("};", 1)[0]
    pair_re = re.compile(r'"([a-z0-9_.]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
    pt = dict(pair_re.findall(pt_block))
    en = dict(pair_re.findall(en_block))
    assert pt and en, "failed to parse i18n dictionaries"
    return pt, en


def _looks_portuguese(text: str) -> bool:
    return any(ch in PT_ACCENTS for ch in text) or bool(PT_WORDS_RE.search(text))


class _UntranslatedTextWalker(HTMLParser):
    """Collects visible text and attributes outside translatable markup."""

    VOID = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "source", "track", "wbr",
    }
    SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.i18n_depth = 0
        self.skip_depth = 0
        self.stack: list[tuple[str, bool, bool]] = []
        self.free_text: list[str] = []
        self.attr_issues: list[str] = []

    def _handle_attrs(self, tag: str, attrs: dict[str, str | None]) -> None:
        i18n_attr = attrs.get("data-i18n-attr")
        for name in VISIBLE_ATTRS:
            value = attrs.get(name)
            if value and _looks_portuguese(value) and i18n_attr != name:
                self.attr_issues.append(f'<{tag} {name}="{value}"> lacks data-i18n-attr')

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        self._handle_attrs(tag, attrs_d)
        if tag in self.VOID:
            return
        # data-i18n translates the element text unless it targets an attribute.
        translates_text = "data-i18n" in attrs_d and "data-i18n-attr" not in attrs_d
        skips = tag in self.SKIP
        self.stack.append((tag, translates_text, skips))
        if translates_text:
            self.i18n_depth += 1
        if skips:
            self.skip_depth += 1

    def handle_startendtag(self, tag, attrs):
        self._handle_attrs(tag, dict(attrs))

    def handle_endtag(self, tag):
        while self.stack:
            name, translates_text, skips = self.stack.pop()
            if translates_text:
                self.i18n_depth -= 1
            if skips:
                self.skip_depth -= 1
            if name == tag:
                break

    def handle_data(self, data):
        if self.i18n_depth == 0 and self.skip_depth == 0 and data.strip():
            self.free_text.append(data.strip())


def test_landing_exposes_accessible_pt_en_language_switcher():
    html = H.read_text(H.LANDING_HTML)

    assert 'data-language-switcher' in html
    assert 'aria-label="Choose language"' in html
    assert 'data-lang-option="pt"' in html
    assert 'data-lang-option="en"' in html
    assert re.search(r'<button[^>]*data-lang-option="en"[^>]*aria-pressed="true"|<button[^>]*aria-pressed="true"[^>]*data-lang-option="en"', html)


def test_landing_declares_translatable_copy_and_metadata():
    html = H.read_text(H.LANDING_HTML)

    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    assert "meta.title" in keys
    assert "hero.title" in keys
    assert "pricing.title" in keys
    assert "footer.rights" in keys
    assert len(keys) >= 90


def test_every_html_i18n_key_exists_in_both_dictionaries():
    html = H.read_text(H.LANDING_HTML)
    pt, en = _extract_dictionaries()

    keys = set(re.findall(r'data-i18n="([^"]+)"', html))
    missing_pt = sorted(keys - set(pt))
    missing_en = sorted(keys - set(en))
    assert not missing_pt, f"data-i18n keys missing from PT dictionary: {missing_pt}"
    assert not missing_en, f"data-i18n keys missing from EN dictionary: {missing_en}"


def test_pt_and_en_dictionaries_cover_the_same_keys():
    pt, en = _extract_dictionaries()
    only_pt = sorted(set(pt) - set(en))
    only_en = sorted(set(en) - set(pt))
    assert not only_pt, f"keys present only in PT: {only_pt}"
    assert not only_en, f"keys present only in EN: {only_en}"


def test_english_dictionary_contains_no_portuguese():
    _, en = _extract_dictionaries()

    accented = {
        key: value
        for key, value in en.items()
        if any(ch in PT_ACCENTS for ch in value)
    }
    assert not accented, f"EN dictionary values with Portuguese accents: {accented}"

    leaked = {
        key: value for key, value in en.items() if PT_WORDS_RE.search(value)
    }
    assert not leaked, f"EN dictionary values with Portuguese words: {leaked}"


def test_important_html_sections_are_marked_translatable():
    html = H.read_text(H.LANDING_HTML)
    keys = set(re.findall(r'data-i18n="([^"]+)"', html))

    required = {
        "hero.eyebrow", "hero.subtitle", "hero.meta.scroll", "hero.meta.location",
        "hero.meta.est", "hero.title.line1", "hero.title.line2", "hero.title.line3",
        "ticker.inpi", "ticker.euipo", "ticker.bpi", "ticker.nice",
        "ticker.phonetic", "ticker.alerts",
        "manifesto.eyebrow", "manifesto.text",
        "features.eyebrow", "features.title",
        "feature.sim.title", "feature.sim.desc", "feature.sim.meta",
        "feature.life.title", "feature.life.desc", "feature.life.meta",
        "feature.structured.title", "feature.structured.desc",
        "feature.prospect.title", "feature.prospect.desc",
        "feature.email.title", "feature.email.desc",
        "stats.label", "stats.official", "stats.classes", "stats.weights", "stats.pt",
        "engine.eyebrow", "engine.title", "engine.aria",
        "engine.sim.title", "engine.sim.desc",
        "engine.deadlines.title", "engine.deadlines.desc",
        "engine.alert.title", "engine.alert.desc",
        "engine.report", "engine.verdict", "engine.email_one", "engine.email_two",
        "engine.timeline.label", "engine.timeline.registered",
        "engine.timeline.opposition", "engine.timeline.renewal", "engine.sent",
        "pricing.eyebrow", "pricing.title", "pricing.note", "pricing.per_month",
        "pricing.tier.free", "pricing.tier.individual", "pricing.tier.pro",
        "pricing.tier.professional", "pricing.tier.enterprise",
        "pricing.ind.2", "pricing.prof.2", "pricing.start",
        "final.eyebrow", "final.title", "final.hint",
        "footer.aria", "footer.product", "footer.platform", "footer.registers",
        "footer.inpi", "footer.euipo", "footer.rights", "footer.made",
        "nav.aria", "nav.home_aria", "nav.open_menu", "nav.features",
        "nav.engine", "nav.pricing", "nav.login", "nav.create",
        "nav.service_status", "language.aria", "skip.content",
    }
    missing = sorted(required - keys)
    assert not missing, f"expected data-i18n markers missing in HTML: {missing}"


def test_no_visible_portuguese_outside_translatable_markup():
    html = H.read_text(H.LANDING_HTML)

    walker = _UntranslatedTextWalker()
    walker.feed(html)

    leaks = [text for text in walker.free_text if _looks_portuguese(text)]
    assert not leaks, f"visible Portuguese text outside data-i18n markup: {leaks}"
    assert not walker.attr_issues, (
        f"visible Portuguese attributes outside data-i18n-attr markup: {walker.attr_issues}"
    )


def test_landing_english_dictionary_contains_real_english_copy():
    js = H.read_text(H.LANDING_JS)

    assert "Can I protect this trademark?" in js
    assert "Find out before you file" in js
    assert "Register a trademark" in js
    assert "Choose the right level" in js
    assert "built in lisbon" in js.lower()
    english_block = js.split('"en":', 1)[-1]
    assert "A sua marca," not in english_block


def test_landing_language_switch_persists_choice_and_updates_document_language():
    js = H.read_text(H.LANDING_JS)

    assert "localStorage.getItem('markee-language')" in js
    assert "localStorage.setItem('markee-language'" in js
    assert "document.documentElement.lang" in js
    assert "document.title" in js
    assert "meta[name=\"description\"]" in js


def test_language_switch_preserves_split_text_animations():
    js = H.read_text(H.LANDING_JS)

    # Hero lines: translated copy must land inside the .hero__line-inner
    # wrapper or the intro clip animation loses its target.
    assert "querySelector('.hero__line-inner')" in js

    # Manifesto: switching language replaces the split .w spans, so the words
    # must be re-split and the scrub tween rebuilt afterwards.
    assert js.count("buildManifestoScrub(") >= 3  # definition + init + refresh
    assert "refreshSplitText" in js
    switch_body = js.split("function initLanguageSwitch", 1)[-1].split("function ", 1)[0]
    assert "refreshSplitText()" in switch_body
