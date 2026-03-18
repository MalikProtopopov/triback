# Клиентский сайт — полная документация API для фронтенда

**Дата:** 2026-03-18  
**Базовый URL:** `{API_URL}/api/v1`  
**Swagger:** `{API_URL}/docs`  
**Провайдер оплаты:** Moneta (Moneta.Assistant + BPA PayAnyWay)

---

## Содержание

1. [Общие правила](#1-общие-правила)
2. [Публичные API (без авторизации)](#2-публичные-api)
3. [Auth — регистрация и авторизация](#3-auth)
4. [Онбординг](#4-онбординг)
5. [ЛК: Профиль врача](#5-лк-профиль)
6. [ЛК: Подписки и платежи](#6-лк-подписки-и-платежи)
7. [ЛК: Коллеги](#7-лк-коллеги)
8. [ЛК: Сертификаты](#8-лк-сертификаты)
9. [ЛК: Telegram](#9-лк-telegram)
10. [ЛК: Голосование](#10-лк-голосование)
11. [Регистрация на мероприятия](#11-регистрация-на-мероприятия)
12. [Оплата через Moneta — redirect flow](#12-оплата-moneta)
13. [Карта страниц → эндпоинты](#13-карта-страниц)

---

## 1. Общие правила

### 1.1 Формат ответов

**Пагинированный список:**
```json
{ "data": [...], "total": 150, "limit": 20, "offset": 0 }
```

**Ошибка (RFC 7807):**
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": null } }
```

| HTTP | Code | Когда |
|------|------|-------|
| 401 | UNAUTHORIZED | Нет / невалидный токен |
| 403 | FORBIDDEN | Нет нужной роли или подписка неактивна |
| 404 | NOT_FOUND | Ресурс не найден |
| 409 | CONFLICT | Дубликат (email, голос, черновик) |
| 422 | VALIDATION_ERROR | Ошибка валидации полей |
| 429 | RATE_LIMITED | Превышен лимит запросов |

### 1.2 JWT (RS256)

- **Access token:** 15 мин, в заголовке `Authorization: Bearer {token}`.
- **Refresh token:** 30 дней, HttpOnly cookie `refresh_token`, path `/api/v1/auth`.
- **Payload:** `{ sub: UUID, role: "doctor"|"user"|"admin"|..., type: "access" }`.

### 1.3 Пагинация

Все списки: `?limit=20&offset=0`. Ответ содержит `total`.

### 1.4 Idempotency

Для платёжных запросов **обязателен** `idempotency_key` (UUID v4). Повторный запрос с тем же ключом вернёт тот же результат. TTL: 24 часа.

### 1.5 Медиа

Изображения приходят как presigned S3 URL. Загрузка файлов — `multipart/form-data`.

---

## 2. Публичные API

> Все запросы ниже **без авторизации**.

### 2.1 Настройки сайта

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/settings/public` | Публичные настройки |

**Ответ:**
```json
{
  "data": {
    "contact_email": "info@trichology.ru",
    "contact_phone": "+7 (495) 123-45-67",
    "telegram_bot_link": "https://t.me/tricho_bot",
    "site_name": "Ассоциация трихологов",
    "site_description": "..."
  }
}
```

### 2.2 Врачи (каталог)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/doctors` | Список врачей |
| GET | `/doctors/{identifier}` | Карточка врача (UUID или slug) |

**GET `/doctors` — Query параметры:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 12 | 1–50 |
| `offset` | int | 0 | ≥0 |
| `city_id` | UUID? | — | Фильтр по городу |
| `city_slug` | string? | — | Фильтр по slug города |
| `specialization` | string? | — | Поиск по специализации (ilike) |
| `search` | string? | — | Поиск по имени/фамилии (мин. 2 символа) |

**Ответ:**
```json
{
  "data": [{
    "id": "uuid",
    "first_name": "Иван",
    "last_name": "Петров",
    "middle_name": "Сергеевич",
    "city": "Москва",
    "clinic_name": "Клиника А",
    "specialization": "Трихология",
    "academic_degree": "к.м.н.",
    "bio": "...",
    "photo_url": "https://...",
    "public_phone": "+7...",
    "public_email": "doctor@clinic.ru",
    "slug": "petrov-ivan"
  }],
  "total": 42, "limit": 12, "offset": 0
}
```

**GET `/doctors/{identifier}` — дополнительные поля:** `position`, `seo` (title, description, og_image...), `content_blocks` (массив блоков с type, content, media_url...).

**ВАЖНО (обновление март 2026):**
- В выдачу попадают **только врачи с активной подпиской** (`status=active`, `ends_at > now`).
- Врач без подписки → **не в списке** и **404 по slug/UUID**.
- Фронт: показывать «Врач временно недоступен» или страницу 404.

### 2.3 Города

| Метод | Путь | Query | Описание |
|-------|------|-------|----------|
| GET | `/cities` | `with_doctors=true` | Список городов |
| GET | `/cities/{slug}` | — | Город по slug |

**Ответ `/cities?with_doctors=true`:**
```json
{
  "data": [{ "id": "uuid", "name": "Москва", "slug": "moskva", "doctors_count": 15 }]
}
```

**ВАЖНО:** `doctors_count` учитывает только врачей с **активной подпиской**.

### 2.4 Мероприятия

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/events` | Список мероприятий |
| GET | `/events/{slug}` | Детальная страница |
| GET | `/events/{event_id}/galleries` | Галереи (фото) |
| GET | `/events/{event_id}/recordings` | Видеозаписи |

**GET `/events` — Query параметры:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | ≥0 |
| `period` | string | "upcoming" | `upcoming` / `past` / `all` |

**Ответ `/events/{slug}`:**
```json
{
  "id": "uuid", "title": "...", "slug": "...",
  "event_date": "2026-05-01T10:00:00Z",
  "event_end_date": "2026-05-01T18:00:00Z",
  "location": "Москва, ул. ...",
  "cover_image_url": "https://...",
  "tariffs": [{
    "id": "uuid", "name": "Участник", "price": 10000.0,
    "member_price": 5000.0, "seats_limit": 100, "seats_available": 42,
    "description": "...", "conditions": "...", "benefits": [...]
  }],
  "galleries": [{ "id": "uuid", "title": "...", "access_level": "public", "photos_count": 12 }],
  "recordings": [{ "id": "uuid", "title": "...", "access_level": "members_only", "duration_seconds": 3600 }],
  "seo": { "title": "...", "description": "..." },
  "content_blocks": [...]
}
```

**Доступ к галереям/записям:** при `access_level=members_only` нужна **активная подписка** или подтверждённая регистрация. JWT опционален — если передан, бекенд проверяет права.

### 2.5 Статьи

| Метод | Путь | Query | Описание |
|-------|------|-------|----------|
| GET | `/articles` | `limit`, `offset`, `theme_slug`, `search` | Список статей |
| GET | `/article-themes` | `active`, `has_articles` | Темы статей |
| GET | `/articles/{slug}` | — | Статья |

### 2.6 Документы организации

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/organization-documents` | Список документов |
| GET | `/organization-documents/{slug}` | Документ по slug |

### 2.7 SEO

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/seo/{slug}` | Метаданные страницы |

**Ответ:** `{ title, description, og_title, og_description, og_image_url, og_type, twitter_card, canonical_url }`.

---

## 3. Auth

> Rate-limit: `/register` 5/мин, `/login` 10/мин, `/forgot-password` 5/мин.

| Метод | Путь | Auth | Body | Ответ |
|-------|------|------|------|-------|
| POST | `/auth/register` | Нет | `{ email, password, re_password }` | `{ message }` |
| POST | `/auth/verify-email` | Нет | `{ token }` | `{ message }` |
| POST | `/auth/resend-verification-email` | Нет | `{ email }` | `{ message }` |
| POST | `/auth/login` | Нет | `{ email, password }` | `{ access_token, token_type, role }` |
| POST | `/auth/refresh` | Cookie | — | `{ access_token, token_type, role }` |
| GET | `/auth/me` | JWT | — | `{ id, email, role, is_staff, sidebar_sections }` |
| POST | `/auth/logout` | Cookie | — | `{ message }` |
| POST | `/auth/forgot-password` | Нет | `{ email }` | `{ message }` |
| POST | `/auth/reset-password` | Нет | `{ token, new_password }` | `{ message }` |
| POST | `/auth/change-password` | JWT | `{ current_password, new_password }` | `{ message }` |
| POST | `/auth/change-email` | JWT | `{ new_email, password }` | `{ message }` |
| POST | `/auth/confirm-email-change` | Нет | `{ token }` | `{ message }` |

**Валидация:** `password` мин. 8 символов. `re_password` должен совпадать с `password`.

**Хранение:**
- `access_token` — **in-memory** (React state / Zustand). **НЕ** localStorage.
- `refresh_token` — HttpOnly cookie, автоматически.
- При 401 → `POST /auth/refresh` → обновить access → retry. При неудаче → logout + redirect `/login`.

---

## 4. Онбординг

> Auth: JWT (любая роль).

| Метод | Путь | Body | Ответ |
|-------|------|------|-------|
| GET | `/onboarding/status` | — | `OnboardingStatusResponse` |
| POST | `/onboarding/choose-role` | `{ role: "doctor" }` | `{ message, next_step, profile_id }` |
| PATCH | `/onboarding/doctor-profile` | см. ниже | `{ message, next_step }` |
| POST | `/onboarding/documents` | FormData: `file` + `document_type` | `{ id, document_type, original_filename, uploaded_at }` |
| POST | `/onboarding/submit` | — | `{ message, next_step, moderation_status }` |

**PATCH `/onboarding/doctor-profile`:**
```json
{
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "phone": "+79001234567",
  "passport_data": "...",
  "city_id": "uuid",
  "clinic_name": "Клиника А",
  "position": "Главный врач",
  "academic_degree": "к.м.н."
}
```

**`document_type`:** `medical_diploma` | `retraining_cert` | `oncology_cert` | `additional_cert`.

**GET `/onboarding/status` — ответ:**
```json
{
  "email_verified": true,
  "role_chosen": true,
  "role": "doctor",
  "profile_filled": true,
  "documents_uploaded": true,
  "has_medical_diploma": true,
  "moderation_status": "pending_review",
  "submitted_at": "2026-03-10T12:00:00Z",
  "rejection_comment": null,
  "next_step": "wait_moderation"
}
```

**Значения `next_step`:** `verify_email` → `choose_role` → `fill_profile` → `upload_documents` → `submit` → `wait_moderation` → `done`.

---

## 5. ЛК: Профиль

> Auth: JWT, роль `doctor`.

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/profile/personal` | Личные данные |
| PATCH | `/profile/personal` | Обновить личные данные |
| GET | `/profile/public` | Публичный профиль (+ pending_draft) |
| PATCH | `/profile/public` | Обновить публичный профиль (→ черновик на модерацию) |
| POST | `/profile/photo` | Загрузка фото (FormData: `file`) |
| POST | `/profile/diploma-photo` | Загрузка фото диплома (FormData: `file`) |
| GET | `/profile/events` | Мои мероприятия (`limit`, `offset`) |

**PATCH `/profile/personal` — body:**
```json
{
  "first_name": "...", "last_name": "...", "middle_name": "...",
  "phone": "...", "passport_data": "...",
  "registration_address": "...", "colleague_contacts": "Telegram: @petrov"
}
```

**PATCH `/profile/public` — body:**
```json
{
  "bio": "...", "public_email": "...", "public_phone": "...",
  "city_id": "uuid", "clinic_name": "...", "academic_degree": "..."
}
```

**Изменения уходят в черновик.** Ответ `GET /profile/public`:
```json
{
  "bio": "...", "photo_url": "https://...", "city": { "id": "uuid", "name": "Москва" },
  "pending_draft": {
    "status": "pending",
    "changes": { "bio": "Новый текст", "photo_url": "doctors/uuid/photo/new.jpg" },
    "submitted_at": "2026-03-17T12:00:00Z",
    "rejection_reason": null
  }
}
```

**POST `/profile/photo` — ответ:**
```json
{ "photo_url": "https://...", "message": "Фото отправлено на модерацию", "pending_moderation": true }
```

**Для фронта:** если `pending_moderation=true` → показывать «Фото на модерации». Превью нового фото: `MEDIA_BASE_URL + pending_draft.changes.photo_url`.

---

## 6. ЛК: Подписки и платежи

> Auth: JWT, роль `doctor`.

| Метод | Путь | Body / Query | Описание |
|-------|------|--------------|----------|
| GET | `/subscriptions/status` | — | Полный статус подписки |
| POST | `/subscriptions/pay` | `{ plan_id, idempotency_key }` | Создать платёж → получить payment_url |
| GET | `/subscriptions/payments` | `limit`, `offset` | История платежей |
| GET | `/subscriptions/payments/{id}/receipt` | — | Чек (фискальный документ) |

### GET `/subscriptions/status` — ответ:

```json
{
  "has_subscription": false,
  "current_subscription": null,
  "has_paid_entry_fee": false,
  "can_renew": false,
  "next_action": "pay_entry_fee_and_subscription",
  "entry_fee_required": true,
  "entry_fee_plan": {
    "id": "uuid", "code": "entry", "name": "Вступительный взнос",
    "plan_type": "entry_fee", "price": 5000.0, "duration_months": 0
  },
  "available_plans": [{
    "id": "uuid", "code": "annual", "name": "Годовой членский взнос",
    "plan_type": "subscription", "price": 15000.0, "duration_months": 12
  }]
}
```

### Значения `next_action` — что показывать:

| next_action | Что делать на фронте |
|-------------|---------------------|
| `pay_entry_fee_and_subscription` | Показать сумму (entry_fee + plan), кнопку «Оплатить». Сумма = `entry_fee_plan.price + selected_plan.price` |
| `pay_subscription` | Выбор плана из `available_plans`, кнопка «Оплатить» |
| `renew` | Подписка истекла. Кнопка «Продлить», выбор плана |
| `complete_payment` | Есть незавершённый платёж. Показать предупреждение |
| `null` | Подписка активна. Если `can_renew=true` (≤30 дней) — кнопка «Продлить досрочно». Показать `days_remaining` |

### Как работает подписка:

1. **Первая оплата** или перерыв >60 дней → `entry_fee` (вступительный + годовой в одном платеже).
2. **Продление** (перерыв ≤60 дней или подписка ещё активна) → `subscription` (только годовой).
3. Бекенд **сам определяет тип**. Фронт вызывает `POST /subscriptions/pay` с `plan_id` (годового плана), бекенд автоматически добавит entry_fee, если нужен.
4. При продлении `ends_at` считается **от текущего `ends_at`**, не от `now()`. Оплаченное время не теряется.

### POST `/subscriptions/pay` — ответ:

```json
{
  "payment_id": "uuid",
  "payment_url": "https://moneta.ru/assistant.htm?operationId=12345",
  "amount": 20000.0,
  "expires_at": null
}
```

Фронт: `window.location.href = payment_url`.

### GET `/subscriptions/payments` — ответ:

```json
{
  "data": [{
    "id": "uuid", "amount": 20000.0, "product_type": "entry_fee",
    "status": "succeeded", "description": "Вступительный + Годовой взнос",
    "paid_at": "2026-01-15T14:30:00Z", "created_at": "2026-01-15T14:25:00Z"
  }],
  "total": 3, "limit": 20, "offset": 0
}
```

### GET `/subscriptions/payments/{id}/receipt` — ответ:

```json
{
  "id": "uuid", "receipt_type": "payment",
  "receipt_url": "https://receipt.moneta.ru/...",
  "fiscal_number": "FN123", "fiscal_document": "FD456", "fiscal_sign": "FS789",
  "amount": 20000.0, "status": "succeeded"
}
```

**404** — чек ещё не готов (receipt webhook формируется 1–30 мин после оплаты). Фронт: «Чек формируется», retry через 30 сек.

---

## 7. ЛК: Коллеги

> Auth: JWT, роль `doctor`, **активная подписка обязательна** (иначе 403).

| Метод | Путь | Query | Описание |
|-------|------|-------|----------|
| GET | `/colleagues` | `limit` (50), `offset`, `search` (мин 2) | Список врачей с контактами |

**Ответ:**
```json
{
  "data": [{
    "id": "uuid", "first_name": "Иван", "last_name": "Петров",
    "middle_name": "Сергеевич", "city": "Москва", "specialization": "Трихология",
    "photo_url": "https://...", "public_phone": "+7...", "public_email": "...",
    "colleague_contacts": "Telegram: @petrov, WhatsApp: +7..."
  }],
  "total": 42, "limit": 50, "offset": 0
}
```

---

## 8. ЛК: Сертификаты

> Auth: JWT, роль `doctor`.

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/certificates` | Список сертификатов |
| GET | `/certificates/{id}/download` | Presigned URL для скачивания |

Member-сертификаты видны только при **активной подписке**.

---

## 9. ЛК: Telegram

> Auth: JWT, роль `doctor`.

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/telegram/binding` | Статус привязки |
| POST | `/telegram/generate-code` | Генерация кода привязки |

**GET `/telegram/binding`:** `{ is_linked: bool, tg_username: "...", is_in_channel: bool }`.

**POST `/telegram/generate-code`:** `{ auth_code: "ABC123", expires_at: "...", bot_link: "https://t.me/...", instruction: "..." }`.

---

## 10. ЛК: Голосование

> Auth: JWT, роль `doctor`.

| Метод | Путь | Body | Описание |
|-------|------|------|----------|
| GET | `/voting/active` | — | Текущая активная сессия |
| POST | `/voting/{session_id}/vote` | `{ candidate_id: "uuid" }` | Отдать голос |

**GET `/voting/active`:** `{ id, title, description, starts_at, ends_at, candidates: [...], has_voted: bool }`.

---

## 11. Регистрация на мероприятия

### POST `/events/{event_id}/register`

**Body:**
```json
{
  "tariff_id": "uuid",
  "idempotency_key": "uuid-v4",
  "guest_email": "user@example.com",
  "guest_full_name": "Иван Иванов",
  "guest_workplace": "Клиника А",
  "guest_specialization": "Трихология",
  "fiscal_email": "user@example.com"
}
```

**3 сценария по значению `action` в ответе:**

| Сценарий | Условие | `action` | Что делать |
|----------|---------|----------|------------|
| 1 | JWT передан | `null` | Есть `payment_url` → redirect на оплату |
| 2 | Без JWT, email есть в базе | `verify_existing` | Показать форму логина. После логина — повторить запрос с JWT |
| 3 | Без JWT, новый email | `verify_new_email` | Показать ввод 6-значного кода из email |

### POST `/events/{event_id}/confirm-guest-registration`

**Body (после сценария 3):**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "tariff_id": "uuid",
  "idempotency_key": "uuid-v4",
  "guest_full_name": "Иван Иванов"
}
```

**Ответ:** `{ registration_id, payment_url, applied_price, is_member_price }`.

**`is_member_price`:** `true` — врач с активной подпиской, применена льготная цена `member_price`. `false` — полная цена.

**Ошибки:**

| Сообщение | Действие |
|-----------|----------|
| "No seats available for this tariff" | «Места закончились» |
| "Invalid verification code. N attempt(s) remaining." | Показать оставшиеся попытки |
| "Verification code expired..." | «Код истёк», кнопка «Отправить новый» |
| "Too many verification attempts..." | «Запросите новый код» |
| "Too many verification codes sent..." | «Попробуйте позже» |
| "Registration is closed for this event" | Disable кнопку |

---

## 12. Оплата через Moneta — redirect flow

### Порядок

1. `POST /subscriptions/pay` (или регистрация на мероприятие) → получить `payment_url`.
2. `window.location.href = payment_url` — пользователь уходит на Moneta.
3. Оплата на стороне Moneta.
4. Redirect на `MONETA_SUCCESS_URL` (успех) или `MONETA_FAIL_URL` (отмена).
5. Webhook приходит **асинхронно** — подписка может обновиться не сразу.

### Страница `/payment/success`

1. Показать «Оплата прошла, обрабатываем…».
2. Polling `GET /subscriptions/status` каждые 2–3 сек (максимум 30 сек).
3. Когда `has_subscription=true`, `current_subscription.status="active"` → «Подписка активирована!».
4. Таймаут → «Обработка может занять несколько минут».

### Страница `/payment/fail`

1. «Оплата не прошла».
2. Кнопка «Попробовать снова» → вернуть на страницу оплаты.

### Чеки

Фискальный чек формируется **через 1–30 мин** после оплаты. Бекенд отправляет email со ссылкой на чек. Чек также доступен через `GET /subscriptions/payments/{id}/receipt`.

---

## 13. Карта страниц → эндпоинты

| Страница | Эндпоинты |
|----------|-----------|
| Главная | `GET /events?period=upcoming&limit=4`, `GET /articles?limit=3`, `GET /seo/home`, `GET /settings/public` |
| Каталог врачей | `GET /doctors`, `GET /cities?with_doctors=true` |
| Профиль врача | `GET /doctors/{slug}` |
| Город | `GET /cities/{slug}`, `GET /doctors?city_slug={slug}` |
| Мероприятия | `GET /events?period=upcoming` |
| Мероприятие | `GET /events/{slug}`, `POST /events/{id}/register`, `POST /events/{id}/confirm-guest-registration` |
| Статьи | `GET /articles`, `GET /article-themes` |
| Статья | `GET /articles/{slug}` |
| Документы | `GET /organization-documents` |
| Регистрация | `POST /auth/register` |
| Вход | `POST /auth/login` |
| ЛК: Подписка | `GET /subscriptions/status`, `POST /subscriptions/pay` |
| ЛК: Платежи | `GET /subscriptions/payments`, `GET .../receipt` |
| ЛК: Коллеги | `GET /colleagues` |
| ЛК: Профиль | `GET /profile/personal`, `GET /profile/public`, `PATCH ...`, `POST /profile/photo` |
| ЛК: Мои мероприятия | `GET /profile/events` |
| ЛК: Сертификаты | `GET /certificates` |
| ЛК: Telegram | `GET /telegram/binding`, `POST /telegram/generate-code` |
| ЛК: Голосование | `GET /voting/active`, `POST /voting/{id}/vote` |
| Онбординг | `GET /onboarding/status`, `POST /onboarding/choose-role`, `PATCH /onboarding/doctor-profile`, `POST /onboarding/documents`, `POST /onboarding/submit` |
| Оплата (success/fail) | Polling `GET /subscriptions/status` |

---

## Enum-справочник

| Группа | Значения |
|--------|----------|
| Subscription status | `pending_payment`, `active`, `expired` |
| Payment status | `pending`, `succeeded`, `failed`, `refunded` |
| Product type | `entry_fee`, `subscription`, `event` |
| next_action | `pay_entry_fee_and_subscription`, `pay_subscription`, `renew`, `complete_payment`, `null` |
| Moderation status | `pending_review`, `approved`, `rejected` |
| Doctor status | `pending_review`, `approved`, `active`, `inactive` |
| Event status | `upcoming`, `ongoing`, `finished`, `cancelled` |
| Registration status | `pending`, `confirmed`, `cancelled` |
| Document type | `medical_diploma`, `retraining_cert`, `oncology_cert`, `additional_cert` |
| Access level (gallery/recording) | `public`, `members_only`, `participants_only` |
