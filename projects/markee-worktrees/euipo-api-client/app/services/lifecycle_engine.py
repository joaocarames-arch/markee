"""Deadline and lifecycle calculation engine.

Implements the Portuguese (INPI) and European (EUIPO) rules for trademark
deadlines:

- **Renewal** — 10-year cycle, 6-month pre-expiry window, 6-month grace period.
- **Opposition** — 60 days (PT/INPI) / 90 days (EUIPO) after publication.
- **Response to provisional refusal** — configurable window (default 60 days).
- **Status transitions** — Active → Renewal → Grace → Lapsed → Recoverable → Dead.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class DeadlineRule:
    """A single calculated deadline with its escalating alert schedule."""

    rule_type: str
    due_date: date
    description: str
    alert_dates: list[date]


class LifecycleEngine:
    """Calculate deadlines and state transitions for trademarks."""

    PT_RENEWAL_YEARS = 10
    PT_GRACE_MONTHS = 6
    PT_OPPOSITION_DAYS = 60
    EU_OPPOSITION_DAYS = 90
    RESPONSE_REFUSAL_DAYS = 60
    GRACE_PERIOD_END_DAYS = 180

    def _next_renewal_date(self, registration_date: date, reference_year: int) -> date:
        """Return the next renewal date on the 10-year cycle.

        Args:
            registration_date: The date the mark was registered.
            reference_year: The year to compute the next cycle relative to.

        Returns:
            The date of the upcoming renewal.
        """
        cycle = self.PT_RENEWAL_YEARS
        years_elapsed = reference_year - registration_date.year
        cycles = years_elapsed // cycle
        next_cycle_number = cycles if years_elapsed % cycle == 0 else cycles + 1
        renewal_year = registration_date.year + (next_cycle_number * cycle)
        return date(renewal_year, registration_date.month, registration_date.day)

    def calculate_renewal_deadlines(
        self, registration_date: date, current_year: int | None = None
    ) -> list[DeadlineRule]:
        """Calculate the renewal and grace-period deadlines for a mark.

        Only the next renewal cycle is returned to avoid flooding the user.

        Args:
            registration_date: The mark's registration date.
            current_year: Year to compute against (defaults to today's year).

        Returns:
            A list with the renewal deadline and the grace-period deadline.
        """
        if current_year is None:
            current_year = date.today().year

        renewal_date = self._next_renewal_date(registration_date, current_year)
        grace_end = renewal_date + timedelta(days=self.GRACE_PERIOD_END_DAYS)

        return [
            DeadlineRule(
                rule_type="renewal",
                due_date=renewal_date,
                description=f"Renovação do registo — vence em {renewal_date.isoformat()}",
                alert_dates=self.get_alert_schedule(renewal_date),
            ),
            DeadlineRule(
                rule_type="grace_period",
                due_date=grace_end,
                description=(
                    f"Fim do período de graça para renovação — {grace_end.isoformat()}"
                ),
                alert_dates=self.get_alert_schedule(grace_end),
            ),
        ]

    def calculate_opposition_deadline(
        self, publication_date: date, jurisdiction: str
    ) -> DeadlineRule:
        """Return the opposition deadline for a published application.

        Args:
            publication_date: The date the application was published.
            jurisdiction: The jurisdiction (``"PT"``/``"INPI"`` or ``"EUIPO"``).

        Returns:
            The opposition :class:`DeadlineRule`.
        """
        days = (
            self.PT_OPPOSITION_DAYS
            if jurisdiction.upper() in ("INPI", "PT")
            else self.EU_OPPOSITION_DAYS
        )
        due = publication_date + timedelta(days=days)
        return DeadlineRule(
            rule_type="opposition",
            due_date=due,
            description=(
                f"Prazo para apresentação de oposição ({jurisdiction}) — {due.isoformat()}"
            ),
            alert_dates=self.get_alert_schedule(due),
        )

    def calculate_response_deadline(
        self, refusal_date: date, days: int = RESPONSE_REFUSAL_DAYS
    ) -> DeadlineRule:
        """Return the deadline to respond to a provisional refusal.

        Args:
            refusal_date: The date of the provisional refusal.
            days: The response window in days (default 60).

        Returns:
            The response :class:`DeadlineRule`.
        """
        due = refusal_date + timedelta(days=days)
        return DeadlineRule(
            rule_type="response_refusal",
            due_date=due,
            description=f"Prazo para resposta à recusa provisória — {due.isoformat()}",
            alert_dates=self.get_alert_schedule(due),
        )

    def get_alert_schedule(self, due_date: date) -> list[date]:
        """Return the future alert dates leading up to a deadline.

        Alerts are staged at 6 months, 3 months, 1 month, 7 days and 1 day
        before the deadline; dates already in the past are omitted.

        Args:
            due_date: The deadline the alerts count down to.

        Returns:
            Sorted list of future alert dates.
        """
        today = date.today()
        alerts = [
            due_date - timedelta(days=delta)
            for delta in (180, 90, 30, 7, 1)
            if due_date - timedelta(days=delta) >= today
        ]
        return sorted(alerts)

    def transition_status(self, current_status: str, event: str) -> str:
        """Return the new status after applying an event to the current status.

        Args:
            current_status: The mark's current lifecycle status.
            event: The event triggering a possible transition.

        Returns:
            The resulting status, or the unchanged status if the transition is
            not recognised.
        """
        status = (current_status or "").lower().strip()
        evt = event.lower().strip()

        transitions = {
            ("active", "renewal_due"): "renewal_period",
            ("renewal_period", "payment_received"): "active",
            ("renewal_period", "grace_period_started"): "grace_period",
            ("grace_period", "payment_received"): "active",
            ("grace_period", "grace_period_ended"): "lapsed",
            ("lapsed", "restoration_requested"): "recoverable",
            ("recoverable", "restoration_granted"): "active",
            ("recoverable", "restoration_denied"): "dead",
            ("lapsed", "restoration_window_closed"): "dead",
            ("active", "provisional_refusal"): "refused",
            ("refused", "response_accepted"): "active",
            ("refused", "response_rejected"): "dead",
        }
        return transitions.get((status, evt), status)

    def is_renewal_window_open(
        self, registration_date: date, today: date | None = None
    ) -> bool:
        """Check whether the mark is within its 6-month pre-expiry window.

        Args:
            registration_date: The mark's registration date.
            today: The reference date (defaults to today).

        Returns:
            ``True`` if the renewal window is currently open.
        """
        if today is None:
            today = date.today()
        renewal_date = self._next_renewal_date(registration_date, today.year)
        window_start = renewal_date - timedelta(days=self.GRACE_PERIOD_END_DAYS)
        return window_start <= today <= renewal_date

    def is_in_grace_period(
        self, registration_date: date, today: date | None = None
    ) -> bool:
        """Check whether the mark is within its 6-month post-expiry grace period.

        Args:
            registration_date: The mark's registration date.
            today: The reference date (defaults to today).

        Returns:
            ``True`` if the mark is currently in the grace period.
        """
        if today is None:
            today = date.today()
        renewal_date = self._next_renewal_date(registration_date, today.year)
        grace_end = renewal_date + timedelta(days=self.GRACE_PERIOD_END_DAYS)
        return renewal_date < today <= grace_end
