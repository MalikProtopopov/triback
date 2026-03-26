"""Tests for notification user contact context loading."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import TelegramBinding
from app.services.notification_user_context import build_user_contact_context
from tests.factories import create_doctor_profile, create_user


@pytest.mark.anyio
async def test_build_user_contact_context_full(db_session: AsyncSession):
    user = await create_user(db_session, email="doc@example.com")
    await create_doctor_profile(
        db_session,
        user=user,
        first_name="Иван",
        last_name="Петров",
    )
    db_session.add(
        TelegramBinding(
            user_id=user.id,
            tg_user_id=1,
            tg_username="ivan_doc",
            tg_chat_id=100,
        )
    )
    await db_session.commit()

    ctx = await build_user_contact_context(db_session, user.id)

    assert ctx.email == "doc@example.com"
    assert ctx.full_name == "Петров Иван"
    assert ctx.phone is not None
    assert ctx.telegram_username == "ivan_doc"
    assert ctx.user_id == user.id


@pytest.mark.anyio
async def test_build_user_contact_context_minimal_user_only(db_session: AsyncSession):
    user = await create_user(db_session, email="plain@test.com")
    await db_session.commit()

    ctx = await build_user_contact_context(db_session, user.id)

    assert ctx.email == "plain@test.com"
    assert ctx.full_name is None
    assert ctx.phone is None
    assert ctx.telegram_username is None
