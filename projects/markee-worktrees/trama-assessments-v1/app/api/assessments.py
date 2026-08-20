"""Assessment router — stateless free trademark check (``POST /assessments``).

Public endpoint (no authentication): the user submits a mark name, jurisdiction
and business description and receives a structured assessment report. Prior-art
candidates come from the existing :class:`SimilarityEngine` when a database is
reachable; any failure degrades safely to an empty candidate list flagged as
``unavailable`` so the rest of the report is always produced.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.assessment import (
    AssessmentReport,
    AssessmentRequest,
    CandidateMatch,
    build_report,
    similarity_band,
)
from app.services.similarity_engine import SimilarityEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assessments", tags=["assessments"])

# Candidate search tuning: a low threshold maximises recall for the report,
# while the cap keeps the payload small.
_CANDIDATE_THRESHOLD = 45
_CANDIDATE_LIMIT = 10


async def _gather_candidates(
    db: AsyncSession, request: AssessmentRequest
) -> tuple[list[CandidateMatch], str]:
    """Run the similarity pass, degrading safely on any failure.

    Returns:
        A ``(candidates, provenance)`` tuple. ``provenance`` is ``"database"``
        when the query succeeded (even with zero rows) and ``"unavailable"``
        when the data source could not be reached.
    """
    try:
        engine = SimilarityEngine(db)
        rows = await engine.find_similar_marks(
            query=request.mark_name,
            nice_classes=request.nice_classes,
            threshold=_CANDIDATE_THRESHOLD,
            limit=_CANDIDATE_LIMIT,
        )
    except Exception:  # noqa: BLE001 - fail-soft: never break the report
        logger.warning("Similarity pass unavailable; returning empty candidates")
        return [], "unavailable"

    candidates: list[CandidateMatch] = []
    for row in rows:
        word_mark = row.get("word_mark") or ""
        if not word_mark:
            continue
        score = float(
            row.get("composite_score")
            or row.get("similarity_score")
            or 0.0
        )
        candidates.append(
            CandidateMatch(
                word_mark=word_mark,
                jurisdiction=row.get("jurisdiction") or request.jurisdiction,
                similarity=round(min(100.0, max(0.0, score)), 1),
                similarity_band=similarity_band(score),
                source=str(row.get("source_id") or "database"),
            )
        )
    return candidates, "database"


@router.post("", response_model=AssessmentReport)
async def create_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
) -> AssessmentReport:
    """Generate a stateless free trademark check report.

    Args:
        request: The assessment request (mark name, jurisdiction, description
            and optional Nice classes).
        db: Database session (used only for the similarity pass; failures are
            tolerated).

    Returns:
        The full :class:`AssessmentReport`. Nothing is persisted.
    """
    candidates, provenance = await _gather_candidates(db, request)
    return build_report(request, candidates=candidates, provenance=provenance)
