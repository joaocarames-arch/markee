"""Integration tests for watchlist API endpoints."""
from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.database import get_db
from app.services.email import get_in_memory_gateway

_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")


def _extract_verification_token(text_body: str) -> str:
    """Return the ``token`` query value from the first URL carrying one.

    Robust against line layout, adjacent punctuation and URL encoding — it
    scans every URL in the body instead of splitting on lines.
    """
    for raw_url in _URL_RE.findall(text_body):
        candidate = raw_url.rstrip(".,;:!?")
        values = parse_qs(urlparse(candidate).query).get("token")
        if values and values[0]:
            return values[0]
    raise AssertionError("no verification token found in email body")


@pytest_asyncio.fixture
async def api_client(override_get_db: Callable[[], object]) -> AsyncIterator[AsyncClient]:
    """Return an async client wired to the real integration DB session."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def auth_header(api_client: AsyncClient, email: str) -> dict[str, str]:
    """Register and log in a user, returning an Authorization header."""
    register_response = await api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secret123"},
    )
    assert register_response.status_code == 201

    verification_email = get_in_memory_gateway().sent[-1]
    token = _extract_verification_token(verification_email.text_body)
    verify_response = await api_client.post(
        "/api/v1/auth/verify", json={"token": token}
    )
    assert verify_response.status_code == 200

    login_response = await api_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "secret123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_watchlist(
    api_client: AsyncClient,
    headers: dict[str, str],
    name: str,
    similarity_threshold: int = 80,
) -> dict[str, object]:
    """Create a watchlist through the public API."""
    response = await api_client.post(
        "/api/v1/watchlists",
        headers=headers,
        json={"name": name, "similarity_threshold": similarity_threshold},
    )
    assert response.status_code == 201
    return response.json()


class TestWatchlistEndpoints:
    """Watchlist endpoints with real persistence and ownership checks."""

    @pytest.mark.asyncio
    async def test_list_watchlists_requires_authentication(
        self, api_client: AsyncClient
    ) -> None:
        response = await api_client.get("/api/v1/watchlists")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
        assert response.headers["www-authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_list_watchlists_returns_only_current_users_rows(
        self, api_client: AsyncClient
    ) -> None:
        owner_headers = await auth_header(api_client, "owner@example.com")
        other_headers = await auth_header(api_client, "other@example.com")
        owned = await create_watchlist(api_client, owner_headers, "Owned brand")
        await create_watchlist(api_client, other_headers, "Foreign brand")

        response = await api_client.get("/api/v1/watchlists", headers=owner_headers)

        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data] == [owned["id"]]
        assert data[0]["name"] == "Owned brand"
        assert data[0]["user_id"] == owned["user_id"]

    @pytest.mark.asyncio
    async def test_create_watchlist_persists_supported_fields_and_defaults(
        self, api_client: AsyncClient
    ) -> None:
        headers = await auth_header(api_client, "creator@example.com")

        response = await api_client.post(
            "/api/v1/watchlists",
            headers=headers,
            json={
                "name": "Core marks",
                "similarity_threshold": 87,
                "phonetic_weight": 0.4,
                "class_weight": 0.1,
                "nice_classes_filter": [9, 42],
            },
        )

        assert response.status_code == 201
        created = response.json()
        assert created["name"] == "Core marks"
        assert created["similarity_threshold"] == 87
        assert created["phonetic_weight"] == 0.4
        assert created["class_weight"] == 0.1
        assert created["nice_classes_filter"] == [9, 42]
        assert created["jurisdictions"] == ["EUIPO", "INPI"]
        assert created["is_active"] is True

        list_response = await api_client.get("/api/v1/watchlists", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json() == [created]

    @pytest.mark.asyncio
    async def test_validation_rejects_missing_required_name_and_malformed_ids(
        self, api_client: AsyncClient
    ) -> None:
        headers = await auth_header(api_client, "validation@example.com")

        missing_name = await api_client.post(
            "/api/v1/watchlists",
            headers=headers,
            json={"similarity_threshold": 80},
        )
        malformed_id = await api_client.get(
            "/api/v1/watchlists/not-a-uuid",
            headers=headers,
        )

        assert missing_name.status_code == 422
        assert missing_name.json()["detail"][0]["loc"] == ["body", "name"]
        assert malformed_id.status_code == 422
        assert malformed_id.json()["detail"][0]["loc"] == ["path", "watchlist_id"]

    @pytest.mark.asyncio
    async def test_get_update_and_delete_do_not_cross_users(
        self, api_client: AsyncClient
    ) -> None:
        owner_headers = await auth_header(api_client, "crud-owner@example.com")
        other_headers = await auth_header(api_client, "crud-other@example.com")
        owned = await create_watchlist(api_client, owner_headers, "Owner list")
        owned_id = str(owned["id"])

        foreign_get = await api_client.get(
            f"/api/v1/watchlists/{owned_id}", headers=other_headers
        )
        foreign_update = await api_client.put(
            f"/api/v1/watchlists/{owned_id}",
            headers=other_headers,
            json={"name": "Stolen", "similarity_threshold": 10, "is_active": False},
        )
        foreign_delete = await api_client.delete(
            f"/api/v1/watchlists/{owned_id}", headers=other_headers
        )

        assert foreign_get.status_code == 404
        assert foreign_update.status_code == 404
        assert foreign_delete.status_code == 404

        owner_update = await api_client.put(
            f"/api/v1/watchlists/{owned_id}",
            headers=owner_headers,
            json={"name": "Updated owner list", "similarity_threshold": 91, "is_active": False},
        )
        assert owner_update.status_code == 200
        updated = owner_update.json()
        assert updated["name"] == "Updated owner list"
        assert updated["similarity_threshold"] == 91
        assert updated["is_active"] is False

        owner_delete = await api_client.delete(
            f"/api/v1/watchlists/{owned_id}", headers=owner_headers
        )
        assert owner_delete.status_code == 204
        assert owner_delete.content == b""

        owner_get_after_delete = await api_client.get(
            f"/api/v1/watchlists/{owned_id}", headers=owner_headers
        )
        assert owner_get_after_delete.status_code == 404

    @pytest.mark.asyncio
    async def test_items_create_list_and_delete_are_limited_to_watchlist_owner(
        self, api_client: AsyncClient
    ) -> None:
        owner_headers = await auth_header(api_client, "items-owner@example.com")
        other_headers = await auth_header(api_client, "items-other@example.com")
        watchlist = await create_watchlist(api_client, owner_headers, "Item list")
        watchlist_id = str(watchlist["id"])

        foreign_create = await api_client.post(
            f"/api/v1/watchlists/{watchlist_id}/items",
            headers=other_headers,
            json={"mark_text": "FOREIGN", "nice_classes": [9]},
        )
        assert foreign_create.status_code == 404

        owner_create = await api_client.post(
            f"/api/v1/watchlists/{watchlist_id}/items",
            headers=owner_headers,
            json={"mark_text": "MARKEE", "nice_classes": [9, 42], "notes": "Core"},
        )
        assert owner_create.status_code == 201
        item = owner_create.json()
        assert item["watchlist_id"] == watchlist_id
        assert item["mark_text"] == "MARKEE"
        assert item["nice_classes"] == [9, 42]
        assert item["notes"] == "Core"

        foreign_list = await api_client.get(
            f"/api/v1/watchlists/{watchlist_id}/items", headers=other_headers
        )
        owner_list = await api_client.get(
            f"/api/v1/watchlists/{watchlist_id}/items", headers=owner_headers
        )
        assert foreign_list.status_code == 404
        assert owner_list.status_code == 200
        assert owner_list.json() == [item]

        foreign_delete = await api_client.delete(
            f"/api/v1/watchlists/{watchlist_id}/items/{item['id']}",
            headers=other_headers,
        )
        assert foreign_delete.status_code == 404

        owner_delete = await api_client.delete(
            f"/api/v1/watchlists/{watchlist_id}/items/{item['id']}",
            headers=owner_headers,
        )
        assert owner_delete.status_code == 204

        owner_list_after_delete = await api_client.get(
            f"/api/v1/watchlists/{watchlist_id}/items", headers=owner_headers
        )
        assert owner_list_after_delete.status_code == 200
        assert owner_list_after_delete.json() == []
