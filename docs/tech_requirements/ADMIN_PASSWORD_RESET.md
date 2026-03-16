# Сброс пароля для администраторов (Фронт — Админка)

## Как это работает

Сброс пароля для admin/manager/accountant использует **те же API-эндпоинты**, что и для обычных пользователей, но письмо содержит ссылку на **домен админки** (`ADMIN_FRONTEND_URL`), а не на клиентский сайт.

Бэкенд автоматически определяет, является ли пользователь staff (admin/manager/accountant), и формирует ссылку в письме соответственно.

---

## Флоу восстановления пароля

```
1. Страница "Забыли пароль?" на домене админки
        ↓ ввод email
2. POST /api/v1/auth/forgot-password
        ↓ 200 OK (всегда, не раскрывает существование email)
3. Письмо с ссылкой на {ADMIN_FRONTEND_URL}/admin/reset-password?token=xxx
        ↓ пользователь открывает ссылку
4. Страница "Новый пароль" на домене админки
        ↓ ввод нового пароля
5. POST /api/v1/auth/reset-password
        ↓ 200 OK
6. Редирект на страницу входа /login (или /auth/login)
```

---

## API

### POST /api/v1/auth/forgot-password

Инициирует отправку письма со ссылкой сброса пароля.

**Request:**
```json
{
  "email": "admin@example.com"
}
```

**Response 200:**
```json
{
  "message": "Если email зарегистрирован, вы получите письмо для сброса пароля"
}
```

- Ответ **всегда 200** — не раскрывает, существует ли email в системе.
- Rate limit: 5 запросов в минуту с одного IP.
- Ссылка в письме действительна **1 час**.

---

### POST /api/v1/auth/reset-password

Устанавливает новый пароль по одноразовому токену из письма.

**Request:**
```json
{
  "token": "токен-из-ссылки-в-письме",
  "new_password": "НовыйПароль123!"
}
```

**Response 200:**
```json
{
  "message": "Пароль успешно изменён"
}
```

**Коды ошибок:**

| Код | Причина |
|-----|---------|
| 404 | Токен не найден или истёк (прошло более 1 часа) |
| 422 | Пароль слишком короткий (менее 8 символов) |

---

## Что нужно реализовать на фронте

### Страница 1: Забыли пароль

**URL:** `/admin/forgot-password` (на домене админки, например `https://admin.trichologia.ru/admin/forgot-password` или на тесте `https://admin.trichologia.mediann.dev/admin/forgot-password`)

**Форма:**
- Поле: Email
- Кнопка: «Отправить инструкцию»

**Логика:**
1. При сабмите: `POST /api/v1/auth/forgot-password`
2. Показать сообщение: «Если ваш email зарегистрирован, вы получите письмо с инструкцией»
3. Не переходить никуда автоматически — пользователь сам перейдёт по ссылке из письма

**Пример (fetch):**
```js
const response = await fetch('/api/v1/auth/forgot-password', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email }),
});
// Всегда 200 — показать сообщение о письме
```

---

### Страница 2: Новый пароль

**URL:** `/admin/reset-password` (должен читать токен из query параметра `?token=...`)

**Форма:**
- Поле: Новый пароль (min 8 символов)
- Поле: Подтверждение пароля
- Кнопка: «Сохранить пароль»

**Логика:**
1. При загрузке страницы — читать `token` из URL: `new URLSearchParams(location.search).get('token')`
2. Если `token` отсутствует → показать ошибку «Ссылка недействительна»
3. Валидация на фронте: оба поля совпадают, минимум 8 символов
4. При сабмите: `POST /api/v1/auth/reset-password`
5. **200** → показать «Пароль изменён» и редиректнуть на `/login` (через 2-3 сек или сразу)
6. **404** → «Ссылка недействительна или устарела» + кнопка «Запросить новую» → `/forgot-password`
7. **422** → «Пароль слишком короткий»

**Пример (fetch):**
```js
const token = new URLSearchParams(window.location.search).get('token');

const response = await fetch('/api/v1/auth/reset-password', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ token, new_password: newPassword }),
});

if (response.ok) {
  // Показать "Пароль изменён" → редирект на /login
} else if (response.status === 404) {
  // Показать "Ссылка недействительна" + кнопка повтора
} else if (response.status === 422) {
  // Показать ошибку валидации
}
```

---

## Структура страниц в проекте

Согласно ТЗ (`docs/tech_requirements/06_Фронтенд_админка.md`), страницы уже предусмотрены:

```
src/app/
  auth/
    forgot-password/page.tsx   ← форма ввода email
    reset-password/page.tsx    ← форма нового пароля (читает ?token=...)
```

---

## Важно про токен

- Токен в ссылке — одноразовый. После успешного сброса — инвалидируется.
- После истечения 1 часа — 404 при попытке использовать.
- Ссылка из письма ведёт на домен **админки**: `{ADMIN_FRONTEND_URL}/admin/reset-password?token=XXX`
- Тот же endpoint `POST /api/v1/auth/reset-password` используется и для клиентского сайта — это нормально, токен один и тот же, разница только в домене.

---

## Конфигурация (для DevOps / бэкенда)

В файле `.env.prod` должна быть задана переменная:

```bash
# Prod
ADMIN_FRONTEND_URL=https://admin.trichologia.ru

# Тест (staging)
ADMIN_FRONTEND_URL=https://admin.trichologia.mediann.dev
```

Если переменная не задана, письма staff-пользователям будут приходить со ссылкой на клиентский сайт (с предупреждением в логах бэкенда). Для корректной работы — обязательно задать.
