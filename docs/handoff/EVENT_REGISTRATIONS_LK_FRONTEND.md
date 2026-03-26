# Регистрации на мероприятия — клиентский ЛК (handoff)

Список регистраций текущего пользователя с мероприятием, тарифом (включая фактическую цену и признак членской цены) и опциональным платежом.

**Базовый URL:** `https://trihoback.mediann.dev` (или другой хост бэкенда).

---

## Эндпоинт

| Метод | Путь |
|-------|------|
| `GET` | `/api/v1/profile/event-registrations` |

**Авторизация:** `Authorization: Bearer <access_token>` (роль обычно `doctor` или `user`).

---

## Query-параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int, 1–100, по умолчанию 20 | Размер страницы |
| `offset` | int ≥ 0 | Смещение |
| `status` | string, optional | Фильтр: `pending`, `confirmed`, `cancelled` |
| `event_id` | UUID, optional | Только регистрации на указанное мероприятие |

---

## Ответ 200

```json
{
  "data": [
    {
      "registration": {
        "id": "uuid",
        "status": "pending",
        "created_at": "2026-03-01T12:00:00Z",
        "guest_full_name": null,
        "guest_email": null,
        "guest_workplace": null,
        "guest_specialization": null,
        "fiscal_email": null
      },
      "event": {
        "id": "uuid",
        "slug": "conference-2026",
        "title": "Конференция",
        "event_date": "2026-06-01T10:00:00Z",
        "event_end_date": null,
        "location": "Москва",
        "status": "upcoming",
        "cover_image_url": "https://..."
      },
      "tariff": {
        "id": "uuid",
        "name": "Старт",
        "price": 5000.0,
        "member_price": 2500.0,
        "applied_price": 5000.0,
        "is_member_price": false
      },
      "payment": null
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

- **`payment`** — `null`, если платёж ещё не создан или не привязан к регистрации; для ожидающей оплаты может быть объект со статусом `pending`, полями `payment_url` (если ссылка ещё действительна), `expires_at`.
- **`tariff.applied_price` / `is_member_price`** — фактическая цена и снятие билета по членской цене или полной (см. логику регистрации).
- Гостевые поля в `registration` заполняются при соответствующем сценарии регистрации.

---

## Связь со страницей мероприятий

1. **Список «Мои регистрации»** в ЛК — один запрос `GET /api/v1/profile/event-registrations` с пагинацией; отображать строки таблицы из `event` + `tariff` + `registration.status` + сумму из `payment.amount` или `tariff.applied_price`.
2. **Переход на карточку события** — использовать `event.slug` (например маршрут `/events/{slug}` на клиенте, если такой есть).
3. **Продолжить оплату** — если `payment` не `null`, `status === "pending"` и есть `payment_url`, показать кнопку «Оплатить» по этой ссылке.

---

## Отличие от `GET /api/v1/profile/events`

| | `GET /profile/events` | `GET /profile/event-registrations` |
|---|------------------------|-------------------------------------|
| Статусы регистраций | только `confirmed` | все (`pending`, `confirmed`, `cancelled`) |
| Платёж | не отдаётся | вложенный объект `payment` или `null` |
| Тариф | только имя (`tariff_name`) | полный тариф + `applied_price` / `is_member_price` |

Старый эндпоинт оставлен для обратной совместимости (краткий список подтверждённых участий).

---

## Ошибки

| Код | Причина |
|-----|---------|
| 401 | Нет или невалидный токен |
