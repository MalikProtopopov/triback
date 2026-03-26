# Telegram-интеграция — Админ-панель

**Дата:** 2026-03-21  
**Кому:** Фронтенд-разработчик админ-панели  
**Тема:** Гибкая настройка Telegram-интеграции через админку

---

## Что добавлено

1. Раздел **«Telegram»** — настройка бота, канала для уведомлений, webhook.
2. Токен и секрет хранятся в БД (токен зашифрован Fernet).
3. Fallback на env-переменные (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`) при отсутствии записи в БД.
4. Webhook с secret в URL: `POST /api/v1/telegram/webhook/{webhook_secret}`.
5. При создании/обновлении интеграции — авто-обновление `site_settings.telegram_bot_link`.

---

## 1. API

**Префикс:** `/api/v1/admin/telegram`  
**Роль:** admin или manager

### 1.1. Получить настройки: `GET /api/v1/admin/telegram/integration`

Возвращает текущие настройки или `null`, если интеграция не настроена.

**Ответ (200):**

```json
{
  "id": 1,
  "bot_username": "tricho_bot",
  "owner_chat_id": -1001234567890,
  "webhook_url": "https://api.trichologia.ru/api/v1/telegram/webhook/abc123...",
  "is_webhook_active": true,
  "is_active": true,
  "welcome_message": "Добро пожаловать!",
  "bot_token_masked": "1234...5678",
  "created_at": "2026-03-21T12:00:00+00:00",
  "updated_at": "2026-03-21T12:00:00+00:00"
}
```

Если интеграция не настроена — `null`.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Синглтон-идентификатор (всегда 1) |
| `bot_username` | string / null | Username бота без @ (из getMe) |
| `owner_chat_id` | int / null | ID канала/чата для уведомлений |
| `webhook_url` | string / null | URL для регистрации в Telegram |
| `is_webhook_active` | bool | Webhook зарегистрирован в Telegram |
| `is_active` | bool | Интеграция включена |
| `welcome_message` | string / null | Сообщение для /start (опционально) |
| `bot_token_masked` | string / null | Маскированный токен (1234...5678) |
| `created_at`, `updated_at` | datetime | Метаданные |

---

### 1.2. Создать интеграцию: `POST /api/v1/admin/telegram/integration`

**Тело запроса:**

```json
{
  "bot_token": "1234567890:AAH...",
  "owner_chat_id": -1001234567890,
  "welcome_message": "Добро пожаловать!"
}
```

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `bot_token` | string | да | Токен бота от @BotFather |
| `owner_chat_id` | int | да | ID канала/чата для уведомлений |
| `welcome_message` | string | нет | Сообщение для /start |

**Логика:** Валидация через getMe, шифрование, генерация webhook_secret. При наличии PUBLIC_API_URL — авто-регистрация webhook. Обновление site_settings.telegram_bot_link.

**Ответ (201):** объект TelegramIntegrationResponse.

---

### 1.3. Обновить (частично): `PATCH /api/v1/admin/telegram/integration`

**Тело запроса (partial):** `bot_token`, `owner_chat_id`, `is_active`, `welcome_message` — все опциональны.

**Ответ (200):** объект TelegramIntegrationResponse. **404** — интеграция не настроена.

---

### 1.4. Удалить интеграцию: `DELETE /api/v1/admin/telegram/integration`

**Ответ (204).** **404** — интеграция не настроена.

---

### 1.5. URL для webhook: `GET /api/v1/admin/telegram/integration/webhook-url`

**Ответ (200):** `{"webhook_url": "https://..."}`. **404** — интеграция не настроена.

---

### 1.6. Установить webhook: `POST /api/v1/admin/telegram/integration/webhook`

**Ответ (200):** `{"ok": true}`. **422** — PUBLIC_API_URL не задан или ошибка Telegram API.

---

### 1.7. Удалить webhook: `DELETE /api/v1/admin/telegram/integration/webhook`

**Ответ (200):** `{"ok": true}`.

---

### 1.8. Тестовое сообщение: `POST /api/v1/admin/telegram/integration/test`

**Ответ (200):** `{"ok": true}`. **404** — интеграция не настроена.

---

## 2. Переменные окружения

| Переменная | Описание |
|------------|----------|
| `ENCRYPTION_KEY` | Base64 Fernet-ключ. Генерация: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `PUBLIC_API_URL` | Нужен для webhook URL |
| `TELEGRAM_*` | Fallback при отсутствии записи в БД |

---

## 3. Уведомления пользователей через Telegram

После привязки Telegram-аккаунта пользователь получает дублирующие уведомления в боте:

| Триггер | Задача |
|---------|--------|
| Результат модерации онбординга | `notify_user_moderation_result` |
| Результат модерации черновика профиля | `notify_user_draft_result` |
| Успешная оплата | `notify_user_payment_succeeded` |
| Ошибка оплаты | `notify_user_payment_failed` |
| Билет на мероприятие | `notify_user_event_ticket` |
| Чек готов | `notify_user_receipt_available` |
| Напоминание о подписке | `notify_user_subscription_expiring` |

---

## 4. Уведомления администратора

Отправляются в `owner_chat_id` (настройка интеграции или `TELEGRAM_CHANNEL_ID`):

| Триггер | Задача |
|---------|--------|
| Новая заявка на модерацию (онбординг) | `notify_admin_new_registration` |
| Новый черновик профиля / фото на модерацию | `notify_admin_new_draft` |
| Успешная оплата | `notify_admin_payment_received` |
| Подписки истекают в ближайшие 7 дней (ежедневно) | `send_admin_expiring_subscriptions_report` |
| Ошибка генерации сертификата | встроено в `certificate_tasks` |

---

## 5. Привязка Telegram для роли `user`

Роль `user` теперь имеет доступ к эндпоинтам:

- `GET /api/v1/telegram/binding` — статус привязки
- `POST /api/v1/telegram/generate-code` — генерация кода для привязки

Раздел `"telegram"` добавлен в sidebar клиента для роли `user`.

---

## 6. Telegram-статус в Admin API

Поля `telegram_linked: bool` и `tg_username: string | null` добавлены в ответы:

- `GET /api/v1/admin/doctors` — список врачей (`DoctorListItemResponse`)
- `GET /api/v1/admin/doctors/{id}` — детальная карточка врача (`DoctorDetailResponse`)
- `GET /api/v1/admin/portal-users` — список пользователей (`PortalUserListItem`)
- `GET /api/v1/admin/portal-users/{id}` — детальная карточка пользователя (`PortalUserDetailResponse`)
