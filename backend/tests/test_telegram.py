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
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)

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
    monkeypatch.setattr("app.core.config.settings.DEBUG", True)

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


async def test_telegram_legacy_webhook_forbidden_without_secret_in_production(
    client: AsyncClient, monkeypatch
):
    """Legacy /webhook must reject when bot token is set but webhook secret is empty (non-DEBUG)."""
    monkeypatch.setattr("app.core.config.settings.DEBUG", False)
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_BOT_TOKEN", "123:fake-token")
    monkeypatch.setattr("app.core.config.settings.TELEGRAM_CHANNEL_ID", "-1001")
    resp = await client.post("/api/v1/telegram/webhook", json={"update_id": 1})
    assert resp.status_code == 403


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


# ── User role binding tests ───────────────────────────────────────

async def test_user_role_can_get_binding_status(
    client: AsyncClient, db_session: AsyncSession
):
    """Role 'user' should now be allowed to check binding status."""
    from uuid import uuid4
    from tests.conftest import _create_user_with_role

    plain_user = await _create_user_with_role(
        db_session, f"user_{uuid4().hex[:8]}@test.com", "user"
    )
    headers = _make_auth_headers(plain_user.id, "user")
    resp = await client.get("/api/v1/telegram/binding", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_linked"] is False


async def test_user_role_can_generate_code(
    client: AsyncClient, db_session: AsyncSession, redis_mock
):
    """Role 'user' should be allowed to generate a Telegram auth code."""
    from uuid import uuid4
    from tests.conftest import _create_user_with_role

    plain_user = await _create_user_with_role(
        db_session, f"user_{uuid4().hex[:8]}@test.com", "user"
    )
    headers = _make_auth_headers(plain_user.id, "user")
    resp = await client.post("/api/v1/telegram/generate-code", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "auth_code" in data
    assert "bot_link" in data
