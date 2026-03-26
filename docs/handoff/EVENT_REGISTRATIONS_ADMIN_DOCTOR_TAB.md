# Регистрации на мероприятия — админка, вкладка у врача (handoff)

Тот же состав данных, что и в ЛК, но для **выбранного пользователя портала** (страница врача / карточка пользователя).

**Базовый URL:** `https://trihoback.mediann.dev` (или другой хост бэкенда).

---

## Эндпоинт

| Метод | Путь |
|-------|------|
| `GET` | `/api/v1/admin/portal-users/{user_id}/event-registrations` |

**Авторизация:** `Authorization: Bearer <access_token>` с ролью **admin** или **manager**.

**Параметр пути:** `user_id` — UUID того же пользователя, что и в `GET /api/v1/admin/portal-users/{user_id}` (детали пользователя портала). Подставляйте из текущей открытой карточки врача.

Если пользователь с таким `user_id` не найден, ответ **404** (как у деталки portal user).

---

## Query-параметры

Те же, что в ЛК:

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int, 1–100 | По умолчанию 20 |
| `offset` | int ≥ 0 | Смещение |
| `status` | string, optional | `pending` \| `confirmed` \| `cancelled` |
| `event_id` | UUID, optional | Фильтр по мероприятию |

---

## Тело ответа

Формат идентичен **`GET /api/v1/profile/event-registrations`**: массив `data` с объектами `registration`, `event`, `tariff`, `payment` (или `null`), плюс `total`, `limit`, `offset`.

См. пример JSON в [EVENT_REGISTRATIONS_LK_FRONTEND.md](./EVENT_REGISTRATIONS_LK_FRONTEND.md).

---

## UI: вкладка «Мероприятия»

Рекомендуемые колонки таблицы:

| Колонка | Источник |
|---------|----------|
| Мероприятие | `event.title` |
| Дата | `event.event_date` (и при необходимости `event_end_date`) |
| Тариф | `tariff.name` |
| Цена билета | `tariff.applied_price` |
| Членская цена? | `tariff.is_member_price` → да/нет |
| Статус регистрации | `registration.status` |
| Сумма платежа | `payment.amount` или «—» если `payment === null` |
| Статус платежа | `payment.status` / `payment.status_label` или «—» |

Фильтры на странице можно связать с query: `status`, при выборе конкретного события — `event_id`.

---

## Ошибки

| Код | Причина |
|-----|---------|
| 401 | Не авторизован |
| 403 | Роль не admin/manager |
| 404 | Пользователь `user_id` не найден |
