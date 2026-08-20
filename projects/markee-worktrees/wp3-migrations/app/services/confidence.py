"""Confidence scoring for extracted data.

Every ingested record gets a score in ``[0, 1]`` describing how much we trust
the extraction. Records/events below :data:`REVIEW_THRESHOLD` are routed to
``app.review_queue`` instead of (or in addition to) being written to core.

Two scorers exist:

- :func:`score_trademark_record` — structured API records (EUIPO/TMview).
- :func:`score_bpi_event` — events extracted from BPI PDFs via regex, which
  are inherently less reliable than structured API data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.utils import parse_date

# Below this overall score a result is queued for human review.
REVIEW_THRESHOLD = 0.6

# Known status vocabulary across EUIPO/TMview/INPI (upper-cased for matching).
_KNOWN_STATUSES = {
    "REGISTERED",
    "PUBLISHED",
    "APPLICATION_PUBLISHED",
    "FILED",
    "APPLICATION FILED",
    "UNDER_EXAMINATION",
    "OPPOSED",
    "OPPOSITION_PENDING",
    "REFUSED",
    "WITHDRAWN",
    "EXPIRED",
    "CANCELLED",
    "SURRENDERED",
}

# EU application numbers are numeric (9 digits, but historic ones are shorter);
# INPI uses 5-7 digits, optionally prefixed (e.g. "N-123456").
_RE_EU_APP_NUMBER = re.compile(r"^\d{6,10}$")
_RE_PT_APP_NUMBER = re.compile(r"^(?:[A-Z]{1,3}[-/ ]?)?\d{4,8}$", re.IGNORECASE)

# BPI event types the parser can emit.
_KNOWN_BPI_EVENT_TYPES = {
    "publication",
    "grant",
    "provisional_refusal",
    "opposition_filed",
    "renewal",
    "lapse",
    "transfer",
    "change_name",
}


@dataclass
class RecordConfidence:
    """Per-field and overall confidence for one extracted record."""

    overall: float
    fields: dict[str, float] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        """Whether the record should be queued for human review."""
        return self.overall < REVIEW_THRESHOLD


def _clamp(value: float) -> float:
    """Clamp a score into the [0, 1] interval."""
    return max(0.0, min(1.0, value))


def score_application_number(value: str | None, jurisdiction: str | None = None) -> float:
    """Score an application number against the expected per-office format.

    Args:
        value: The application number as received.
        jurisdiction: Optional jurisdiction hint (``EUIPO``/``EU``/``INPI``/``PT``).

    Returns:
        1.0 for a well-formed number, 0.5 for a plausible-but-odd one,
        0.0 when missing.
    """
    if not value:
        return 0.0
    value = value.strip()
    juris = (jurisdiction or "").upper()
    if juris in {"EUIPO", "EU"}:
        return 1.0 if _RE_EU_APP_NUMBER.match(value) else 0.5
    if juris in {"INPI", "PT"}:
        return 1.0 if _RE_PT_APP_NUMBER.match(value) else 0.5
    # Unknown jurisdiction: accept either format.
    if _RE_EU_APP_NUMBER.match(value) or _RE_PT_APP_NUMBER.match(value):
        return 1.0
    return 0.5


def score_word_mark(value: str | None) -> float:
    """Score a word mark: present, not suspiciously short/garbled."""
    if not value or not value.strip():
        return 0.0
    text = value.strip()
    if len(text) < 2:
        return 0.4
    # A mark made mostly of non-word characters is likely an extraction artefact.
    wordish = sum(1 for c in text if c.isalnum() or c.isspace())
    return 1.0 if wordish / len(text) >= 0.6 else 0.5


def score_status(value: str | None) -> float:
    """Score a status value against the known vocabulary."""
    if not value:
        return 0.0
    normalised = value.strip().upper().replace(" ", "_")
    if normalised in _KNOWN_STATUSES or value.strip().upper() in _KNOWN_STATUSES:
        return 1.0
    return 0.7  # present but unrecognised — usable, worth flagging


def score_date_field(value: Any) -> float:
    """Score a date-ish field: 1.0 parseable, 0.3 present but unparseable, 0.0 absent."""
    if value in (None, ""):
        return 0.0
    return 1.0 if parse_date(value) is not None else 0.3


def score_nice_classes(value: Any) -> float:
    """Score a Nice class list: all classes must be within 1-45."""
    if not value:
        return 0.0
    try:
        classes = [int(c) for c in value]
    except (TypeError, ValueError):
        return 0.2
    if not classes:
        return 0.0
    valid = sum(1 for c in classes if 1 <= c <= 45)
    return _clamp(valid / len(classes))


def score_trademark_record(record: dict[str, Any]) -> RecordConfidence:
    """Score a normalised trademark record from a structured source.

    The overall score is a weighted average; identity fields (application
    number, word mark) weigh the most because everything downstream keys on
    them. Optional fields that are simply absent lower the score less than
    fields that are present but malformed.

    Args:
        record: A normalised trademark record (see ingestion service).

    Returns:
        A :class:`RecordConfidence` with per-field scores and issue notes.
    """
    jurisdiction = record.get("jurisdiction")
    fields: dict[str, float] = {
        "application_number": score_application_number(
            record.get("application_number"), jurisdiction
        ),
        "word_mark": score_word_mark(record.get("word_mark")),
        "status": score_status(record.get("status")),
        "application_date": score_date_field(record.get("application_date")),
        "nice_classes": score_nice_classes(record.get("nice_classes")),
    }
    weights = {
        "application_number": 0.30,
        "word_mark": 0.30,
        "status": 0.15,
        "application_date": 0.10,
        "nice_classes": 0.15,
    }
    overall = _clamp(sum(fields[name] * weights[name] for name in weights))

    issues = [name for name, value in fields.items() if value < 1.0]
    return RecordConfidence(overall=overall, fields=fields, issues=issues)


def score_bpi_event(
    event_type: str,
    application_number: str | None,
    excerpt: str | None = None,
    has_event_date: bool = True,
) -> float:
    """Score a lifecycle event extracted from a BPI PDF.

    PDF extraction is regex-driven, so the score reflects how well the pieces
    match their expected shapes: a known event type, a well-formed PT
    application number, a meaningful surrounding excerpt and an event date.

    Args:
        event_type: The classified event type.
        application_number: The extracted application number.
        excerpt: The source text surrounding the match.
        has_event_date: Whether the event carries a date.

    Returns:
        A score in [0, 1].
    """
    type_score = 1.0 if event_type in _KNOWN_BPI_EVENT_TYPES else 0.3
    number_score = score_application_number(application_number, "PT")
    excerpt_len = len((excerpt or "").strip())
    if excerpt_len >= 40:
        excerpt_score = 1.0
    elif excerpt_len >= 10:
        excerpt_score = 0.6
    else:
        excerpt_score = 0.2
    date_score = 1.0 if has_event_date else 0.0

    overall = (
        0.25 * type_score + 0.40 * number_score + 0.20 * excerpt_score + 0.15 * date_score
    )
    return _clamp(overall)
