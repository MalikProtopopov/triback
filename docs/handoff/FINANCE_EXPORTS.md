# Finance XLSX exports — frontend handoff

Все эндпоинты под префиксом **`/api/v1/exports`**, только для ролей **admin**, **manager**, **accountant**. Ответ — бинарный **XLSX** (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), заголовок **`Content-Disposition: attachment; filename="..."`**.

Если записей больше **10 000**, API возвращает **400** с сообщением вида: «Найдено N записей, максимум 10 000. Уточните диапазон дат» (в JSON обёртке приложения поле `error.message`).

## GET `/api/v1/exports/payments`

Выгрузка платежей.

| Параметр | Описание |
|----------|----------|
| `date_from`, `date_to` | Даты (YYYY-MM-DD). Если **оба** не переданы — подставляется **текущий календарный месяц** (МСК). Если указано только одно из двух — **422**. |
| `date_field` | `paid_at` (по умолчанию) или `created_at` — по какому полю фильтровать диапазон. |
| `status` | Повторяемый query: статусы платежа. |
| `product_type` | Повторяемый: тип продукта. |
| `payment_provider` | Повторяемый: провайдер оплаты. |
| `user_id` | UUID пользователя. |

Имя файла: `payments_{date_from}_{date_to}.xlsx`.

## GET `/api/v1/exports/arrears`

Задолженности.

| Параметр | Описание |
|----------|----------|
| `date_from`, `date_to` | Фильтр по `created_at` задолженности; можно опустить оба — без ограничения по дате создания. |
| `status` | Повторяемый. |
| `year` | Повторяемый: год задолженности. |
| `user_id` | UUID. |

Имя файла: `arrears_{date_from|all}_{date_to|all}.xlsx`.

## GET `/api/v1/exports/event-registrations`

Регистрации на мероприятия и связанные оплаты.

**Обязательно:** либо **`event_id`**, либо **оба** `date_from` и `date_to` (фильтр по дате мероприятия). Иначе **422**.

| Параметр | Описание |
|----------|----------|
| `event_id` | UUID события (приоритет над датами). |
| `date_from`, `date_to` | Диапазон по дате события. |
| `registration_status` | Повторяемый. |
| `payment_status` | Повторяемый: статус связанного платежа. |
| `is_member_price` | `true` / `false` — членская цена тарифа. |

Имя файла: `event_registrations_{event_id}.xlsx` или `event_registrations_{date_from}_{date_to}.xlsx`.

## GET `/api/v1/exports/subscriptions`

Подписки и агрегаты по платежам.

| Параметр | Описание |
|----------|----------|
| `date_from`, `date_to` | Фильтр по `subscriptions.created_at`; оба можно не передавать. |
| `status` | Повторяемый. |
| `plan_id` | Повторяемый UUID. |
| `plan_type` | Повторяемый. |
| `is_first_year` | `true` / `false`. |
| `active_on` | Дата: подписки, **активные на эту дату**. |
| `user_id` | UUID. |

Имя файла: `subscriptions_{date_from|all}_{date_to|all}.xlsx`.

## Примеры

```http
GET /api/v1/exports/payments?date_from=2025-01-01&date_to=2025-01-31&date_field=paid_at
Authorization: Bearer <token>
```

```http
GET /api/v1/exports/event-registrations?event_id=<uuid>
Authorization: Bearer <token>
```

Колонки и форматы дат/чисел соответствуют ТЗ в `docs/finance_exports.docx` (заголовки на русском, даты в МСК, автофильтр на листе).
