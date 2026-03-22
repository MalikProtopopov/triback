"""Email tasks — real SMTP sending via TaskIQ background workers."""

from __future__ import annotations

import html
import structlog

from app.core.config import settings
from app.services.email_sender import send_smtp_email
from app.tasks import broker

logger = structlog.get_logger(__name__)

_BRAND = "Ассоциация трихологов"
_BASE_URL = settings.FRONTEND_URL.rstrip("/")


def _wrap_html(inner: str) -> str:
    return f"""\
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f4f4f7;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f7;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;">
  <tr><td style="background:#2563eb;padding:24px;text-align:center;">
    <span style="color:#ffffff;font-size:20px;font-weight:bold;">{_BRAND}</span>
  </td></tr>
  <tr><td style="padding:32px 24px;">
    {inner}
  </td></tr>
  <tr><td style="padding:16px 24px;text-align:center;color:#9ca3af;font-size:12px;border-top:1px solid #e5e7eb;">
    &copy; {_BRAND}. Это письмо отправлено автоматически, не отвечайте на него.
  </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _esc(value: str | None) -> str:
    """Escape user-supplied text for safe HTML insertion."""
    return html.escape(str(value)) if value else ""


def _safe_url(url: str | None) -> str:
    """Return URL only if it uses http(s) scheme, preventing javascript: injection."""
    if not url:
        return ""
    if url.startswith(("https://", "http://")):
        return html.escape(url, quote=True)
    return ""


def _button(url: str, label: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" style="margin:24px 0;">'
        f'<tr><td style="background:#2563eb;border-radius:6px;padding:12px 28px;">'
        f'<a href="{url}" style="color:#ffffff;text-decoration:none;font-size:16px;font-weight:bold;">'
        f'{label}</a></td></tr></table>'
    )


@broker.task  # type: ignore[misc]
async def send_verification_email(email: str, token: str) -> None:
    url = f"{_BASE_URL}/auth/verify-email?token={token}"
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Подтвердите email</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Спасибо за регистрацию! "
        f"Нажмите кнопку ниже, чтобы подтвердить ваш адрес электронной почты.</p>"
        f"{_button(url, 'Подтвердить email')}"
        f"<p style='color:#9ca3af;font-size:13px;'>Если вы не регистрировались — просто проигнорируйте это письмо.</p>"
    )
    await send_smtp_email(email, f"Подтверждение email — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_password_reset_email(email: str, token: str, is_staff: bool = False) -> None:
    if is_staff and settings.ADMIN_FRONTEND_URL:
        base = settings.ADMIN_FRONTEND_URL.rstrip("/")
    elif is_staff:
        logger.warning("ADMIN_FRONTEND_URL not set, sending staff password reset to FRONTEND_URL", email=email)
        base = _BASE_URL
    else:
        base = _BASE_URL
    path = "/admin/reset-password" if is_staff else "/auth/reset-password"
    url = f"{base}{path}?token={token}"
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Сброс пароля</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Вы запросили сброс пароля. "
        f"Нажмите кнопку ниже, чтобы задать новый пароль. Ссылка действительна 1 час.</p>"
        f"{_button(url, 'Сбросить пароль')}"
        f"<p style='color:#9ca3af;font-size:13px;'>Если вы не запрашивали сброс — просто проигнорируйте это письмо.</p>"
    )
    await send_smtp_email(email, f"Сброс пароля — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_email_change_confirmation(email: str, token: str) -> None:
    url = f"{_BASE_URL}/auth/confirm-email?token={token}"
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Смена email</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Вы запросили смену адреса электронной почты. "
        f"Подтвердите новый адрес, нажав кнопку ниже.</p>"
        f"{_button(url, 'Подтвердить новый email')}"
        f"<p style='color:#9ca3af;font-size:13px;'>Если вы не запрашивали смену — просто проигнорируйте это письмо.</p>"
    )
    await send_smtp_email(email, f"Подтверждение нового email — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_moderation_result_notification(
    email: str,
    status: str,
    comment: str | None = None,
    has_active_subscription: bool | None = None,
) -> None:
    if status == "approved":
        title = "Профиль одобрен"
        if has_active_subscription:
            msg = (
                "Ваш профиль успешно прошёл модерацию. "
                "Профиль опубликован на сайте с обновлённой информацией."
            )
            button_url = _BASE_URL + "/profile"
            button_label = "Перейти в профиль"
        else:
            msg = (
                "Ваш профиль успешно прошёл модерацию. "
                "Чтобы он был доступен на сайте, оплатите членский взнос в личном кабинете."
            )
            button_url = _BASE_URL + "/subscription"
            button_label = "Перейти в личный кабинет"
        html = _wrap_html(
            f"<h2 style='margin:0 0 16px;color:#1f2937;'>{title}</h2>"
            f"<p style='color:#4b5563;line-height:1.6;'>{msg}</p>"
            f"{_button(button_url, button_label)}"
        )
    else:
        title = "Профиль отклонён"
        msg = "К сожалению, ваш профиль не прошёл модерацию."
        if comment:
            msg += f"<br><br><strong>Причина:</strong> {_esc(comment)}"
        html = _wrap_html(
            f"<h2 style='margin:0 0 16px;color:#1f2937;'>{title}</h2>"
            f"<p style='color:#4b5563;line-height:1.6;'>{msg}</p>"
            f"{_button(_BASE_URL + '/profile', 'Перейти в профиль')}"
        )
    await send_smtp_email(email, f"{title} — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_draft_result_notification(
    email: str, status: str, rejection_reason: str | None = None
) -> None:
    if status == "approved":
        title = "Изменения профиля одобрены"
        msg = "Ваши изменения публичного профиля прошли модерацию и применены."
    else:
        title = "Изменения профиля отклонены"
        msg = "Ваши изменения не прошли модерацию."
        if rejection_reason:
            msg += f"<br><br><strong>Причина:</strong> {_esc(rejection_reason)}"

    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>{title}</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>{msg}</p>"
        f"{_button(_BASE_URL + '/profile', 'Перейти в профиль')}"
    )
    await send_smtp_email(email, f"{title} — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_reminder_notification(email: str, message: str | None = None) -> None:
    text = _esc(message) if message else "Ваша подписка скоро истекает. Не забудьте продлить членство."
    html_body = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Напоминание</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>{text}</p>"
        f"{_button(_BASE_URL + '/subscription', 'Продлить подписку')}"
    )
    await send_smtp_email(email, f"Напоминание — {_BRAND}", html_body)


@broker.task  # type: ignore[misc]
async def send_custom_email(email: str, subject: str, body: str) -> None:
    wrapped = _wrap_html(
        f"<div style='color:#4b5563;line-height:1.6;'>{html.escape(body)}</div>"
    )
    await send_smtp_email(email, subject, wrapped)


@broker.task  # type: ignore[misc]
async def send_payment_succeeded_notification(
    email: str, amount: float, product_type: str, receipt_url: str | None = None
) -> None:
    receipt_link = ""
    safe_receipt = _safe_url(receipt_url)
    if safe_receipt:
        receipt_link = f'<p><a href="{safe_receipt}" style="color:#2563eb;">Скачать чек</a></p>'

    html_body = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Оплата прошла успешно</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>"
        f"Мы получили вашу оплату на сумму <strong>{amount:.2f} ₽</strong> "
        f"за «{_esc(product_type)}».</p>"
        f"{receipt_link}"
    )
    await send_smtp_email(email, f"Оплата подтверждена — {_BRAND}", html_body)


@broker.task  # type: ignore[misc]
async def send_payment_failed_notification(email: str) -> None:
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Ошибка оплаты</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>К сожалению, платёж не прошёл. "
        f"Пожалуйста, попробуйте ещё раз или свяжитесь с поддержкой.</p>"
        f"{_button(_BASE_URL + '/subscription', 'Попробовать снова')}"
    )
    await send_smtp_email(email, f"Ошибка оплаты — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_event_verification_code(
    email: str, code: str, event_title: str
) -> None:
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Код подтверждения</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Ваш код для регистрации "
        f"на мероприятие «{_esc(event_title)}»:</p>"
        f"<div style='text-align:center;margin:24px 0;'>"
        f"<span style='font-size:32px;font-weight:bold;letter-spacing:8px;color:#2563eb;'>{_esc(code)}</span>"
        f"</div>"
        f"<p style='color:#9ca3af;font-size:13px;'>Код действителен 10 минут.</p>"
    )
    await send_smtp_email(email, f"Код подтверждения — {_esc(event_title)}", html)


@broker.task  # type: ignore[misc]
async def send_doctor_invite_email(
    email: str, temp_password: str, frontend_url: str
) -> None:
    login_url = frontend_url.rstrip("/") + "/auth/login"
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Добро пожаловать в {_BRAND}!</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Администратор создал для вас аккаунт врача. "
        f"Используйте данные ниже для входа в личный кабинет.</p>"
        f"<table style='margin:16px 0;width:100%;' cellpadding='8' cellspacing='0'>"
        f"<tr><td style='color:#6b7280;'>Email:</td><td style='font-weight:bold;'>{_esc(email)}</td></tr>"
        f"<tr><td style='color:#6b7280;'>Пароль:</td><td style='font-weight:bold;'>{_esc(temp_password)}</td></tr>"
        f"</table>"
        f"<p style='color:#4b5563;'>Рекомендуем сменить пароль после первого входа.</p>"
        f"{_button(login_url, 'Войти в личный кабинет')}"
    )
    await send_smtp_email(email, f"Ваш аккаунт врача — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_receipt_available_notification(
    email: str, receipt_url: str, amount: float
) -> None:
    safe_url = _safe_url(receipt_url)
    if not safe_url:
        logger.warning("receipt_url_invalid_or_empty", email=email)
        return
    html_body = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Ваш чек готов</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>"
        f"Чек на сумму <strong>{amount:.2f} ₽</strong> сформирован и доступен для скачивания.</p>"
        f"{_button(safe_url, 'Скачать чек')}"
        f"<p style='color:#9ca3af;font-size:13px;'>Чек также доступен в вашем личном кабинете в разделе «Платежи».</p>"
    )
    await send_smtp_email(email, f"Ваш чек — {_BRAND}", html_body)


@broker.task  # type: ignore[misc]
async def send_guest_account_created(
    email: str, temp_password: str, event_title: str, frontend_url: str
) -> None:
    login_url = frontend_url.rstrip("/") + "/auth/login"
    events_url = frontend_url.rstrip("/") + "/my/events"
    html = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Добро пожаловать!</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Для участия в мероприятии "
        f"«{_esc(event_title)}» мы создали для вас аккаунт.</p>"
        f"<table style='margin:16px 0;width:100%;' cellpadding='8' cellspacing='0'>"
        f"<tr><td style='color:#6b7280;'>Email:</td><td style='font-weight:bold;'>{_esc(email)}</td></tr>"
        f"<tr><td style='color:#6b7280;'>Пароль:</td><td style='font-weight:bold;'>{_esc(temp_password)}</td></tr>"
        f"</table>"
        f"<p style='color:#4b5563;'>Информация о вашем мероприятии доступна в "
        f"<a href='{events_url}' style='color:#2563eb;'>личном кабинете</a>.</p>"
        f"<p style='color:#4b5563;'>Рекомендуем сменить пароль после первого входа.</p>"
        f"{_button(login_url, 'Войти в аккаунт')}"
    )
    await send_smtp_email(email, f"Ваш аккаунт — {_BRAND}", html)


@broker.task  # type: ignore[misc]
async def send_event_ticket_purchased(
    email: str,
    event_title: str,
    event_date: str,
    event_end_date: str | None,
    event_location: str | None,
    applied_price: float,
    is_member_price: bool,
    receipt_url: str | None = None,
) -> None:
    dates = _esc(event_date)
    if event_end_date:
        dates += f" — {_esc(event_end_date)}"

    location_row = ""
    if event_location:
        location_row = (
            f"<tr><td style='color:#6b7280;padding:6px 8px;'>Место:</td>"
            f"<td style='padding:6px 8px;'>{_esc(event_location)}</td></tr>"
        )

    price_label = "Цена для членов ассоциации" if is_member_price else "Стоимость билета"

    receipt_block = ""
    safe_receipt = _safe_url(receipt_url)
    if safe_receipt:
        receipt_block = (
            f'<p style="margin-top:16px;">'
            f'<a href="{safe_receipt}" style="color:#2563eb;">Скачать чек</a></p>'
        )

    events_url = _BASE_URL + "/my/events"
    html_body = _wrap_html(
        f"<h2 style='margin:0 0 16px;color:#1f2937;'>Билет на мероприятие</h2>"
        f"<p style='color:#4b5563;line-height:1.6;'>Вы успешно приобрели билет:</p>"
        f"<table style='margin:16px 0;width:100%;border-collapse:collapse;' cellpadding='0' cellspacing='0'>"
        f"<tr><td style='color:#6b7280;padding:6px 8px;'>Мероприятие:</td>"
        f"<td style='padding:6px 8px;font-weight:bold;'>{_esc(event_title)}</td></tr>"
        f"<tr><td style='color:#6b7280;padding:6px 8px;'>Дата:</td>"
        f"<td style='padding:6px 8px;'>{dates}</td></tr>"
        f"{location_row}"
        f"<tr><td style='color:#6b7280;padding:6px 8px;'>{price_label}:</td>"
        f"<td style='padding:6px 8px;font-weight:bold;'>{applied_price:.2f} ₽</td></tr>"
        f"</table>"
        f"{receipt_block}"
        f"<p style='color:#4b5563;line-height:1.6;'>Подробная информация доступна в "
        f"<a href='{events_url}' style='color:#2563eb;'>личном кабинете</a>.</p>"
        f"{_button(events_url, 'Мои мероприятия')}"
    )
    await send_smtp_email(email, f"Билет: {_esc(event_title)} — {_BRAND}", html_body)
