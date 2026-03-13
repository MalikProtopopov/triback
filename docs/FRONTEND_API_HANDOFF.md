# Handoff: Backend API → Frontend (Client + Admin)

**Дата:** 2026-03-12
**Backend URL (тест):** `https://trihoback.mediann.dev`
**Swagger:** `https://trihoback.mediann.dev/docs`
**Фронт-домены (тест):** `https://trichologia.mediann.dev` (клиент), `https://admin.trichologia.mediann.dev` (админ)

---

## 1. Что реализовано на бекенде (полный список)

### 1.1 Реализованные модули

| Модуль | Статус | Примечание |
|--------|--------|------------|
| Auth (регистрация, логин, refresh, logout, сброс/смена пароля, смена email) | **Готов** | RS256 JWT, Argon2id |
| Онбординг (выбор роли, анкета, документы, submit) | **Готов** | |
| Профиль врача (личный, публичный, модерация правок) | **Готов** | |
| Подписки + Платежи + YooKassa webhook | **Готов** | Фискализация 54-ФЗ |
| Публичный API (врачи, города, мероприятия, статьи, документы) | **Готов** | |
| Регистрация на мероприятия (3 сценария + верификация email) | **Готов** | Новый флоу! |
| Админ: врачи (CRUD, модерация, импорт Excel) | **Готов** | |
| Админ: мероприятия (CRUD, тарифы, галереи, записи) | **Готов** | |
| Админ: контент (статьи, темы, документы организации) | **Готов** | |
| Админ: платежи (список, ручной платёж) | **Готов** | |
| Админ: настройки (site_settings, города, планы) | **Готов** | |
| Админ: SEO-страницы | **Готов** | |
| Админ: Dashboard | **Готов** | |
| Уведомления (email/telegram, шаблоны) | **Готов** | Email-таски = заглушки (логирование) |
| Сертификаты (генерация PDF, скачивание) | **Готов** | |
| Telegram-привязка (код, webhook, канал) | **Готов** | |
| Голосование (CRUD, vote, результаты) | **Готов** | |
| Пользователи портала (список, детальная) | **Готов** | |

### 1.2 Что НЕ реализовано (нет на бекенде)

| Endpoint из ТЗ | Статус | Комментарий |
|----------------|--------|-------------|
| `GET /api/v1/pages/home` (контент hero, миссия) | **Нет** | Использовать `GET /api/v1/admin/settings` для получения контактов. Hero/миссию можно захардкодить на фронте или добавить через `site_settings` |
| `GET /api/v1/settings/public` (контакты, бот) | **Нет** | Данные можно получить через `GET /api/v1/admin/settings` (требует auth). Нужен публичный endpoint или захардкодить на фронте |
| `GET /api/v1/events/{id}/check-price` | **Нет** | Цена определяется на клиенте: если JWT → цена = `member_price` (при активной подписке) или `price`. Бекенд сам определит при `POST /register` |
| Content Blocks CRUD (`/api/v1/admin/content-blocks`) | **Нет** | Модель `ContentBlock` есть в БД, но эндпоинтов нет. Если нужно — добавим |
| `GET /api/v1/specializations` | **Нет** | Фильтр по специализации = строковый query param `specialization` в `GET /doctors`. Список специализаций можно собрать из результатов |

---

## 2. Формат ответов API

### 2.1 Успех

**Пагинированный список:**
```json
{
  "data": [...],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

**Единичный объект:** JSON-объект напрямую.

**Сообщение:** `{ "message": "..." }`

### 2.2 Ошибки (RFC 7807)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required for guest registration",
    "details": null
  }
}
```

| HTTP | Code | Когда |
|------|------|-------|
| 401 | UNAUTHORIZED | Нет/невалидный токен |
| 403 | FORBIDDEN | Нет роли / IP не в whitelist |
| 404 | NOT_FOUND | Ресурс не найден |
| 409 | CONFLICT | Дубликат (email, vote, draft) |
| 422 | VALIDATION_ERROR | Ошибка валидации |

### 2.3 JWT (RS256)

- **Access token:** 15 мин, передаётся в `Authorization: Bearer {token}`
- **Refresh token:** 30 дней, HttpOnly cookie `refresh_token` (path `/api/v1/auth`)
- **Payload:** `{ sub: UUID, role: string, type: "access", iat, exp }`

---

## 3. CORS

Бекенд принимает запросы от:
- `https://trichologia.mediann.dev`
- `https://admin.trichologia.mediann.dev`
- (и боевые домены, настраиваются через `ALLOWED_HOSTS` в `.env`)

`allow_credentials: true` — cookies (refresh token) передаются.

---

## 4. КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ: Регистрация на мероприятие

> Это главное отличие от оригинального ТЗ. Старый флоу (один POST → оплата) заменён на безопасный 3-сценарный процесс.

### 4.1 Обзор нового флоу

```
POST /api/v1/events/{event_id}/register
```

**Запрос:**
```json
{
  "tariff_id": "UUID",
  "idempotency_key": "unique-string",
  "guest_email": "user@example.com",
  "guest_full_name": "Иван Иванов",
  "guest_workplace": "Клиника А",
  "guest_specialization": "Трихология",
  "fiscal_email": "user@example.com"
}
```

**Ответ (расширенный `RegisterForEventResponse`):**
```json
{
  "registration_id": "UUID | null",
  "payment_url": "string | null",
  "applied_price": "float | null",
  "is_member_price": "bool | null",
  "action": "string | null",
  "masked_email": "string | null"
}
```

### 4.2 Сценарий 1: Авторизованный (JWT передан)

```
Frontend                              Backend
   │                                     │
   │  POST /register                     │
   │  Authorization: Bearer {jwt}        │
   │  { tariff_id, idempotency_key }     │
   │ ──────────────────────────────────> │
   │                                     │  Создаёт регистрацию + платёж
   │                                     │  Вызывает YooKassa
   │  201 {                              │
   │    registration_id: "...",          │
   │    payment_url: "https://yookassa.ru/...",
   │    applied_price: 10000.0,          │
   │    is_member_price: false,          │
   │    action: null                     │
   │  }                                  │
   │ <────────────────────────────────── │
   │                                     │
   │  window.location = payment_url      │
```

**Frontend:** если `action === null` и `payment_url !== null` → redirect на `payment_url`.

### 4.3 Сценарий 2: Не авторизован, email ЕСТЬ в базе

```
Frontend                              Backend
   │                                     │
   │  POST /register                     │
   │  (без JWT)                          │
   │  { tariff_id, guest_email: "a@b.c" }│
   │ ──────────────────────────────────> │
   │                                     │  Email найден в users
   │  201 {                              │
   │    action: "verify_existing",       │
   │    masked_email: "a***@b.c",        │
   │    registration_id: null,           │
   │    payment_url: null                │
   │  }                                  │
   │ <────────────────────────────────── │
   │                                     │
   │  Показать форму логина (email + пароль)
   │  + ссылку "Забыли пароль?"          │
   │                                     │
   │  POST /api/v1/auth/login            │
   │  { email, password }                │
   │ ──────────────────────────────────> │
   │  200 { access_token, ... }          │
   │ <────────────────────────────────── │
   │                                     │
   │  Повторный POST /register с JWT     │
   │  (→ Сценарий 1)                     │
```

**Frontend:** если `action === "verify_existing"`:
1. Показать модалку/форму: «Этот email уже зарегистрирован. Войдите, чтобы продолжить»
2. Поля: пароль (email уже известен)
3. Кнопки: «Войти», «Забыли пароль?» → `/forgot-password`
4. После успешного логина → повторить `POST /register` с JWT

### 4.4 Сценарий 3: Не авторизован, email НЕТ в базе

```
Frontend                              Backend
   │                                     │
   │  POST /register                     │
   │  (без JWT)                          │
   │  { tariff_id, guest_email: "new@..." }
   │ ──────────────────────────────────> │
   │                                     │  Email НЕ найден
   │                                     │  Генерирует 6-значный код
   │                                     │  Сохраняет в Redis (10 мин)
   │                                     │  Шлёт код на email
   │  201 {                              │
   │    action: "verify_new_email",      │
   │    masked_email: "n***@...",        │
   │    registration_id: null,           │
   │    payment_url: null                │
   │  }                                  │
   │ <────────────────────────────────── │
   │                                     │
   │  Показать форму ввода кода (6 цифр) │
   │                                     │
   │  POST /events/{id}/confirm-guest-registration
   │  { email, code, tariff_id,          │
   │    idempotency_key, guest_full_name,│
   │    ... }                            │
   │ ──────────────────────────────────> │
   │                                     │  Проверяет код
   │                                     │  Создаёт аккаунт (temp пароль)
   │                                     │  Создаёт регистрацию + платёж
   │                                     │  Шлёт письмо с паролем
   │  201 {                              │
   │    registration_id: "...",          │
   │    payment_url: "https://yookassa.ru/...",
   │    applied_price: 15000.0,          │
   │    is_member_price: false,          │
   │    action: null                     │
   │  }                                  │
   │ <────────────────────────────────── │
   │                                     │
   │  window.location = payment_url      │
```

**Frontend:** если `action === "verify_new_email"`:
1. Показать форму: «Мы отправили код подтверждения на {masked_email}»
2. Поле: 6-значный код
3. Кнопка: «Подтвердить»
4. Таймер 10 мин (после — «Код истёк, запросите новый»)
5. Кнопка «Отправить код повторно» → повторный `POST /register` с тем же email

**Endpoint подтверждения:**

```
POST /api/v1/events/{event_id}/confirm-guest-registration
```

```json
{
  "email": "new@example.com",
  "code": "123456",
  "tariff_id": "UUID",
  "idempotency_key": "unique-string",
  "guest_full_name": "Иван Иванов",
  "guest_workplace": "Клиника А",
  "guest_specialization": "Трихология",
  "fiscal_email": "new@example.com"
}
```

### 4.5 Ошибки регистрации

| Ошибка | HTTP | `error.message` | Действие фронта |
|--------|------|-----------------|-----------------|
| Мест нет | 422 | "No seats available for this tariff" | Toast «Места закончились» |
| Нет email (гость) | 422 | "Email is required for guest registration" | Подсветить поле email |
| Неверный код | 422 | "Invalid verification code. N attempt(s) remaining." | Toast + показать оставшиеся попытки |
| Код истёк | 422 | "Verification code expired or not found..." | Toast «Код истёк» + кнопка «Отправить новый» |
| Лимит попыток (5) | 422 | "Too many verification attempts..." | Toast «Слишком много попыток, запросите новый код» |
| Лимит отправки кодов (3) | 422 | "Too many verification codes sent..." | Toast «Попробуйте позже» |
| Тариф не найден | 404 | "Tariff not found for this event" | Toast «Тариф не найден» |
| Регистрация закрыта | 422 | "Registration is closed for this event" | Toast + disable кнопку |

### 4.6 Обновлённая логика кнопки «Оплатить» на странице мероприятия

```
Пользователь нажал "Зарегистрироваться и оплатить"
│
├─ JWT есть?
│   ├─ Да → POST /register с JWT (Сценарий 1) → redirect на payment_url
│   └─ Нет → Открыть модалку с формой (email, ФИО, ...)
│             │
│             └─ Пользователь заполнил → POST /register без JWT
│                 │
│                 ├─ action === null → redirect на payment_url
│                 ├─ action === "verify_existing" → показать форму логина
│                 └─ action === "verify_new_email" → показать форму ввода кода
```

---

## 5. Полная карта эндпоинтов по фронтенд-страницам

### 5.1 Клиентский сайт (публичные страницы)

| Страница | URL | Endpoints |
|----------|-----|-----------|
| Главная | `/` | `GET /events?period=upcoming&limit=4`, `GET /articles?limit=3`, `GET /seo/home` |
| Каталог врачей | `/doctors` | `GET /doctors?limit=12&offset=0&city_id=&specialization=&search=`, `GET /cities` |
| Профиль врача | `/doctors/{id}` | `GET /doctors/{id}` |
| Город (врачи) | `/cities/{slug}` | `GET /doctors?city_slug={slug}`, `GET /cities?with_doctors=true` |
| Список городов | `/cities` | `GET /cities?with_doctors=true` |
| Мероприятия | `/events` | `GET /events?period=upcoming&limit=10&offset=0` |
| Детальная мероприятия | `/events/{slug}` | `GET /events/{slug}`, `POST /events/{id}/register`, `POST /events/{id}/confirm-guest-registration` |
| Статьи | `/articles` | `GET /articles?limit=10&offset=0&theme_slug=`, `GET /article-themes` |
| Статья | `/articles/{slug}` | `GET /articles/{slug}` |
| Документы | `/documents` | `GET /organization-documents` |
| SEO | (любая) | `GET /seo/{slug}` |

### 5.2 Auth + Onboarding

| Страница | URL | Endpoints |
|----------|-----|-----------|
| Регистрация | `/register` | `POST /auth/register` |
| Подтверждение email | `/confirm-email?token=` | `POST /auth/verify-email` |
| Вход | `/login` | `POST /auth/login` |
| Забыл пароль | `/forgot-password` | `POST /auth/forgot-password` |
| Сброс пароля | `/reset-password?token=` | `POST /auth/reset-password` |
| Выбор роли | `/onboarding/role` | `GET /onboarding/status`, `POST /onboarding/choose-role` |
| Анкета врача | `/onboarding/profile` | `GET /onboarding/status`, `GET /cities`, `PATCH /onboarding/doctor-profile`, `POST /onboarding/documents`, `POST /onboarding/submit` |
| Ожидание модерации | `/onboarding/pending` | `GET /onboarding/status` (polling 30s) |

### 5.3 Личный кабинет

| Страница | URL | Endpoints |
|----------|-----|-----------|
| Главная ЛК | `/cabinet` | `GET /onboarding/status`, `GET /subscriptions/status`, `GET /events?period=upcoming&limit=3` |
| Личная информация | `/cabinet/personal` | `GET /profile/personal`, `PATCH /profile/personal`, `POST /profile/photo`, `POST /profile/diploma-photo` |
| Публичный профиль | `/cabinet/public` | `GET /profile/public`, `PATCH /profile/public`, `POST /profile/photo`, `GET /cities` |
| Оплаты и подписка | `/cabinet/payments` | `GET /subscriptions/status`, `POST /subscriptions/pay`, `GET /subscriptions/payments`, `GET /subscriptions/payments/{id}/receipt` |
| Мои мероприятия | `/cabinet/events` | `GET /profile/events` |
| Сертификат | `/cabinet/certificate` | `GET /certificates`, `GET /certificates/{id}/download` |
| Telegram | `/cabinet/telegram` | `GET /telegram/binding`, `POST /telegram/generate-code` |
| Настройки | `/cabinet/settings` | `POST /auth/change-password`, `POST /auth/change-email` |
| Голосование | `/cabinet/voting` | `GET /voting/active`, `POST /voting/{session_id}/vote` |
| Успешная оплата | `/payment/success` | — |
| Ошибка оплаты | `/payment/fail` | — |

### 5.4 Админ-панель

| Страница | URL | Endpoints |
|----------|-----|-----------|
| Дашборд | `/admin/dashboard` | `GET /admin/dashboard` |
| Врачи (список) | `/admin/doctors` | `GET /admin/doctors?limit=20&offset=0&status=&search=&city_id=&subscription_status=`, `GET /admin/cities` |
| Врач (карточка) | `/admin/doctors/{id}` | `GET /admin/doctors/{id}`, `POST .../moderate`, `POST .../approve-draft`, `POST .../toggle-active`, `POST .../send-reminder`, `POST .../send-email` |
| Импорт | `/admin/doctors/import` | `POST /admin/doctors/import`, `GET /admin/doctors/import/{task_id}` |
| Мероприятия (список) | `/admin/events` | `GET /admin/events` |
| Мероприятие (создание) | `/admin/events/new` | `POST /admin/events` |
| Мероприятие (редактирование) | `/admin/events/{id}/edit` | `GET /admin/events/{id}`, `PATCH /admin/events/{id}`, `POST .../tariffs`, `PATCH .../tariffs/{tid}`, `DELETE .../tariffs/{tid}`, `POST .../galleries`, `POST .../galleries/{gid}/photos`, `POST .../recordings`, `PATCH .../recordings/{rid}` |
| Мероприятие (детальная) | `/admin/events/{id}` | `GET /admin/events/{id}/registrations` |
| Платежи | `/admin/payments` | `GET /admin/payments`, `POST /admin/payments/manual` |
| Статьи (список) | `/admin/content/articles` | `GET /admin/articles` |
| Статья (создание) | `/admin/content/articles/new` | `POST /admin/articles` |
| Статья (редактирование) | `/admin/content/articles/{id}/edit` | `GET /admin/articles/{id}`, `PATCH /admin/articles/{id}` |
| Темы статей | `/admin/content/article-themes` | `GET /admin/article-themes`, `POST`, `PATCH/{id}`, `DELETE/{id}` |
| Документы орг. | `/admin/content/documents` | `GET /admin/organization-documents`, `POST`, `PATCH/{id}`, `DELETE/{id}` |
| Настройки | `/admin/settings` | `GET /admin/settings`, `PATCH /admin/settings` |
| Города | `/admin/settings/cities` | `GET /admin/cities`, `POST`, `PATCH/{id}`, `DELETE/{id}` |
| Тарифы подписки | `/admin/settings/plans` | `GET /admin/plans`, `POST`, `PATCH/{id}`, `DELETE/{id}` |
| SEO | `/admin/settings/seo` | `GET /admin/seo-pages`, `POST`, `PATCH/{slug}`, `DELETE/{slug}` |
| Голосование (список) | `/admin/voting` | `GET /admin/voting` |
| Голосование (создание) | `/admin/voting/new` | `POST /admin/voting` |
| Голосование (детальная) | `/admin/voting/{id}` | `GET /admin/voting/{id}/results`, `PATCH /admin/voting/{id}` |
| Уведомления | `/admin/notifications` | `GET /admin/notifications`, `POST /admin/notifications/send` |
| Пользователи портала | `/admin/portal-users` | `GET /admin/portal-users` |
| Пользователь (детальная) | `/admin/portal-users/{id}` | `GET /admin/portal-users/{id}` |

---

## 6. Роли и доступ (матрица)

| Endpoint prefix | Public | user | doctor | admin | manager | accountant |
|----------------|--------|------|--------|-------|---------|-----------|
| `/auth/*` | Частично | — | — | — | — | — |
| `/onboarding/*` | — | Auth | Auth | — | — | — |
| `/profile/*` | — | — | Auth | — | — | — |
| `/subscriptions/*` | — | — | doctor | — | — | — |
| `/certificates/*` | — | — | doctor | — | — | — |
| `/telegram/*` | — | — | doctor | — | — | — |
| `/voting/*` | — | — | doctor | — | — | — |
| `/doctors`, `/events`, `/articles`, ... (public) | Read | Read | Read | — | — | — |
| `/events/{id}/register` | Optional JWT | ✓ | ✓ | — | — | — |
| `/admin/dashboard` | — | — | — | ✓ | ✓ | — |
| `/admin/doctors/*` | — | — | — | ✓ | ✓ | — |
| `/admin/events/*` | — | — | — | ✓ | ✓ | — |
| `/admin/articles/*` | — | — | — | ✓ | ✓ | — |
| `/admin/payments` | — | — | — | ✓ | ✓ | ✓ |
| `/admin/settings` | — | — | — | ✓ | — | — |
| `/admin/cities` | — | — | — | ✓ | ✓ | — |
| `/admin/plans` | — | — | — | ✓ | — | — |
| `/admin/voting/*` | — | — | — | ✓ | ✓ | — |
| `/admin/notifications/*` | — | — | — | ✓ | ✓ | — |
| `/admin/portal-users/*` | — | — | — | ✓ | ✓ | — |

---

## 7. Rate Limits

| Endpoint | Лимит |
|----------|-------|
| `POST /auth/register` | 5 / мин |
| `POST /auth/login` | 10 / мин |
| `POST /auth/forgot-password` | 5 / мин |
| Отправка кода верификации (мероприятие) | 3 кода на email / 10 мин |
| Проверка кода верификации (мероприятие) | 5 попыток на email / 10 мин |

---

## 8. Задачи для бекенда (чтобы фронт мог работать полноценно)

### 8.1 Нужно добавить (приоритет P0 — блокирует фронт)

| # | Задача | Приоритет | Описание |
|---|--------|-----------|----------|
| 1 | `GET /api/v1/settings/public` | **P0** | Публичные настройки (контакты, ссылка бота) без авторизации. Сейчас `GET /admin/settings` требует auth |
| 2 | Контент главной (hero, миссия) | **P1** | Либо endpoint `GET /api/v1/pages/home`, либо через `site_settings`, либо захардкодить на фронте. Обсудить |
| 3 | Content Blocks CRUD | **P2** | Модель `ContentBlock` в БД есть, но API нет. Нужны CRUD-эндпоинты в `/admin/content-blocks` + GET в публичных ответах `doctors/{id}`, `events/{slug}`, `articles/{slug}` |

### 8.2 Можно обойтись без (nice-to-have)

| # | Задача | Описание |
|---|--------|----------|
| 4 | `GET /api/v1/specializations` | Список уникальных специализаций для фильтра. Пока можно собрать из `GET /doctors` |
| 5 | Администраторы CRUD (`/admin/users`) | Управление admin/manager/accountant ролями |

---

## 9. Рекомендации фронтенд-разработчику

### 9.1 Хранение токена

- `access_token`: in-memory (React state / Zustand). **НЕ** localStorage.
- `refresh_token`: HttpOnly cookie, path `/api/v1/auth`. Устанавливается автоматически бекендом.

### 9.2 Axios interceptor

```typescript
// При 401 → попытка refresh → retry
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        const { data } = await api.post('/api/v1/auth/refresh');
        setAccessToken(data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api(error.config);
      } catch {
        clearAuth();
        window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
      }
    }
    return Promise.reject(error);
  }
);
```

### 9.3 Idempotency keys

Для платежных запросов **обязательно** генерировать уникальный `idempotency_key` (UUID v4) на клиенте:
- `POST /subscriptions/pay`
- `POST /events/{id}/register`
- `POST /events/{id}/confirm-guest-registration`

Это предотвращает двойные оплаты при retry.

### 9.4 Пагинация

Все списки: `limit` + `offset`. Ответ содержит `total` для расчёта страниц.

```
Страница 1: ?limit=20&offset=0
Страница 2: ?limit=20&offset=20
Страница N: ?limit=20&offset=(N-1)*20
```

### 9.5 Загрузка файлов

Все файлы загружаются как `multipart/form-data`. Изображения из API приходят как presigned S3 URL (временные ссылки).

### 9.6 Тестовая оплата (YooKassa)

На тестовом сервере YooKassa работает в sandbox-режиме. Карта для теста: `1111 1111 1111 1026`, любой CVC, любая дата.

---

## 10. Docker и развёртывание фронтенда

Фронтенд (client + admin) — отдельные Next.js приложения, деплоятся на свои домены.

**ENV-переменные для фронтенда:**
```env
NEXT_PUBLIC_API_URL=https://trihoback.mediann.dev/api/v1
NEXT_PUBLIC_SITE_URL=https://trichologia.mediann.dev
```

Nginx для фронтенда настраивается отдельно на сервере-хосте фронтов.
