"""Accessible, versioned PT-PT templates for alert notification emails."""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from typing import Any

ALERT_TEMPLATE_VERSION = "1"
_SUPPORTED_TEMPLATES = frozenset({"alert_generic", "alert_deadline"})
_CONTROL_RE = re.compile(r"[\r\n\t\0]")


@dataclass(frozen=True)
class RenderedAlertEmail:
    """Complete plaintext and HTML representations of one alert email."""

    subject: str
    text_body: str
    html_body: str


def _clean_subject(value: str) -> str:
    if _CONTROL_RE.search(value):
        raise ValueError("control characters not allowed in email subject")
    return value.strip()


def render_alert_email(
    template_key: str,
    template_version: str,
    payload: dict[str, Any],
) -> RenderedAlertEmail:
    """Render one supported alert payload to equivalent text and escaped HTML."""
    if template_key not in _SUPPORTED_TEMPLATES:
        raise ValueError(f"unsupported alert template: {template_key!r}")
    if template_version != ALERT_TEMPLATE_VERSION:
        raise ValueError(f"unsupported alert template version: {template_version!r}")

    title = str(payload.get("title", "Alerta markee"))
    body = str(payload.get("body", ""))
    subject = _clean_subject(title)
    if not subject:
        subject = "Alerta markee"

    if template_key == "alert_deadline":
        due_date = str(payload.get("due_date", ""))
        days_remaining = payload.get("days_remaining")
        if not due_date or not isinstance(days_remaining, int):
            raise ValueError("deadline template requires due_date and days_remaining")
        detail_text = (
            f"Data do prazo: {due_date}. Dias restantes: {days_remaining}."
        )
    else:
        detail_text = "Foi detetado um alerta associado à sua monitorização."

    text_body = (
        f"{title}\n\n"
        f"{body}\n\n"
        f"{detail_text}\n\n"
        "Pode consultar os detalhes na sua conta markee.\n\n"
        "Equipa markee\n"
    )
    safe_title = escape(title, quote=True)
    safe_body = escape(body, quote=True).replace("\n", "<br>")
    safe_detail = escape(detail_text, quote=True)
    html_body = (
        '<!DOCTYPE html>\n'
        '<html lang="pt-PT">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        "</head>\n"
        '<body style="margin:0;background:#08090a;color:#e8e8e8;'
        'font-family:Arial,Helvetica,sans-serif;line-height:1.5;padding:24px;">\n'
        '<main role="main" style="max-width:560px;margin:0 auto;'
        'background:#111214;border:1px solid rgba(255,255,255,0.08);'
        'border-radius:10px;padding:24px;">\n'
        f'<h1 style="color:#35d0e0;font-size:20px;margin:0 0 16px;">'
        f"{safe_title}</h1>\n"
        f"<p>{safe_body}</p>\n"
        f'<p style="color:#8a8d93;">{safe_detail}</p>\n'
        "<p>Pode consultar os detalhes na sua conta markee.</p>\n"
        '<hr style="border:0;border-top:1px solid rgba(255,255,255,0.08);'
        'margin:24px 0;">\n'
        '<p style="font-size:12px;color:#8a8d93;margin:0;">Equipa markee</p>\n'
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )
    return RenderedAlertEmail(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
