# Клиентский сайт и ЛК врача — сводка для фронтенда

Единая точка входа по **подпискам, платежам и задолженностям** после доработок по плану задолженностей. Детали по отдельным фичам см. в связанных handoff-файлах в этой же папке.

**Источник контрактов:** `GET /api/v1/openapi.json` или `/docs` на бэкенде. При расхождении с текстом ниже приоритет у OpenAPI.

---

## 1. Аутентификация и роли

- Публичные эндпоинты каталога и контента — без токена (см. раздел «Каталог»).
- ЛК врача: `Authorization: Bearer <access_token>`, роль **doctor** для маршрутов под `/api/v1/subscriptions/*`, профиля и т.д.

---

## 2. Подписки и оплата — главный экран

### 2.1 Статус подписки (единый источник для экрана оплаты)

**`GET /api/v1/subscriptions/status`**

Используйте **один** этот запрос для отрисовки: планы, вступительный, членский, **открытые долги**, флаги блокировки, состояние исключения.

| Поле / блок | Смысл для UI |
|-------------|----------------|
| `has_subscription`, `current_subscription` | Активная подписка, даты, дни до окончания |
| `has_paid_entry_fee`, `entry_fee_required`, `entry_fee_plan` | Нужен ли вступительный; если у профиля **`entry_fee_exempt`** на бэкенде, вступительный не требуется |
| `available_plans` | Активные планы членского (`plan_type=subscription`) |
| `next_action` | Подсказка сценария: `pay_subscription`, `pay_entry_fee_and_subscription`, `renew`, `complete_payment` и т.д. |
| **`open_arrears`** | Массив **только** долгов со статусом **`open`** (к оплате). Элементы: `id`, `year`, `amount`, `description`, `source`, **`escalation_level`** (может быть `null`) |
| **`arrears_total`** | Сумма открытых долгов (для отображения итога) |
| **`arrears_block_active`** | `true`, если в настройках сайта включена блокировка при долгах **и** есть открытые долги — показать предупреждение (каталог, привилегии — по продукту) |
| **`is_membership_excluded`**, **`membership_excluded_at`** | Врач исключён (при ручном/будущем автоматическом выставлении даты). UI: блок «возврат», сценарий оплаты по полям выше и `next_action` |

**Бизнес-логика:**

- В **`open_arrears` не попадают** статусы **`paid`**, **`cancelled`**, **`waived`**. Прощённые админом долги врач **не видит** как к оплате.
- Членский по календарному году на бэкенде завязан на окончание подписки **31.12** (MSK) — в UI достаточно показывать даты из `current_subscription`.

---

### 2.2 Оплата членского взноса (вступительный + год или только год)

**`POST /api/v1/subscriptions/pay`**

Тело: `{ "plan_id": "uuid", "idempotency_key": "string" }`.

Ответ: `payment_id`, `payment_url`, `amount`, **`expires_at`** (ссылка на оплату ограничена по времени; после истечения статус платежа может стать `expired`).

Подробности по полям истории и статусам: [PAYMENTS_UPDATE_CLIENT_FRONTEND.md](./PAYMENTS_UPDATE_CLIENT_FRONTEND.md).

---

### 2.3 Оплата задолженности по членскому взносу

**`POST /api/v1/subscriptions/pay-arrears`**

Тело: `{ "arrear_id": "uuid", "idempotency_key": "string" }`.

Ответ: как у обычного платежа — `payment_url`, `amount`, `expires_at` → редирект на Moneta, обработка возврата и ошибок.

**Очередь оплаты (продукт):** бэкенд не обязан блокировать «членский за год», пока есть долги — ориентируйтесь на **`next_action`** и тексты ошибок API. Если продукт решит «сначала долги», можно на фронте дизейблить кнопку «Оплатить членский» при `open_arrears.length > 0`.

---

### 2.4 История платежей врача

**`GET /api/v1/subscriptions/payments`**

В элементах списка учитывайте **`product_type`**: в т.ч. **`membership_arrears`** — оплата задолженности по году. Подпись в UI: например «Задолженность за {год}» из `description` или связки с контекстом.

Поля **`status_label`**, **`expires_at`**, **`payment_url`** для `pending` — см. [PAYMENTS_UPDATE_CLIENT_FRONTEND.md](./PAYMENTS_UPDATE_CLIENT_FRONTEND.md).

---

### 2.5 Статус платежа после редиректа

- **`GET /api/v1/subscriptions/payments/{payment_id}/status`** — публичный polling (без авторизации).
- **`POST /api/v1/subscriptions/payments/{payment_id}/check-status`** — проверка через Moneta (doctor).

---

## 3. Каталог и публичный профиль врача

При **`arrears_block_active === true`** врач с открытыми долгами может **не отображаться** в каталоге (список врачей / город / деталка — по реализации бэкенда). В ЛК покажите понятное сообщение о необходимости погасить задолженность.

См. также: [ONBOARDING_API_CLIENT.md](./ONBOARDING_API_CLIENT.md), [PUBLIC_PROFILE_SUBMIT_CLIENT.md](./PUBLIC_PROFILE_SUBMIT_CLIENT.md).

---

## 4. Сценарии «возврат спустя годы» и прощение долгов

- Если бухгалтерия перевела долг в **`waived`**, врач **не видит** эту сумму в `open_arrears` и не оплачивает её как «текущий долг».
- Историю прощений в ЛК **не** выводить, если нет продуктовой необходимости — в API для врача список прощённых не отдаётся в `open_arrears`.

---

## 5. Связанные документы

| Тема | Файл |
|------|------|
| Задолженности (детально) | [ARREARS_CLIENT_LK.md](./ARREARS_CLIENT_LK.md) |
| Обновление платежей (expires, labels) | [PAYMENTS_UPDATE_CLIENT_FRONTEND.md](./PAYMENTS_UPDATE_CLIENT_FRONTEND.md) |
| Онбординг | [ONBOARDING_API_CLIENT.md](./ONBOARDING_API_CLIENT.md) |
| Публичный профиль | [PUBLIC_PROFILE_SUBMIT_CLIENT.md](./PUBLIC_PROFILE_SUBMIT_CLIENT.md) |
| Автоматика задолженностей (будущее) | [ARREARS_PHASE3_BACKLOG.md](./ARREARS_PHASE3_BACKLOG.md) |

---

## 6. Чеклист фронта (клиент)

- [ ] Один экран оплаты на базе **`GET /subscriptions/status`**.
- [ ] Блок **только открытых** долгов + кнопки «Оплатить» → **`POST /subscriptions/pay-arrears`** по `arrear_id`.
- [ ] Учёт **`entry_fee_exempt`** (бэкенд не требует вступительный в ответе).
- [ ] Предупреждение при **`arrears_block_active`**.
- [ ] История платежей с типом **`membership_arrears`**.
- [ ] Истечение ссылки оплаты (`expires_at`) и статус **`expired`**.
- [ ] Блок **исключённого** врача при наличии `membership_excluded_at` / `is_membership_excluded`.
