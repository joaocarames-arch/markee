"""Email templates for the transactional verification flow.

Templates are intentionally minimal: PT-PT, accessible markup, no marketing
claims, no tracking pixels. URLs are minted only against an explicit allowlist.
"""
from __future__ import annotations

from html import escape
from urllib.parse import urlencode, urljoin


_FORBIDDEN_CLAIMS = (
    "garantimos",
    "100%",
    "imediat",
    "instantân",
    "melhor",
    "líder",
    "premium",
)


def _assert_safe(html: str) -> None:
    lowered = html.lower()
    for forbidden in _FORBIDDEN_CLAIMS:
        if forbidden in lowered:
            raise ValueError(f"email template contains forbidden claim: {forbidden!r}")


def verification_url(
    base_url: str, token: str, allowed_bases: list[str]
) -> str:
    """Build a verification URL only if ``base_url`` is in ``allowed_bases``."""
    base = base_url.rstrip("/")
    if base not in allowed_bases:
        raise ValueError(f"base_url {base_url!r} is not in allowlist")
    return urljoin(base + "/", f"?{urlencode({'token': token})}")


def render_verification_email(
    verification_url: str, ttl_minutes: int
) -> tuple[str, str]:
    """Return ``(text_body, html_body)`` for the verification email.

    Args:
        verification_url: Absolute URL the user must click to verify.
        ttl_minutes: Token lifetime; rendered into the copy so the user knows
            how long the link is valid.

    Returns:
        PT-PT text and HTML bodies, both safe and accessible.
    """
    safe_url = escape(verification_url, quote=True)
    hours = max(1, round(ttl_minutes / 60))

    text_body = (
        "Olá,\n\n"
        "Recebemos um pedido para ativar a sua conta markee. "
        f"Para confirmar o seu email, copie e abra este link num browser seguro:\n\n"
        f"{verification_url}\n\n"
        f"Este link é válido durante {hours} hora(s) e só pode ser utilizado uma vez. "
        "Se não fez este pedido, ignore esta mensagem — a sua conta não será criada.\n\n"
        "Obrigado,\n"
        "Equipa markee\n"
    )

    html_body = (
        '<!DOCTYPE html>\n'
        '<html lang="pt-PT">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Verificação de email — markee</title>\n'
        '</head>\n'
        '<body style="margin:0;background:#08090a;color:#e8e8e8;'
        'font-family:Arial,Helvetica,sans-serif;line-height:1.5;padding:24px;">\n'
        '<main role="main" style="max-width:560px;margin:0 auto;'
        'background:#111214;border:1px solid rgba(255,255,255,0.08);'
        'border-radius:10px;padding:24px;">\n'
        '<h1 style="color:#35d0e0;font-size:20px;margin:0 0 16px;">'
        "Verifique o seu email\n"
        "</h1>\n"
        "<p>Recebemos um pedido para ativar a sua conta markee.</p>\n"
        f'<p><a href="{safe_url}" style="display:inline-block;'
        'background:#35d0e0;color:#08090a;padding:12px 18px;'
        'border-radius:6px;text-decoration:none;font-weight:600;">'
        "Confirmar email</a></p>\n"
        f'<p style="word-break:break-all;font-size:13px;color:#8a8d93;">'
        f"Ou copie este link: {safe_url}</p>\n"
        f"<p>Este link é válido durante {hours} hora(s) e só pode ser "
        "utilizado uma vez.</p>\n"
        "<p>Se não fez este pedido, ignore esta mensagem.</p>\n"
        '<hr style="border:0;border-top:1px solid rgba(255,255,255,0.08);'
        'margin:24px 0;">\n'
        '<p style="font-size:12px;color:#8a8d93;margin:0;">'
        "Enviado por markee — monitorização de marcas."
        "</p>\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )

    _assert_safe(html_body)
    return text_body, html_body
