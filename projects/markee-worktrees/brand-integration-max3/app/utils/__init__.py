"""Shared utility helpers."""
from __future__ import annotations

from datetime import date, datetime


def parse_date(value: str | date | datetime | None) -> date | None:
    """Coerce a value into a :class:`datetime.date`.

    Accepts ISO-8601 date/datetime strings, ``date``/``datetime`` instances,
    or ``None``. Invalid strings resolve to ``None`` rather than raising, so
    ingestion of imperfect upstream data never crashes a task.

    Args:
        value: The value to coerce.

    Returns:
        A ``date`` instance, or ``None`` if the value is empty or unparseable.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def truncate(text: str | None, length: int = 500) -> str:
    """Return ``text`` truncated to at most ``length`` characters.

    Args:
        text: The text to truncate (``None`` becomes an empty string).
        length: Maximum length of the returned string.

    Returns:
        The truncated string.
    """
    if not text:
        return ""
    return text[:length]
