# Event Tickets — Client Frontend Handoff

Описание API для покупки билетов на мероприятия. Три сценария в зависимости от состояния авторизации.

---

## Общая схема

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    POST /public/events/{id}/register                    │
│                                                                         │
│  JWT есть?                                                              │
│  ├─ Да → Регистрация + Платёж → { payment_url }                       │
│  └─ Нет → guest_email обязателен                                       │
│       ├─ Email в базе → OTP код на почту → action="verify_existing"    │
│       └─ Новый email → OTP код на почту → action="verify_new_email"    │
│                                                                         │
│  После ввода кода:                                                     │
│  POST /public/events/{id}/confirm-guest-registration                    │
│  → { payment_url, access_token, refresh_token }                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Сценарий 1 — Авторизованный пользователь (JWT)

Пользователь уже залогинен (есть Bearer token).

### Запрос

```
POST /api/v1/public/events/{event_id}/register
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "tariff_id": "uuid-тарифа",
  "idempotency_key": "unique-key-123"
}
```

Поля `guest_email`, `guest_full_name`, `guest_workplace`, `guest_specialization`, `fiscal_email` — **опциональны**, можно не передавать.

### Ответ 201

```json
{
  "registration_id": "uuid-регистрации",
  "payment_url": "https://payanyway.ru/assistant.htm?operationId=...",
  "applied_price": 5000.0,
  "is_member_price": true,
  "action": null,
  "masked_email": null,
  "access_token": null,
  "refresh_token": null
}
```

### Логика цены

- **Действующий член ассоциации** (врач со статусом ACTIVE + активная подписка) → `member_price`
- **Все остальные** (обычный пользователь, врач без подписки) → `price` (полная цена)

### Действия фронта

1. Получить `payment_url`.
2. Перенаправить пользователя на `payment_url` (Moneta/ЮKassa).
3. После возврата — показать страницу успеха/ошибки.

---

## Сценарий 2 — Email уже есть в базе (verify_existing)

Пользователь не авторизован, но email уже зарегистрирован.

### Шаг 1: Отправка email

```
POST /api/v1/public/events/{event_id}/register
Content-Type: application/json

{
  "tariff_id": "uuid-тарифа",
  "idempotency_key": "unique-key-123",
  "guest_email": "user@example.com"
}
```

### Ответ 201

```json
{
  "action": "verify_existing",
  "masked_email": "u***@example.com",
  "registration_id": null,
  "payment_url": null,
  "applied_price": null,
  "is_member_price": null,
  "access_token": null,
  "refresh_token": null
}
```

**OTP-код отправлен на почту пользователя.** Фронт показывает форму ввода 6-значного кода.

### Шаг 2: Подтверждение кода

```
POST /api/v1/public/events/{event_id}/confirm-guest-registration
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456",
  "tariff_id": "uuid-тарифа",
  "idempotency_key": "unique-key-456"
}
```

Поля `guest_full_name`, `guest_workplace`, `guest_specialization`, `fiscal_email` — **опциональны**.

### Ответ 201

```json
{
  "registration_id": "uuid-регистрации",
  "payment_url": "https://payanyway.ru/assistant.htm?operationId=...",
  "applied_price": 5000.0,
  "is_member_price": true,
  "action": null,
  "masked_email": null,
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

### Действия фронта

1. Сохранить `access_token` и `refresh_token` (cookie / localStorage).
2. Перенаправить пользователя на `payment_url`.
3. Пользователь теперь авторизован.

---

## Сценарий 3 — Новый email (verify_new_email)

Пользователь не авторизован, email не существует в базе.

### Шаг 1: Отправка email

```
POST /api/v1/public/events/{event_id}/register
Content-Type: application/json

{
  "tariff_id": "uuid-тарифа",
  "idempotency_key": "unique-key-123",
  "guest_email": "new@example.com"
}
```

### Ответ 201

```json
{
  "action": "verify_new_email",
  "masked_email": "n***@example.com",
  "registration_id": null,
  "payment_url": null,
  "applied_price": null,
  "is_member_price": null,
  "access_token": null,
  "refresh_token": null
}
```

**OTP-код отправлен на почту.** Фронт показывает форму ввода кода.

### Шаг 2: Подтверждение кода

Запрос и ответ **аналогичны сценарию 2**. Бэкенд автоматически:
- Создаёт аккаунт с ролью `user`.
- Отправляет email с временным паролем (для будущих входов).
- Возвращает JWT-токены для немедленной авторизации.

---

## Обработка ошибок

| HTTP | Код | Описание |
|------|-----|----------|
| 404 | NOT_FOUND | Мероприятие или тариф не найдены |
| 422 | VALIDATION_ERROR | `guest_email` не указан (без JWT), тариф недоступен, регистрация закрыта |
| 422 | VALIDATION_ERROR | Неверный OTP-код (показывает оставшиеся попытки) |
| 409 | CONFLICT | Нет мест |
| 429 | — | Лимит отправки кодов (макс. 3 за 10 мин) или лимит попыток (макс. 5) |

---

## OTP-код

- 6 цифр.
- Действителен 10 минут.
- Максимум 3 отправки на один email за 10 минут.
- Максимум 5 попыток ввода на один код.

---

## Email-уведомления

| Когда | Тема письма | Содержимое |
|-------|-------------|-----------|
| OTP-код отправлен | «Код подтверждения — {мероприятие}» | 6-значный код, 10 мин |
| Новый аккаунт создан | «Ваш аккаунт — Ассоциация трихологов» | Email, временный пароль, ссылка на ЛК |
| Оплата прошла | «Билет: {мероприятие} — Ассоциация трихологов» | Название, дата, место, стоимость, ссылка на чек |
| Чек от Moneta | «Ваш чек — Ассоциация трихологов» | Сумма, ссылка на скачивание чека |

---

## Платёжный flow (Moneta)

1. Фронт получает `payment_url` из ответа API.
2. Редирект пользователя на `payment_url` (Moneta payment form).
3. После оплаты Moneta редиректит на `MONETA_RETURN_URL` (настроен на бэкенде).
4. Moneta отправляет webhook на бэкенд → бэкенд подтверждает регистрацию.
5. Фронт показывает страницу результата.

---

## Минимальные поля для фронта

### Для неавторизованного пользователя

На первом шаге достаточно:

```json
{
  "tariff_id": "...",
  "idempotency_key": "...",
  "guest_email": "user@example.com"
}
```

### Для подтверждения кода

```json
{
  "email": "user@example.com",
  "code": "123456",
  "tariff_id": "...",
  "idempotency_key": "..."
}
```

Остальные поля (`guest_full_name`, `guest_workplace`, `guest_specialization`, `fiscal_email`) опциональны и могут быть добавлены позже в профиле.
