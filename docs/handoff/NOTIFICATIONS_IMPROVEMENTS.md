# Уведомления: что сделано (бэкенд)

## Журнал (стратегия A)

Выбран **вариант A** из плана: без миграции `notifications` и без записи каждого Telegram-only сообщения в БД. Сообщения, ушедшие **только** через TaskIQ в Telegram (модерация, оплата, билеты и т.д.), **по-прежнему не попадают** в `GET /api/v1/admin/notifications`. В журнале остаются записи, созданные через `NotificationService.create_notification` (email/TG с записью, напоминания о подписке, ручная рассылка из админки).

Полный единый журнал (вариант B) потребует отдельной задачи: аудитория `admin` vs `user`, nullable `user_id` или отдельная таблица outbox.

## Админ API

`GET /api/v1/admin/notifications` — вложенный объект `user` расширен:

- `phone` — из `doctor_profiles.phone`, если профиль есть  
- `telegram_username` — из `telegram_bindings.tg_username` (без префикса `@` в JSON; на фронте можно показывать как `@username`)

## ЛК врача

`GET /api/v1/profile/notifications` — пагинированный список строк из `notifications` для текущего пользователя (`template_code`, `channel`, `title`, `body`, `status`, даты, `payload`). Сообщения без строки в БД здесь **не видны** (см. стратегию A).

## Telegram

- Общий контекст пользователя: [`app/services/notification_user_context.py`](../../backend/app/services/notification_user_context.py) (`build_user_contact_context`).
- Форматирование HTML: [`app/services/telegram_message_format.py`](../../backend/app/services/telegram_message_format.py).
- Админские алерты (`notify_admin_*`) включают email, ФИО, телефон, @Telegram, User ID.
- `notify_admin_payment_received` теперь принимает `user_id` первым аргументом (TaskIQ); вызов из [`payment_webhook_service`](../../backend/app/services/payment_webhook_service.py) обновлён.
- Пользовательские TG-тексты приведены к структурированному виду, без набора эмодзи; пользовательский текст экранируется для HTML.
- Исправлена логика статуса модерации анкеты в TG: сравнение с `approved` / `rejected` (раньше ошибочно проверялось на `active`).

## Тесты

- `tests/test_notification_user_context.py`
- `tests/test_telegram_message_format.py`
- `tests/test_profile.py::test_list_my_notifications`
