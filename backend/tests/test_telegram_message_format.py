"""Tests for Telegram HTML message helpers."""

from app.services.notification_user_context import UserContactContext
from app.services.telegram_message_format import (
    contact_lines_for_admin,
    format_admin_alert,
    format_user_notice,
    product_type_ru,
    tg_escape,
)


def test_tg_escape_escapes_html():
    assert "&lt;script&gt;" in tg_escape("<script>")
    assert tg_escape(None) == ""


def test_format_admin_alert_structure():
    text = format_admin_alert("Заголовок", [("Ключ", "Значение")])
    assert "<b>Заголовок</b>" in text
    assert "Ключ: Значение" in text


def test_format_user_notice_escapes_values():
    text = format_user_notice("Тест", [("X", "<b>oops</b>")])
    assert "<b>oops</b>" not in text
    assert "&lt;b&gt;oops&lt;/b&gt;" in text


def test_contact_lines_for_admin():
    ctx = UserContactContext(
        user_id=__import__("uuid").uuid4(),
        email="a@b.c",
        full_name="Иванов Иван",
        phone="+7999",
        telegram_username="user",
    )
    lines = contact_lines_for_admin(ctx)
    assert ("Email", "a@b.c") in lines
    assert ("Telegram", "@user") in lines


def test_product_type_ru():
    assert product_type_ru("subscription") == "Членский взнос"
    assert product_type_ru("unknown") == "unknown"
