# API выгрузок отчётов (XLSX) для админки

Базовый префикс: **`/api/v1/exports`**.

## Как это работает сейчас

- Клиент делает **`GET`** с заголовком **`Authorization: Bearer <access_token>`**.
- Успешный ответ: **`200`**, тело — **бинарный файл Excel** (не JSON).
- Заголовок ответа: **`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`**
- Имя файла: в **`Content-Disposition: attachment; filename="..."`** — его можно использовать для сохранения на диск у пользователя.
- Ошибки: **`401`** не авторизован, **`403`** роль не разрешена, **`422`** неверные/неполные query-параметры, **`400`** если строк больше **10 000** (нужно сузить фильтры / даты). Текст ошибки часто в обёртке **`error.message`**.

На фронте обычно: `fetch` / axios с **`responseType: 'blob'`** (или `arraybuffer`), затем создать объектную ссылку и программно нажать «скачать», либо открыть в новой вкладке через URL с токеном (менее предпочтительно из‑за утечки токена в логах).

**Скачивание:** отчёт приходит в **браузер** пользователя (blob / скачивание).

**Telegram:** те же фильтры, но **`POST`** на путь **`…/telegram`** — файл уходит в настроенный **чат/канал** Telegram (см. ниже). Ответ JSON: `{"ok": true, "filename": "...", "telegram_message_id": ...}`.

---

## Роли по группам эндпоинтов

| Эндпоинты | Роли |
|-----------|------|
| `payments`, `arrears`, `event-registrations`, `subscriptions` | **admin**, **manager**, **accountant** |
| `doctors`, `protocol-history` | **admin**, **manager** только (accountant → **403**) |

---

## Финансовые выгрузки

Подробнее параметры: [`FINANCE_EXPORTS.md`](./FINANCE_EXPORTS.md).

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/v1/exports/payments` | Платежи |
| POST | `/api/v1/exports/payments/telegram` | Платежи → Telegram |
| GET | `/api/v1/exports/arrears` | Задолженности |
| POST | `/api/v1/exports/arrears/telegram` | Задолженности → Telegram |
| GET | `/api/v1/exports/event-registrations` | Регистрации на мероприятия |
| POST | `/api/v1/exports/event-registrations/telegram` | Регистрации → Telegram |
| GET | `/api/v1/exports/subscriptions` | Подписки и взносы |
| POST | `/api/v1/exports/subscriptions/telegram` | Подписки → Telegram |

---

## Управленческие выгрузки

Подробнее параметры: [`MANAGEMENT_EXPORTS.md`](./MANAGEMENT_EXPORTS.md).

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/api/v1/exports/doctors` | Реестр врачей |
| POST | `/api/v1/exports/doctors/telegram` | Реестр врачей → Telegram |
| GET | `/api/v1/exports/protocol-history` | История протоколов (опционально два листа) |
| POST | `/api/v1/exports/protocol-history/telegram` | История протоколов → Telegram |

---

## Примеры вызова для фронта

Замените `BASE` на URL API (например `https://api.example.com`).

```http
GET BASE/api/v1/exports/payments?date_from=2025-01-01&date_to=2025-01-31&date_field=paid_at
Authorization: Bearer <token>
```

```http
GET BASE/api/v1/exports/doctors
Authorization: Bearer <token>
```

```http
GET BASE/api/v1/exports/protocol-history?active_doctors_only=true
Authorization: Bearer <token>
```

```http
POST BASE/api/v1/exports/payments/telegram?date_from=2025-01-01&date_to=2025-01-31&date_field=paid_at
Authorization: Bearer <token>
```

Повторяемые query-параметры (массивы) в URL:

`?status=pending&status=succeeded` или `?status[]=pending&status[]=succeeded` — зависит от клиента; FastAPI принимает оба варианта.

---

## Настройка Telegram для POST-выгрузок

1. **`TELEGRAM_BOT_TOKEN`** — токен бота (уже используется приложением).
2. **`TELEGRAM_EXPORTS_CHAT_ID`** (рекомендуется) — ID чата или канала, куда слать XLSX (число, для супергрупп/каналов часто отрицательное, например `-1001234567890`).
3. Если `TELEGRAM_EXPORTS_CHAT_ID` пусто, используется **`TELEGRAM_CHANNEL_ID`** (как запасной вариант).

Бот должен иметь право **отправлять сообщения** в этот чат (для канала — быть администратором с правом постинга; для группы — быть участником).

Ошибки: **`503`** — чат не настроен или неверный ID; **`502`** — сбой ответа Telegram.

---

## Swagger

После деплоя список ручек смотрите в **OpenAPI** приложения, тег **`Exports`** (если в проекте включена документация `/docs`).
