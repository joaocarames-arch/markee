"""Assessment router — stateless free trademark check (``POST /assessments``).

Public endpoint (no authentication): the user submits a mark name, jurisdiction
and business description and receives a structured assessment report. Prior-art
candidates come from the existing :class:`SimilarityEngine` when a database is
reachable; any failure degrades safely to an empty candidate list flagged as
``unavailable`` so the rest of the report is always produced.
"""
from __future__ import annotations

import logging

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.database import get_db
from app.models.user import User
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
_PUBLIC_CANDIDATE_LIMIT = 3


class PublicCandidate(BaseModel):
    """Limited public candidate shape."""

    word_mark: str
    jurisdiction: str
    similarity_band: str


class PublicAssessmentResponse(BaseModel):
    """Simplified public preliminary trademark-check response."""

    mark_name: str
    jurisdiction: str
    preliminary_status: str
    candidate_count: int
    top_candidates: list[PublicCandidate]
    plain_english_explanation: str
    limitations: list[str]
    next_actions: list[str]
    created_at: datetime


class ProfessionalAssessmentResponse(AssessmentReport):
    """Professional response with factor detail and provenance metadata."""

    analysis_detail: dict[str, Any]
    coverage_metadata: dict[str, Any]


async def require_professional_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow only Markee professional/admin users to access deep analysis."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professional access required",
        )
    return current_user


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


def _public_status(report: AssessmentReport) -> str:
    """Map internal verdict/risk to a deliberately coarse public status."""
    if report.verdict == "not_recommended" or report.risk_level == "high":
        return "Significant issue identified"
    if report.verdict == "eligible_with_risk" or report.risk_level == "medium":
        return "Review recommended"
    return "No obvious issue identified"


def _public_explanation(report: AssessmentReport) -> str:
    """Plain-English public explanation without factor-by-factor reasoning."""
    if report.candidates:
        return (
            "The preliminary check found potentially relevant earlier marks. "
            "A professional review is recommended before relying on the result."
        )
    if report.candidates_provenance == "unavailable":
        return (
            "The preliminary check ran, but earlier-right data was unavailable. "
            "Repeat the check or request expert review before filing."
        )
    return (
        "No obvious issue was identified in this preliminary automated check. "
        "This is not a legal clearance opinion."
    )


def _to_public_response(report: AssessmentReport) -> PublicAssessmentResponse:
    """Project the full report into the limited public response contract."""
    return PublicAssessmentResponse(
        mark_name=report.mark_name,
        jurisdiction=report.jurisdiction,
        preliminary_status=_public_status(report),
        candidate_count=len(report.candidates),
        top_candidates=[
            PublicCandidate(
                word_mark=candidate.word_mark,
                jurisdiction=candidate.jurisdiction,
                similarity_band=candidate.similarity_band,
            )
            for candidate in report.candidates[:_PUBLIC_CANDIDATE_LIMIT]
        ],
        plain_english_explanation=_public_explanation(report),
        limitations=[
            "This is an automated preliminary check, not legal advice.",
            "Earlier-right data may be incomplete, outdated or unavailable.",
            "Nice classes help retrieval but do not prove legal similarity of goods/services.",
        ],
        next_actions=["Request expert review", "Register this trademark"],
        created_at=report.created_at,
    )


def _coverage_metadata(report: AssessmentReport) -> dict[str, Any]:
    """Describe what source coverage is actually supported by this assessment."""
    status_value = "unknown" if report.candidates_provenance == "unavailable" else "partial"
    return {
        "coverage_status": status_value,
        "sources_searched": [report.candidates_provenance],
        "jurisdictions": [report.jurisdiction],
        "limitations": [
            "No complete EU-wide national earlier-right coverage is claimed.",
            "Candidate retrieval currently depends on available local trademark data.",
        ],
    }


def _analysis_detail(report: AssessmentReport) -> dict[str, Any]:
    """Expose professional-only factor structure without hiding uncertainty."""
    return {
        "public_response_depth": "limited",
        "professional_response_depth": "factor_level",
        "factors": [
            "distinctiveness",
            "recommended_classes",
            "candidate_retrieval",
            "opposition_risk",
        ],
        "unknown_policy": "Unavailable facts remain unavailable or require professional review.",
        "candidate_retrieval_provenance": report.candidates_provenance,
    }


async def _build_assessment_report(
    request: AssessmentRequest,
    db: AsyncSession,
) -> AssessmentReport:
    candidates, provenance = await _gather_candidates(db, request)
    return build_report(request, candidates=candidates, provenance=provenance)


@router.post("", response_model=AssessmentReport)
async def create_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
) -> AssessmentReport:
    """Generate the backwards-compatible stateless free trademark check report."""
    return await _build_assessment_report(request, db)


@router.post("/public", response_model=PublicAssessmentResponse)
async def create_public_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
) -> PublicAssessmentResponse:
    """Generate a simplified public preliminary trademark-check result."""
    report = await _build_assessment_report(request, db)
    return _to_public_response(report)


@router.post("/professional", response_model=ProfessionalAssessmentResponse)
async def create_professional_assessment(
    request: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_professional_user),
) -> ProfessionalAssessmentResponse:
    """Generate the protected professional factor-level assessment."""
    _ = current_user  # The dependency is the access-control boundary.
    report = await _build_assessment_report(request, db)
    return ProfessionalAssessmentResponse(
        **report.model_dump(),
        analysis_detail=_analysis_detail(report),
        coverage_metadata=_coverage_metadata(report),
    )
