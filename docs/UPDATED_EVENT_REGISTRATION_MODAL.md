# Обновлённая спецификация: Модалка регистрации на мероприятие

> Заменяет раздел § 5.5 «Блок 2a: Модалка регистрации» из `07_Фронтенд_клиент.md`

---

## Состояния модалки (state machine)

```
[CLOSED] ──click "Оплатить"──→ [FORM]
                                  │
                     POST /register (без JWT)
                                  │
                    ┌──────────────┼──────────────┐
                    │              │              │
            action=null    action="verify_   action="verify_
            (JWT path)      existing"         new_email"
                    │              │              │
                    ▼              ▼              ▼
              [REDIRECT]      [LOGIN]        [CODE_INPUT]
                                  │              │
                            POST /auth/login  POST /confirm-guest
                                  │              │
                            [REDIRECT]       [REDIRECT]
```

---

## State 1: FORM (начальная форма)

Показывается когда пользователь **не авторизован** и нажал «Зарегистрироваться и оплатить».

Если пользователь **авторизован** — сразу `POST /register` с JWT, без модалки (или модалка с подтверждением).

```
┌─────────────────────────────────────────┐
│  Регистрация на мероприятие              │
│                                          │
│  Тариф: {tariff.name}                   │
│  Цена: {tariff.price} ₽                 │
│                                          │
│  Email *         [__________________]    │
│  ФИО             [__________________]    │
│  Место работы    [__________________]    │
│  Специализация   [__________________]    │
│                                          │
│  ☐ Отправить чек на другой email         │
│  Email для чека  [__________________]    │  ← появляется при ☐
│                                          │
│  После оплаты на указанный email будет   │
│  отправлен временный пароль для доступа  │
│  к личному кабинету.                     │
│                                          │
│  [Отмена]            [Оплатить {price} ₽]│
└─────────────────────────────────────────┘
```

**Поля:**

| Поле | required | validation |
|------|----------|------------|
| Email | Да | EmailStr |
| ФИО (guest_full_name) | Нет | max 300 |
| Место работы (guest_workplace) | Нет | max 255 |
| Специализация (guest_specialization) | Нет | max 255 |
| Email для чека (fiscal_email) | Нет | EmailStr |

**При отправке:**

```typescript
const response = await api.post(`/events/${eventId}/register`, {
  tariff_id: selectedTariff.id,
  idempotency_key: crypto.randomUUID(),
  guest_email: email,
  guest_full_name: fullName || undefined,
  guest_workplace: workplace || undefined,
  guest_specialization: specialization || undefined,
  fiscal_email: fiscalEmail || undefined,
});

switch (response.data.action) {
  case null:
    // Прямой путь (JWT или immediate) → redirect
    window.location.href = response.data.payment_url;
    break;
  case 'verify_existing':
    // Email в базе → показать форму логина
    setModalState('LOGIN');
    setMaskedEmail(response.data.masked_email);
    break;
  case 'verify_new_email':
    // Новый email → показать форму ввода кода
    setModalState('CODE_INPUT');
    setMaskedEmail(response.data.masked_email);
    break;
}
```

---

## State 2: LOGIN (email в базе — нужно войти)

```
┌─────────────────────────────────────────┐
│  Этот email уже зарегистрирован          │
│                                          │
│  Войдите в аккаунт {masked_email},       │
│  чтобы продолжить регистрацию.           │
│                                          │
│  Пароль *        [__________________]    │
│                                          │
│  Забыли пароль? →                        │
│                                          │
│  [Назад]                    [Войти]      │
└─────────────────────────────────────────┘
```

**Логика:**

1. `POST /api/v1/auth/login { email, password }`
2. При успехе → сохранить `access_token`
3. Повторить `POST /events/{id}/register` с JWT → получить `payment_url`
4. `window.location.href = payment_url`

**Ошибки:**
- 401 → toast «Неверный пароль»
- Кнопка «Забыли пароль?» → redirect `/forgot-password?redirect=/events/{slug}`

---

## State 3: CODE_INPUT (новый email — ввод кода)

```
┌─────────────────────────────────────────┐
│  Подтвердите email                       │
│                                          │
│  Мы отправили 6-значный код              │
│  на {masked_email}                       │
│                                          │
│  Код *   [ _ ] [ _ ] [ _ ] [ _ ] [ _ ] [ _ ]
│                                          │
│  Код действителен: 09:42 ← countdown     │
│                                          │
│  Не получили код?                        │
│  [Отправить повторно] ← disabled 60 сек │
│                                          │
│  [Назад]                [Подтвердить]    │
└─────────────────────────────────────────┘
```

**UI кода:**
- 6 отдельных `<input>` (auto-focus на следующий при вводе)
- Auto-submit при заполнении всех 6 цифр
- Paste support (вставка 6 цифр из буфера)

**Таймер:**
- 10 минут (600 секунд) с момента получения `action: "verify_new_email"`
- По истечении: «Код истёк» + кнопка «Отправить новый код»

**«Отправить повторно»:**
- Disabled 60 секунд после отправки
- Повторный `POST /events/{id}/register` с тем же email
- Максимум 3 отправки за 10 мин (при превышении — toast «Попробуйте позже»)

**При подтверждении:**

```typescript
const response = await api.post(`/events/${eventId}/confirm-guest-registration`, {
  email: email,             // полный email (не masked)
  code: codeDigits.join(''),
  tariff_id: selectedTariff.id,
  idempotency_key: crypto.randomUUID(),
  guest_full_name: fullName || undefined,
  guest_workplace: workplace || undefined,
  guest_specialization: specialization || undefined,
  fiscal_email: fiscalEmail || undefined,
});

// Успех → redirect на оплату
window.location.href = response.data.payment_url;
```

**Ошибки:**

| Код ошибки | Реакция |
|-----------|---------|
| 422 "Invalid verification code. N attempt(s) remaining." | Показать «Неверный код. Осталось N попыток» + очистить поля |
| 422 "Verification code expired or not found..." | Показать «Код истёк» + кнопка «Отправить новый код» |
| 422 "Too many verification attempts..." | Показать «Слишком много попыток» + кнопка «Отправить новый код» |
| 422 "Too many verification codes sent..." | Toast «Слишком много запросов. Попробуйте через 10 минут» |
| 422 "No seats available..." | Toast «Места закончились» + закрыть модалку |

---

## Логика для авторизованного пользователя

Если JWT есть, модалка **не нужна**. Просто:

```typescript
// Авторизованный → прямая регистрация
const response = await api.post(`/events/${eventId}/register`, {
  tariff_id: selectedTariff.id,
  idempotency_key: crypto.randomUUID(),
}, {
  headers: { Authorization: `Bearer ${accessToken}` }
});

toast.info('Перенаправляем на оплату...');
window.location.href = response.data.payment_url;
```

Но можно показать модалку-подтверждение:

```
┌─────────────────────────────────────────┐
│  Подтвердите регистрацию                 │
│                                          │
│  Мероприятие: {event.title}              │
│  Тариф: {tariff.name}                   │
│  Цена: {applied_price} ₽                │
│  Участник: {user.full_name} ({email})    │
│                                          │
│  [Отмена]         [Перейти к оплате]     │
└─────────────────────────────────────────┘
```

---

## Определение цены на карточке тарифа

Фронт **не** делает запрос check-price. Логика:

```typescript
const userHasActiveMembership = /* проверить через GET /subscriptions/status */;

const displayPrice = userHasActiveMembership
  ? tariff.member_price
  : tariff.price;

// Но показать ОБЕ цены:
// "15 000 ₽" (зачёркнутая) + "10 000 ₽ для членов" (зелёная)
// или только одну, если user = член
```

Бекенд сам определит `applied_price` и `is_member_price` при создании регистрации на основе подписки пользователя.
