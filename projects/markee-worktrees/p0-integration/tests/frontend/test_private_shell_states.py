"""Behavioural source contracts for the resilient private-shell states.

P0-S2 slice: the authenticated dashboard shell must

* render an accessible PT-PT 404 state (``renderNotFound``) inside the
  sidebar + topbar shell for any unknown hash route, instead of silently
  coercing near-misses (``#/dashboard-typo``) onto ``#/dashboard``;
* expose a reusable API failure helper (``renderApiError``) with a
  guarded retry button and a polite live status;
* keep the special 401 behaviour (clear session + redirect to
  ``#/login``) out of the generic retry UI;
* wire both new states through a compact ``--shell-*`` CSS token
  contract in ``frontend/dashboard/styles.css``.

Like the rest of the suite, these tests are pure stdlib and assert
against the committed sources (no browser, no server). They trace the
actual function bodies (balanced-brace extraction) so class usage is
verified at real callsites rather than by whole-file regex alone.

Note on the warning token: Brand v2 bans the legacy warning hex (see
``test_no_prohibited_aesthetic``) and the live dashboard renders
warning-level UI with the accent (``.badge-warning``,
``.countdown.warning``). ``--shell-warning`` therefore binds to
``var(--shell-accent)`` instead of reintroducing the banned color.
"""
from __future__ import annotations

import re

import pytest

from . import _helpers as H

ALL_ROUTES = ["/dashboard", "/search", "/watchlists", "/alerts", "/deadlines", "/settings", "/login"]

# Exact color/spacing/radius values of the private-shell token contract.
SHELL_TOKEN_VALUES = {
    "--shell-danger": r"#e05252",
    "--shell-success": r"#4ade80",
    "--shell-accent": r"#35d0e0",
    "--shell-text-primary": r"#e8e8e8",
    "--shell-text-secondary": r"#8a8d93",
    "--shell-bg-surface": r"#1a1c1f",
    "--shell-border": r"rgba\(255,\s*255,\s*255,\s*0\.08\)",
    "--shell-space-sm": r"8px",
    "--shell-space-md": r"16px",
    "--shell-space-lg": r"24px",
    "--shell-radius-sm": r"6px",
    "--shell-radius-md": r"10px",
    "--shell-radius-lg": r"16px",
    "--shell-focus-ring": r"0 0 0 3px rgba\(53,\s*208,\s*224,\s*0\.35\)",
}


def _js() -> str:
    return H.read_text(H.DASHBOARD_JS)


def _css() -> str:
    return H.read_text(H.DASHBOARD_CSS)


def _extract_function(src: str, name: str) -> str:
    """Return the full balanced source of ``function name(...) {...}``.

    The dashboard bundle never nests unbalanced braces inside strings, so
    plain brace counting from the declaration is reliable here.
    """
    match = re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(", src)
    if not match:
        return ""
    start = match.start()
    idx = src.index("{", match.end() - 1)
    depth = 0
    for pos in range(idx, len(src)):
        if src[pos] == "{":
            depth += 1
        elif src[pos] == "}":
            depth -= 1
            if depth == 0:
                return src[start : pos + 1]
    return ""


def _css_rule_bodies(css: str, cls: str) -> list[str]:
    """Bodies of every flat CSS rule whose selector list mentions ``cls``."""
    bodies = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if cls in match.group(1):
            bodies.append(match.group(2))
    return bodies


# ---------------------------------------------------------------------------
# b) Unknown hash routes → accessible 404 inside the shell
# ---------------------------------------------------------------------------


def test_routes_constant_preserves_all_seven_routes():
    """The 404 work must not drop any of the existing hash routes."""
    js = _js()
    for route in ALL_ROUTES:
        assert f"'{route}'" in js, f"route {route!r} missing from app.js"


def test_render_not_found_exists_with_accessible_pt_copy():
    """``renderNotFound(path)`` renders the PT-PT 404 state with alert
    semantics inside the current view (shell stays mounted around it).
    """
    body = _extract_function(_js(), "renderNotFound")
    assert body, "app.js must define renderNotFound(path)"
    assert "Página não encontrada" in body
    assert "não existe" in body, "404 must state that the requested path does not exist"
    assert 'role="alert"' in body
    assert 'aria-live="polite"' in body
    # Must render inside the shell's view container, not replace #root.
    assert "getView()" in body, "renderNotFound must render inside the shell view"
    assert "root.innerHTML" not in body, "renderNotFound must not blow away the shell"
    # The requested path is echoed back, escaped.
    assert "esc(path)" in body, "requested path must be escaped into the message"


def test_render_not_found_cta_and_keyboard_support():
    """The 404 CTA is a focusable PT-PT button back to the dashboard and
    Escape also returns to the dashboard.
    """
    body = _extract_function(_js(), "renderNotFound")
    assert body, "app.js must define renderNotFound(path)"
    assert "Voltar ao painel" in body
    assert "navigate('/dashboard')" in body, "CTA must navigate back to #/dashboard"
    assert ".focus()" in body, "CTA must receive keyboard focus"
    assert "'Escape'" in body, "Escape must return to the dashboard"


def test_unknown_routes_are_dispatched_to_not_found():
    """Near-miss routes (``#/dashboard-typo``, ``#/invalid``, ``#/marks/``)
    must reach ``renderNotFound`` — never silently fall back to the
    dashboard renderer.
    """
    js = _js()
    current_path = _extract_function(js, "currentPath")
    assert current_path, "app.js must keep currentPath()"
    assert "? path : '/dashboard'" not in current_path, (
        "currentPath still coerces unknown routes onto /dashboard"
    )

    router = _extract_function(js, "router")
    assert router, "app.js must keep router()"
    assert not re.search(r"VIEW_RENDERERS\[path\]\s*\|\|\s*renderDashboard", router), (
        "router still silently maps unknown routes to renderDashboard"
    )
    assert "renderNotFound(path)" in router, (
        "router must dispatch unknown routes to renderNotFound(path)"
    )
    # The shell must be rendered before the 404 state so sidebar + topbar stay.
    assert router.index("renderShell(path)") < router.index("renderNotFound(path)"), (
        "renderNotFound must render inside the already-mounted shell"
    )


# ---------------------------------------------------------------------------
# c) Reusable API failure state
# ---------------------------------------------------------------------------


def test_render_api_error_contract():
    """``renderApiError(message, retryId, onRetry)`` renders a PT-PT retry
    state inside a content area with an accessible live status.
    """
    js = _js()
    signature = re.search(r"function\s+renderApiError\s*\(([^)]*)\)", js)
    assert signature, "app.js must define renderApiError(...)"
    params = [p.strip() for p in signature.group(1).split(",")]
    assert params[:3] == ["message", "retryId", "onRetry"], (
        f"renderApiError must take (message, retryId, onRetry, ...), got {params}"
    )

    body = _extract_function(js, "renderApiError")
    assert "Tentar novamente" in body, "retry button must read 'Tentar novamente'"
    assert "aria-label" in body, "retry button must carry an aria-label"
    assert 'aria-live="polite"' in body, "helper must expose a polite live status"
    assert "esc(message" in body, "error message must be escaped"
    # Renders inside a content container, never the whole document root.
    assert "root.innerHTML" not in body, "renderApiError must not replace the shell"


def test_render_api_error_guards_duplicate_retries():
    """The retry button disables while the retried request is in flight
    and is restored on completion or failure.
    """
    body = _extract_function(_js(), "renderApiError")
    assert body, "app.js must define renderApiError(...)"
    assert re.search(r"\.disabled\s*=\s*true", body), "retry must disable while in flight"
    assert re.search(r"\.disabled\s*=\s*false", body), "retry must be restored afterwards"
    assert "finally" in body, "restore must run on completion AND failure"
    assert "await onRetry()" in body, "retry must re-invoke the provided callback"


# ---------------------------------------------------------------------------
# d) Dashboard route wiring + 401 special-casing
# ---------------------------------------------------------------------------


def test_dashboard_failure_uses_reusable_api_error():
    """Dashboard fetch failures use the shared helper, retrying with the
    dashboard renderer itself.
    """
    body = _extract_function(_js(), "renderDashboard")
    assert body, "app.js must keep renderDashboard()"
    call = re.search(r"renderApiError\(([^;]*)\)", body)
    assert call, "renderDashboard must delegate failures to renderApiError"
    assert "renderDashboard" in call.group(1), "retry must re-invoke renderDashboard"
    assert "'retry-dashboard'" in call.group(1), "retry button keeps the retry-dashboard id"


def test_auth_redirect_clears_session_and_skips_retry_ui():
    """A 401 clears the stored session token, redirects to ``#/login`` and
    must NOT surface the generic retry UI.
    """
    js = _js()
    request_body = _extract_function(js, "request")
    assert request_body, "app.js must keep request()"
    branch = re.search(r"if\s*\(response\.status\s*===\s*401\)\s*\{(.*?)\n  \}", request_body, re.DOTALL)
    assert branch, "request() must keep its 401 branch"
    assert "clearToken()" in branch.group(1), "401 must clear the stored token"
    assert "navigate('/login')" in branch.group(1), "401 must redirect to #/login"
    assert "authRedirect" in branch.group(1), (
        "401 errors must be flagged so views can skip the retry UI"
    )

    clear_token = _extract_function(js, "clearToken")
    assert "localStorage.removeItem(TOKEN_KEY)" in clear_token, (
        "clearToken must remove the session token from localStorage"
    )

    dashboard = _extract_function(js, "renderDashboard")
    assert "authRedirect" in dashboard, (
        "renderDashboard must skip the retry UI on auth redirects"
    )
    assert dashboard.index("authRedirect") < dashboard.index("renderApiError"), (
        "the authRedirect guard must run before the generic retry UI renders"
    )


# ---------------------------------------------------------------------------
# a) CSS token contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", sorted(SHELL_TOKEN_VALUES), ids=lambda t: t.lstrip("-"))
def test_shell_token_contract_values(token):
    """Every ``--shell-*`` token is declared with its contracted value."""
    css = _css()
    pattern = rf"{re.escape(token)}\s*:\s*{SHELL_TOKEN_VALUES[token]}\s*;"
    assert re.search(pattern, css), f"styles.css must declare {token} with its contract value"


def test_shell_warning_token_binds_to_accent():
    """Brand v2 marks the warning color as no-color and the live dashboard
    renders warning-level UI with the accent, so ``--shell-warning`` must
    alias the accent token (the legacy hex is banned by the aesthetic guards).
    """
    css = _css()
    assert re.search(r"--shell-warning\s*:\s*var\(--shell-accent\)\s*;", css), (
        "--shell-warning must bind to var(--shell-accent)"
    )


def test_state_bg_border_tokens_derive_from_color_tokens():
    """Error/success bg + border tokens are derived from the shell color
    tokens rather than re-hardcoding rgba values.
    """
    css = _css()
    for token, source in [
        ("--shell-error-bg", "--shell-danger"),
        ("--shell-error-border", "--shell-danger"),
        ("--shell-success-bg", "--shell-success"),
        ("--shell-success-border", "--shell-success"),
    ]:
        declaration = re.search(rf"{re.escape(token)}\s*:\s*([^;]+);", css)
        assert declaration, f"styles.css must declare {token}"
        assert f"var({source})" in declaration.group(1), (
            f"{token} must derive from var({source})"
        )


def test_shell_state_classes_are_wired_through_tokens():
    """The new shell-state classes consume the token contract."""
    css = _css()
    expectations = {
        ".shell-state": ["var(--shell-space-", "var(--shell-radius-"],
        ".shell-state-error": ["var(--shell-error-bg)", "var(--shell-error-border)"],
        ".shell-state-success": ["var(--shell-success-bg)", "var(--shell-success-border)"],
        ".shell-state-not-found": ["var(--shell-border)"],
    }
    for cls, needles in expectations.items():
        bodies = "\n".join(_css_rule_bodies(css, cls))
        assert bodies, f"styles.css must define a {cls} rule"
        for needle in needles:
            assert needle in bodies, f"{cls} must use {needle}"

    focus_bodies = "\n".join(
        body
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)
        if ":focus-visible" in match.group(1) and "shell-state" in match.group(1)
        for body in [match.group(2)]
    )
    assert "var(--shell-focus-ring)" in focus_bodies, (
        "shell-state actionable elements must use the focus ring token on :focus-visible"
    )


def test_js_callsites_use_token_backed_classes():
    """Trace actual callsites: the classes rendered by renderNotFound and
    renderApiError must exist in styles.css and (directly or via the shared
    ``.shell-state`` base) resolve to ``--shell-*`` tokens.
    """
    js = _js()
    css = _css()
    callsites = {
        "renderNotFound": ["shell-state", "shell-state-not-found"],
        "renderApiError": ["shell-state", "shell-state-error"],
    }
    base_bodies = "\n".join(_css_rule_bodies(css, ".shell-state"))
    assert "var(--shell-" in base_bodies, ".shell-state base must consume shell tokens"

    for fn, classes in callsites.items():
        body = _extract_function(js, fn)
        assert body, f"app.js must define {fn}"
        for cls in classes:
            assert re.search(rf'class="[^"]*\b{re.escape(cls)}\b', body), (
                f"{fn} must render an element with class {cls!r}"
            )
            rule_bodies = "\n".join(_css_rule_bodies(css, f".{cls}"))
            assert rule_bodies, f"class .{cls} used by {fn} has no CSS rule"
            assert "var(--shell-" in rule_bodies or cls == "shell-state", (
                f".{cls} must be wired through the shell token contract"
            )
