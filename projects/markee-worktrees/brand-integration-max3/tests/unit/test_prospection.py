"""Tests for prospection filters and CSV export."""
import os
import pytest

from app.services.prospection import (
    filter_by_nice_class,
    filter_by_district,
    export_opportunities_csv,
)


@pytest.fixture
def mock_opportunities():
    return [
        {
            "word_mark": "SOLARIS",
            "owner": "Solaris Lda",
            "representative": None,
            "expiry_date": "2026-12-31",
            "nice_classes": [9, 11],
            "district": "Lisboa",
            "opportunity_type": "expiring_no_representative",
        },
        {
            "word_mark": "ACME",
            "owner": "Acme S.A",
            "representative": "João Silva",
            "expiry_date": "2027-06-30",
            "nice_classes": [35],
            "district": "Porto",
            "opportunity_type": "new_filing_without_agent",
        },
        {
            "word_mark": "ZENITH",
            "owner": "Zenith Unipessoal",
            "representative": None,
            "expiry_date": "2026-09-15",
            "nice_classes": [9],
            "district": "Lisboa",
            "opportunity_type": "recently_expired_company",
        },
    ]


class TestFilterByNiceClass:
    def test_filter_single_class(self, mock_opportunities):
        result = filter_by_nice_class(mock_opportunities, 9)
        assert len(result) == 2
        assert all(9 in opp["nice_classes"] for opp in result)

    def test_filter_no_match(self, mock_opportunities):
        result = filter_by_nice_class(mock_opportunities, 99)
        assert len(result) == 0

    def test_filter_class_35(self, mock_opportunities):
        result = filter_by_nice_class(mock_opportunities, 35)
        assert len(result) == 1
        assert result[0]["word_mark"] == "ACME"


class TestFilterByDistrict:
    def test_filter_lisboa(self, mock_opportunities):
        result = filter_by_district(mock_opportunities, "Lisboa")
        assert len(result) == 2
        assert all(opp["district"] == "Lisboa" for opp in result)

    def test_filter_porto(self, mock_opportunities):
        result = filter_by_district(mock_opportunities, "Porto")
        assert len(result) == 1
        assert result[0]["word_mark"] == "ACME"

    def test_filter_case_insensitive(self, mock_opportunities):
        result = filter_by_district(mock_opportunities, "lisboa")
        assert len(result) == 2

    def test_filter_no_match(self, mock_opportunities):
        result = filter_by_district(mock_opportunities, "Faro")
        assert len(result) == 0


class TestExportCSV:
    @pytest.mark.asyncio
    async def test_export_creates_file(self, mock_opportunities, tmp_path):
        filepath = tmp_path / "opportunities.csv"
        await export_opportunities_csv(mock_opportunities, str(filepath))
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "trademark,owner" in content
        assert "SOLARIS" in content
        assert "Lisboa" in content

    @pytest.mark.asyncio
    async def test_export_empty(self, tmp_path):
        filepath = tmp_path / "empty.csv"
        await export_opportunities_csv([], str(filepath))
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "trademark,owner" in content
        assert content.count("\n") == 1  # header only
