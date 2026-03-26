# Регистрация на мероприятия — Чеклист для фронтенда

Чтобы функционал работал корректно, фронтенд должен выполнить следующее.

---

## 1. Передача токена при запросе регистрации

**Критично.** Если пользователь авторизован, бэкенд должен получить токен. Без него — 422 «Email is required for guest registration».

### Откуда бэкенд берёт токен

1. **Authorization: Bearer** — заголовок
2. **X-Access-Token** — заголовок  
3. **Cookie `access_token`** — при логине и refresh бэкенд выставляет эту cookie

### Что сделать на фронте

**Вариант A (рекомендуемый):** Указать `credentials: 'include'` (fetch) или `withCredentials: true` (axios) — cookie `access_token` уйдёт автоматически.

**Вариант B:** Interceptor, добавляющий `Authorization: Bearer <token>` ко всем запросам к API.

---

## 2. Определение сценария при показе формы

| Пользователь залогинен? | Что показывать | Что отправлять |
|-------------------------|----------------|----------------|
| Да | Сразу кнопку «Оплатить» / выбор тарифа | `tariff_id`, `idempotency_key` + `credentials: include` или Authorization |
| Нет | Поле email → затем форма OTP | `tariff_id`, `idempotency_key`, `guest_email` |

---

## 3. Обработка ответа `POST /api/v1/events/{id}/register`

| `action` в ответе | Действие фронта |
|-------------------|-----------------|
| `null` | Есть `payment_url` → редирект на оплату |
| `verify_existing` | Показать форму ввода 6-значного кода |
| `verify_new_email` | Показать форму ввода 6-значного кода |

---

## 4. Подтверждение OTP (гости)

После ввода кода — `POST /api/v1/events/{id}/confirm-guest-registration`:

```json
{
  "email": "...",
  "code": "123456",
  "tariff_id": "...",
  "idempotency_key": "..."
}
```

Ответ содержит `payment_url`, `access_token`, `refresh_token`. Сохранить токены и выполнить редирект на `payment_url`.

---

## 5. Проверка в DevTools

Перед релизом проверить в Network:

- При авторизованном пользователе в запросе `POST .../register` есть заголовок `Authorization: Bearer …` или `X-Access-Token: …`.
- При отсутствии заголовка приходит 422 и текст «Email is required for guest registration».

---

## Краткий чеклист

- [ ] HTTP-клиент добавляет токен ко всем запросам к API при наличии сессии
- [ ] Страница мероприятия использует этот клиент, а не «голый» fetch
- [ ] Для cross-origin запросов выставлено `credentials: 'include'` (или эквивалент)
- [ ] В DevTools видно, что `Authorization` или `X-Access-Token` уходит с запросом регистрации
