"""Tests for Telegram integration admin endpoints."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_integration import TelegramIntegration
from tests.conftest import _make_auth_headers


async def test_telegram_integration_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/admin/telegram/integration")
    assert resp.status_code == 401


async def test_telegram_integration_get_empty(
    client: AsyncClient, db_session: AsyncSession, admin_user
):
    headers = _make_auth_headers(admin_user.id, "admin")
    resp = await client.get("/api/v1/admin/telegram/integration", headers=headers)
    assert resp.status_code == 200
    # No integration configured - response can be null or empty
    data = resp.json()
    assert data is None or data == {}


@patch(
    "app.services.telegram_integration_service._telegram_api",
    new_callable=AsyncMock,
)
async def test_telegram_integration_create(
    mock_api,
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user,
):
    mock_api.return_value = {"ok": True, "result": {"username": "test_bot"}}

    headers = _make_auth_headers(admin_user.id, "admin")
    resp = await client.post(
        "/api/v1/admin/telegram/integration",
        headers=headers,
        json={
            "bot_token": "123456:AAHtest",
            "owner_chat_id": -1001234567890,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bot_username"] == "test_bot"
    assert data["owner_chat_id"] == -1001234567890
    assert data["bot_token_masked"] is not None
    assert "created_at" in data
