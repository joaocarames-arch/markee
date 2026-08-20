"""Central source allow/deny policy — the BPI containment kill switch.

Single decision point for whether a data source may schedule work, ingest
lifecycle events, produce deadlines, generate alerts or trigger external
dispatch. The beat schedule, ingestion service, deadline recalculation,
alert generation and alert dispatch all consult this module so the deny
logic exists exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings as app_settings

# Canonical registry name of the INPI BPI source (``core.sources.name``).
BPI_SOURCE_NAME = "inpi_bpi"
# Label the BPI parser stamps on the lifecycle events it extracts.
BPI_EVENT_SOURCE_LABEL = "BPI"


def _normalize(source: str) -> str:
    """Normalise a source label for case-insensitive comparison."""
    return source.strip().lower()


@dataclass(frozen=True)
class SourcePolicy:
    """Immutable, typed snapshot of the source allow/deny configuration."""

    bpi_enabled: bool
    bpi_schedule_enabled: bool
    bpi_ingestion_allowed: bool
    deny_sources: frozenset[str]

    @classmethod
    def from_settings(cls, config: Settings) -> SourcePolicy:
        """Build a policy from a settings object.

        While ``BPI_ENABLED`` is off the BPI labels are denied regardless of
        the configured deny list, so an edited or emptied list cannot re-open
        the pipeline (fail closed).

        Args:
            config: The settings to snapshot.

        Returns:
            The derived :class:`SourcePolicy`.
        """
        deny = {_normalize(name) for name in config.BPI_DENY_SOURCES}
        if not config.BPI_ENABLED:
            deny.add(_normalize(BPI_SOURCE_NAME))
            deny.add(_normalize(BPI_EVENT_SOURCE_LABEL))
        return cls(
            bpi_enabled=config.BPI_ENABLED,
            bpi_schedule_enabled=config.BPI_SCHEDULE_ENABLED,
            bpi_ingestion_allowed=config.BPI_INGESTION_ALLOWED,
            deny_sources=frozenset(deny),
        )

    def is_source_denied(self, source: str | None) -> bool:
        """Return whether a source label is denied.

        Args:
            source: A source label (registry name or event label); ``None``
                and empty labels are treated as not denied.

        Returns:
            ``True`` when the source must not produce downstream effects.
        """
        if not source:
            return False
        return _normalize(source) in self.deny_sources

    def is_source_allowed(self, source: str | None) -> bool:
        """Inverse of :meth:`is_source_denied`."""
        return not self.is_source_denied(source)

    @property
    def bpi_ingestion_active(self) -> bool:
        """Whether BPI lifecycle events may be written at all."""
        return self.bpi_enabled and self.bpi_ingestion_allowed

    @property
    def bpi_schedule_active(self) -> bool:
        """Whether the daily BPI beat entry may be registered."""
        return self.bpi_enabled and self.bpi_schedule_enabled


def get_source_policy() -> SourcePolicy:
    """Build the policy from the live settings singleton.

    Reads the singleton on every call (cheap) so tests can monkeypatch
    settings attributes and observe the effect immediately.

    Returns:
        The current :class:`SourcePolicy`.
    """
    return SourcePolicy.from_settings(app_settings)
