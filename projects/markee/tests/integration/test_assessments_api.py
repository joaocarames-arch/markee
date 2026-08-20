"""Integration tests for the stateless assessment endpoint.

Covers the request/response contract, input validation, that the endpoint
needs no authentication (a free check), and — crucially — that a missing or
failing data source degrades safely to empty candidates with an explicit
``unavailable`` provenance rather than erroring.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.database import get_db

client = TestClient(app)


@pytest.fixture
def mock_db_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture(autouse=True)
def override_db_dependency(mock_db_session):
    async def _get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


ENDPOINT = "/api/v1/assessments"


class TestAssessmentContract:
    def test_returns_full_contract(self, mock_db_session):
        # No similar marks in the DB → empty candidate list from the engine.
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_db_session.execute.return_value = result_mock

        response = client.post(
            ENDPOINT,
            json={
                "mark_name": "Zyphora",
                "jurisdiction": "EU",
                "business_description": "plataforma SaaS de software",
            },
        )
        assert response.status_code == 200
        data = response.json()
        for key in (
            "mark_name",
            "jurisdiction",
            "verdict",
            "risk_level",
            "distinctiveness",
            "recommended_classes",
            "identical_match",
            "candidates",
            "candidates_provenance",
            "opposition_risk",
            "recommendations",
            "disclaimers",
            "created_at",
        ):
            assert key in data, f"missing contract field: {key}"
        assert data["mark_name"] == "Zyphora"
        assert data["distinctiveness"]["level"] in {
            "fully_met",
            "partially_met",
            "not_met",
        }
        assert data["recommended_classes"]
        assert data["disclaimers"]

    def test_requires_no_authentication(self, mock_db_session):
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_db_session.execute.return_value = result_mock

        response = client.post(ENDPOINT, json={"mark_name": "Solara"})
        # No Authorization header — a free check must still succeed.
        assert response.status_code == 200

    def test_empty_mark_name_is_rejected(self):
        response = client.post(ENDPOINT, json={"mark_name": "   "})
        assert response.status_code == 422

    def test_missing_mark_name_is_rejected(self):
        response = client.post(ENDPOINT, json={"jurisdiction": "EU"})
        assert response.status_code == 422


class TestFailSoft:
    def test_data_source_failure_degrades_to_unavailable(self, mock_db_session):
        # Simulate an unreachable database: the engine query raises.
        mock_db_session.execute = AsyncMock(side_effect=RuntimeError("db down"))

        response = client.post(
            ENDPOINT,
            json={"mark_name": "Zyphora", "business_description": "software"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["candidates_provenance"] == "unavailable"
        assert data["candidates"] == []
        # The rest of the report is still produced.
        assert data["recommended_classes"]
        assert data["distinctiveness"]["level"]


class TestCandidatePath:
    def test_identical_candidate_flips_verdict(self, mock_db_session, monkeypatch):
        from app.api import assessments as mod

        class _FakeEngine:
            def __init__(self, db):
                pass

            async def find_similar_marks(self, *args, **kwargs):
                return [
                    {
                        "word_mark": "Zyphora",
                        "jurisdiction": "EU",
                        "composite_score": 100.0,
                        "source_id": "EU-1",
                    }
                ]

        monkeypatch.setattr(mod, "SimilarityEngine", _FakeEngine)

        response = client.post(
            ENDPOINT,
            json={"mark_name": "Zyphora", "business_description": "software"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["candidates_provenance"] == "database"
        assert data["identical_match"] is True
        assert data["risk_level"] == "high"
        assert data["verdict"] == "not_recommended"
        assert data["candidates"], "candidate list should include the match"
