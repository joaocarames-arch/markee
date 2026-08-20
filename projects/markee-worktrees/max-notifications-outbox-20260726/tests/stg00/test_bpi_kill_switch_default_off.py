"""STG00-WP1: the BPI kill switch must be default-off with no env override."""
from __future__ import annotations

import pytest

from app.core.config import Settings

BPI_ENV_VARS = (
    "BPI_ENABLED",
    "BPI_SCHEDULE_ENABLED",
    "BPI_INGESTION_ALLOWED",
    "BPI_DENY_SOURCES",
)


@pytest.fixture
def clean_settings(monkeypatch) -> Settings:
    """Settings built without .env and without BPI environment overrides."""
    for name in BPI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)


class TestDefaultOff:
    def test_default_setting_disables_bpi(self, clean_settings):
        assert clean_settings.BPI_ENABLED is False
        assert clean_settings.BPI_SCHEDULE_ENABLED is False
        assert clean_settings.BPI_INGESTION_ALLOWED is False

    def test_default_deny_sources_include_inpi_bpi(self, clean_settings):
        assert "inpi_bpi" in clean_settings.BPI_DENY_SOURCES
        # The parser stamps lifecycle events with the short label "BPI".
        assert "BPI" in clean_settings.BPI_DENY_SOURCES


class TestDefaultPolicy:
    def test_policy_denies_bpi_sources(self, clean_settings):
        from app.core.source_policy import SourcePolicy

        policy = SourcePolicy.from_settings(clean_settings)
        assert policy.is_source_denied("inpi_bpi")
        assert policy.is_source_denied("BPI")
        assert policy.is_source_denied("bpi")

    def test_policy_allows_non_bpi_sources(self, clean_settings):
        from app.core.source_policy import SourcePolicy

        policy = SourcePolicy.from_settings(clean_settings)
        assert policy.is_source_allowed("euipo_api")
        assert policy.is_source_allowed("EUIPO")
        assert policy.is_source_allowed(None)

    def test_policy_gates_ingestion_and_schedule(self, clean_settings):
        from app.core.source_policy import SourcePolicy

        policy = SourcePolicy.from_settings(clean_settings)
        assert policy.bpi_ingestion_active is False
        assert policy.bpi_schedule_active is False

    def test_deny_survives_emptied_deny_list(self, clean_settings):
        """Fail closed: while BPI_ENABLED is False the deny list cannot be
        edited into allowing BPI labels."""
        from app.core.source_policy import SourcePolicy

        config = clean_settings.model_copy(update={"BPI_DENY_SOURCES": []})
        policy = SourcePolicy.from_settings(config)
        assert policy.is_source_denied("inpi_bpi")
        assert policy.is_source_denied("BPI")
