"""Tests for the lifecycle / deadline engine.

Testa cálculo de prazos de renovação (10 anos, 6 meses pré, 6 meses graça),
oposição (60d PT, 90d EU) e transições de estado.
"""
import pytest
from datetime import date, timedelta

from app.services.lifecycle_engine import LifecycleEngine, DeadlineRule


class TestRenewalDeadlines:
    """Ciclo de 10 anos, janela pré-expiração de 6 meses, período de graça de 6 meses."""

    def setup_method(self):
        self.engine = LifecycleEngine()
        self.reg_date = date(2015, 3, 15)

    def test_renewal_year_calculation(self):
        deadlines = self.engine.calculate_renewal_deadlines(self.reg_date, current_year=2024)
        assert len(deadlines) == 2

        renewal = [d for d in deadlines if d.rule_type == "renewal"][0]
        # 2015 + 10*1 = 2025 (próximo ciclo a partir de 2024)
        assert renewal.due_date == date(2025, 3, 15)

    def test_grace_period_end(self):
        deadlines = self.engine.calculate_renewal_deadlines(self.reg_date, current_year=2024)
        grace = [d for d in deadlines if d.rule_type == "grace_period"][0]
        # 6 meses após 2025-03-15
        assert grace.due_date == date(2025, 9, 11)  # 2025-03-15 + 180 days

    def test_alert_schedule_before_renewal(self):
        # Usar current_year = ano atual para garantir que alertas são no futuro
        from datetime import date as dt
        current_year = dt.today().year
        deadlines = self.engine.calculate_renewal_deadlines(self.reg_date, current_year=current_year)
        renewal = [d for d in deadlines if d.rule_type == "renewal"][0]
        # Deve ter alertas escalonados: 6m, 3m, 1m, 7d, 1d antes
        assert len(renewal.alert_dates) > 0
        assert all(a <= renewal.due_date for a in renewal.alert_dates)

    def test_renewal_window_open(self):
        # 6 meses antes de 2025-03-15 = 2024-09-16
        today = date(2024, 10, 1)
        assert self.engine.is_renewal_window_open(self.reg_date, today) is True

    def test_renewal_window_closed_before(self):
        today = date(2024, 1, 1)
        assert self.engine.is_renewal_window_open(self.reg_date, today) is False

    def test_grace_period_active(self):
        # Após 2025-03-15 mas antes de 2025-09-12
        today = date(2025, 5, 1)
        assert self.engine.is_in_grace_period(self.reg_date, today) is True

    def test_grace_period_ended(self):
        today = date(2026, 1, 1)
        assert self.engine.is_in_grace_period(self.reg_date, today) is False


class TestOppositionDeadlines:
    """Prazos de oposição: 60 dias (PT/INPI), 90 dias (EUIPO)."""

    def setup_method(self):
        self.engine = LifecycleEngine()
        self.pub_date = date(2024, 1, 15)

    def test_pt_opposition_deadline(self):
        deadline = self.engine.calculate_opposition_deadline(self.pub_date, "PT")
        assert deadline.due_date == date(2024, 3, 15)  # 60 days
        assert deadline.rule_type == "opposition"

    def test_inpi_opposition_deadline(self):
        deadline = self.engine.calculate_opposition_deadline(self.pub_date, "INPI")
        assert deadline.due_date == date(2024, 3, 15)

    def test_eu_opposition_deadline(self):
        deadline = self.engine.calculate_opposition_deadline(self.pub_date, "EUIPO")
        assert deadline.due_date == date(2024, 4, 14)  # 90 days

    def test_eu_lowercase(self):
        deadline = self.engine.calculate_opposition_deadline(self.pub_date, "euipo")
        assert deadline.due_date == date(2024, 4, 14)


class TestResponseRefusalDeadline:
    """Prazo para resposta a recusa provisória."""

    def setup_method(self):
        self.engine = LifecycleEngine()

    def test_default_60_days(self):
        refusal_date = date(2024, 6, 1)
        deadline = self.engine.calculate_response_deadline(refusal_date)
        assert deadline.due_date == date(2024, 7, 31)

    def test_custom_days(self):
        refusal_date = date(2024, 6, 1)
        deadline = self.engine.calculate_response_deadline(refusal_date, days=30)
        assert deadline.due_date == date(2024, 7, 1)


class TestStatusTransitions:
    """Transições de estado do registo."""

    def setup_method(self):
        self.engine = LifecycleEngine()

    def test_active_to_renewal_period(self):
        assert self.engine.transition_status("active", "renewal_due") == "renewal_period"

    def test_renewal_period_to_active(self):
        assert self.engine.transition_status("renewal_period", "payment_received") == "active"

    def test_renewal_period_to_grace(self):
        assert self.engine.transition_status("renewal_period", "grace_period_started") == "grace_period"

    def test_grace_to_active(self):
        assert self.engine.transition_status("grace_period", "payment_received") == "active"

    def test_grace_to_lapsed(self):
        assert self.engine.transition_status("grace_period", "grace_period_ended") == "lapsed"

    def test_lapsed_to_recoverable(self):
        assert self.engine.transition_status("lapsed", "restoration_requested") == "recoverable"

    def test_recoverable_to_active(self):
        assert self.engine.transition_status("recoverable", "restoration_granted") == "active"

    def test_recoverable_to_dead(self):
        assert self.engine.transition_status("recoverable", "restoration_denied") == "dead"

    def test_lapsed_to_dead(self):
        assert self.engine.transition_status("lapsed", "restoration_window_closed") == "dead"

    def test_active_to_refused(self):
        assert self.engine.transition_status("active", "provisional_refusal") == "refused"

    def test_refused_to_active(self):
        assert self.engine.transition_status("refused", "response_accepted") == "active"

    def test_refused_to_dead(self):
        assert self.engine.transition_status("refused", "response_rejected") == "dead"

    def test_unknown_event_unchanged(self):
        assert self.engine.transition_status("active", "unknown_event") == "active"
