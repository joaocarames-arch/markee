"""Tests for the confidence scoring service."""
from __future__ import annotations

from app.services.confidence import (
    REVIEW_THRESHOLD,
    score_application_number,
    score_bpi_event,
    score_date_field,
    score_nice_classes,
    score_status,
    score_trademark_record,
    score_word_mark,
)


def _full_record() -> dict:
    return {
        "application_number": "018765432",
        "word_mark": "ACME TECH",
        "status": "REGISTERED",
        "application_date": "2024-01-15",
        "nice_classes": [9, 42],
        "jurisdiction": "EUIPO",
    }


class TestFieldScores:
    def test_application_number_eu_valid(self):
        assert score_application_number("018765432", "EUIPO") == 1.0

    def test_application_number_pt_valid(self):
        assert score_application_number("N-123456", "INPI") == 1.0
        assert score_application_number("123456", "PT") == 1.0

    def test_application_number_malformed(self):
        assert score_application_number("???", "EUIPO") == 0.5

    def test_application_number_missing(self):
        assert score_application_number(None) == 0.0
        assert score_application_number("") == 0.0

    def test_word_mark_scores(self):
        assert score_word_mark("ACME TECH") == 1.0
        assert score_word_mark("A") == 0.4
        assert score_word_mark("###@@@!!") == 0.5
        assert score_word_mark("") == 0.0
        assert score_word_mark(None) == 0.0

    def test_status_scores(self):
        assert score_status("REGISTERED") == 1.0
        assert score_status("Application Published") == 1.0
        assert score_status("SOMETHING_ODD") == 0.7
        assert score_status(None) == 0.0

    def test_date_scores(self):
        assert score_date_field("2024-01-15") == 1.0
        assert score_date_field("not-a-date") == 0.3
        assert score_date_field(None) == 0.0

    def test_nice_classes_scores(self):
        assert score_nice_classes([9, 42]) == 1.0
        assert score_nice_classes([9, 99]) == 0.5
        assert score_nice_classes([]) == 0.0
        assert score_nice_classes(None) == 0.0
        assert score_nice_classes("garbage") == 0.2


class TestTrademarkRecordScore:
    def test_complete_record_scores_high(self):
        confidence = score_trademark_record(_full_record())
        assert confidence.overall == 1.0
        assert not confidence.needs_review
        assert confidence.issues == []

    def test_sparse_record_needs_review(self):
        confidence = score_trademark_record({"application_number": None, "word_mark": ""})
        assert confidence.overall < REVIEW_THRESHOLD
        assert confidence.needs_review
        assert "application_number" in confidence.issues
        assert "word_mark" in confidence.issues

    def test_partial_record_between_thresholds(self):
        record = _full_record()
        record["application_date"] = None
        record["nice_classes"] = None
        confidence = score_trademark_record(record)
        assert 0.6 <= confidence.overall < 1.0
        assert not confidence.needs_review

    def test_scores_are_bounded(self):
        confidence = score_trademark_record({})
        assert 0.0 <= confidence.overall <= 1.0


class TestBPIEventScore:
    def test_good_event_scores_high(self):
        score = score_bpi_event(
            "publication",
            "123456",
            "Publicação do pedido | Nº de pedido 123456 | Marca XPTO em Lisboa",
            has_event_date=True,
        )
        assert score >= 0.9

    def test_unknown_event_type_lowers_score(self):
        good = score_bpi_event("publication", "123456", "x" * 50, True)
        odd = score_bpi_event("mystery_event", "123456", "x" * 50, True)
        assert odd < good

    def test_bad_application_number_lowers_score(self):
        good = score_bpi_event("publication", "123456", "x" * 50, True)
        bad = score_bpi_event("publication", "!!invalid!!", "x" * 50, True)
        assert bad < good

    def test_hopeless_event_needs_review(self):
        score = score_bpi_event("mystery", None, "", has_event_date=False)
        assert score < REVIEW_THRESHOLD

    def test_score_is_bounded(self):
        for score in (
            score_bpi_event("publication", "123456", "x" * 100, True),
            score_bpi_event("weird", None, "", False),
        ):
            assert 0.0 <= score <= 1.0
