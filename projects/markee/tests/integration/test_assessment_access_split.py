"""Public/professional split for trademark assessment access."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import assessments
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


def _empty_similarity(mock_db_session):
    result_mock = MagicMock()
    result_mock.mappings.return_value.all.return_value = []
    mock_db_session.execute.return_value = result_mock


def _user(superuser=False):
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        email="pro@example.com" if superuser else "user@example.com",
        is_active=True,
        is_superuser=superuser,
    )


class TestPublicAssessmentAccess:
    def test_public_assessment_requires_no_authentication_and_is_limited(self, mock_db_session):
        _empty_similarity(mock_db_session)

        response = client.post(
            "/api/v1/assessments/public",
            json={"mark_name": "Zyphora", "business_description": "software"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mark_name"] == "Zyphora"
        assert data["preliminary_status"] in {
            "No obvious issue identified",
            "Review recommended",
            "Significant issue identified",
        }
        assert "candidate_count" in data
        assert "top_candidates" in data
        assert "limitations" in data
        assert "next_actions" in data
        # Public output must not expose the professional working file.
        for hidden in (
            "distinctiveness",
            "opposition_risk",
            "recommendations",
            "analysis_detail",
            "coverage_metadata",
        ):
            assert hidden not in data


class TestProfessionalAssessmentAccess:
    def test_professional_assessment_requires_authentication(self, mock_db_session):
        _empty_similarity(mock_db_session)

        response = client.post(
            "/api/v1/assessments/professional",
            json={"mark_name": "Zyphora"},
        )

        assert response.status_code == 401

    def test_professional_assessment_forbids_non_professional_user(self, mock_db_session):
        _empty_similarity(mock_db_session)
        app.dependency_overrides[assessments.get_current_user] = lambda: _user(False)

        response = client.post(
            "/api/v1/assessments/professional",
            json={"mark_name": "Zyphora"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Professional access required"

    def test_professional_assessment_returns_deep_detail_for_authorised_user(self, mock_db_session):
        _empty_similarity(mock_db_session)
        app.dependency_overrides[assessments.get_current_user] = lambda: _user(True)

        response = client.post(
            "/api/v1/assessments/professional",
            json={"mark_name": "Zyphora", "business_description": "software"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mark_name"] == "Zyphora"
        assert "distinctiveness" in data
        assert "opposition_risk" in data
        assert "recommendations" in data
        assert "analysis_detail" in data
        assert "coverage_metadata" in data
        assert data["coverage_metadata"]["coverage_status"] in {"partial", "unknown"}
        assert data["analysis_detail"]["public_response_depth"] == "limited"
        assert data["analysis_detail"]["professional_response_depth"] == "factor_level"
