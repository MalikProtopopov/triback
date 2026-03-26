# Отмена платежа — Админ-панель

**Дата:** 2026-03-19  
**Кому:** Фронтенд-разработчик административной панели  
**Тема:** Новый эндпоинт — отмена pending-платежа администратором

---

## Зачем

Иногда платёж «зависает» в статусе `pending`: пользователь случайно создал два платежа, выбрал неверный тариф, или возникла техническая проблема. Сейчас единственный способ — ждать 24 часа до автоматического `expired`. 

Новый эндпоинт позволяет админу **мгновенно отменить** pending-платёж, чтобы пользователь мог свободно создать новый.

---

## Эндпоинт: `POST /api/v1/admin/payments/{payment_id}/cancel`

### Авторизация

- **Роли:** `admin`, `accountant`
- **Заголовок:** `Authorization: Bearer {access_token}`

### Запрос

```
POST /api/v1/admin/payments/a1b2c3d4-5678-9abc-def0-123456789abc/cancel
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Тело:**

```json
{
  "reason": "Клиент запросил отмену, создаст новый платёж"
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `reason` | string | ✅ | Причина отмены (макс. 500 символов) |

### Успешный ответ — `200 OK`

```json
{
  "payment_id": "a1b2c3d4-5678-9abc-def0-123456789abc",
  "status": "failed",
  "cancelled_subscription": true,
  "cancelled_event_registration": false,
  "message": "Платёж отменён. Пользователь может создать новый платёж."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `payment_id` | UUID | ID отменённого платежа |
| `status` | string | Новый статус — всегда `"failed"` |
| `cancelled_subscription` | boolean | `true` если связанная подписка в `pending_payment` была отменена |
| `cancelled_event_registration` | boolean | `true` если связанная регистрация на мероприятие была отменена |
| `message` | string | Человекочитаемое сообщение для отображения |

### Ошибки

| Код | Когда | Пример `detail` |
|-----|-------|-----------------|
| 401 | Не авторизован | `"Not authenticated"` |
| 403 | Роль не admin/accountant | `"Forbidden"` |
| 404 | Платёж не найден | `"Payment not found"` |
| 422 | Платёж не в статусе `pending` | `"Можно отменить только платёж в статусе 'pending'. Текущий статус: 'succeeded'"` |

---

## Что происходит на бекенде при отмене

1. **Платёж:** `status` меняется с `pending` на `failed`
2. **Описание:** к `description` добавляется `" | Отменён администратором: {reason}"`
3. **Подписка** (если есть): если `subscription.status == "pending_payment"` → переводится в `"cancelled"`
4. **Мероприятие** (если есть): `EventRegistration` отменяется, `seats_taken` уменьшается на 1
5. После отмены пользователь может свободно повторить оплату через `/subscriptions/pay` или `/events/{id}/register`

---

## Интеграция в UI таблицы платежей

### Когда показывать кнопку «Отменить»

Кнопка должна отображаться **только** для платежей со `status === "pending"`.

```
| Петров И.  | 20 000 ₽ | Вступительный взнос | ⏳ Ожидает оплаты | [Скопировать ссылку] [Отменить] | до 20.03 |
| Сидорова М.| 15 000 ₽ | Членский взнос      | ✅ Оплачен        | [Чек] [Возврат]                 |          |
| Козлов Д.  | 20 000 ₽ | Вступительный взнос | ⚫ Истёк          | —                               |          |
```

### Рекомендуемый UX-флоу

1. Админ нажимает кнопку **«Отменить»** на строке с pending-платежом
2. Открывается **модальное окно подтверждения**:
   - Заголовок: «Отмена платежа»
   - Текст: «Вы уверены, что хотите отменить платёж на сумму {amount} ₽ для {user.full_name || user.email}?»
   - Поле ввода: `reason` (обязательное, placeholder: «Укажите причину отмены»)
   - Информационное предупреждение: «Связанная подписка / регистрация на мероприятие также будет отменена»
   - Кнопки: **[Отменить платёж]** (красная) и **[Назад]**
3. При подтверждении — `POST /api/v1/admin/payments/{id}/cancel` с `{ "reason": "..." }`
4. При успехе — показать toast с `response.message`, обновить строку в таблице:
   - `status` → `"failed"`, `status_label` → `"Отклонён"`
   - Убрать кнопки «Скопировать ссылку» и «Отменить»

### Пример компонента

```jsx
function CancelPaymentButton({ payment, onCancelled }) {
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  if (payment.status !== 'pending') return null;

  const handleCancel = async () => {
    if (!reason.trim()) return;
    setLoading(true);
    try {
      const res = await api.post(`/admin/payments/${payment.id}/cancel`, { reason });
      toast.success(res.data.message);
      onCancelled(res.data);
      setIsOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка при отмене');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button onClick={() => setIsOpen(true)} className="text-red-600 hover:text-red-800">
        Отменить
      </button>

      {isOpen && (
        <Modal onClose={() => setIsOpen(false)}>
          <h3>Отмена платежа</h3>
          <p>
            Отменить платёж на сумму <b>{payment.amount.toLocaleString()} ₽</b>
            {' '}для {payment.user.full_name || payment.user.email}?
          </p>
          <p className="text-amber-600 text-sm">
            Связанная подписка или регистрация на мероприятие также будет отменена.
          </p>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Укажите причину отмены"
            maxLength={500}
            required
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setIsOpen(false)}>Назад</button>
            <button
              onClick={handleCancel}
              disabled={loading || !reason.trim()}
              className="bg-red-600 text-white"
            >
              {loading ? 'Отмена...' : 'Отменить платёж'}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
```

---

## Обновлённые кнопки действий по статусу

| `status` | Доступные действия |
|----------|-------------------|
| `pending` | Скопировать ссылку, **Отменить** |
| `succeeded` | Чек (если `has_receipt`), Возврат |
| `failed` | — |
| `expired` | — |
| `refunded` | — |

---

## Полная карта API платежей (для справки)

| Метод | Путь | Описание | Роли |
|-------|------|----------|------|
| GET | `/api/v1/admin/payments` | Список платежей | admin, manager, accountant |
| POST | `/api/v1/admin/payments/manual` | Ручной платёж | admin, accountant |
| POST | `/api/v1/admin/payments/{id}/cancel` | **Отмена платежа** ← новый | admin, accountant |
| POST | `/api/v1/admin/payments/{id}/refund` | Возврат платежа | admin, accountant |

---

## Жизненный цикл платежа (обновлённый)

```
POST /subscriptions/pay
         │
         ▼
    status: pending ──────────── expires_at (24 ч) ──────► status: expired
         │         │                                             │
         │         │  Админ: POST .../cancel       подписка → cancelled
         │         │  + причина                    пользователь создаёт новый
         │         ▼
         │    status: failed (отменён админом)
         │         │
         │         ├── подписка → cancelled
         │         └── регистрация на мероприятие → cancelled, seats_taken -= 1
         │
         │  Moneta/YooKassa webhook (оплата)
         ▼
    status: succeeded
         │
         ├──► подписка → active
         ├──── чек → receipt webhook → email
         │
         │  Админ: POST .../refund
         ▼
    status: refunded
```
