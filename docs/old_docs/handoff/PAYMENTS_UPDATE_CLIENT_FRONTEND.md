# Обновление платежей — Клиентский сайт

**Дата:** 2026-03-19  
**Кому:** Фронтенд-разработчик клиентского сайта  
**Тема:** Обновление схемы работы с платежами и подписками

---

## Что изменилось

1. У платежей теперь есть **срок жизни** — по умолчанию **24 часа** с момента создания.
2. Истёкшие pending-платежи **автоматически переходят в статус `expired`**.
3. В истории платежей (ЛК) теперь возвращаются **новые поля**: `status_label`, `payment_url`, `expires_at`.
4. В ответе на создание платежа (`POST /subscriptions/pay`) теперь **всегда есть `expires_at`**.
5. Появился **новый статус платежа** — `expired`.

---

## 1. Создание платежа: `POST /api/v1/subscriptions/pay`

### Тело запроса (не изменилось)

```json
{
  "plan_id": "uuid",
  "idempotency_key": "uuid-v4"
}
```

### Ответ (обновлён)

```json
{
  "payment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "payment_url": "https://demo.moneta.ru/assistant.htm?operationId=987654321",
  "amount": 20000.0,
  "expires_at": "2026-03-20T14:25:00Z"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `payment_id` | UUID | ID платежа |
| `payment_url` | string | Ссылка для оплаты на странице Moneta |
| `amount` | float | Сумма в рублях |
| `expires_at` | datetime (UTC) | **Новое.** Время истечения ссылки (через 24 ч). После — `expired` |

### Что делать на фронте

```js
// 1. Сохранить idempotency_key перед запросом
localStorage.setItem('payment_idempotency_key', idempotencyKey)

// 2. Сделать запрос
const { payment_id, payment_url, expires_at } = await api.post('/subscriptions/pay', { plan_id, idempotency_key })

// 3. Сохранить данные
localStorage.setItem('pending_payment_id', payment_id)
localStorage.setItem('pending_payment_expires', expires_at)

// 4. Перейти на страницу оплаты
window.location.href = payment_url
```

---

## 2. История платежей: `GET /api/v1/subscriptions/payments`

### Запрос (не изменился)

```
GET /api/v1/subscriptions/payments?limit=20&offset=0
Authorization: Bearer {access_token}
```

### Ответ (обновлён — новые поля в каждом элементе)

```json
{
  "data": [
    {
      "id": "uuid",
      "amount": 20000.0,
      "product_type": "entry_fee",
      "status": "pending",
      "status_label": "Ожидает оплаты",
      "description": "Вступительный взнос + Годовой взнос",
      "payment_url": "https://demo.moneta.ru/assistant.htm?operationId=987654321",
      "expires_at": "2026-03-20T14:25:00Z",
      "paid_at": null,
      "created_at": "2026-03-19T14:25:00Z"
    },
    {
      "id": "uuid",
      "amount": 15000.0,
      "product_type": "subscription",
      "status": "succeeded",
      "status_label": "Оплачен",
      "description": "Годовой членский взнос",
      "payment_url": null,
      "expires_at": null,
      "paid_at": "2026-01-15T14:30:00Z",
      "created_at": "2026-01-15T14:25:00Z"
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

### Новые поля

| Поле | Тип | Когда не null |
|------|-----|----------------|
| `status_label` | string | Всегда. Готовый текст для отображения |
| `payment_url` | string \| null | Только для `status=pending` и только если срок не истёк |
| `expires_at` | datetime \| null | Только для `status=pending` |

---

## 3. Все возможные статусы платежа

| `status` | `status_label` | Смысл |
|----------|----------------|-------|
| `pending` | Ожидает оплаты | Создан, ждёт оплаты на стороне Moneta |
| `succeeded` | Оплачен | Оплачен (получен webhook) |
| `failed` | Отклонён | Отменён / ошибка платёжной системы |
| `expired` | Истёк | Не оплачен в течение 24 часов — **новый статус** |
| `refunded` | Возвращён | Полный возврат |
| `partially_refunded` | Частичный возврат | Частичный возврат |

---

## 4. Логика отображения истории платежей

### Таблица сценариев

| `status` | `payment_url` | Что показать пользователю |
|----------|---------------|--------------------------|
| `pending` | строка | Статус «Ожидает оплаты» + кнопка **«Оплатить»** → redirect на `payment_url`. Опционально: таймер до `expires_at` |
| `pending` | `null` | Статус «Ожидает оплаты» + текст «Срок оплаты истёк. Создайте новый платёж» |
| `succeeded` | `null` | Статус «Оплачен» + кнопка «Чек» (если есть) |
| `expired` | `null` | Статус «Истёк» + текст «Время оплаты вышло» |
| `failed` | `null` | Статус «Отклонён» |
| `refunded` | `null` | Статус «Возвращён» |

### Пример компонента (React/псевдокод)

```jsx
function PaymentRow({ payment }) {
  const isExpired = payment.expires_at && new Date(payment.expires_at) < new Date()

  return (
    <tr>
      <td>{payment.status_label}</td>
      <td>{payment.amount} ₽</td>
      <td>{payment.description}</td>
      <td>
        {payment.status === 'pending' && payment.payment_url && !isExpired && (
          <a href={payment.payment_url}>Оплатить</a>
        )}
        {payment.status === 'pending' && (!payment.payment_url || isExpired) && (
          <span>Срок истёк — создайте новый платёж</span>
        )}
        {payment.status === 'succeeded' && (
          <button onClick={() => openReceipt(payment.id)}>Чек</button>
        )}
      </td>
    </tr>
  )
}
```

---

## 5. Баннер «Незавершённый платёж» на странице подписки

Бекенд возвращает `next_action: "complete_payment"` в `GET /subscriptions/status`, когда у пользователя есть незавершённый pending-платёж.

```json
{
  "has_subscription": false,
  "next_action": "complete_payment",
  ...
}
```

### Что показать

```
⚠️ У вас есть незавершённый платёж.
   [Перейти к оплате]   — кнопка: достать payment_url из GET /subscriptions/payments
```

Алгоритм получения ссылки:
1. Вызвать `GET /subscriptions/payments?limit=5`
2. Найти первый элемент с `status=pending` и ненулевым `payment_url`
3. Если нашли — redirect на `payment_url`
4. Если `payment_url = null` — срок истёк, предложить создать новый

---

## 6. Повторная оплата / повторный вызов `POST /subscriptions/pay`

Если пользователь вышел с формы и хочет оплатить заново, фронт должен позвонить `POST /subscriptions/pay` **с тем же `idempotency_key`**, что был при первом запросе.

```js
const savedKey = localStorage.getItem('payment_idempotency_key')

// Если ключ есть и не истёк (24 ч TTL)
const { payment_url } = await api.post('/subscriptions/pay', {
  plan_id: selectedPlanId,
  idempotency_key: savedKey,
})
window.location.href = payment_url
```

Если идемпотентный ключ истёк (прошло > 24 ч) — сгенерировать новый UUID и создать новый платёж.

---

## 7. После успешной оплаты: страница `/payment/success`

1. Показать спиннер «Обрабатываем оплату…»
2. Polling `GET /subscriptions/status` каждые 2–3 сек, максимум 30 сек
3. Как только `current_subscription.status === "active"` — показать «Подписка активирована!»
4. Очистить localStorage: `payment_idempotency_key`, `pending_payment_id`, `pending_payment_expires`
5. Таймаут без ответа → «Оплата обрабатывается, обновите страницу через минуту»

---

## 8. Страница `/payment/fail`

```
❌ Оплата не прошла
   [Попробовать снова]   — redirect на payment_url из localStorage или новый POST /subscriptions/pay
```

---

## Резюме изменений для фронта

| Что | Было | Стало |
|-----|------|-------|
| `POST /subscriptions/pay` → `expires_at` | всегда `null` | UTC datetime через 24 ч |
| `GET /subscriptions/payments` → `status_label` | отсутствовал | Готовый текст на русском |
| `GET /subscriptions/payments` → `payment_url` | отсутствовал | URL для pending, иначе `null` |
| `GET /subscriptions/payments` → `expires_at` | отсутствовал | Datetime для pending, иначе `null` |
| Статус `expired` | нет | Появился — платёж не оплачен 24 ч |
| Pending платёж | висел вечно | Автоматически → `expired` через 24 ч |
