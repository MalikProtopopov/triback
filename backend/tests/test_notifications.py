"""Tests for notification service (unit-level tests via service)."""

from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import NotificationTemplate
from app.services.notification_service import NotificationService
from tests.factories import create_user


async def test_create_notification_email(db_session: AsyncSession):
    user = await create_user(db_session)
    svc = NotificationService(db_session)

    with patch.object(svc, "send_email", new_callable=AsyncMock):
        notif = await svc.create_notification(
            user_id=user.id,
            template_code="test",
            channel="email",
            title="Test Title",
            body="Test body",
        )

    assert notif.id is not None
    assert notif.user_id == user.id
    assert notif.status == "sent"


async def test_create_notification_telegram_no_binding(db_session: AsyncSession):
    """When no telegram binding exists, notification is still marked sent (no-op delivery)."""
    user = await create_user(db_session)
    svc = NotificationService(db_session)

    notif = await svc.create_notification(
        user_id=user.id,
        template_code="test",
        channel="telegram",
        title="Test Tg",
        body="Test body",
    )

    assert notif.status == "sent"


async def test_send_by_template(db_session: AsyncSession):
    user = await create_user(db_session)

    tpl = NotificationTemplate(
        code="test_tpl",
        name="Test Template",
        channel="email",
        subject="Hello {{ name }}",
        body_template="Dear {{ name }}, welcome!",
    )
    db_session.add(tpl)
    await db_session.flush()

    svc = NotificationService(db_session)
    with patch.object(svc, "send_email", new_callable=AsyncMock):
        notif = await svc.send_by_template(
            user_id=user.id,
            template_code="test_tpl",
            context={"name": "Doctor"},
        )

    assert notif is not None
    assert "Dear Doctor, welcome!" in notif.body


async def test_send_by_template_missing_template(db_session: AsyncSession):
    user = await create_user(db_session)
    svc = NotificationService(db_session)
    result = await svc.send_by_template(
        user_id=user.id,
        template_code="nonexistent",
        context={},
    )
    assert result is None


async def test_create_multiple_notifications(db_session: AsyncSession):
    user = await create_user(db_session)
    svc = NotificationService(db_session)

    with patch.object(svc, "send_email", new_callable=AsyncMock):
        for i in range(3):
            notif = await svc.create_notification(
                user_id=user.id,
                template_code=f"test_{i}",
                channel="email",
                title=f"Title {i}",
                body=f"Body {i}",
            )
            assert notif.status == "sent"


async def test_notification_dispatch_failure_marks_failed(db_session: AsyncSession):
    user = await create_user(db_session)
    svc = NotificationService(db_session)

    with patch.object(svc, "send_email", new_callable=AsyncMock, side_effect=Exception("SMTP error")):
        notif = await svc.create_notification(
            user_id=user.id,
            template_code="fail",
            channel="email",
            title="Fail",
            body="Body",
        )

    assert notif.status == "failed"


async def test_jinja2_template_escaping(db_session: AsyncSession):
    """Verify Jinja2 auto-escaping prevents XSS in templates."""
    user = await create_user(db_session)

    tpl = NotificationTemplate(
        code="xss_test",
        name="XSS Test",
        channel="email",
        subject="Test",
        body_template="Hello {{ name }}!",
    )
    db_session.add(tpl)
    await db_session.flush()

    svc = NotificationService(db_session)
    with patch.object(svc, "send_email", new_callable=AsyncMock):
        notif = await svc.send_by_template(
            user_id=user.id,
            template_code="xss_test",
            context={"name": "<script>alert('xss')</script>"},
        )

    assert notif is not None
    assert "<script>" not in notif.body
    assert "&lt;script&gt;" in notif.body
