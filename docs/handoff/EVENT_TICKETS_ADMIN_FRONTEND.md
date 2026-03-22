# Event Tickets — Admin Frontend Handoff

Описание API и данных для отображения регистраций на мероприятия в админке.

---

## Регистрации на мероприятие

### Список регистраций

```
GET /api/v1/admin/events/{event_id}/registrations?limit=20&offset=0&status=confirmed
Authorization: Bearer <admin_token>
```

**Query-параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int (1–100) | Кол-во записей, по умолчанию 20 |
| `offset` | int | Смещение |
| `status` | string? | Фильтр: `pending`, `confirmed`, `cancelled` |

### Связь регистрация → платёж

Каждая регистрация привязана к платежу через `event_registration_id` в таблице `payments`.

```
EventRegistration (id) ←── Payment (event_registration_id)
       │                         │
       ├── user_id               ├── amount
       ├── applied_price         ├── status (pending/succeeded/failed/expired)
       ├── is_member_price       ├── external_payment_url
       ├── status                ├── paid_at
       ├── guest_email           └── receipts[] (Receipt)
       └── event_tariff_id
```

---

## Статусы регистрации

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает оплаты |
| `confirmed` | Оплата прошла успешно |
| `cancelled` | Отменена (платёж не прошёл или возврат) |

---

## Статусы платежа

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает оплаты (ссылка активна) |
| `succeeded` | Оплачен |
| `failed` | Ошибка оплаты |
| `expired` | Срок ссылки истёк |
| `refunded` | Возврат |

---

## Цена и скидка

- `applied_price` — фактическая цена, по которой прошла оплата.
- `is_member_price` — `true` если применена цена для членов ассоциации.
- Скидка применяется автоматически: бэкенд проверяет, что пользователь — врач со статусом ACTIVE и имеет активную подписку.

---

## Чеки (Receipts)

Чеки хранятся в таблице `receipts` и привязаны к `payment_id`.

### Получение чека

```
GET /api/v1/subscriptions/payments/{payment_id}/receipt
Authorization: Bearer <token>
```

**Ограничение:** Endpoint доступен только владельцу платежа (роль `doctor`) — для платежей за подписку. В списке платежей админки (`GET /api/v1/admin/payments`) каждому платежу соответствует флаг `has_receipt`. Отдельного endpoint для скачивания чека администратором нет — чек приходит пользователю на email.

### Ответ

```json
{
  "id": "uuid",
  "receipt_type": "payment",
  "provider_receipt_id": "12345",
  "receipt_url": "https://receipt.moneta.ru/receipt/12345",
  "fiscal_number": "...",
  "fiscal_document": "...",
  "fiscal_sign": "...",
  "amount": 5000.0,
  "status": "succeeded"
}
```

### Как формируется чек

1. При создании платежа — данные о товаре (название мероприятия + тариф) передаются в платёжную систему.
2. Moneta формирует фискальный чек (54-ФЗ) и отправляет webhook на `POST /api/v1/webhooks/moneta/receipt`.
3. Бэкенд сохраняет `Receipt` в БД и отправляет email пользователю со ссылкой на скачивание чека.

---

## Email-уведомления при покупке билета

| Событие | Получатель | Содержимое |
|---------|-----------|-----------|
| Оплата прошла | Покупатель | Название мероприятия, дата, место, стоимость, ссылка на ЛК |
| Чек сформирован | Покупатель | Сумма, ссылка на скачивание чека |
| Новый аккаунт создан | Новый пользователь | Временный пароль, ссылка в ЛК |
| Оплата получена | Админ (Telegram) | Email, сумма, тип продукта |

---

## Тарифы мероприятия

Каждое мероприятие имеет тарифы (`event_tariffs`):

| Поле | Описание |
|------|----------|
| `name` | Название тарифа |
| `price` | Полная цена |
| `member_price` | Цена для членов ассоциации |
| `seats_limit` | Лимит мест (null = без лимита) |
| `seats_taken` | Занято мест |
| `is_active` | Активен ли тариф |

При покупке бэкенд автоматически увеличивает `seats_taken` и проверяет лимит.

---

## API эндпоинты для управления

Базовый URL: `https://trihoback.mediann.dev` (или другой хост бэкенда).

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/v1/admin/events/{id}/registrations` | Список регистраций |
| GET | `/api/v1/admin/events` | Список мероприятий |
| GET | `/api/v1/admin/events/{id}` | Детали мероприятия |
| POST | `/api/v1/admin/events` | Создать мероприятие (FormData: title, event_date, slug?, description?, location?, cover_image?) |
| PATCH | `/api/v1/admin/events/{id}` | Обновить мероприятие (FormData) |
| DELETE | `/api/v1/admin/events/{id}` | Удалить мероприятие |
| POST | `/api/v1/admin/events/{id}/tariffs` | Создать тариф (JSON) |
| PATCH | `/api/v1/admin/events/{id}/tariffs/{tid}` | Обновить тариф (JSON) |
| DELETE | `/api/v1/admin/events/{id}/tariffs/{tid}` | Удалить тариф |
| GET | `/api/v1/admin/payments` | Список всех платежей (фильтры: status, product_type, user_id, date_from, date_to) |
