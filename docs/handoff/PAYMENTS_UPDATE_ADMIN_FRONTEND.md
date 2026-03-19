# Обновление платежей — Админ-панель

**Дата:** 2026-03-19  
**Кому:** Фронтенд-разработчик административной панели  
**Тема:** Обновление схемы отображения платежей

---

## Что изменилось

1. Появился **новый статус платежа** — `expired` («Истёк»).
2. В список платежей добавлены **три новых поля**: `status_label`, `payment_url`, `expires_at`.
3. **Ошибка в отображении статусов**: `pending` не означает «На модерации» — это «Ожидает оплаты».
4. Автоматический переход `pending → expired` через 24 часа без оплаты.

---

## 1. Список платежей: `GET /api/v1/admin/payments`

### Запрос (не изменился)

```
GET /api/v1/admin/payments?limit=20&offset=0&sort_by=created_at&sort_order=desc
Authorization: Bearer {access_token}
```

**Фильтры (query params):**

| Параметр | Тип | Значения |
|----------|-----|----------|
| `status` | string? | `pending` / `succeeded` / `failed` / `expired` / `refunded` |
| `product_type` | string? | `entry_fee` / `subscription` / `event` |
| `user_id` | UUID? | — |
| `date_from` | datetime? | — |
| `date_to` | datetime? | — |

### Ответ — пример с pending-платежом

```json
{
  "data": [
    {
      "id": "a1b2-...",
      "user": {
        "id": "uuid",
        "email": "doctor@example.com",
        "full_name": "Петров Иван"
      },
      "amount": 20000.0,
      "product_type": "entry_fee",
      "payment_provider": "moneta",
      "status": "pending",
      "status_label": "Ожидает оплаты",
      "description": "Вступительный взнос + Годовой взнос",
      "payment_url": "https://demo.moneta.ru/assistant.htm?operationId=987654",
      "expires_at": "2026-03-20T14:25:00Z",
      "has_receipt": false,
      "paid_at": null,
      "created_at": "2026-03-19T14:25:00Z"
    },
    {
      "id": "b2c3-...",
      "user": { "id": "uuid", "email": "doc2@example.com", "full_name": "Сидорова Мария" },
      "amount": 15000.0,
      "product_type": "subscription",
      "payment_provider": "moneta",
      "status": "succeeded",
      "status_label": "Оплачен",
      "description": "Годовой членский взнос",
      "payment_url": null,
      "expires_at": null,
      "has_receipt": true,
      "paid_at": "2026-01-15T14:30:00Z",
      "created_at": "2026-01-15T14:25:00Z"
    },
    {
      "id": "c3d4-...",
      "user": { "id": "uuid", "email": "doc3@example.com", "full_name": "Козлов Дмитрий" },
      "amount": 20000.0,
      "product_type": "entry_fee",
      "payment_provider": "moneta",
      "status": "expired",
      "status_label": "Истёк",
      "description": "Вступительный взнос + Годовой взнос",
      "payment_url": null,
      "expires_at": "2026-03-18T10:00:00Z",
      "has_receipt": false,
      "paid_at": null,
      "created_at": "2026-03-17T10:00:00Z"
    }
  ],
  "summary": {
    "total_amount": 15000.0,
    "count_completed": 1,
    "count_pending": 1
  },
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

---

## 2. Новые поля и их значения

| Поле | Тип | Когда не null |
|------|-----|----------------|
| `status_label` | string | **Всегда**. Готовый текст на русском |
| `payment_url` | string \| null | Только для `status=pending` и только если `expires_at` ещё не прошёл |
| `expires_at` | datetime \| null | Только для `status=pending` |

---

## 3. Все статусы платежей — маппинг для отображения

| `status` | `status_label` | Цвет | Иконка |
|----------|----------------|------|--------|
| `pending` | Ожидает оплаты | 🟡 Жёлтый | ⏳ |
| `succeeded` | Оплачен | 🟢 Зелёный | ✅ |
| `failed` | Отклонён | 🔴 Красный | ❌ |
| `expired` | Истёк | ⚫ Серый | 🕐 |
| `refunded` | Возвращён | 🟣 Фиолетовый | ↩️ |
| `partially_refunded` | Частичный возврат | 🟣 Светло-фиолетовый | ↩️ |

> **Рекомендация:** Используйте поле `status_label` напрямую для текста в таблице. Поле `status` используйте только для программной логики (фильтры, условия).

---

## 4. Исправление ошибки: `pending` ≠ «На модерации»

### Проблема

В текущем фронте статус платежа `"pending"` отображается как «На модерации». Это **неверно**.

### Разъяснение

В системе существует **два независимых статуса**:

| Статус | Где | Поле | Значение |
|--------|-----|------|---------|
| Платёж ожидает оплаты | Таблица платежей | `status = "pending"` | «Ожидает оплаты» |
| Профиль врача на модерации | Карточка врача | `moderation_status = "pending_review"` | «На модерации» |

Это **разные объекты и разные поля**. Платёж в `pending` — это незавершённая оплата, а не модерация.

### Исправление

В таблице платежей — показывать `status_label` (готовый текст, правильный):

```js
// ❌ Было (неверно)
const displayStatus = status === 'pending' ? 'На модерации' : status

// ✅ Стало (правильно)
const displayStatus = payment.status_label
// или
const statusMap = {
  pending: 'Ожидает оплаты',
  succeeded: 'Оплачен',
  failed: 'Отклонён',
  expired: 'Истёк',
  refunded: 'Возвращён',
  partially_refunded: 'Частичный возврат',
}
const displayStatus = statusMap[payment.status] ?? payment.status
```

---

## 5. Отображение pending-платежа в таблице

Для платежей со `status=pending` и ненулевым `payment_url` — добавить кнопку-ссылку, чтобы админ мог скопировать ссылку на оплату или помочь пользователю.

```
| Петров И.  | 20 000 ₽  | Вступительный взнос | ⏳ Ожидает оплаты | [Скопировать ссылку]  | до 20.03 14:25 |
| Сидорова М.| 15 000 ₽  | Членский взнос      | ✅ Оплачен        | [Чек]                 |                |
| Козлов Д.  | 20 000 ₽  | Вступительный взнос | ⚫ Истёк          | —                     |                |
```

**Логика кнопки «Скопировать ссылку»:**
- Показывать только если `status=pending` и `payment_url !== null`
- При нажатии — скопировать `payment_url` в буфер обмена
- Если `payment_url = null` (срок истёк) — показать «Ссылка истекла»

```jsx
function PaymentActions({ payment }) {
  if (payment.status === 'pending') {
    if (payment.payment_url) {
      return (
        <>
          <button onClick={() => navigator.clipboard.writeText(payment.payment_url)}>
            Скопировать ссылку
          </button>
          <span>до {formatDate(payment.expires_at)}</span>
        </>
      )
    }
    return <span className="text-gray-400">Ссылка истекла</span>
  }
  if (payment.status === 'succeeded' && payment.has_receipt) {
    return <button onClick={() => openReceipt(payment.id)}>Чек</button>
  }
  return null
}
```

---

## 6. Жизненный цикл платежа (для понимания)

```
POST /subscriptions/pay
         │
         ▼
    status: pending ──────────── expires_at (24 ч) ──────► status: expired
         │                                                        │
         │  Moneta webhook (оплата)                    подписка → cancelled
         ▼                                             пользователь создаёт новый
    status: succeeded
         │
         ├──► подписка → active
         └──── чек → receipt webhook → email
         
    status: failed (Moneta webhook: отмена)
```

**Автоматика (cron каждые 30 мин):**
- Ищет все `pending` платежи где `expires_at < now()`
- Переводит в `expired`
- Связанную подписку в `pending_payment` → `cancelled`

---

## 7. Фильтрация по статусам в интерфейсе

Добавить в выпадающий список фильтра `status` новое значение:

```js
const statusOptions = [
  { value: '',                label: 'Все статусы' },
  { value: 'pending',        label: 'Ожидает оплаты' },
  { value: 'succeeded',      label: 'Оплачен' },
  { value: 'failed',         label: 'Отклонён' },
  { value: 'expired',        label: 'Истёк' },        // ← новый
  { value: 'refunded',       label: 'Возвращён' },
  { value: 'partially_refunded', label: 'Частичный возврат' },
]
```

---

## 8. Ручной платёж: `POST /api/v1/admin/payments/manual`

Не изменился. Работает для ситуаций когда платёж нужно отметить вручную (наличными, банковским переводом). Бекенд автоматически активирует подписку.

```json
{
  "user_id": "uuid",
  "amount": 20000.0,
  "product_type": "entry_fee",
  "description": "Оплата наличными на конференции",
  "subscription_id": "uuid"
}
```

---

## Резюме изменений для фронта

| Что | Было | Стало |
|-----|------|-------|
| Отображение `pending` | «На модерации» (ошибка) | «Ожидает оплаты» (верно) |
| Фильтр по статусам | нет `expired` | Добавить `expired` → «Истёк» |
| `status_label` в ответе | отсутствовал | Готовый текст на русском, использовать напрямую |
| `payment_url` в списке | отсутствовал | URL для pending, иначе `null` |
| `expires_at` в списке | отсутствовал | Datetime для pending, иначе `null` |
| Статус `expired` | не существовал | Платёж не оплачен 24 ч → авто-перевод |
