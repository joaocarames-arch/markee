"""STG00-WP1: the beat schedule must exclude BPI work while BPI is disabled."""
from __future__ import annotations

from app.core.config import Settings
from app.core.source_policy import SourcePolicy
from app.tasks import build_beat_schedule, celery_app


def _policy(**overrides) -> SourcePolicy:
    config = Settings(_env_file=None).model_copy(update=overrides)
    return SourcePolicy.from_settings(config)


class TestScheduleDisabled:
    def test_parse_bpi_not_in_beat_schedule_when_disabled(self):
        schedule = build_beat_schedule(_policy())
        assert "parse-bpi-daily" not in schedule

    def test_registered_celery_schedule_has_no_bpi_entry(self):
        """The schedule actually loaded into the Celery app (built from the
        default settings) must not contain the BPI entry."""
        assert "parse-bpi-daily" not in celery_app.conf.beat_schedule

    def test_non_bpi_entries_remain(self):
        """Containment must not disable the rest of the pipeline."""
        schedule = build_beat_schedule(_policy())
        for entry in (
            "poll-euipo-6h",
            "calculate-deadlines-hourly",
            "match-similar-hourly",
            "send-alerts-every-15min",
            "check-expiry-weekly",
        ):
            assert entry in schedule


class TestEnablementIsLocalOnly:
    def test_enabled_policy_can_represent_bpi_schedule(self):
        """Explicit enablement is representable in local config (gated by
        João before any deployment; nothing here touches runtime)."""
        enabled = _policy(BPI_ENABLED=True, BPI_SCHEDULE_ENABLED=True)
        schedule = build_beat_schedule(enabled)
        assert "parse-bpi-daily" in schedule
        assert (
            schedule["parse-bpi-daily"]["task"]
            == "app.tasks.parse_bpi.download_and_parse"
        )

    def test_enabled_flag_alone_is_not_enough(self):
        assert "parse-bpi-daily" not in build_beat_schedule(_policy(BPI_ENABLED=True))
        assert "parse-bpi-daily" not in build_beat_schedule(
            _policy(BPI_SCHEDULE_ENABLED=True)
        )

    def test_local_enablement_does_not_mutate_registered_schedule(self):
        build_beat_schedule(_policy(BPI_ENABLED=True, BPI_SCHEDULE_ENABLED=True))
        assert "parse-bpi-daily" not in celery_app.conf.beat_schedule
