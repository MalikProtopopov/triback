"""Subscription expiry reminders: email + TaskIQ kiq, and Telegram task behavior.

Reminders about expiring subscriptions do not create membership arrears; automatic
arrears accrual (when implemented) belongs in arrears_auto_accrual_job tests.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionStatus
from app.models.users import Notification, TelegramBinding, User
from app.services.notification_service import NotificationService
from app.services.telegram_service import TelegramService
from tests.factories import create_plan, create_subscription, create_user

# Fixed "now" for deterministic windows (see send_subscription_reminders thresholds).
_FIXED_NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


def _ends_at_for_window(template_code: str) -> datetime:
    """ends_at in [now+lo, now+hi) for each reminder_* template."""
    n = _FIXED_NOW
    if template_code == "reminder_30d":
        return n + timedelta(days=29, hours=6)  # in [+29d, +30d)
    if template_code == "reminder_7d":
        return n + timedelta(days=6, hours=6)
    if template_code == "reminder_3d":
        return n + timedelta(days=2, hours=6)
    if template_code == "reminder_last_day":
        return n + timedelta(hours=6)
    raise ValueError(template_code)


def _expected_days_left(template_code: str) -> int:
    end = _ends_at_for_window(template_code)
    return (end - _FIXED_NOW).days


@pytest.fixture
def patch_reminder_time():
    """Patch notification_service datetime so send_subscription_reminders uses FIXED_NOW."""
    with patch("app.services.notification_service.datetime") as mock_dt:
        mock_dt.now.return_value = _FIXED_NOW
        mock_dt.UTC = UTC
        yield mock_dt


@pytest.mark.anyio
async def test_send_subscription_reminders_each_window_creates_notification_email_kiq(
    db_session: AsyncSession,
    patch_reminder_time,
):
    """Each threshold window: Notification row, send_email, notify_user_subscription_expiring.kiq."""
    mock_kiq = AsyncMock()
    with patch(
        "app.tasks.telegram_tasks.notify_user_subscription_expiring",
        MagicMock(kiq=mock_kiq),
    ):
        for code in (
            "reminder_30d",
            "reminder_7d",
            "reminder_3d",
            "reminder_last_day",
        ):
            user = await create_user(db_session)
            plan = await create_plan(db_session)
            await create_subscription(
                db_session,
                user=user,
                plan=plan,
                status=SubscriptionStatus.ACTIVE,
                starts_at=_FIXED_NOW - timedelta(days=400),
                ends_at=_ends_at_for_window(code),
            )

        svc = NotificationService(db_session)
        with patch.object(svc, "send_email", new_callable=AsyncMock):
            count = await svc.send_subscription_reminders()

    assert count == 4
    assert mock_kiq.await_count == 4

    rows = (
        await db_session.execute(
            select(Notification.template_code).order_by(Notification.template_code)
        )
    ).scalars().all()
    assert sorted(rows) == sorted(
        [
            "reminder_30d",
            "reminder_7d",
            "reminder_3d",
            "reminder_last_day",
        ]
    )

    # kiq order follows threshold loop: 30d, 7d, 3d, last_day
    assert [c.args[1] for c in mock_kiq.await_args_list] == [
        _expected_days_left("reminder_30d"),
        _expected_days_left("reminder_7d"),
        _expected_days_left("reminder_3d"),
        _expected_days_left("reminder_last_day"),
    ]
    for c in mock_kiq.await_args_list:
        assert isinstance(c.args[0], str)


@pytest.mark.anyio
async def test_send_subscription_reminders_dedup_same_utc_day(
    db_session: AsyncSession,
    patch_reminder_time,
):
    """Second pass does not duplicate Notification or re-send email/Telegram when already sent today."""
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        starts_at=_FIXED_NOW - timedelta(days=400),
        ends_at=_ends_at_for_window("reminder_7d"),
    )

    mock_kiq = AsyncMock()
    with patch(
        "app.tasks.telegram_tasks.notify_user_subscription_expiring",
        MagicMock(kiq=mock_kiq),
    ):
        svc = NotificationService(db_session)
        with patch.object(svc, "send_email", new_callable=AsyncMock) as mock_send:
            n1 = await svc.send_subscription_reminders()
            n2 = await svc.send_subscription_reminders()

    assert n1 == 1
    assert n2 == 0
    assert mock_send.await_count == 1
    assert mock_kiq.await_count == 1

    total = (
        await db_session.execute(select(func.count(Notification.id)))
    ).scalar_one()
    assert total == 1


@pytest.mark.anyio
async def test_send_subscription_reminders_skips_non_active(
    db_session: AsyncSession,
    patch_reminder_time,
):
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status=SubscriptionStatus.CANCELLED,
        starts_at=_FIXED_NOW - timedelta(days=400),
        ends_at=_ends_at_for_window("reminder_3d"),
    )

    mock_kiq = AsyncMock()
    with patch(
        "app.tasks.telegram_tasks.notify_user_subscription_expiring",
        MagicMock(kiq=mock_kiq),
    ):
        svc = NotificationService(db_session)
        with patch.object(svc, "send_email", new_callable=AsyncMock) as mock_send:
            count = await svc.send_subscription_reminders()

    assert count == 0
    mock_send.assert_not_awaited()
    mock_kiq.assert_not_awaited()


@pytest.mark.anyio
async def test_send_subscription_reminders_skips_ends_at_outside_windows(
    db_session: AsyncSession,
    patch_reminder_time,
):
    user = await create_user(db_session)
    plan = await create_plan(db_session)
    await create_subscription(
        db_session,
        user=user,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        starts_at=_FIXED_NOW - timedelta(days=400),
        ends_at=_FIXED_NOW + timedelta(days=100),
    )

    mock_kiq = AsyncMock()
    with patch(
        "app.tasks.telegram_tasks.notify_user_subscription_expiring",
        MagicMock(kiq=mock_kiq),
    ):
        svc = NotificationService(db_session)
        with patch.object(svc, "send_email", new_callable=AsyncMock) as mock_send:
            count = await svc.send_subscription_reminders()

    assert count == 0
    mock_send.assert_not_awaited()
    mock_kiq.assert_not_awaited()


# ── Telegram task notify_user_subscription_expiring ─────────────────


def _fake_async_session_local(db_session: AsyncSession):
    """AsyncSessionLocal() yields db_session (imported inside _send_to_user)."""

    def _factory():
        @asynccontextmanager
        async def _cm():
            yield db_session

        return _cm()

    return _factory


@pytest.mark.anyio
async def test_notify_user_subscription_expiring_sends_when_binding_and_token(
    db_session: AsyncSession,
    doctor_user: User,
):
    binding = TelegramBinding(
        user_id=doctor_user.id,
        tg_user_id=111,
        tg_username="doc",
        tg_chat_id=424242,
        linked_at=_FIXED_NOW,
    )
    db_session.add(binding)
    await db_session.flush()

    async def fake_get() -> TelegramService:
        return TelegramService(bot_token="test-token", owner_chat_id=1)

    with (
        patch(
            "app.core.database.AsyncSessionLocal",
            _fake_async_session_local(db_session),
        ),
        patch("app.tasks.telegram_tasks._get_svc_async", fake_get),
        patch.object(TelegramService, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        from app.tasks.telegram_tasks import notify_user_subscription_expiring

        await notify_user_subscription_expiring(str(doctor_user.id), 7)

    mock_send.assert_awaited_once()
    call = mock_send.await_args
    assert call[0][0] == 424242
    assert "7" in call[0][1]


@pytest.mark.anyio
async def test_notify_user_subscription_expiring_noop_without_binding(
    db_session: AsyncSession,
    doctor_user: User,
):
    async def fake_get() -> TelegramService:
        return TelegramService(bot_token="test-token", owner_chat_id=1)

    with (
        patch(
            "app.core.database.AsyncSessionLocal",
            _fake_async_session_local(db_session),
        ),
        patch("app.tasks.telegram_tasks._get_svc_async", fake_get),
        patch.object(TelegramService, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        from app.tasks.telegram_tasks import notify_user_subscription_expiring

        await notify_user_subscription_expiring(str(doctor_user.id), 3)

    mock_send.assert_not_awaited()


@pytest.mark.anyio
async def test_notify_user_subscription_expiring_noop_without_bot_token(
    db_session: AsyncSession,
    doctor_user: User,
):
    binding = TelegramBinding(
        user_id=doctor_user.id,
        tg_user_id=222,
        tg_username="doc2",
        tg_chat_id=999,
        linked_at=_FIXED_NOW,
    )
    db_session.add(binding)
    await db_session.flush()

    async def fake_get() -> TelegramService:
        svc = TelegramService(bot_token="x", owner_chat_id=1)
        svc._token = ""
        return svc

    with (
        patch(
            "app.core.database.AsyncSessionLocal",
            _fake_async_session_local(db_session),
        ),
        patch("app.tasks.telegram_tasks._get_svc_async", fake_get),
        patch.object(TelegramService, "send_message", new_callable=AsyncMock) as mock_send,
    ):
        from app.tasks.telegram_tasks import notify_user_subscription_expiring

        await notify_user_subscription_expiring(str(doctor_user.id), 1)

    mock_send.assert_not_awaited()
