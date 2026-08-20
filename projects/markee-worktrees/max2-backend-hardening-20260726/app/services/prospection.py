"""Prospection engine — surfaces client opportunities for IP professionals."""
from __future__ import annotations

import csv
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trademark import Trademark


class ProspectionService:
    """Opportunity radar for IP agents and lawyers."""

    COMPANY_INDICATORS = (
        "lda",
        "l.d.a",
        "s.a",
        "sa",
        "unipessoal",
        "limitada",
        "sociedade",
    )

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialise the service.

        Args:
            db_session: Async database session.
        """
        self.db = db_session

    async def find_expiring_without_representative(
        self, months_ahead: int = 6, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Find marks expiring soon that have no representative.

        Args:
            months_ahead: How far ahead (in months) to look for expiry.
            limit: Maximum number of opportunities to return.

        Returns:
            A list of opportunity dicts.
        """
        today = date.today()
        horizon = today + timedelta(days=months_ahead * 30)
        stmt = (
            select(Trademark)
            .where(
                and_(
                    Trademark.status.in_(["REGISTERED", "PENDING", "ACTIVE"]),
                    Trademark.renewal_status != "RENEWED",
                )
            )
            .where(
                text(
                    """
                    (raw_data->>'expiry_date')::date BETWEEN :today AND :horizon
                    AND (
                        representatives IS NULL
                        OR jsonb_array_length(representatives) = 0
                        OR representatives = '[]'::jsonb
                    )
                    """
                ).bindparams(today=today, horizon=horizon)
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            self._to_opportunity(row, "expiring_no_representative")
            for row in result.scalars().all()
        ]

    async def find_new_filings_without_agent(
        self, days_back: int = 30, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Find recent filings without an appointed agent.

        Args:
            days_back: How many days back to consider as "recent".
            limit: Maximum number of opportunities to return.

        Returns:
            A list of opportunity dicts.
        """
        since = date.today() - timedelta(days=days_back)
        stmt = (
            select(Trademark)
            .where(
                and_(
                    Trademark.application_date >= since,
                    or_(
                        Trademark.representatives.is_(None),
                        text("jsonb_array_length(representatives) = 0"),
                        text("representatives = '[]'::jsonb"),
                    ),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            self._to_opportunity(row, "new_filing_without_agent")
            for row in result.scalars().all()
        ]

    async def find_recently_expired_active_companies(
        self, days_back: int = 90, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Find recently lapsed marks held by what look like active companies.

        Args:
            days_back: How many days back to consider expiries.
            limit: Maximum number of opportunities to return.

        Returns:
            A list of opportunity dicts.
        """
        since = date.today() - timedelta(days=days_back)
        stmt = (
            select(Trademark)
            .where(
                and_(
                    Trademark.status.in_(["EXPIRED", "LAPSED"]),
                    text("(raw_data->>'expiry_date')::date >= :since").bindparams(
                        since=since
                    ),
                )
            )
            .limit(limit * 3)
        )
        result = await self.db.execute(stmt)
        out: list[dict[str, Any]] = []
        for row in result.scalars().all():
            owner = self._extract_owner_name(row)
            if owner and self._looks_like_company(owner):
                out.append(self._to_opportunity(row, "recently_expired_company"))
        return out[:limit]

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _extract_owner_name(self, tm: Trademark) -> str | None:
        """Return the primary applicant/owner name for a mark."""
        if tm.applicants and isinstance(tm.applicants, list) and tm.applicants:
            first = tm.applicants[0]
            if isinstance(first, dict):
                return (
                    first.get("name")
                    or first.get("applicant_name")
                    or first.get("owner_name")
                )
            return str(first)
        return tm.word_mark

    def _extract_representative_name(self, tm: Trademark) -> str | None:
        """Return the primary representative name for a mark, if any."""
        if tm.representatives and isinstance(tm.representatives, list) and tm.representatives:
            first = tm.representatives[0]
            if isinstance(first, dict):
                return first.get("name") or first.get("representative_name")
            return str(first)
        return None

    def _extract_nice_classes(self, tm: Trademark) -> list[int]:
        """Return the mark's Nice classes as a list."""
        return list(tm.nice_classes) if tm.nice_classes else []

    def _looks_like_company(self, name: str) -> bool:
        """Heuristically decide whether a holder name denotes a company."""
        lowered = name.lower()
        return any(indicator in lowered for indicator in self.COMPANY_INDICATORS)

    def _to_opportunity(self, tm: Trademark, opportunity_type: str) -> dict[str, Any]:
        """Convert a trademark row into an opportunity dict.

        Args:
            tm: The source trademark.
            opportunity_type: The opportunity category label.

        Returns:
            A serialisable opportunity dict.
        """
        district: str | None = None
        expiry_date: Any = None
        if tm.raw_data and isinstance(tm.raw_data, dict):
            district = tm.raw_data.get("district") or tm.raw_data.get("holder_district")
            expiry_date = tm.raw_data.get("expiry_date")

        return {
            "trademark_id": str(tm.id),
            "word_mark": tm.word_mark,
            "owner": self._extract_owner_name(tm),
            "representative": self._extract_representative_name(tm),
            "status": tm.status,
            "nice_classes": self._extract_nice_classes(tm),
            "jurisdiction": tm.jurisdiction,
            "application_date": (
                tm.application_date.isoformat() if tm.application_date else None
            ),
            "expiry_date": expiry_date,
            "district": district,
            "opportunity_type": opportunity_type,
        }


# ── Module-level helpers (usable without a database session) ────────────────

CSV_COLUMNS = [
    "trademark",
    "owner",
    "representative",
    "expiry_date",
    "nice_classes",
    "opportunity_type",
    "district",
]


async def export_opportunities_csv(
    opportunities: list[dict[str, Any]], filepath: str
) -> None:
    """Write opportunities to a CSV file with the standard column layout.

    Args:
        opportunities: The opportunity dicts to export.
        filepath: Destination file path.
    """
    with open(filepath, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for opp in opportunities:
            writer.writerow(
                {
                    "trademark": opp.get("word_mark", ""),
                    "owner": opp.get("owner", ""),
                    "representative": opp.get("representative", ""),
                    "expiry_date": opp.get("expiry_date", ""),
                    "nice_classes": ",".join(
                        str(c) for c in opp.get("nice_classes", [])
                    ),
                    "opportunity_type": opp.get("opportunity_type", ""),
                    "district": opp.get("district", ""),
                }
            )


def filter_by_nice_class(
    opportunities: list[dict[str, Any]], class_num: int
) -> list[dict[str, Any]]:
    """Return opportunities that include a given Nice class.

    Args:
        opportunities: The opportunities to filter.
        class_num: The Nice class to require.

    Returns:
        The matching opportunities.
    """
    return [opp for opp in opportunities if class_num in opp.get("nice_classes", [])]


def filter_by_district(
    opportunities: list[dict[str, Any]], district: str
) -> list[dict[str, Any]]:
    """Return opportunities in a given district (case-insensitive).

    Args:
        opportunities: The opportunities to filter.
        district: The district name to match.

    Returns:
        The matching opportunities.
    """
    target = district.lower()
    return [
        opp for opp in opportunities if (opp.get("district") or "").lower() == target
    ]
