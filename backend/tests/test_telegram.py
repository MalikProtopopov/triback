"""Tests for telegram binding endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import TelegramBinding
from tests.conftest import _make_auth_headers


async def test_telegram_binding_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/telegram/binding")
    assert resp.status_code == 401


async def test_telegram_binding_status_unlinked(
    client: AsyncClient, db_session: AsyncSession, doctor_user
):
    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/telegram/binding", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_linked"] is False
    assert data["tg_username"] is None


async def test_telegram_binding_status_linked(
    client: AsyncClient, db_session: AsyncSession, doctor_user
):
    binding = TelegramBinding(
        user_id=doctor_user.id,
        tg_user_id=12345,
        tg_username="testuser",
        tg_chat_id=12345,
        linked_at=datetime.now(UTC),
        is_in_channel=True,
    )
    db_session.add(binding)
    await db_session.flush()

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/telegram/binding", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_linked"] is True
    assert data["tg_username"] == "testuser"
    assert data["is_in_channel"] is True


async def test_generate_auth_code(
    client: AsyncClient, db_session: AsyncSession, doctor_user, redis_mock
):
    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.post("/api/v1/telegram/generate-code", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "auth_code" in data
    assert len(data["auth_code"]) == 6
    assert "bot_link" in data
    assert "expires_at" in data


async def test_generate_code_conflict_if_already_linked(
    client: AsyncClient, db_session: AsyncSession, doctor_user, redis_mock
):
    binding = TelegramBinding(
        user_id=doctor_user.id,
        tg_user_id=99999,
        tg_username="already_linked",
        tg_chat_id=99999,
        linked_at=datetime.now(UTC),
    )
    db_session.add(binding)
    await db_session.flush()

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.post("/api/v1/telegram/generate-code", headers=headers)
    assert resp.status_code == 409


@patch("app.services.telegram_service.TelegramService.send_message", new_callable=AsyncMock)
async def test_telegram_webhook_binds_user(
    mock_send,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    redis_mock: AsyncMock,
    monkeypatch,
):
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "")

    binding = TelegramBinding(
        user_id=doctor_user.id,
        auth_code="ABC123",
        auth_code_expires_at=datetime.now(UTC),
    )
    db_session.add(binding)
    await db_session.flush()

    _store: dict[str, str] = {"tg_auth:ABC123": str(doctor_user.id)}

    async def _get(key: str) -> str | None:
        return _store.get(key)

    async def _set(key: str, value: str, **kwargs) -> None:
        _store[key] = value

    async def _delete(key: str) -> None:
        _store.pop(key, None)

    redis_mock.get = AsyncMock(side_effect=_get)
    redis_mock.set = AsyncMock(side_effect=_set)
    redis_mock.delete = AsyncMock(side_effect=_delete)
    redis_mock.setex = AsyncMock()

    webhook_body = {
        "message": {
            "text": "/start ABC123",
            "from": {"id": 12345, "username": "tg_user"},
            "chat": {"id": 12345},
        }
    }

    resp = await client.post("/api/v1/telegram/webhook", json=webhook_body)
    assert resp.status_code == 200

    await db_session.refresh(binding)
    assert binding.tg_user_id == 12345
    assert binding.tg_username == "tg_user"
    assert binding.auth_code is None


@patch("app.services.telegram_service.TelegramService.send_message", new_callable=AsyncMock)
async def test_telegram_webhook_redis_key_cleaned(
    mock_send,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    redis_mock: AsyncMock,
    monkeypatch,
):
    """BUG-1 fix: Verify that Redis key is deleted when binding succeeds."""
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "")

    binding = TelegramBinding(
        user_id=doctor_user.id,
        auth_code="XYZ789",
        auth_code_expires_at=datetime.now(UTC),
    )
    db_session.add(binding)
    await db_session.flush()

    _store: dict[str, str] = {"tg_auth:XYZ789": str(doctor_user.id)}

    async def _get(key: str) -> str | None:
        return _store.get(key)

    async def _set(key: str, value: str, **kwargs) -> None:
        _store[key] = value

    async def _delete(key: str) -> None:
        _store.pop(key, None)

    redis_mock.get = AsyncMock(side_effect=_get)
    redis_mock.set = AsyncMock(side_effect=_set)
    redis_mock.delete = AsyncMock(side_effect=_delete)
    redis_mock.setex = AsyncMock()

    webhook_body = {
        "message": {
            "text": "/start XYZ789",
            "from": {"id": 55555, "username": "tg_user2"},
            "chat": {"id": 55555},
        }
    }

    resp = await client.post("/api/v1/telegram/webhook", json=webhook_body)
    assert resp.status_code == 200

    assert "tg_auth:XYZ789" not in _store


async def test_telegram_webhook_rejects_bad_secret(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "mysecret")
    resp = await client.post(
        "/api/v1/telegram/webhook",
        json={"message": {"text": "/start CODE"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert resp.status_code == 403
