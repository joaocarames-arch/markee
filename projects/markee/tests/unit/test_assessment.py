"""Unit tests for the stateless trademark assessment service.

These target the pure, deterministic heuristics (distinctiveness, Nice class
recommendation, opposition-risk and verdict) plus the report assembly. No
database, network or FastAPI involvement — the logic must stand alone.
"""
from __future__ import annotations

import pytest

from app.services.assessment import (
    DISCLAIMERS,
    AssessmentRequest,
    CandidateMatch,
    assess_distinctiveness,
    assess_opposition_risk,
    build_report,
    determine_verdict,
    recommend_nice_classes,
)


class TestDistinctiveness:
    """Distinctiveness heuristic: coined marks strong, generic marks weak."""

    def test_coined_mark_is_fully_met(self):
        result = assess_distinctiveness("Zyphora", "plataforma de software")
        assert result.level == "fully_met"
        assert result.score >= 70
        assert result.rationale  # PT rationale present

    def test_all_generic_descriptive_mark_is_not_fully_met(self):
        result = assess_distinctiveness("Online Shop", "online shop de roupa")
        assert result.level in {"partially_met", "not_met"}
        assert result.score < 70

    def test_purely_generic_mark_scores_low(self):
        result = assess_distinctiveness("Loja Online", "loja online")
        assert result.score < assess_distinctiveness("Zyphora", "").score

    def test_empty_mark_is_not_met(self):
        result = assess_distinctiveness("   ", "")
        assert result.level == "not_met"

    def test_short_acronym_is_penalised(self):
        short = assess_distinctiveness("AB", "")
        coined = assess_distinctiveness("Zyphora", "")
        assert short.score < coined.score


class TestNiceRecommendation:
    """Nice class recommendation heuristic (covers 35/42/45 and common cases)."""

    def test_software_saas_recommends_42(self):
        recs = recommend_nice_classes("SaaS e desenvolvimento de software", None)
        numbers = {r.class_number for r in recs}
        assert 42 in numbers

    def test_ecommerce_recommends_35(self):
        recs = recommend_nice_classes("loja online de roupa e comércio eletrónico", None)
        numbers = {r.class_number for r in recs}
        assert 35 in numbers

    def test_legal_services_recommends_45(self):
        recs = recommend_nice_classes("serviços jurídicos e de advocacia", None)
        numbers = {r.class_number for r in recs}
        assert 45 in numbers

    def test_provided_classes_are_preserved(self):
        recs = recommend_nice_classes("", [12])
        numbers = {r.class_number for r in recs}
        assert 12 in numbers

    def test_empty_input_falls_back_to_safe_default(self):
        recs = recommend_nice_classes("", None)
        assert recs, "recommendation must never be empty"
        assert all(1 <= r.class_number <= 45 for r in recs)

    def test_recommendations_sorted_and_titled(self):
        recs = recommend_nice_classes("software e loja online", None)
        assert [r.class_number for r in recs] == sorted(r.class_number for r in recs)
        assert all(r.title_pt for r in recs)


class TestOppositionRiskAndVerdict:
    """Risk scoring and the derived verdict."""

    def _cand(self, sim: float) -> CandidateMatch:
        return CandidateMatch(
            word_mark="OTHER",
            jurisdiction="EU",
            similarity=sim,
            similarity_band="low",
            source="database",
        )

    def test_no_candidates_low_risk(self):
        risk = assess_opposition_risk("fully_met", [], identical_match=False)
        assert risk.level == "low"

    def test_identical_match_is_high_risk(self):
        risk = assess_opposition_risk("fully_met", [], identical_match=True)
        assert risk.level == "high"

    def test_high_similarity_is_high_risk(self):
        risk = assess_opposition_risk("fully_met", [self._cand(92)], identical_match=False)
        assert risk.level == "high"

    def test_medium_similarity_is_medium_risk(self):
        risk = assess_opposition_risk("fully_met", [self._cand(74)], identical_match=False)
        assert risk.level == "medium"

    def test_verdict_eligible_when_low_risk_and_distinctive(self):
        verdict, label = determine_verdict("fully_met", "low", identical_match=False)
        assert verdict == "eligible"
        assert label

    def test_verdict_not_recommended_on_identical(self):
        verdict, _ = determine_verdict("fully_met", "high", identical_match=True)
        assert verdict == "not_recommended"

    def test_verdict_with_reservations_on_partial(self):
        verdict, _ = determine_verdict("partially_met", "medium", identical_match=False)
        assert verdict == "eligible_with_risk"


class TestBuildReport:
    """The report assembly must satisfy the published contract."""

    def test_full_report_shape(self):
        req = AssessmentRequest(
            mark_name="Zyphora",
            jurisdiction="EU",
            business_description="plataforma SaaS de software",
            nice_classes=None,
        )
        report = build_report(req, candidates=[], provenance="unavailable")

        assert report.mark_name == "Zyphora"
        assert report.verdict in {"eligible", "eligible_with_risk", "not_recommended"}
        assert report.risk_level in {"low", "medium", "high"}
        assert report.distinctiveness.level in {"fully_met", "partially_met", "not_met"}
        assert report.recommended_classes
        assert report.candidates_provenance == "unavailable"
        assert report.candidates == []
        assert report.opposition_risk.level in {"low", "medium", "high"}
        assert report.recommendations
        assert report.disclaimers == DISCLAIMERS
        assert report.created_at is not None

    def test_identical_candidate_sets_identical_match_and_risk(self):
        req = AssessmentRequest(mark_name="Zyphora", jurisdiction="EU")
        identical = CandidateMatch(
            word_mark="Zyphora",
            jurisdiction="EU",
            similarity=100.0,
            similarity_band="high",
            source="database",
        )
        report = build_report(req, candidates=[identical], provenance="database")
        assert report.identical_match is True
        assert report.risk_level == "high"
        assert report.verdict == "not_recommended"

    def test_disclaimer_mentions_not_legal_advice(self):
        joined = " ".join(DISCLAIMERS).lower()
        assert "legal advice" in joined
