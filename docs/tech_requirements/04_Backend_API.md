# Техническое задание: Backend и API

## Проект: «Ассоциация трихологов»

> **Актуализировано 2026-03-12.** Бекенд полностью реализован и задеплоен.
> Swagger (тест): `https://trihoback.mediann.dev/docs`
> Справочные документы: `docs/FRONTEND_API_HANDOFF.md`, `docs/BACKEND_VS_SPEC_GAP_ANALYSIS.md`

---

## 1. Общая архитектура

### 1.1 Стек технологий

| Компонент        | Технология              | Обоснование                                                                           |
|------------------|-------------------------|---------------------------------------------------------------------------------------|
| Язык             | Python 3.12+            | Зрелая экосистема, типизация, быстрая разработка, отличная поддержка async            |
| Фреймворк        | FastAPI 0.115+          | Async из коробки, автогенерация OpenAPI, Pydantic-валидация, dependency injection     |
| БД               | PostgreSQL 16+          | Надёжность, JSON-поддержка, полнотекстовый поиск, CTE, оконные функции               |
| ORM              | SQLAlchemy 2.0 + Alembic| Декларативные модели, async-драйвер (asyncpg), миграции                               |
| Очереди задач    | TaskIQ + Redis          | Отложенные задачи (уведомления, генерация PDF), cron-расписание через TaskIQ Scheduler |
| Кеш              | Redis 7+                | Кеш сессий, rate limiting, кеш публичных страниц, брокер для TaskIQ                    |
| Файловое хранилище | S3-совместимое (MinIO / Yandex Object Storage) | Масштабируемость, presigned URL, CDN-ready          |
| Email            | SMTP (любой провайдер)  | Через aiosmtplib для async-отправки или TaskIQ-задачи                                 |
| PDF-генерация    | WeasyPrint / reportlab  | Генерация сертификатов из HTML-шаблонов                                               |
| Контейнеризация  | Docker + docker-compose | Единообразное окружение, простота деплоя                                              |

### 1.2 Структура модулей

```
app/
├── main.py                  # Точка входа FastAPI
├── core/
│   ├── config.py            # Настройки приложения (pydantic-settings)
│   ├── security.py          # JWT, хеширование паролей, RBAC
│   ├── database.py          # Async-сессия SQLAlchemy
│   ├── dependencies.py      # Общие Depends (текущий пользователь, роли)
│   ├── exceptions.py        # Кастомные исключения и обработчики
│   └── pagination.py        # Общая логика пагинации
├── models/                  # SQLAlchemy-модели (1 файл на таблицу или группу)
├── schemas/                 # Pydantic-схемы (request / response)
├── api/
│   └── v1/
│       ├── auth.py
│       ├── onboarding.py
│       ├── doctors_admin.py
│       ├── doctors_public.py
│       ├── profile.py
│       ├── subscriptions.py
│       ├── events_admin.py
│       ├── events_public.py
│       ├── payments.py
│       ├── content.py
│       ├── certificates.py
│       ├── notifications.py
│       ├── telegram.py
│       ├── dashboard.py
│       └── voting.py
├── services/                # Бизнес-логика (1 сервис на домен)
│   ├── auth_service.py
│   ├── doctor_service.py
│   ├── subscription_service.py
│   ├── payment_service.py
│   ├── event_service.py
│   ├── moderation_service.py
│   ├── notification_service.py
│   ├── telegram_service.py
│   ├── certificate_service.py
│   ├── file_service.py
│   └── voting_service.py
├── tasks/                   # TaskIQ-задачи
│   ├── notifications.py
│   ├── subscriptions.py
│   ├── certificates.py
│   └── telegram.py
└── utils/
    ├── email.py
    ├── excel.py
    └── seo.py
```

### 1.3 Авторизация

**Подход:** JWT (access + refresh tokens), stateless.

| Параметр               | Значение                      |
|------------------------|-------------------------------|
| Access Token TTL       | 15 минут                      |
| Refresh Token TTL      | 30 дней                       |
| Алгоритм подписи       | RS256 (асимметричные ключи)   |
| Хранение refresh token | HttpOnly Secure cookie + запись в Redis (для возможности отзыва) |
| Хеширование паролей    | Argon2id                      |

**Структура JWT payload (access token):**
```json
{
  "sub": "uuid-пользователя",
  "roles": ["doctor"],
  "email_verified": true,
  "exp": 1700000000,
  "iat": 1699999100,
  "jti": "unique-token-id"
}
```

**Logout:** refresh token удаляется из Redis и из cookie. Access token остаётся валиден до истечения TTL (15 мин) — приемлемое окно.

### 1.4 Ролевая модель — матрица доступов

Роли: **Admin**, **Manager**, **Accountant**, **Doctor**, **NonDoctor**, **Guest** (неавторизованный).

| Ресурс / Действие                              | Admin | Manager | Accountant | Doctor | NonDoctor | Guest |
|-------------------------------------------------|:-----:|:-------:|:----------:|:------:|:---------:|:-----:|
| **Управление врачами** (список, карточка, модерация) | ✓     | ✓       |            |        |           |       |
| Активация/деактивация профиля врача              | ✓     | ✓       |            |        |           |       |
| Импорт врачей из Excel                           | ✓     |         |            |        |           |       |
| **Платежи** — полный список                      | ✓     | ✓       | ✓          |        |           |       |
| **Платежи** — только свои                        |       |         |            | ✓      |           |       |
| **Чеки** — скачивание                            | ✓     | ✓       | ✓          | ✓*     |           |       |
| **Мероприятия** — CRUD                           | ✓     | ✓       |            |        |           |       |
| **Мероприятия** — просмотр                       | ✓     | ✓       | ✓          | ✓      | ✓         | ✓     |
| **Мероприятия** — регистрация и оплата           | ✓     | ✓       |            | ✓      |           | ✓**   |
| **Контент** (статьи, документы орг., SEO)        | ✓     | ✓       |            |        |           |       |
| **Контент** — чтение публичного                  | ✓     | ✓       | ✓          | ✓      | ✓         | ✓     |
| **Управление городами**                          | ✓     | ✓       |            |        |           |       |
| **Управление тарифами подписок**                 | ✓     |         |            |        |           |       |
| **Профиль врача** — свой                         |       |         |            | ✓      |           |       |
| **Подписка** — своя                              |       |         |            | ✓      |           |       |
| **Сертификат** — свой                            |       |         |            | ✓      |           |       |
| **Голосование** — создание/управление            | ✓     |         |            |        |           |       |
| **Голосование** — голосовать                     |       |         |            | ✓      |           |       |
| **Telegram** — привязка                          |       |         |            | ✓      |           |       |
| **Дашборд**                                      | ✓     | ✓       |            |        |           |       |
| **Уведомления** — ручная отправка                | ✓     | ✓       |            |        |           |       |
| **Уведомления** — лог                            | ✓     | ✓       |            |        |           |       |
| **Настройки** (Telegram-ссылка, контакты)        | ✓     |         |            |        |           |       |
| **Каталог врачей** — публичный                   | ✓     | ✓       | ✓          | ✓      | ✓         | ✓     |

*Только свои чеки. **По обычной цене, с заполнением формы.

### 1.5 Общие соглашения API

- **Базовый путь:** `/api/v1/`
- **Формат:** JSON (application/json), multipart/form-data для загрузки файлов
- **Пагинация:** единый стандарт — `limit` + `offset` для всех list-эндпоинтов (публичных и административных)
- **Формат даты:** ISO 8601 (`2026-03-02T14:30:00Z`)
- **Формат ошибок:**

```json
{
  "error": {
    "code": "HUMAN_READABLE_ERROR_CODE",
    "message": "Описание ошибки на русском для отображения пользователю",
    "details": {}
  }
}
```

- **Формат пагинированного ответа:**

```json
{
  "data": [],
  "total": 150,
  "limit": 20,
  "offset": 0
}
```

- **HTTP-коды:**
  - 200 — успех (GET, PUT, PATCH)
  - 201 — создано (POST)
  - 204 — успех без тела (DELETE)
  - 400 — ошибка валидации
  - 401 — не авторизован
  - 403 — нет прав
  - 404 — не найдено
  - 409 — конфликт (дублирование)
  - 422 — бизнес-правило нарушено
  - 429 — rate limit
  - 500 — внутренняя ошибка

---

## 2. API эндпоинты

---

### AUTH

---

#### POST /api/v1/auth/register

**Назначение:** Регистрация нового пользователя  
**Доступ:** Guest

**Request body:**
```json
{
  "email": "string (required, unique, email format)",
  "password": "string (required, min 8, max 128, 1 цифра + 1 буква)"
}
```

**Response 201:**
```json
{
  "message": "Письмо с подтверждением отправлено на указанный email"
}
```

**Response 409:**
```json
{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "Пользователь с таким email уже зарегистрирован"
  }
}
```

**Бизнес-логика:**
1. Проверить уникальность email (case-insensitive, trim + lowercase)
2. Валидировать сложность пароля
3. Хешировать пароль (Argon2id)
4. Создать запись в `users` с `email_verified_at = NULL`
5. Сгенерировать токен подтверждения (UUID v4, сохранить в Redis, TTL 24ч)
6. Отправить email с ссылкой `{FRONTEND_URL}/verify-email?token={token}`
7. Rate limit: 3 запроса/мин на один IP

---

#### POST /api/v1/auth/verify-email

**Назначение:** Подтверждение email по токену из письма  
**Доступ:** Guest

**Request body:**
```json
{
  "token": "string (required, UUID)"
}
```

**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": {
    "id": "uuid",
    "email": "string",
    "roles": [],
    "has_chosen_role": false
  }
}
```

**Response 400:**
```json
{
  "error": {
    "code": "INVALID_OR_EXPIRED_TOKEN",
    "message": "Ссылка недействительна или устарела"
  }
}
```

**Бизнес-логика:**
1. Найти токен в Redis
2. Найти пользователя по token → user_id
3. Установить `email_verified_at = now()`
4. Удалить токен из Redis
5. Выдать JWT-пару (access + refresh)
6. Вернуть информацию о пользователе

---

#### POST /api/v1/auth/login

**Назначение:** Вход в систему  
**Доступ:** Guest

**Request body:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Response 200:**
```json
{
  "access_token": "string",
  "user": {
    "id": "uuid",
    "email": "string",
    "roles": ["doctor"],
    "email_verified": true,
    "has_chosen_role": true,
    "onboarding_completed": true,
    "moderation_status": "approved"
  }
}
```

**Response headers:** `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`

**Response 401:**
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный email или пароль"
  }
}
```

**Бизнес-логика:**
1. Найти пользователя по email (case-insensitive)
2. Проверить пароль через Argon2id verify
3. Проверить `is_active = true` (иначе `ACCOUNT_DEACTIVATED`)
4. Обновить `last_login_at`
5. Выдать access token (в body) + refresh token (в HttpOnly cookie + Redis)
6. Rate limit: 5 попыток/мин на один email, 20/мин на один IP

---

#### POST /api/v1/auth/refresh

**Назначение:** Обновление access token по refresh token  
**Доступ:** Авторизованный (cookie)

**Request:** Refresh token из HttpOnly cookie

**Response 200:**
```json
{
  "access_token": "string"
}
```

**Response headers:** `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict` (ротация)

**Response 401:**
```json
{
  "error": {
    "code": "INVALID_REFRESH_TOKEN",
    "message": "Сессия истекла, войдите заново"
  }
}
```

**Бизнес-логика:**
1. Извлечь refresh token из cookie
2. Проверить наличие в Redis (не отозван)
3. Верифицировать подпись и срок
4. Выдать новый access token
5. Ротация: выдать новый refresh token, старый удалить из Redis (Refresh Token Rotation)

---

#### POST /api/v1/auth/logout

**Назначение:** Выход из системы  
**Доступ:** Авторизованный

**Response 204:** (no content)

**Бизнес-логика:**
1. Извлечь refresh token из cookie
2. Удалить из Redis
3. Очистить cookie: `Set-Cookie: refresh_token=; Max-Age=0`

---

#### POST /api/v1/auth/forgot-password

**Назначение:** Запрос сброса пароля  
**Доступ:** Guest

**Request body:**
```json
{
  "email": "string (required)"
}
```

**Response 200:**
```json
{
  "message": "Если аккаунт существует, письмо с инструкцией отправлено"
}
```

**Бизнес-логика:**
1. Найти пользователя по email
2. Если не найден — всё равно вернуть 200 (защита от перебора)
3. Сгенерировать токен (UUID v4, Redis, TTL 1ч)
4. Отправить email с ссылкой `{FRONTEND_URL}/reset-password?token={token}`
5. Rate limit: 3 запроса/час на один email

---

#### POST /api/v1/auth/reset-password

**Назначение:** Установка нового пароля по токену сброса  
**Доступ:** Guest

**Request body:**
```json
{
  "token": "string (required, UUID)",
  "password": "string (required, min 8)"
}
```

**Response 200:**
```json
{
  "message": "Пароль успешно изменён"
}
```

**Бизнес-логика:**
1. Найти токен в Redis → user_id
2. Хешировать новый пароль
3. Обновить `users.password_hash`
4. Удалить токен из Redis
5. Отозвать все refresh-токены пользователя (удалить из Redis по паттерну `refresh:{user_id}:*`)

---

#### POST /api/v1/auth/change-password

**Назначение:** Смена пароля из ЛК  
**Доступ:** Авторизованный (любая роль)

**Request headers:** `Authorization: Bearer {access_token}`

**Request body:**
```json
{
  "current_password": "string (required)",
  "new_password": "string (required, min 8)"
}
```

**Response 200:**
```json
{
  "message": "Пароль успешно изменён"
}
```

**Response 400:**
```json
{
  "error": {
    "code": "WRONG_CURRENT_PASSWORD",
    "message": "Текущий пароль указан неверно"
  }
}
```

**Бизнес-логика:**
1. Верифицировать `current_password` против хеша в БД
2. Проверить что `new_password != current_password`
3. Хешировать и обновить
4. Отозвать все refresh-токены кроме текущего

---

#### POST /api/v1/auth/change-email

**Назначение:** Запрос смены email  
**Доступ:** Авторизованный

**Request body:**
```json
{
  "new_email": "string (required, email format)",
  "password": "string (required)"
}
```

**Response 200:**
```json
{
  "message": "Письмо с подтверждением отправлено на новый email"
}
```

**Бизнес-логика:**
1. Верифицировать пароль
2. Проверить уникальность нового email
3. Сгенерировать токен подтверждения (Redis, TTL 24ч, связь: token → {user_id, new_email})
4. Отправить на **новый** email ссылку подтверждения

---

#### POST /api/v1/auth/confirm-email-change

**Назначение:** Подтверждение смены email по токену  
**Доступ:** Guest (по токену)

**Request body:**
```json
{
  "token": "string (required)"
}
```

**Response 200:**
```json
{
  "message": "Email успешно изменён"
}
```

**Бизнес-логика:**
1. Найти токен в Redis → {user_id, new_email}
2. Повторно проверить уникальность new_email
3. Обновить `users.email`
4. Удалить токен
5. Отозвать все refresh-токены

---

### ONBOARDING

---

#### POST /api/v1/onboarding/choose-role

**Назначение:** Выбор роли после подтверждения email (врач / не-врач)  
**Доступ:** Авторизованный, email подтверждён, роль ещё не выбрана

**Request body:**
```json
{
  "role": "string (required, enum: doctor | non_doctor)"
}
```

**Response 200 (role=doctor):**
```json
{
  "next_step": "fill_profile",
  "message": "Заполните анкету врача для прохождения модерации"
}
```

**Response 200 (role=non_doctor):**
```json
{
  "next_step": "wait",
  "message": "Ваши данные сохранены. Мы уведомим вас, когда для вашей роли откроется дополнительный функционал"
}
```

**Response 409:**
```json
{
  "error": {
    "code": "ROLE_ALREADY_CHOSEN",
    "message": "Роль уже выбрана"
  }
}
```

**Бизнес-логика:**
1. Проверить что у пользователя нет ролей doctor/non_doctor
2. Добавить запись в `user_roles`
3. Если role=doctor → создать `doctor_profiles` с `moderation_status_id = 'new'`
4. Если role=non_doctor → только добавить роль, больше ничего

---

#### PATCH /api/v1/onboarding/doctor-profile

**Назначение:** Заполнение анкеты врача (шаг онбординга)  
**Доступ:** Doctor, moderation_status = 'new'

**Request body:**
```json
{
  "first_name": "string (required, max 100)",
  "last_name": "string (required, max 100)",
  "middle_name": "string (optional, max 100)",
  "phone": "string (required, формат +7XXXXXXXXXX)",
  "passport_data": "string (optional)",
  "city_id": "uuid (required)",
  "clinic_name": "string (optional, max 255)",
  "position": "string (optional, max 255)",
  "specialization": "string (optional, max 255)",
  "academic_degree": "string (optional, max 255)"
}
```

**Response 200:**
```json
{
  "profile_id": "uuid",
  "moderation_status": "new",
  "next_step": "upload_documents",
  "message": "Анкета сохранена. Загрузите необходимые документы"
}
```

**Бизнес-логика:**
1. Валидировать city_id (существует и is_active=true)
2. Обновить `doctor_profiles`
3. Зашифровать `passport_data` перед сохранением (AES-256-GCM, ключ из env)
4. Статус модерации остаётся `new` до загрузки документов

---

#### POST /api/v1/onboarding/documents

**Назначение:** Загрузка документов врача  
**Доступ:** Doctor, moderation_status IN ('new', 'rejected')

**Request:** `multipart/form-data`

| Поле             | Тип    | Обязательность | Описание                                   |
|------------------|--------|----------------|--------------------------------------------|
| document_type_id | int    | required       | ID типа документа                          |
| file             | file   | required       | Файл (PDF, JPG, PNG, max 10MB)            |

**Response 201:**
```json
{
  "document": {
    "id": "uuid",
    "document_type": {
      "id": 1,
      "code": "medical_diploma",
      "title": "Диплом о высшем медицинском образовании"
    },
    "original_filename": "diploma.pdf",
    "moderation_status": "new",
    "uploaded_at": "2026-03-02T14:30:00Z"
  }
}
```

**Response 400:**
```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Допустимые форматы: PDF, JPG, PNG"
  }
}
```

**Бизнес-логика:**
1. Валидация: тип файла (по magic bytes, не только расширению), размер ≤ 10MB
2. Загрузить файл в S3: `doctors/{user_id}/documents/{uuid}.{ext}`
3. Создать запись в `doctor_documents`
4. Если загружен `medical_diploma` → установить `doctor_profiles.has_medical_diploma = true`
5. Вернуть информацию о загруженном документе

---

#### POST /api/v1/onboarding/submit

**Назначение:** Отправка заявки на модерацию  
**Доступ:** Doctor, moderation_status = 'new', анкета заполнена

**Response 200:**
```json
{
  "moderation_status": "pending",
  "message": "Заявка отправлена на модерацию. Мы уведомим вас о результате"
}
```

**Response 422:**
```json
{
  "error": {
    "code": "MEDICAL_DIPLOMA_REQUIRED",
    "message": "Для отправки заявки необходимо загрузить диплом о высшем медицинском образовании"
  }
}
```

**Бизнес-логика:**
1. Проверить заполненность обязательных полей анкеты (first_name, last_name, phone, city_id)
2. Проверить наличие всех required-документов (medical_diploma)
3. Перевести `moderation_status_id` → `pending`
4. Создать запись в `moderation_history`
5. Отправить уведомление администраторам (email + Telegram-бот)

---

#### GET /api/v1/onboarding/status

**Назначение:** Получение текущего шага онбординга  
**Доступ:** Авторизованный

**Response 200:**
```json
{
  "email_verified": true,
  "role_chosen": true,
  "role": "doctor",
  "profile_filled": true,
  "documents_uploaded": true,
  "has_medical_diploma": true,
  "moderation_status": "pending",
  "submitted_at": "2026-03-02T14:30:00Z",
  "rejection_comment": null,
  "next_step": "await_moderation"
}
```

**Бизнес-логика:**
1. Собрать текущее состояние из `users`, `user_roles`, `doctor_profiles`, `doctor_documents`
2. Определить `next_step`: `verify_email` → `choose_role` → `fill_profile` → `upload_documents` → `submit` → `await_moderation` → `pay_entry_fee` → `completed`

---

### DOCTORS (Admin)

---

#### GET /api/v1/admin/doctors

**Назначение:** Список врачей с фильтрами и пагинацией  
**Доступ:** Admin, Manager

**Query params:**

| Параметр          | Тип    | Default | Описание                                                |
|-------------------|--------|---------|----------------------------------------------------------|
| limit             | int    | 20      | Кол-во записей (max 100)                                 |
| offset         | int    | 0       | Смещение                                                 |
| status            | string | —       | Фильтр по doctor_status: pending_review, approved, rejected, active, deactivated |
| subscription_status | string | —     | active, expired, expiring_soon, never                    |
| city_id           | uuid   | —       | Фильтр по городу                                        |
| has_pending_draft | bool   | —       | true — только врачи с ожидающими модерации изменениями   |
| has_data_changed  | bool   | —       | true — подсказка: врачи, у которых изменились данные (для проверки) |
| search            | string | —       | Поиск по ФИО, email, городу (min 2 символа)              |
| sort_by           | string | created_at | created_at, last_name, subscription_ends_at          |
| sort_order        | string | desc    | asc / desc                                               |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "email": "doctor@example.com",
      "first_name": "Иван",
      "last_name": "Петров",
      "middle_name": "Сергеевич",
      "phone": "+79001234567",
      "city": { "id": "uuid", "name": "Москва" },
      "specialization": "Трихология",
      "moderation_status": "approved",
      "is_public": true,
      "has_medical_diploma": true,
      "subscription": {
        "status": "active",
        "ends_at": "2027-03-02T00:00:00Z",
        "plan_name": "Ежегодный членский взнос"
      },
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": ..., "limit": 20, "offset": 0
}
```

**Бизнес-логика:**
1. JOIN `doctor_profiles` + `users` + `cities` + последняя `subscriptions`
2. Применить фильтры
3. `subscription_status=expiring_soon` → ends_at BETWEEN now() AND now() + 7 days
4. `search` → ILIKE по last_name, first_name, email, city.name

---

#### GET /api/v1/admin/doctors/{doctor_profile_id}

**Назначение:** Детальная карточка врача  
**Доступ:** Admin, Manager

**Response 200:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "email": "doctor@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "phone": "+79001234567",
  "passport_data": "серия **** номер ******",
  "city": { "id": "uuid", "name": "Москва" },
  "clinic_name": "Клиника А",
  "position": "Врач-трихолог",
  "specialization": "Трихология",
  "academic_degree": "к.м.н.",
  "bio": "Краткое описание",
  "public_email": "public@example.com",
  "public_phone": "+79001234567",
  "photo_url": "https://storage.example.com/...",
  "is_public": true,
  "moderation_status": "approved",
  "has_medical_diploma": true,
  "documents": [
    {
      "id": "uuid",
      "type": { "code": "medical_diploma", "title": "Диплом" },
      "original_filename": "diploma.pdf",
      "file_url": "presigned-url",
      "moderation_status": "approved",
      "uploaded_at": "2026-01-15T10:00:00Z"
    }
  ],
  "subscription": {
    "id": "uuid",
    "status": "active",
    "plan": { "code": "annual_fee", "name": "Ежегодный" },
    "starts_at": "2026-03-02T00:00:00Z",
    "ends_at": "2027-03-02T00:00:00Z"
  },
  "payments": [
    {
      "id": "uuid",
      "amount": 5000.00,
      "product_type": "entry_fee",
      "status": "completed",
      "paid_at": "2026-01-20T12:00:00Z"
    }
  ],
  "pending_draft": null,
  "moderation_history": [
    {
      "id": "uuid",
      "admin_email": "admin@example.com",
      "from_status": "pending",
      "to_status": "approved",
      "comment": null,
      "created_at": "2026-01-16T15:00:00Z"
    }
  ],
  "created_at": "2026-01-15T10:00:00Z"
}
```

**Бизнес-логика:**
1. Загрузить профиль со всеми связями
2. Для `documents.file_url` генерировать presigned URL (TTL 10 мин)
3. Passport data расшифровывается и маскируется для Manager (полный доступ только Admin)

---

#### POST /api/v1/admin/doctors/{doctor_profile_id}/moderate

**Назначение:** Одобрение или отклонение заявки врача  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "action": "string (required, enum: approve | reject)",
  "comment": "string (optional, required if reject)"
}
```

**Response 200:**
```json
{
  "moderation_status": "approved",
  "message": "Врач одобрен"
}
```

**Бизнес-логика:**
1. Проверить текущий статус = `pending`
2. Обновить `moderation_status_id` → `approved` / `rejected`
3. Создать запись в `moderation_history`
4. **При approve:**
   - Генерировать сертификат (TaskIQ-задача)
   - Отправить уведомление врачу (email + Telegram): «Заявка одобрена, оплатите вступительный взнос»
5. **При reject:**
   - Обязателен `comment`
   - Отправить уведомление с причиной отказа
   - Врач может исправить документы и повторно подать

---

#### POST /api/v1/admin/doctors/{doctor_profile_id}/toggle-active

**Назначение:** Ручная активация/деактивация профиля врача  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "is_public": "boolean (required)"
}
```

**Response 200:**
```json
{
  "is_public": false,
  "message": "Профиль деактивирован"
}
```

**Бизнес-логика:**
1. Обновить `doctor_profiles.is_public`
2. Создать запись в `moderation_history` (entity_type = 'doctor_profile', action logged)
3. Если деактивация → удалить из Telegram-канала (TaskIQ-задача)

---

#### POST /api/v1/admin/doctors/{doctor_profile_id}/approve-draft

**Назначение:** Одобрение/отклонение изменений профиля врача  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "action": "string (required, enum: approve | reject)",
  "comment": "string (required при action=reject)"
}
```

**Response 200:**
```json
{
  "message": "Изменения одобрены и применены к профилю"
}
```

**Response 400** (при action=reject без comment):
```json
{
  "error": {
    "code": "REJECTION_COMMENT_REQUIRED",
    "message": "При отклонении необходимо указать причину"
  }
}
```

**Response 404:**
```json
{
  "error": {
    "code": "NO_PENDING_DRAFT",
    "message": "Нет ожидающих изменений"
  }
}
```

**Бизнес-логика:**
1. Найти `doctor_profile_changes` (или `doctor_profile_drafts`) со status=`pending` для данного профиля
2. **При approve:**
   - Скопировать ненулевые поля из draft → `doctor_profiles`
   - Установить draft.status = `approved`, reviewed_at, reviewed_by
   - Создать запись в `moderation_history`
3. **При reject:**
   - Проверить: `comment` обязателен, иначе 400
   - Сохранить `rejection_reason` в `doctor_profile_changes`
   - draft.status = `rejected`, reviewed_at, reviewed_by
   - Отправить уведомление врачу (email + Telegram) с шаблоном `profile_change_rejected`, переменные: `{full_name}`, `{rejection_reason}`, `{profile_url}`

---

#### POST /api/v1/admin/doctors/{doctor_profile_id}/send-reminder

**Назначение:** Ручная отправка напоминания об оплате врачу  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "message": "string (optional, кастомный текст)"
}
```

**Response 200:**
```json
{
  "message": "Напоминание отправлено"
}
```

**Бизнес-логика:**
1. Найти врача и его контакты
2. Создать запись в `notifications` (type=`manual_reminder`)
3. Отправить email + Telegram (если привязан)

---

#### POST /api/v1/admin/doctors/{doctor_profile_id}/send-email

**Назначение:** Отправка произвольного email врачу  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "subject": "string (required, max 255)",
  "body": "string (required, HTML)"
}
```

**Response 200:**
```json
{
  "message": "Письмо отправлено"
}
```

---

#### POST /api/v1/admin/doctors/import

**Назначение:** Импорт врачей из Excel-файла  
**Доступ:** Admin

**Request:** `multipart/form-data`

| Поле | Тип  | Описание                                 |
|------|------|------------------------------------------|
| file | file | Excel-файл (.xlsx, max 5MB)              |

**Response 202:**
```json
{
  "task_id": "uuid",
  "message": "Импорт запущен. Результат будет доступен по task_id"
}
```

**Бизнес-логика:**
1. Валидировать файл (формат, размер)
2. Запустить TaskIQ-задачу для обработки
3. Задача парсит Excel, для каждой строки:
   - Создаёт `users` с временным паролем
   - Создаёт `user_roles(doctor)`
   - Создаёт `doctor_profiles` с `moderation_status = approved`
   - Отправляет email с временным паролем
4. Результат (успех/ошибки по строкам) сохраняется в Redis по task_id

---

#### GET /api/v1/admin/doctors/import/{task_id}

**Назначение:** Получение статуса импорта  
**Доступ:** Admin

**Response 200:**
```json
{
  "status": "completed",
  "total_rows": 50,
  "imported": 47,
  "errors": [
    { "row": 12, "error": "Дублирующий email: test@test.com" },
    { "row": 23, "error": "Некорректный формат телефона" },
    { "row": 45, "error": "Город не найден: Нижнекамск" }
  ]
}
```

---

### PORTAL USERS (Admin)

---

#### GET /api/v1/admin/portal-users

**Назначение:** Список всех пользователей портала (врачи, не-врачи, без онбординга) с фильтрами и пагинацией  
**Доступ:** Admin, Manager

**Query params:**

| Параметр           | Тип    | Default     | Описание                                                      |
|--------------------|--------|-------------|---------------------------------------------------------------|
| limit           | int    | 20          | Кол-во на страницу (max 100)                                  |
| role               | string | all         | Фильтр: all / doctor / user / no_role                         |
| onboarding_status  | string | —           | completed / partial / none (для doctor — этапы онбординга)   |
| search             | string | —           | Поиск по email, ФИО (min 2 символа)                           |
| sort_by            | string | created_at  | created_at, last_name, last_payment_at                        |
| sort_order         | string | desc        | asc / desc                                                    |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "Иван Петров",
      "role": "doctor",
      "role_display": "Врач",
      "onboarding_status": "completed",
      "doctor_profile_id": "uuid",
      "subscription": {
        "status": "active",
        "ends_at": "2027-03-02T00:00:00Z"
      },
      "last_payment": {
        "id": "uuid",
        "created_at": "2026-02-01T12:00:00Z",
        "product_type": "subscription",
        "amount": 3000,
        "status": "succeeded"
      },
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": ..., "limit": 20, "offset": 0
}
```

**Бизнес-логика:**
1. Выборка из `users` + `user_roles` (исключая admin, manager, accountant)
2. Для doctor — JOIN `doctor_profiles`, `subscriptions`; для user — только базовая информация
3. `last_payment` — последний платёж из `payments` (status=succeeded) по user_id, ORDER BY created_at DESC LIMIT 1
4. `role=no_role` — пользователи без ролей doctor/user (только базовые роли или пусто)
5. `search` → ILIKE по email, last_name, first_name (из users или doctor_profiles)

---

#### GET /api/v1/admin/portal-users/{user_id}

**Назначение:** Детальная карточка пользователя портала с роль-зависимыми блоками  
**Доступ:** Admin, Manager

**Response 200** — составной объект. Структура зависит от роли пользователя.

**Общие поля (всегда):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-01-15T10:00:00Z",
  "last_login_at": "2026-03-01T14:00:00Z",
  "role": "doctor",
  "role_display": "Врач",
  "last_payment": {
    "id": "uuid",
    "created_at": "2026-02-01T12:00:00Z",
    "product_type": "subscription",
    "amount": 3000,
    "status": "succeeded"
  },
  "payments": [
    {
      "id": "uuid",
      "amount": 5000.00,
      "product_type": "entry_fee",
      "status": "succeeded",
      "created_at": "2026-01-20T12:00:00Z"
    }
  ]
}
```

**Дополнительно для role=doctor:**
- `doctor_profile`: полные данные из `doctor_profiles` (ФИО, телефон, паспорт, город, клиника, специализация, модерация, документы)
- `subscription`: текущая подписка (план, даты, статус)
- `doctor_profile_id`: ссылка на карточку врача `/admin/doctors/{doctor_profile_id}`

**Дополнительно для role=user (не-врач):**
- `full_name`: из event_registrations или users
- `event_registrations`: список мероприятий (название, дата, статус оплаты)
- `events_with_materials`: мероприятия с доступом к записям/фотоархивам (participants_only)

**Дополнительно для role=no_role:**
- `event_registrations`: мероприятия, на которые записан как гость (если есть)
- `onboarding_status`: «Роль не выбрана»

**Бизнес-логика:**
1. Загрузить user + user_roles
2. Определить роль (doctor / user / no_role)
3. Для doctor — полные данные как в GET /admin/doctors/{id}
4. Для user — event_registrations с event_id, payment status
5. `payments` — последние 10 платежей пользователя

---

### DOCTORS (Public)

---

#### GET /api/v1/doctors

**Назначение:** Публичный каталог врачей — членов ассоциации  
**Доступ:** Guest (любой)

**Query params:**

| Параметр       | Тип    | Default    | Описание                          |
|----------------|--------|------------|-----------------------------------|
| limit       | int    | 12         | Кол-во на страницу (max 50)       |
| city_id        | uuid   | —          | Фильтр по городу (по UUID)        |
| city_slug      | string | —          | Фильтр по городу (по slug) — альтернатива city_id, используется при переходе со страниц /cities/{slug} |
| specialization | string | —          | Фильтр по специализации           |
| search         | string | —          | Поиск по ФИО                      |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "first_name": "Иван",
      "last_name": "Петров",
      "middle_name": "Сергеевич",
      "city": "Москва",
      "clinic_name": "Клиника А",
      "specialization": "Трихология",
      "academic_degree": "к.м.н.",
      "bio": "Краткое описание",
      "photo_url": "https://...",
      "public_phone": "+79001234567",
      "public_email": "public@example.com",
      "slug": "petrov-ivan-sergeevich"
    }
  ],
  "total": ..., "limit": 20, "offset": 0
}
```

**Бизнес-логика:**
1. **Правило видимости:** Врач показывается только при выполнении всех условий: `doctor_profiles.status = 'active'` (или эквивалент: `moderation_status = approved` + `subscriptions.status = 'active'` + `is_public = true`). Неоплатившие взнос и неоплатившие продление — не отображаются.
2. Выбирать только `is_public = true` и `moderation_status = approved`
3. У врача должна быть активная подписка (JOIN subscriptions WHERE status='active')
4. Фильтр по городу: принимается `city_id` (UUID) ИЛИ `city_slug` (string). Если передан `city_slug` — resolve через `cities.slug` → `city_id` (запрос: `WHERE cities.slug = :slug`). Оба параметра взаимозаменяемы.
5. Кешировать в Redis (TTL 5 мин, инвалидация при изменении профиля)
6. Не отдавать личные данные (passport_data, phone, email самого юзера)

---

#### GET /api/v1/doctors/{doctor_profile_id}

**Назначение:** Публичный профиль конкретного врача  
**Доступ:** Guest

**Response 200:**
```json
{
  "id": "uuid",
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "city": "Москва",
  "clinic_name": "Клиника А",
  "position": "Врач-трихолог",
  "specialization": "Трихология",
  "academic_degree": "к.м.н.",
  "bio": "Подробное описание...",
  "photo_url": "https://...",
  "public_phone": "+79001234567",
  "public_email": "public@example.com",
  "slug": "petrov-ivan-sergeevich",
  "seo": {
    "title": "Петров Иван Сергеевич — врач-трихолог в Москве | РОТА",
    "description": "Публичный профиль врача-трихолога Петрова Ивана Сергеевича. Клиника А, Москва.",
    "og_url": "https://[DOMAIN]/doctors/petrov-ivan-sergeevich",
    "og_type": "profile",
    "og_image": "https://...",
    "twitter_card": "summary_large_image",
    "canonical_url": null
  }
}
```

**Response 404:** если профиль не публичный или не существует.

**Бизнес-логика:** Те же правила видимости, что и для каталога — врач показывается только при `status = 'active'`, активной подписке и `is_public = true`.
- Поле `slug` заполнено только у одобренных профилей (`slug IS NOT NULL`). URL строится по slug; если slug отсутствует — fallback на UUID.
- SEO-объект формируется на бекенде: приоритет — данные из `pages_seo`; fallback — шаблон из профиля.

---

### PROFILE (Врач)

---

#### GET /api/v1/profile/personal

**Назначение:** Получение личной информации профиля  
**Доступ:** Doctor

**Response 200:**
```json
{
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "phone": "+79001234567",
  "passport_data": "серия **** номер ******",
  "registration_address": "г. Москва, ул. Примерная, д. 1",
  "city": { "id": "uuid", "name": "Москва" },
  "clinic_name": "Клиника А",
  "position": "Врач-трихолог",
  "specialization": "Трихология",
  "academic_degree": "к.м.н.",
  "diploma_photo_url": "https://...",
  "colleague_contacts": "Контакты для коллег",
  "documents": [
    {
      "id": "uuid",
      "type": { "code": "medical_diploma", "title": "Диплом" },
      "original_filename": "diploma.pdf",
      "moderation_status": "approved"
    }
  ]
}
```

---

#### PATCH /api/v1/profile/personal

**Назначение:** Обновление личной информации (НЕ уходит на модерацию — это приватные данные)  
**Доступ:** Doctor, moderation_status = 'approved'

**Request body:** (все поля optional)
```json
{
  "first_name": "string",
  "last_name": "string",
  "middle_name": "string",
  "phone": "string",
  "passport_data": "string",
  "registration_address": "string",
  "colleague_contacts": "string"
}
```

**Примечание:** Загрузка фото диплома — отдельный endpoint `POST /api/v1/profile/diploma-photo` (multipart/form-data).

**Response 200:**
```json
{
  "message": "Данные обновлены"
}
```

---

#### POST /api/v1/profile/diploma-photo

**Назначение:** Загрузка фото диплома о высшем медицинском образовании  
**Доступ:** Doctor, moderation_status = 'approved'

**Request:** `multipart/form-data`, поле `file` (image: jpeg, png, webp; max 5MB)

**Response 200:**
```json
{
  "diploma_photo_url": "https://storage.../diploma.jpg",
  "message": "Фото диплома загружено"
}
```

**Бизнес-логика:** сохранить в S3/Storage, обновить `doctor_profiles.diploma_photo_url`. Используется в онбординге и в ЛК (раздел personal).

---

#### GET /api/v1/profile/public

**Назначение:** Получение публичной информации профиля  
**Доступ:** Doctor

**Response 200:**
```json
{
  "bio": "Описание",
  "public_email": "public@example.com",
  "public_phone": "+79001234567",
  "photo_url": "https://...",
  "city": { "id": "uuid", "name": "Москва" },
  "clinic_name": "Клиника А",
  "specialization": "Трихология",
  "pending_draft": {
    "status": "pending",
    "bio": "Новое описание",
    "submitted_at": "2026-03-01T10:00:00Z"
  }
}
```

---

#### PATCH /api/v1/profile/public

**Назначение:** Обновление публичной информации (уходит на модерацию)  
**Доступ:** Doctor, moderation_status = 'approved'

**Request body:** (все поля optional, отправляются только изменённые)
```json
{
  "bio": "string",
  "public_email": "string",
  "public_phone": "string",
  "city_id": "uuid",
  "clinic_name": "string",
  "specialization": "string",
  "academic_degree": "string",
  "moderation_comment": "string"
}
```

**Примечание:** `moderation_comment` — комментарий пользователя при отправке (для исправления ошибок и т.д.). Пока новые данные на модерации — на сайте отображаются старые опубликованные/подтверждённые данные.

**Response 200:**
```json
{
  "message": "Изменения отправлены на модерацию",
  "draft_status": "pending"
}
```

**Response 409:**
```json
{
  "error": {
    "code": "DRAFT_ALREADY_PENDING",
    "message": "Предыдущие изменения ещё на модерации. Дождитесь решения"
  }
}
```

**Бизнес-логика:**
1. Проверить, нет ли уже pending-черновика
2. Создать/обновить запись в `doctor_profile_drafts`
3. Уведомить администраторов о новых правках

---

#### POST /api/v1/profile/photo

**Назначение:** Загрузка/обновление фото профиля  
**Доступ:** Doctor

**Request:** `multipart/form-data`

| Поле  | Тип  | Описание                       |
|-------|------|--------------------------------|
| photo | file | JPG/PNG, max 5MB, min 200x200  |

**Response 200:**
```json
{
  "photo_url": "https://storage.example.com/...",
  "message": "Фото отправлено на модерацию"
}
```

**Бизнес-логика:**
1. Валидировать формат (JPG, PNG) и размер
2. Ресайз до max 800x800 и создание thumbnail 200x200
3. Загрузить в S3: `doctors/{user_id}/photo/{uuid}.jpg`
4. Сохранить путь в `doctor_profile_drafts.photo_path` (на модерацию)

---

### SUBSCRIPTIONS

---

#### GET /api/v1/subscriptions/status

**Назначение:** Получение статуса текущей подписки  
**Доступ:** Doctor

**Response 200:**
```json
{
  "has_subscription": true,
  "current_subscription": {
    "id": "uuid",
    "plan": { "code": "annual_fee", "name": "Ежегодный членский взнос" },
    "status": "active",
    "starts_at": "2026-03-02T00:00:00Z",
    "ends_at": "2027-03-02T00:00:00Z",
    "days_remaining": 365
  },
  "has_paid_entry_fee": true,
  "can_renew": false,
  "next_action": null
}
```

**Response 200 (новый врач после модерации):**
```json
{
  "has_subscription": false,
  "current_subscription": null,
  "has_paid_entry_fee": false,
  "can_renew": false,
  "next_action": "pay_entry_fee"
}
```

**Бизнес-логика:**
1. Найти последнюю подписку для user_id
2. Если `has_paid_entry_fee = false` → next_action = `pay_entry_fee`
3. Если подписка expired → next_action = `renew`
4. Если подписка active и ends_at < 30 дней → `can_renew = true`

---

#### GET /api/v1/subscriptions/plans

**Назначение:** Список доступных тарифов  
**Доступ:** Doctor

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "code": "entry_fee",
      "name": "Вступительный взнос",
      "description": "Включает первый год членства",
      "price": 10000.00,
      "duration_months": 12,
      "is_available": true
    },
    {
      "id": "uuid",
      "code": "annual_fee",
      "name": "Ежегодный членский взнос",
      "description": "Продление членства на 1 год",
      "price": 5000.00,
      "duration_months": 12,
      "is_available": false
    }
  ]
}
```

**Бизнес-логика:**
1. Вернуть все `plans` с `is_active = true`
2. `is_available` вычисляется:
   - `entry_fee` доступен только если `has_paid_entry_fee = false`
   - `annual_fee` доступен только если `has_paid_entry_fee = true`

---

#### POST /api/v1/subscriptions/pay

**Назначение:** Инициация оплаты подписки  
**Доступ:** Doctor, moderation_status = 'approved'

**Request body:**
```json
{
  "plan_id": "uuid (required)",
  "idempotency_key": "string (required, UUID, клиентский)"
}
```

**Response 201:**
```json
{
  "payment_id": "uuid",
  "payment_url": "https://pay.example.com/...",
  "amount": 10000.00,
  "expires_at": "2026-03-02T15:30:00Z"
}
```

**Response 422:**
```json
{
  "error": {
    "code": "MEDICAL_DIPLOMA_REQUIRED",
    "message": "Оплата невозможна без диплома о высшем медицинском образовании"
  }
}
```

**Бизнес-логика:**
1. Проверить `has_medical_diploma = true`
2. Проверить что plan доступен для этого пользователя (entry_fee ещё не оплачивался / annual_fee только после entry)
3. **Логика просрочки:**
   - Если подписка истекла **≤ 90 дней назад** (новая анкета) → продление как обычная подписка (`product_type = subscription`), `starts_at = prev.ends_at`
   - Если подписка истекла **> 90 дней назад** (или > 1 года, старая анкета) → полный новый платёж: `product_type = entry_fee`, обязателен диплом. Включает вступительный взнос + годовую подписку.
   - Порог 90 дней зафиксирован в [01_Функциональные_требования.md](docs/tech_requirements/01_Функциональные_требования.md). При проверке: `now() - subscription.ends_at > interval '90 days'`.
4. Проверить idempotency_key (Redis, TTL 24ч) — если уже есть, вернуть тот же payment
5. Создать `subscriptions` со status=`pending`
6. Создать `payments` со status=`pending`, payment_provider по конфигурации, привязать к subscription
7. Вызвать API платёжной системы для создания платежа → получить `payment_url`
8. Сохранить `external_payment_id` и `external_payment_url`
9. Вернуть URL для редиректа пользователя

---

#### POST /api/v1/webhooks/yookassa

**Назначение:** Webhook от ЮKassa (основной провайдер)  
**Доступ:** Только с IP ЮKassa (whitelist) + проверка заголовка

**Request body:** (формат определяется API ЮKassa — `notification_type`, `event`, `object`)
```json
{
  "type": "notification",
  "event": "payment.succeeded",
  "object": {
    "id": "2b4c5d6e-...",
    "status": "succeeded",
    "amount": { "value": "10000.00", "currency": "RUB" },
    "metadata": { "payment_id": "uuid" }
  }
}
```

**Response 200:**
```json
{
  "status": "ok"
}
```

**Бизнес-логика:**
1. Проверить IP отправителя (whitelist ЮKassa)
2. Найти payment по `metadata.payment_id` или `external_payment_id`
3. Идемпотентность: если payment уже `succeeded` → вернуть 200 без действий
4. **При успешной оплате (event = `payment.succeeded`):**
   - `payments.status` → `succeeded`, `paid_at = now()`
   - Если `product_type = entry_fee / subscription`:
     - `subscriptions.status` → `active`, `starts_at = now()`, `ends_at = now() + duration_months`
     - `doctor_profiles.is_public = true` (если moderation_status = approved)
     - Чек **не формируется** (взносы НКО не фискализируются, п. 2 ст. 1.2 54-ФЗ, 251 НК РФ)
   - Если `product_type = event`:
     - `event_registrations.status` → `confirmed`
     - Запросить фискальный чек → создать `receipts` (receipt_type = 'payment')
   - Уведомить пользователя (email + Telegram): «Оплата получена»
   - Уведомить админов (Telegram-бот)
   - Если есть `telegram_binding` → добавить в закрытый канал (TaskIQ)
5. **При неуспешной оплате (event = `payment.canceled`):**
   - `payments.status` → `failed`
6. **При возврате (event = `refund.succeeded`):**
   - Обновить `payments.status` → `refunded` или `partially_refunded`
   - Если `product_type = event` → создать `receipts` (receipt_type = 'refund')

---

#### POST /api/v1/webhooks/psb

**Назначение:** Webhook от ПСБ Банк (СБП, при прямом подключении)  
**Доступ:** Только с IP ПСБ (whitelist) + подпись запроса

**Request body:** (формат определяется API ПСБ)
```json
{
  "order_id": "string",
  "status": "string",
  "amount": 10000.00,
  "signature": "string"
}
```

**Response 200:**
```json
{
  "status": "ok"
}
```

**Бизнес-логика:**
1. Верифицировать подпись запроса (HMAC SHA256)
2. Проверить IP отправителя (whitelist ПСБ)
3. Найти payment по `external_payment_id = order_id`
4. Идемпотентность: если payment уже `succeeded` → вернуть 200 без действий
5. Далее — аналогично `/webhooks/yookassa` (п. 4–6)

---

### EVENTS (Admin)

---

#### GET /api/v1/admin/events

**Назначение:** Список мероприятий для админки  
**Доступ:** Admin, Manager

**Query params:** limit, offset, status (draft/published/completed/cancelled), period (upcoming/past/all)

**Response 200:** пагинированный список мероприятий (id, title, slug, event_date, event_end_date, location, status, registrations_count, revenue, cover_image_url)

---

#### POST /api/v1/admin/events

**Назначение:** Создание мероприятия  
**Доступ:** Admin, Manager

**Request:** `multipart/form-data`

```json
{
  "title": "string (required, max 500)",
  "description": "string (optional, HTML)",
  "event_date": "datetime (required, ISO 8601)",
  "event_end_date": "datetime (optional)",
  "location": "string (optional)",
  "status": "string (optional, default: draft)",
  "cover_image": "file (optional, JPG/PNG, max 5MB)"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "title": "Конференция 2026",
  "slug": "konferenciya-2026",
  "status": "draft",
  "created_at": "2026-03-02T14:30:00Z"
}
```

**Бизнес-логика:**
1. Автогенерация slug из title (транслитерация, уникальность)
2. Загрузить cover_image в S3: `events/{event_id}/cover.jpg`
3. Создать запись в `events`

---

#### PATCH /api/v1/admin/events/{event_id}

**Назначение:** Обновление мероприятия  
**Доступ:** Admin, Manager

**Request body:** (аналогично POST, все поля optional)

**Response 200:** обновлённый объект мероприятия

---

#### DELETE /api/v1/admin/events/{event_id}

**Назначение:** Удаление мероприятия  
**Доступ:** Admin

**Response 204**

**Бизнес-логика:**
1. Проверить что нет confirmed-регистраций (иначе 422: сначала отмените регистрации)
2. Каскадное удаление: tariffs, galleries, photos, recordings
3. Удалить файлы из S3

---

#### POST /api/v1/admin/events/{event_id}/tariffs

**Назначение:** Добавление тарифа к мероприятию  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "name": "string (required, max 255)",
  "description": "string (optional, TEXT)",
  "conditions": "string (optional, TEXT)",
  "details": "string (optional, TEXT)",
  "price": "number (required, >= 0)",
  "member_price": "number (required, >= 0)",
  "benefits": ["string", "string", "..."],
  "seats_limit": "integer (optional, > 0, null = без ограничений)",
  "sort_order": "integer (optional, default: 0)"
}
```

**Поля:**
| Поле | Описание |
|------|----------|
| `name` | Название тарифа («Стандарт», «VIP», «Онлайн») |
| `description` | Описание тарифа — что входит, для кого подходит |
| `conditions` | Условия применения — кто может выбрать этот тариф (например: «Для членов ассоциации», «Для студентов при предъявлении студенческого») |
| `details` | Дополнительные детали — уточнения (например: «Запись включена», «Без питания», «Доступ к воркшопу по отдельной записи») |
| `price` | Обычная цена (для всех участников) |
| `member_price` | Цена для резидентов/членов ассоциации |
| `benefits` | Список преимуществ тарифа |
| `seats_limit` | Лимит мест (null = без ограничений) |

**Response 201:**
```json
{
  "id": "uuid",
  "name": "Стандарт",
  "description": "Базовый пакет участия в конференции",
  "conditions": "Для всех участников",
  "details": "Запись докладов включена. Кофе-брейки в стоимость.",
  "price": 15000.00,
  "member_price": 10000.00,
  "benefits": [
    "Доступ ко всем докладам",
    "Раздаточные материалы",
    "Кофе-брейки"
  ],
  "seats_limit": 100,
  "seats_taken": 0,
  "sort_order": 0
}
```

---

#### PATCH /api/v1/admin/events/{event_id}/tariffs/{tariff_id}

**Назначение:** Обновление тарифа мероприятия  
**Доступ:** Admin, Manager

**Request body:** (аналогично POST, все поля optional)

**Response 200:** обновлённый тариф (полный объект, аналогично POST 201)

**Бизнес-логика:**
1. Нельзя уменьшать seats_limit ниже seats_taken
2. Нельзя менять цену если уже есть confirmed-регистрации по этому тарифу (или выводить предупреждение)

---

#### DELETE /api/v1/admin/events/{event_id}/tariffs/{tariff_id}

**Назначение:** Удаление тарифа мероприятия  
**Доступ:** Admin

**Response 204**

**Бизнес-логика:** Нельзя удалить если есть привязанные registrations (422).

---

#### GET /api/v1/admin/events/{event_id}/registrations

**Назначение:** Список зарегистрировавшихся на мероприятие  
**Доступ:** Admin, Manager

**Query params:** limit, offset, status

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user": {
        "id": "uuid",
        "email": "user@example.com",
        "full_name": "Иван Петров"
      },
      "tariff": { "id": "uuid", "name": "Стандарт" },
      "applied_price": 10000.00,
      "is_member_price": true,
      "status": "confirmed",
      "payment_status": "succeeded",
      "created_at": "2026-02-15T10:00:00Z"
    }
  ],
  "summary": {
    "total_registrations": 45,
    "confirmed": 40,
    "pending": 3,
    "cancelled": 2,
    "total_revenue": 500000.00
  },
  "total": ..., "limit": 20, "offset": 0
}
```

---

#### POST /api/v1/admin/events/{event_id}/galleries

**Назначение:** Создание фотогалереи для мероприятия  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "title": "string (required)",
  "access_level": "string (required, enum: public | members_only)"
}
```

**Response 201:** объект галереи

---

#### POST /api/v1/admin/events/{event_id}/galleries/{gallery_id}/photos

**Назначение:** Загрузка фотографий в галерею  
**Доступ:** Admin, Manager

**Request:** `multipart/form-data`

| Поле   | Тип    | Описание                            |
|--------|--------|-------------------------------------|
| photos | file[] | Массив файлов (JPG/PNG, max 10MB каждый, max 50 за раз) |

**Response 201:**
```json
{
  "uploaded": 15,
  "photos": [
    { "id": "uuid", "file_url": "https://...", "thumbnail_url": "https://..." }
  ]
}
```

**Бизнес-логика:**
1. Для каждого файла: валидация, ресайз, создание thumbnail
2. Загрузка в S3: `events/{event_id}/galleries/{gallery_id}/{uuid}.jpg`
3. Массовый INSERT в `event_gallery_photos`

---

#### POST /api/v1/admin/events/{event_id}/recordings

**Назначение:** Добавление записи конференции (загрузка видео ИЛИ внешняя ссылка)  
**Доступ:** Admin, Manager

Поддерживаются два формата запроса в зависимости от источника видео.

**Вариант A — внешняя ссылка** (application/json):
```json
{
  "title": "string (required)",
  "video_source": "external",
  "video_url": "string (required, URL — YouTube, VK Video, Rutube и т.д.)",
  "duration_seconds": "integer (optional)",
  "access_level": "string (required, enum: public | members_only | participants_only)",
  "status": "string (optional, default: hidden)"
}
```

**Вариант B — загрузка файла** (multipart/form-data):

| Поле | Тип | Описание |
|------|-----|----------|
| title | string | Название (required) |
| video_source | string | `"uploaded"` (required) |
| video_file | file | Видеофайл (MP4/WebM/MOV, max 2GB) |
| duration_seconds | integer | Длительность (optional, определяется автоматически при загрузке) |
| access_level | string | Уровень доступа (required) |
| status | string | Статус (optional, default: hidden) |

**Response 201:**
```json
{
  "id": "uuid",
  "title": "Доклад: Современные методы",
  "video_source": "uploaded",
  "video_url": null,
  "video_playback_url": "https://presigned-s3-url...",
  "video_file_size": 524288000,
  "video_mime_type": "video/mp4",
  "duration_seconds": 3600,
  "access_level": "members_only",
  "status": "hidden"
}
```

**Бизнес-логика:**
1. Если `video_source = uploaded`: загрузить файл в S3 (`events/{event_id}/recordings/{uuid}.{ext}`), сохранить `video_file_key`, `video_file_size`, `video_mime_type`
2. Если `video_source = external`: сохранить `video_url`
3. Валидация: для uploaded — magic bytes (MP4/WebM/MOV), размер ≤ 2GB; для external — валидный URL

---

#### PATCH /api/v1/admin/events/{event_id}/recordings/{recording_id}

**Назначение:** Обновление записи (включая смену статуса, замену видео)  
**Доступ:** Admin, Manager

Формат: application/json (обновление метаданных) или multipart/form-data (замена видеофайла).

**Request body:** (все поля optional)

При замене видео: можно сменить `video_source` (например, с external на uploaded и наоборот). При загрузке нового файла старый удаляется из S3.

**Response 200:** обновлённый объект (формат аналогичен POST 201)

---

### EVENTS (Public)

---

#### GET /api/v1/events

**Назначение:** Список мероприятий  
**Доступ:** Guest

**Query params:**

| Параметр | Тип    | Default    | Описание                               |
|----------|--------|------------|----------------------------------------|
| limit | int    | 20         | Кол-во записей (max 100)               |
| offset | int    | 0          | Смещение                               |
| period   | string | upcoming   | upcoming / past / all                  |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Конференция 2026",
      "slug": "konferenciya-2026",
      "description": "Краткое описание...",
      "event_date": "2026-06-15T10:00:00Z",
      "event_end_date": "2026-06-15T18:00:00Z",
      "location": "Москва, отель Хилтон",
      "cover_image_url": "https://...",
      "tariffs": [
        {
          "id": "uuid",
          "name": "Стандарт",
          "description": "Базовый пакет участия",
          "conditions": "Для всех участников",
          "details": "Запись включена",
          "price": 15000.00,
          "member_price": 10000.00,
          "benefits": ["Доступ ко всем докладам", "Раздаточные материалы"],
          "seats_limit": 100,
          "seats_available": 55
        }
      ],
      "status": "published"
    }
  ],
  "total": ..., "limit": 20, "offset": 0
}
```

**Бизнес-логика:**
1. Только `status = published`
2. `seats_available = seats_limit - seats_taken` (или null если без лимита)
3. Кеш Redis TTL 5 мин

---

#### GET /api/v1/events/{event_slug}

**Назначение:** Детальная страница мероприятия  
**Доступ:** Guest

**Response 200:**
```json
{
  "id": "uuid",
  "title": "Конференция 2026",
  "slug": "konferenciya-2026",
  "description": "Полное описание HTML...",
  "event_date": "2026-06-15T10:00:00Z",
  "event_end_date": "2026-06-15T18:00:00Z",
  "location": "Москва, отель Хилтон",
  "cover_image_url": "https://...",
  "tariffs": [
    {
      "id": "uuid",
      "name": "Стандарт",
      "description": "Базовый пакет участия в конференции",
      "conditions": "Для всех участников",
      "details": "Запись докладов включена. Кофе-брейки в стоимость.",
      "price": 15000.00,
      "member_price": 10000.00,
      "benefits": [
        "Доступ ко всем докладам",
        "Раздаточные материалы",
        "Кофе-брейки"
      ],
      "seats_limit": 100,
      "seats_available": 55
    }
  ],
  "galleries": [
    {
      "id": "uuid",
      "title": "Фотоотчёт",
      "access_level": "public",
      "photos_count": 45,
      "preview_photos": [
        { "thumbnail_url": "https://..." }
      ]
    }
  ],
  "recordings": [
    {
      "id": "uuid",
      "title": "Доклад: Современные методы",
      "video_source": "uploaded",
      "duration_seconds": 3600,
      "access_level": "members_only"
    }
  ],
  "seo": {
    "title": "Конференция 2026 | РОТА",
    "description": "...",
    "og_url": "https://[DOMAIN]/events/konferenciya-2026",
    "og_type": "event",
    "og_image": "https://...",
    "twitter_card": "summary_large_image",
    "canonical_url": null
  },
  "user_registration": null
}
```

**Бизнес-логика:**
1. Если авторизован → проверить наличие registration и вернуть `user_registration`
2. Galleries: для guest — только public. Для doctor с active подпиской — all
3. Recordings: для guest — показать метаданные (title, duration, access_level, video_source), **не** давать `video_playback_url`. URL отдаётся только через `GET /recordings/{id}` при наличии доступа

---

#### POST /api/v1/events/{event_id}/register

> ✅ **РЕАЛИЗОВАН.** 3-сценарный flow с верификацией email для гостей.

**Назначение:** Регистрация и инициация оплаты участия  
**Доступ:** Авторизованный (JWT) или Guest (без JWT)

**Request body:**
```json
{
  "tariff_id": "uuid (required)",
  "idempotency_key": "string (required, max 255)",
  "guest_email": "string (required если нет JWT)",
  "guest_full_name": "string (optional, max 300)",
  "guest_workplace": "string (optional, max 255)",
  "guest_specialization": "string (optional, max 255)",
  "fiscal_email": "string (optional, email для чека)"
}
```

**Response 201 — 3 сценария:**

**Сценарий 1: Авторизованный (JWT)** — прямой redirect на оплату:
```json
{
  "registration_id": "uuid",
  "payment_url": "https://yookassa.ru/...",
  "applied_price": 10000.00,
  "is_member_price": true,
  "action": null,
  "masked_email": null
}
```

**Сценарий 2: Guest, email уже в базе** — фронт переключает на ввод пароля:
```json
{
  "registration_id": null,
  "payment_url": null,
  "applied_price": null,
  "is_member_price": null,
  "action": "verify_existing",
  "masked_email": "i***@example.com"
}
```

**Сценарий 3: Guest, email новый** — отправлен 6-значный код на email:
```json
{
  "registration_id": null,
  "payment_url": null,
  "applied_price": null,
  "is_member_price": null,
  "action": "verify_new_email",
  "masked_email": "n***@example.com"
}
```

**Ошибки:** 422 `NO_SEATS_AVAILABLE`, 422 `guest_email required`, 404 tariff not found, 422 `SEND_LIMIT_EXCEEDED` (>3 кодов/10 мин)

**Redis-ключи (сценарий 3):**
- `event_reg_verify:{email}` — хранит JSON `{code, tariff_id, event_id}`, TTL 600 сек
- `event_reg_attempts:{email}` — счётчик попыток ввода кода, max 5, TTL 600 сек
- `event_reg_send_count:{email}` — счётчик отправок кодов, max 3, TTL 600 сек

---

#### POST /api/v1/events/{event_id}/confirm-guest-registration

> ✅ **РЕАЛИЗОВАН.** Новый эндпоинт для подтверждения кода верификации (сценарий 3).

**Назначение:** Подтверждение email нового гостя по коду, создание временного аккаунта, регистрация и оплата  
**Доступ:** Public (без JWT)

**Request body:**
```json
{
  "email": "string (required, EmailStr)",
  "code": "string (required, 6 символов)",
  "tariff_id": "uuid (required)",
  "idempotency_key": "string (required, max 255)",
  "guest_full_name": "string (optional, max 300)",
  "guest_workplace": "string (optional, max 255)",
  "guest_specialization": "string (optional, max 255)",
  "fiscal_email": "string (optional, EmailStr)"
}
```

**Response 201:**
```json
{
  "registration_id": "uuid",
  "payment_url": "https://yookassa.ru/...",
  "applied_price": 15000.00,
  "is_member_price": false,
  "action": null,
  "masked_email": null
}
```

**Ошибки:**
- 422 `Invalid verification code` — неверный код (counter +1)
- 422 `Verification code expired` — код не найден / истёк
- 422 `Too many attempts` — 5 неудачных попыток, запросите новый код
- 422 `NO_SEATS_AVAILABLE` — мест нет
- 404 tariff/event not found

**Бизнес-логика:**
1. Получить сохранённые данные из Redis (`event_reg_verify:{email}`)
2. Проверить код, инкрементировать счётчик попыток
3. Создать `users` с ролью `non_doctor` и временным паролем
4. Создать `event_registrations` (status=pending)
5. Создать `payments` (product_type=event)
6. Вызвать YooKassa API → payment_url
7. Отправить email с временным паролем и инструкциями
8. Удалить Redis-ключи верификации

---

#### ~~GET /api/v1/events/{event_id}/check-price~~

> **NOT IMPLEMENTED.** Фронт показывает обе цены (`price` и `member_price`) из данных тарифа. Бекенд определяет `applied_price` при создании регистрации.

---

#### GET /api/v1/events/{event_id}/galleries

> **ОБНОВЛЕНО.** Фактический endpoint возвращает все галереи с фотографиями inline (нет отдельного `/{gallery_id}/photos`).

**Назначение:** Список галерей мероприятия с фотографиями  
**Доступ:** Guest (public) / Doctor с подпиской или подтверждённой регистрацией (members_only)

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Открытие конференции",
      "access_level": "public",
      "photos": [
        {
          "id": "uuid",
          "file_url": "https://...",
          "thumbnail_url": "https://...",
          "caption": "Фото 1"
        }
      ]
    }
  ]
}
```

**Логика доступа:** Галереи с `access_level = "members_only"` скрываются от гостей и пользователей без активной подписки/подтверждённой регистрации.

---

#### GET /api/v1/events/{event_id}/recordings

> **ОБНОВЛЕНО.** Фактический endpoint возвращает список записей (нет отдельного `/{recording_id}`).

**Назначение:** Список записей конференции  
**Доступ:** Зависит от access_level каждой записи

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Доклад: Современные методы",
      "video_source": "uploaded",
      "video_url": "https://...",
      "duration_seconds": 3600,
      "access_level": "public"
    }
  ]
}
```

**Логика доступа:** Записи с `access_level` = `"members_only"` или `"participants_only"` скрываются от пользователей без активной подписки или подтверждённой регистрации. Только опубликованные записи (`status = "published"`) возвращаются.

> `video_playback_url` — единое поле для фронтенда. Backend формирует его автоматически:
> - Если `video_source = external` → значение = `video_url` (прямая ссылка на YouTube/VK/Rutube)
> - Если `video_source = uploaded` → значение = presigned S3 URL (TTL 2 часа)

**Бизнес-логика:**
1. `public` → все
2. `members_only` → только doctor с active subscription
3. `participants_only` → только зарегистрированные на это мероприятие (confirmed)
4. При отсутствии доступа → 403, `video_playback_url` не возвращается

---

### PAYMENTS

---

#### GET /api/v1/admin/payments

**Назначение:** Полный список платежей  
**Доступ:** Admin, Manager, Accountant

**Query params:**

| Параметр     | Тип    | Default    | Описание                                |
|--------------|--------|------------|-----------------------------------------|
| limit     | int    | 20         | Кол-во записей (max 100)                |
| offset    | int    | 0          | Смещение                                |
| product_type | string | —          | entry_fee / subscription / event        |
| status       | string | —          | pending / succeeded / failed / partially_refunded / refunded |
| user_id      | uuid   | —          | Фильтр по плательщику                   |
| date_from    | date   | —          | Дата начала периода                      |
| date_to      | date   | —          | Дата окончания периода                   |
| sort_by      | string | created_at |                                         |
| sort_order   | string | desc       |                                         |

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user": {
        "id": "uuid",
        "email": "doctor@example.com",
        "full_name": "Иван Петров"
      },
      "amount": 10000.00,
      "product_type": "entry_fee",
      "payment_provider": "yookassa",
      "status": "succeeded",
      "description": "Вступительный взнос",
      "has_receipt": false,
      "paid_at": "2026-01-20T12:00:00Z",
      "created_at": "2026-01-20T11:55:00Z"
    }
  ],
  "summary": {
    "total_amount": 500000.00,
    "count_completed": 45,
    "count_pending": 3
  },
  "total": ..., "limit": 20, "offset": 0
}
```

---

#### GET /api/v1/payments

**Назначение:** Список собственных платежей врача  
**Доступ:** Doctor

**Query params:** limit, offset

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "amount": 10000.00,
      "product_type": "entry_fee",
      "payment_provider": "yookassa",
      "status": "succeeded",
      "description": "Вступительный взнос",
      "has_receipt": false,
      "paid_at": "2026-01-20T12:00:00Z"
    }
  ],
  "total": ..., "limit": 20, "offset": 0
}
```

---

#### GET /api/v1/payments/{payment_id}/receipt

**Назначение:** Получение чека по платежу  
**Доступ:** Doctor (свой), Admin, Manager, Accountant

> **Важно:** Чеки формируются только для мероприятий (`product_type = 'event'`).
> Для взносов (`entry_fee`, `subscription`) endpoint возвращает 404 — чеки НКО не требуются (251 НК РФ).

**Response 200:**
```json
{
  "receipts": [
    {
      "receipt_type": "payment",
      "receipt_url": "https://ofd.example.com/check/...",
      "fiscal_number": "0000123456789",
      "fiscal_document": "12345",
      "fiscal_sign": "9876543210",
      "amount": 10000.00,
      "status": "succeeded",
      "created_at": "2026-01-20T12:00:05Z"
    }
  ]
}
```

**Response 404:** если чеки не предусмотрены для данного типа платежа (взносы) или ещё не сформированы

---

#### GET /api/v1/payments/{payment_id}/status

**Назначение:** Polling статуса платежа (используется после возврата с платёжной страницы)  
**Доступ:** Doctor (свой), Guest (по payment_id из сессии)

**Response 200:**
```json
{
  "payment_id": "uuid",
  "status": "pending",
  "product_type": "entry_fee",
  "amount": 10000.00,
  "created_at": "2026-01-20T11:55:00Z",
  "paid_at": null
}
```

**Бизнес-логика:**
1. Frontend вызывает этот endpoint каждые 2–3 секунды после редиректа с платёжной страницы
2. Когда `status` меняется на `succeeded` / `failed` — frontend останавливает polling и показывает результат
3. Timeout на клиенте: 5 минут, после чего показать сообщение «Платёж обрабатывается»

---

#### POST /api/v1/admin/payments/manual

**Назначение:** Ручное создание платежа администратором (наличные, перевод и т.д.)  
**Доступ:** Admin, Accountant

**Request body:**
```json
{
  "user_id": "uuid (required)",
  "amount": 10000.00,
  "product_type": "entry_fee",
  "description": "Наличный вступительный взнос",
  "subscription_id": "uuid (optional)",
  "event_registration_id": "uuid (optional)"
}
```

**Response 201:**
```json
{
  "payment_id": "uuid",
  "status": "succeeded",
  "payment_provider": "manual"
}
```

**Бизнес-логика:**
1. Создать `payments` с `payment_provider = 'manual'`, `status = 'succeeded'`, `paid_at = now()`
2. Обновить связанные сущности (subscription / event_registration) аналогично webhook-логике
3. Чек **не формируется** для ручных платежей
4. Уведомить пользователя (email + Telegram)

---

#### POST /api/v1/admin/payments/{payment_id}/refund

**Назначение:** Возврат средств по платежу  
**Доступ:** Admin, Accountant

**Request body:**
```json
{
  "amount": 10000.00,
  "reason": "Отмена регистрации на мероприятие"
}
```

**Response 200:**
```json
{
  "refund_id": "uuid",
  "payment_id": "uuid",
  "status": "pending",
  "amount": 10000.00
}
```

**Response 422:**
```json
{
  "error": {
    "code": "REFUND_EXCEEDS_AMOUNT",
    "message": "Сумма возврата превышает оплаченную сумму"
  }
}
```

**Бизнес-логика:**
1. Проверить: payment.status = 'succeeded' или 'partially_refunded'
2. Проверить: сумма возврата ≤ (amount - уже возвращённая сумма)
3. Вызвать API платёжной системы (`payment_provider`) для создания возврата
4. Если `amount` возврата = полная сумма → `payments.status` = 'refunded'
5. Если частичный → `payments.status` = 'partially_refunded'
6. Если `product_type = event` → создать `receipts` (receipt_type = 'refund')
7. Обновить связанные сущности (event_registration → cancelled)
8. Для `payment_provider = 'manual'` → просто обновить статус без вызова API

---

### CONTENT (Admin)

---

#### GET /api/v1/admin/articles

**Назначение:** Список всех статей (включая черновики)  
**Доступ:** Admin, Manager

**Query params:** limit, offset, status (draft/published/archived)

**Response 200:** массив статей с пагинацией

---

#### POST /api/v1/admin/articles

**Назначение:** Создание статьи  
**Доступ:** Admin, Manager

**Request:** `multipart/form-data`
```json
{
  "title": "string (required)",
  "content": "string (required, HTML)",
  "excerpt": "string (optional)",
  "status": "string (optional, default: draft)",
  "seo_title": "string (optional)",
  "seo_description": "string (optional)",
  "cover_image": "file (optional)"
}
```

**Response 201:** объект статьи

**Бизнес-логика:**
1. Автогенерация slug из title
2. Если status=`published` → установить `published_at = now()`

---

#### PATCH /api/v1/admin/articles/{article_id}

**Назначение:** Обновление статьи  
**Доступ:** Admin, Manager

**Response 200:** обновлённый объект

---

#### DELETE /api/v1/admin/articles/{article_id}

**Назначение:** Удаление статьи  
**Доступ:** Admin

**Response 204**

---

#### GET /api/v1/articles

**Назначение:** Публичный список статей  
**Доступ:** Guest

**Query params:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| limit | int | Кол-во на страницу |
| theme_id | uuid | Фильтр по теме (или theme_slug) |

**Бизнес-логика:** только `status = published`, отсортировано по published_at DESC. При `theme_id` — JOIN article_theme_assignments. Кеш Redis 5 мин.

---

#### GET /api/v1/articles/{slug}

**Назначение:** Публичная страница статьи  
**Доступ:** Guest

**Response 200:**
```json
{
  "id": "uuid",
  "slug": "nazvanie-stati",
  "title": "Название статьи",
  "content": "HTML или Markdown контент...",
  "cover_url": "https://...",
  "published_at": "2026-01-15T10:00:00Z",
  "themes": [
    { "id": "uuid", "slug": "trichologia", "title": "Трихология" }
  ],
  "seo": {
    "title": "Название статьи | РОТА",
    "description": "SEO-описание статьи...",
    "og_url": "https://[DOMAIN]/articles/nazvanie-stati",
    "og_type": "article",
    "og_image": "https://...",
    "twitter_card": "summary_large_image",
    "canonical_url": null
  }
}
```

**Бизнес-логика:**
1. Отдавать только статьи со `status = 'published'`
2. SEO-объект: приоритет — `articles.seo_title` / `articles.seo_description`; fallback — `title` + автогенерированное описание
3. `og_url` = `https://[DOMAIN]/articles/{slug}`, `canonical_url` = явный из `pages_seo` или null

---

#### GET /api/v1/article-themes

**Назначение:** Публичный список активных тем статей (для фильтра на клиенте)  
**Доступ:** Guest

**Query params:** active (bool), has_articles (bool)

**Response 200:** `{ "data": [{ "id", "slug", "title" }] }`

---

#### GET /api/v1/admin/article-themes

**Назначение:** CRUD тем статей для админки  
**Доступ:** Admin, Manager

**Query params:** active, has_articles

---

#### POST /api/v1/admin/article-themes

**Назначение:** Создание темы  
**Доступ:** Admin, Manager

---

#### PATCH /api/v1/admin/article-themes/{theme_id}

**Назначение:** Обновление темы  
**Доступ:** Admin, Manager

---

#### DELETE /api/v1/admin/article-themes/{theme_id}

**Назначение:** Удаление темы  
**Доступ:** Admin, Manager

---

#### GET /api/v1/admin/organization-documents

**Назначение:** Список документов организации  
**Доступ:** Admin, Manager

---

#### POST /api/v1/admin/organization-documents

**Назначение:** Создание документа организации  
**Доступ:** Admin, Manager

**Request:** `multipart/form-data`
```json
{
  "title": "string (required)",
  "content": "string (optional, HTML — WYSIWYG)",
  "file": "file (optional, PDF, max 20MB)",
  "sort_order": "integer (optional)",
  "is_active": "boolean (optional, default: true)"
}
```

---

#### PATCH /api/v1/admin/organization-documents/{doc_id}

**Назначение:** Обновление документа организации  
**Доступ:** Admin, Manager

---

#### DELETE /api/v1/admin/organization-documents/{doc_id}

**Назначение:** Удаление документа организации  
**Доступ:** Admin

---

#### GET /api/v1/organization-documents

**Назначение:** Публичный список документов организации (устав, правление)  
**Доступ:** Guest

**Бизнес-логика:** только `is_active = true`, отсортировано по sort_order

---

#### GET /api/v1/organization-documents/{slug}

**Назначение:** Публичная страница документа организации (для отображения контента и content_blocks)  
**Доступ:** Guest

**Response 200:** `{ "id", "title", "slug", "content", "file_url", "content_blocks": [...] }`

---

### CONTENT BLOCKS

> **NOT IMPLEMENTED** — CRUD-эндпоинты для Content Blocks **не реализованы** на бекенде. Модель `ContentBlock` существует в БД, но API отсутствует. Спецификация сохранена для будущей реализации.

Универсальные контентные блоки для статей, мероприятий, профилей врачей, документов организации. Полиморфная связь через `entity_type` + `entity_id`.

#### GET /api/v1/admin/content-blocks

**Назначение:** Список блоков сущности  
**Доступ:** Admin, Manager

**Query params:** `entity_type` (required), `entity_id` (required), `locale` (optional, default `ru`)

**Response 200:** `{ "data": [ {...block} ] }`

---

#### POST /api/v1/admin/content-blocks

**Назначение:** Создание блока  
**Доступ:** Admin, Manager

**Request body:** `entity_type`, `entity_id`, `locale`, `block_type`, `sort_order`, `title`, `content`, `media_url`, `thumbnail_url`, `link_url`, `link_label`, `device_type`, `block_metadata`

---

#### PATCH /api/v1/admin/content-blocks/{block_id}

**Назначение:** Обновление блока  
**Доступ:** Admin, Manager

---

#### DELETE /api/v1/admin/content-blocks/{block_id}

**Назначение:** Удаление блока  
**Доступ:** Admin, Manager

**Response 204**

---

#### POST /api/v1/admin/content-blocks/reorder

**Назначение:** Изменение порядка блоков (drag-and-drop)  
**Доступ:** Admin, Manager

**Request body:** `{ "entity_type", "entity_id", "locale", "block_ids": ["uuid1", "uuid2"] }`

---

**Публичный API:** блоки возвращаются в поле `content_blocks` при запросе:
- `GET /api/v1/articles/{slug}`
- `GET /api/v1/events/{event_slug}`
- `GET /api/v1/doctors/{id}`
- `GET /api/v1/organization-documents/{slug}` *(добавить endpoint для одиночного документа)*

---

#### GET /api/v1/admin/seo-pages

**Назначение:** Список всех SEO-настроек  
**Доступ:** Admin

---

#### GET /api/v1/admin/seo-pages/{slug}

**Назначение:** Получение SEO-настройки по slug  
**Доступ:** Admin

---

#### POST /api/v1/admin/seo-pages

**Назначение:** Создание SEO-настройки для новой страницы  
**Доступ:** Admin

---

#### DELETE /api/v1/admin/seo-pages/{slug}

**Назначение:** Удаление SEO-настройки  
**Доступ:** Admin

---

#### PATCH /api/v1/admin/seo-pages/{slug}

**Назначение:** Обновление SEO-полей страницы (upsert по slug)  
**Доступ:** Admin

**Request body:**
```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "og_title": "string (optional)",
  "og_description": "string (optional)",
  "og_image": "file (optional)"
}
```

---

#### GET /api/v1/seo/{slug}

**Назначение:** Получение SEO-данных для страницы  
**Доступ:** Guest

**Управление в админке:** `/admin/settings/seo` (GET/PATCH /admin/seo-pages)

---

#### ~~GET /api/v1/settings/public~~

> **NOT IMPLEMENTED.** Публичный эндпоинт для контактов и ссылки на бота не реализован. Фронт использует env-переменные (`NEXT_PUBLIC_CONTACT_EMAIL`, и т.д.) как workaround.

---

#### ~~GET /api/v1/pages/home~~

> **NOT IMPLEMENTED.** CMS-эндпоинт для главной страницы не реализован. Контент hero-блока и миссии захардкоден на фронте.

---

#### GET /api/v1/profile/events

**Назначение:** Список мероприятий с регистрациями текущего пользователя (для ЛК «Мероприятия»).  
**Доступ:** Авторизованный

**Response 200:**
```json
{
  "data": [
    {
      "event": { "id": "uuid", "title": "...", "slug": "...", "starts_at": "...", "status": "..." },
      "registration": { "id": "uuid", "status": "confirmed", "tariff_name": "..." }
    }
  ]
}
```

**Управление в админке:** не требуется (данные из `event_registrations` + `events`)

---

#### GET /api/v1/telegram/binding

**Назначение:** Статус привязки Telegram для текущего пользователя.  
**Доступ:** Doctor

**Response 200:**
```json
{
  "is_linked": true,
  "tg_username": "username",
  "is_in_channel": true
}
```

**Управление в админке:** не требуется (пользователь привязывает через бота)

---

#### GET /api/v1/admin/cities

**Назначение:** Список городов (для управления)  
**Доступ:** Admin, Manager

---

#### POST /api/v1/admin/cities

**Назначение:** Добавление города  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "name": "string (required, unique)",
  "sort_order": "integer (optional)"
}
```

---

#### PATCH /api/v1/admin/cities/{city_id}

**Назначение:** Обновление города  
**Доступ:** Admin, Manager

---

#### DELETE /api/v1/admin/cities/{city_id}

**Назначение:** Удаление/деактивация города  
**Доступ:** Admin

**Бизнес-логика:** если у города есть привязанные врачи — не удалять, а `is_active = false`.

---

#### GET /api/v1/cities

**Назначение:** Публичный справочник активных городов  
**Доступ:** Guest

**Query params:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| with_doctors | bool | false | Если `true` — возвращать только города с активными врачами + поле `doctors_count` |
| sort | string | name | Сортировка: `name` (по названию) |

**Response 200 (без `with_doctors`):**
```json
{
  "data": [
    { "id": "uuid", "name": "Москва", "slug": "moskva" },
    { "id": "uuid", "name": "Санкт-Петербург", "slug": "spb" }
  ]
}
```

**Response 200 (`?with_doctors=true`):**
```json
{
  "data": [
    { "id": "uuid", "name": "Москва", "slug": "moskva", "doctors_count": 12 },
    { "id": "uuid", "name": "Санкт-Петербург", "slug": "spb", "doctors_count": 8 }
  ]
}
```

**Бизнес-логика (with_doctors=true):** Выборка `city_id` из `doctor_profiles` JOIN `subscriptions` WHERE `subscriptions.status = 'active'` AND `doctor_profiles.status = 'active'`. GROUP BY city, фильтр `doctors_count > 0`. Кеш Redis 5 мин.

> **Deprecated:** `GET /api/v1/cities-with-doctors` — использовать `GET /api/v1/cities?with_doctors=true`

---

#### GET /api/v1/admin/plans

**Назначение:** Список тарифов подписки (для управления)  
**Доступ:** Admin

---

#### POST /api/v1/admin/plans

**Назначение:** Создание тарифа  
**Доступ:** Admin

---

#### PATCH /api/v1/admin/plans/{plan_id}

**Назначение:** Обновление тарифа  
**Доступ:** Admin

**Бизнес-логика:** нельзя менять `code` у существующего тарифа. Цена меняется, но не влияет на уже оплаченные подписки.

---

#### GET /api/v1/admin/settings

**Назначение:** Получение системных настроек  
**Доступ:** Admin

**Response 200:**
```json
{
  "telegram_bot_link": "https://t.me/trichology_bot",
  "contacts_for_doctors": { "email": "...", "phone": "...", "address": "..." },
  "contacts_for_visitors": { "email": "...", "phone": "...", "address": "..." },
  "home_hero": { "title": "...", "text": "...", "image_url": "..." },
  "home_mission": { "text": "..." }
}
```

---

#### PATCH /api/v1/admin/settings

**Назначение:** Обновление системных настроек  
**Доступ:** Admin

**Request body:**
```json
{
  "telegram_bot_link": "string (optional)",
  "contacts_for_doctors": { "email": "string", "phone": "string", "address": "string" },
  "contacts_for_visitors": { "email": "string", "phone": "string", "address": "string" },
  "home_hero": { "title": "string", "text": "string", "image_url": "string" },
  "home_mission": { "text": "string" }
}
```

Все поля опциональны. Частичное обновление — только переданные ключи обновляются в `site_settings`.

---

### CERTIFICATES

---

#### GET /api/v1/certificates

**Назначение:** Список сертификатов врача  
**Доступ:** Doctor

**Бизнес-логика:** Сертификаты **скрыты** (пустой список или 403), если членские взносы не оплачены (нет активной подписки). Сертификат члена ассоциации доступен после одобрения и оплаты. Сертификаты мероприятий — после оплаты участия в мероприятии.

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "certificate_type": "member",
      "year": 2026,
      "event": null,
      "certificate_number": "AT-2026-00042",
      "is_active": true,
      "generated_at": "2026-01-16T15:00:00Z",
      "download_url": "presigned-url (TTL 10 мин)"
    },
    {
      "id": "uuid",
      "certificate_type": "event",
      "year": null,
      "event": { "id": "uuid", "title": "Конференция 2026" },
      "certificate_number": "AT-EV-2026-00123",
      "is_active": true,
      "generated_at": "2026-04-20T18:00:00Z",
      "download_url": "presigned-url (TTL 10 мин)"
    }
  ]
}
```

---

#### GET /api/v1/certificates/{certificate_id}/download

**Назначение:** Скачивание PDF-файла сертификата  
**Доступ:** Doctor (свой)

**Response:** Redirect 302 → presigned S3 URL (Content-Type: application/pdf)

---

### NOTIFICATIONS

---

#### POST /api/v1/admin/notifications/send

**Назначение:** Ручная отправка уведомления  
**Доступ:** Admin, Manager

**Request body:**
```json
{
  "user_id": "uuid (required)",
  "type": "string (required, enum: manual_reminder | custom)",
  "title": "string (required)",
  "body": "string (required)",
  "channels": ["email", "telegram"]
}
```

**Response 201:**
```json
{
  "notification_id": "uuid",
  "status": "pending"
}
```

---

#### GET /api/v1/admin/notifications

**Назначение:** Лог отправленных уведомлений  
**Доступ:** Admin, Manager

**Query params:** limit, offset, user_id, type, status, date_from, date_to

**Response 200:** массив уведомлений с пагинацией

---

### TELEGRAM

---

#### POST /api/v1/telegram/generate-code

**Назначение:** Генерация одноразового кода для привязки Telegram  
**Доступ:** Doctor

**Response 201:**
```json
{
  "auth_code": "ABC123",
  "expires_at": "2026-03-02T15:00:00Z",
  "bot_link": "https://t.me/trichology_bot?start=ABC123",
  "instruction": "Перейдите по ссылке и отправьте боту команду /start"
}
```

**Бизнес-логика:**
1. Сгенерировать 6-символьный код (uppercase alphanumeric)
2. Сохранить в `telegram_bindings.auth_code`, TTL 15 мин
3. Если привязки нет — создать с пустым tg_user_id

---

#### POST /api/v1/telegram/webhook

**Назначение:** Webhook для Telegram Bot API  
**Доступ:** Только от Telegram (проверка secret token)

**Request body:** Telegram Update объект

**Бизнес-логика:**
1. Верифицировать `X-Telegram-Bot-Api-Secret-Token`
2. При `/start {code}`:
   - Найти `telegram_bindings` по auth_code, проверить срок
   - Установить `tg_user_id`, `tg_username`, `tg_chat_id`
   - Очистить `auth_code`
   - Если врач с активной подпиской → добавить в закрытый канал
   - Ответить: «Аккаунт привязан!»
3. При сообщении от админа — перенаправить на соответствующие действия
4. При нажатии inline-кнопок — обработать callback_query

---

### DASHBOARD (Admin)

---

#### GET /api/v1/admin/dashboard

**Назначение:** Данные для дашборда администратора  
**Доступ:** Admin, Manager

**Response 200:**
```json
{
  "funnel": {
    "total_registered": 250,
    "doctors": 180,
    "doctors_approved": 150,
    "doctors_active_subscription": 120,
    "non_doctors": 70
  },
  "subscriptions": {
    "expiring_this_week": [
      {
        "doctor_id": "uuid",
        "full_name": "Иван Петров",
        "email": "doctor@example.com",
        "ends_at": "2026-03-08T00:00:00Z"
      }
    ],
    "expired_last_2_months": [
      {
        "doctor_id": "uuid",
        "full_name": "Мария Сидорова",
        "email": "maria@example.com",
        "expired_at": "2026-02-15T00:00:00Z"
      }
    ]
  },
  "events": {
    "upcoming": [
      {
        "id": "uuid",
        "title": "Конференция 2026",
        "event_date": "2026-06-15T10:00:00Z",
        "registrations_count": 45,
        "revenue": 500000.00
      }
    ],
    "recent_registrations": 12
  },
  "moderation": {
    "pending_count": 5,
    "pending_drafts_count": 2
  },
  "payments": {
    "this_month_total": 150000.00,
    "this_month_count": 12
  }
}
```

**Бизнес-логика:**
1. Агрегирующие запросы с кешированием (Redis TTL 2 мин)
2. `expiring_this_week` → subscriptions WHERE status='active' AND ends_at BETWEEN now() AND now() + 7d
3. `expired_last_2_months` → subscriptions WHERE status='expired' AND ends_at > now() - 60d, без новой active-подписки

---

### VOTING

---

#### GET /api/v1/admin/voting

**Назначение:** Список сессий голосования для админки  
**Доступ:** Admin

**Query params:** limit, offset, status (draft/active/closed/cancelled)

**Response 200:** пагинированный список сессий (id, title, description, status, starts_at, ends_at, candidates_count)

---

#### POST /api/v1/admin/voting

**Назначение:** Создание сессии голосования  
**Доступ:** Admin

**Request body:**
```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "starts_at": "datetime (required)",
  "ends_at": "datetime (required)",
  "candidates": [
    {
      "doctor_profile_id": "uuid (required)",
      "description": "string (optional)"
    }
  ]
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "title": "Выборы президента 2026",
  "status": "draft",
  "starts_at": "2026-04-01T00:00:00Z",
  "ends_at": "2026-04-07T23:59:59Z",
  "candidates_count": 3
}
```

**Бизнес-логика:**
1. `ends_at > starts_at`
2. Все candidates должны быть approved-врачами
3. Статус `draft` — голосование не видно врачам

---

#### PATCH /api/v1/admin/voting/{session_id}

**Назначение:** Обновление / активация / закрытие сессии  
**Доступ:** Admin

**Request body:**
```json
{
  "status": "string (optional, enum: active | closed | cancelled)",
  "title": "string (optional)",
  "ends_at": "datetime (optional)"
}
```

**Бизнес-логика:**
1. Переход `draft → active` — голосование открыто, уведомить всех врачей
2. Переход `active → closed` — голосование закрыто, подсчёт результатов
3. Нельзя менять candidates после `active`

---

#### GET /api/v1/voting/active

**Назначение:** Получение текущего активного голосования  
**Доступ:** Doctor (с активной подпиской)

**Response 200:**
```json
{
  "id": "uuid",
  "title": "Выборы президента 2026",
  "description": "Описание...",
  "starts_at": "2026-04-01T00:00:00Z",
  "ends_at": "2026-04-07T23:59:59Z",
  "candidates": [
    {
      "id": "uuid",
      "full_name": "Иван Петров",
      "photo_url": "https://...",
      "description": "Программа кандидата..."
    }
  ],
  "has_voted": false
}
```

**Response 404:** если нет активного голосования

---

#### POST /api/v1/voting/{session_id}/vote

**Назначение:** Голосование за кандидата  
**Доступ:** Doctor (с активной подпиской, не голосовал ранее)

**Request body:**
```json
{
  "candidate_id": "uuid (required)"
}
```

**Response 201:**
```json
{
  "message": "Ваш голос учтён",
  "voted_at": "2026-04-03T14:30:00Z"
}
```

**Response 409:**
```json
{
  "error": {
    "code": "ALREADY_VOTED",
    "message": "Вы уже проголосовали в этом голосовании"
  }
}
```

**Бизнес-логика:**
1. Проверить что сессия `active` и текущая дата в диапазоне starts_at..ends_at
2. Проверить UNIQUE (session_id, user_id)
3. Проверить что candidate_id принадлежит этой сессии
4. Проверить что пользователь — doctor с active подпиской
5. Создать запись в `votes`

---

#### GET /api/v1/admin/voting/{session_id}/results

**Назначение:** Результаты голосования  
**Доступ:** Admin (всегда), Doctor (только после `closed`)

**Response 200:**
```json
{
  "session": {
    "id": "uuid",
    "title": "Выборы президента 2026",
    "status": "closed",
    "total_votes": 95,
    "total_eligible_voters": 120
  },
  "results": [
    {
      "candidate": {
        "id": "uuid",
        "full_name": "Иван Петров"
      },
      "votes_count": 52,
      "percentage": 54.74
    },
    {
      "candidate": {
        "id": "uuid",
        "full_name": "Мария Сидорова"
      },
      "votes_count": 43,
      "percentage": 45.26
    }
  ]
}
```

---

#### GET /sitemap.xml

> **ОБНОВЛЕНО.** Фактический URL: `/sitemap.xml` (не `/api/v1/seo/sitemap.xml`).

**Назначение:** Автоматически генерируемый Sitemap  
**Доступ:** Guest

**Response:** XML (Content-Type: application/xml)

**Включаемые URL-типы:**

| URL-тип | `<changefreq>` | `<priority>` | `<lastmod>` |
|---------|---------------|-------------|------------|
| Главная `/` | `weekly` | `1.0` | Дата последнего deploy |
| Страницы справочника (`/doctors`, `/events`, `/articles`) | `daily` | `0.8` | `now()` |
| Профиль врача `/doctors/{slug}` | `weekly` | `0.7` | `doctor_profiles.updated_at` |
| Страница мероприятия `/events/{slug}` | `weekly` | `0.7` | `events.updated_at` |
| Страница статьи `/articles/{slug}` | `weekly` | `0.7` | `articles.updated_at` |
| Страница города `/cities/{slug}` | `weekly` | `0.6` | `cities.updated_at` |
| Статические страницы (`/about`, `/contacts`) | `monthly` | `0.5` | — |

**Правила включения:**
- Врачи: `doctor_profiles.status = 'active'` AND `is_public = true` AND активная подписка AND `slug IS NOT NULL`
- Мероприятия: `events.status IN ('upcoming', 'ongoing')` OR архив (последние 12 мес.)
- Статьи: `articles.status = 'published'`
- Города: `cities.is_active = true`

**Бизнес-логика:**
- Генерируется TaskIQ задачей `generate_sitemap` (cron: ежедневно 04:00 UTC)
- Дополнительно инвалидируется при: публикации статьи, одобрении профиля врача, публикации мероприятия
- Результат кешируется в Redis (TTL 24ч)

---

#### GET /robots.txt

> **ОБНОВЛЕНО.** Фактический URL: `/robots.txt` (не `/api/v1/seo/robots.txt`).

**Назначение:** robots.txt  
**Доступ:** Guest

**Response:** text/plain

```
User-agent: *
Disallow: /cabinet
Disallow: /admin
Disallow: /onboarding
Disallow: /login
Disallow: /register
Disallow: /payment
Allow: /

Sitemap: https://[DOMAIN]/sitemap.xml
```

**Бизнес-логика:** Обслуживается бекендом напрямую как `/robots.txt`. Фронт (Next.js) может также генерировать через `app/robots.ts`.

---

## 3. Бизнес-логика

### 3.1 Flow онбординга врача

```
Регистрация (email + password)
    │
    ▼
Подтверждение email (ссылка, TTL 24ч)
    │
    ▼
Выбор роли: врач / не-врач ──── не-врач → сохранить, показать "ожидайте"
    │
    ▼ (врач)
Заполнение анкеты:
  - ФИО, телефон, паспортные данные
  - Город, клиника, должность
  - Специализация, научная степень
    │
    ▼
Загрузка документов:
  - Диплом о высшем мед. образовании (обязательный)
  - Сертификат о переподготовке (опц.)
  - Сертификат онколога (опц.)
  - Другие (опц.)
    │
    ▼
Отправка заявки на модерацию
  → moderation_status: new → pending
  → уведомление администраторам
    │
    ▼
Решение администратора:
  ├── ОДОБРИТЬ
  │     → moderation_status → approved
  │     → генерация сертификата (TaskIQ)
  │     → уведомление врачу: "Одобрено. Оплатите вступительный взнос"
  │     │
  │     ▼
  │   Оплата вступительного взноса
  │     → payment created → redirect на платёжную страницу
  │     → webhook: payment succeeded
  │     → subscription activated (status=active, +12 months)
  │     → is_public = true (профиль виден на сайте)
  │     → добавить в Telegram-канал
  │     → чек НЕ формируется (взносы НКО, 251 НК РФ)
  │     → уведомление: "Добро пожаловать!"
  │
  └── ОТКЛОНИТЬ
        → moderation_status → rejected
        → уведомление врачу с причиной
        → врач может исправить и повторно подать
          (moderation_status → new → pending)
```

### 3.2 Flow оплаты вступительного взноса

```
1. Врач нажимает "Оплатить вступительный взнос"
2. POST /api/v1/subscriptions/pay { plan_id: entry_fee, idempotency_key }
3. Backend:
   a. Проверить: moderation_status = approved
   b. Проверить: has_medical_diploma = true
   c. Проверить: нет completed-платежей с типом entry_fee для этого user
   d. Найти план entry_fee → получить price и duration_months
   e. Проверить idempotency_key в Redis:
      - есть → вернуть существующий payment
      - нет → продолжить
   f. Создать subscription (status=pending)
   g. Создать payment (status=pending, product_type=entry_fee)
   h. Вызвать API платёжной системы (payment_provider): создать заказ
   i. Сохранить external_payment_id, external_payment_url
   j. Записать idempotency_key в Redis (TTL 24ч)
4. Вернуть { payment_url, payment_id, amount }
5. Frontend: redirect на payment_url
6. После возврата: polling GET /payments/{id}/status каждые 2-3 сек
7. Платёжная система вызывает webhook:
   a. Верификация подписи / IP whitelist
   b. Найти payment по external_payment_id
   c. Идемпотентность: если уже succeeded → return 200
   d. payment.status → succeeded, paid_at = now()
   e. subscription.status → active, starts_at = now(), ends_at = now() + 12m
   f. doctor_profiles.is_public = true
   g. Чек НЕ формируется (взносы НКО не фискализируются, 251 НК РФ)
   h. Создать notification (payment_success) → отправить email + tg
   i. Если telegram_binding → inviteChannelMember (TaskIQ)
   j. Уведомить админов через TG-бот
```

### 3.3 Flow продления подписки

```
1. Врач видит кнопку "Продлить подписку" (доступна за 30 дней до истечения)
2. POST /api/v1/subscriptions/pay { plan_id: annual_fee, idempotency_key }
3. Backend:
   a. Проверить: has_paid_entry_fee = true (есть succeeded entry_fee payment)
   b. Найти план annual_fee → price, duration_months
   c. Определить дату начала новой подписки:
      - если текущая ещё active → starts_at = current.ends_at (без потери дней)
      - если expired → starts_at = now()
   d. Создать subscription (status=pending)
   e. Создать payment → вызвать API платёжной системы
4. Frontend: polling GET /payments/{id}/status
5. Webhook при успешной оплате:
   a. payment.status → succeeded
   b. subscription.status → active
   c. Чек НЕ формируется (взносы НКО, 251 НК РФ)
   d. Если профиль был деактивирован (is_public=false из-за expired):
      → is_public = true
      → добавить обратно в Telegram-канал
```

### 3.4 Flow модерации изменений профиля

```
1. Врач редактирует публичные данные:
   PATCH /api/v1/profile/public { bio: "Новое описание", city_id: "uuid" }
2. Backend:
   a. Проверить что нет pending-черновика (409 если есть)
   b. Создать/обновить doctor_profile_drafts:
      - Записать ТОЛЬКО изменённые поля (остальные NULL)
      - status = pending, submitted_at = now()
   c. Уведомить админов
3. Администратор видит pending-черновики в карточке врача:
   POST /api/v1/admin/doctors/{id}/approve-draft { action: approve }
4. Backend при approve:
   a. Для каждого ненулевого поля в draft → обновить doctor_profiles
   b. draft.status = approved, reviewed_at = now(), reviewed_by = admin_id
   c. Создать moderation_history запись
   d. Инвалидировать кеш публичного каталога
   e. Уведомить врача: "Изменения одобрены"
5. Backend при reject:
   a. draft.status = rejected
   b. Уведомить врача с комментарием
   c. Врач может подать новые правки
```

### 3.5 Flow регистрации на мероприятие (3 сценария)

> **Актуализировано.** Flow переписан с учётом реализованной верификации email для гостей.

```
СЦЕНАРИЙ 1 — АВТОРИЗОВАННЫЙ (JWT):
1. POST /events/{id}/register { tariff_id, idempotency_key } + JWT
2. Backend:
   a. SELECT FOR UPDATE seats → проверить seats_available > 0
   b. Определить цену: doctor + approved + active_subscription → member_price, иначе → price
   c. Создать event_registration (status=pending)
   d. Создать payment → YooKassa API → payment_url
3. Response: { registration_id, payment_url, applied_price, action: null }
4. Фронт → redirect на payment_url

СЦЕНАРИЙ 2 — ГОСТЬ, EMAIL УЖЕ В БАЗЕ:
1. POST /events/{id}/register { tariff_id, idempotency_key, guest_email: "existing@..." }
2. Backend: находит user по email
3. Response: { action: "verify_existing", masked_email: "e***@..." }
4. Фронт → показывает форму ввода пароля
5. POST /auth/login { email, password } → получить JWT
6. Повторить СЦЕНАРИЙ 1 с JWT

СЦЕНАРИЙ 3 — ГОСТЬ, EMAIL НОВЫЙ:
1. POST /events/{id}/register { tariff_id, idempotency_key, guest_email: "new@..." }
2. Backend:
   a. Генерирует 6-значный код
   b. Сохраняет в Redis: event_reg_verify:{email} (TTL 600s)
   c. Инкрементирует event_reg_send_count:{email} (max 3 / 600s)
   d. Отправляет код на email (TaskIQ задача)
3. Response: { action: "verify_new_email", masked_email: "n***@..." }
4. Фронт → показывает форму ввода 6-значного кода
5. POST /events/{id}/confirm-guest-registration { email, code, tariff_id, idempotency_key, ... }
6. Backend:
   a. Проверяет код (max 5 попыток через event_reg_attempts:{email})
   b. Создаёт users + user_roles(non_doctor) с временным паролем
   c. Создаёт event_registration + payment → YooKassa → payment_url
   d. Отправляет email с временным паролем
7. Фронт → redirect на payment_url

WEBHOOK (для всех сценариев):
1. YooKassa webhook → POST /api/v1/payment/webhook
2. payment.status → completed
3. event_registration.status → confirmed
4. Atomic: UPDATE events SET seats_taken = seats_taken + 1
5. Уведомить пользователя: "Регистрация подтверждена"
```

### 3.6 Автоматическая деактивация при просрочке подписки

```
TaskIQ Scheduler задача: check_expired_subscriptions
Расписание: каждый день в 01:00 UTC

Алгоритм:
1. SELECT FROM subscriptions
   WHERE status = 'active' AND ends_at < now()
2. Для каждой просроченной подписки:
   a. subscription.status → expired
   b. doctor_profiles.is_public = false (триггер в БД)
   c. Если telegram_binding.is_in_channel = true:
      → Telegram API: banChatMember (удалить из канала)
      → telegram_binding.is_in_channel = false
   d. Создать notification: "Ваша подписка истекла. Продлите членство"
```

### 3.7 Расписание и логика cron-задач

| Задача                           | Расписание           | Описание                                                   |
|----------------------------------|----------------------|------------------------------------------------------------|
| `check_expired_subscriptions`    | Ежедневно 01:00 UTC | Деактивация просроченных подписок                          |
| `send_subscription_reminders`    | Ежедневно 09:00 UTC | Напоминания: 30, 7, 3, 1 день до истечения                 |
| `cleanup_expired_tokens`         | Ежедневно 03:00 UTC | Очистка устаревших записей из Redis                        |
| `generate_sitemap`               | Ежедневно 04:00 UTC | Перегенерация sitemap.xml                                  |
| `close_expired_voting_sessions`  | Каждый час           | Закрытие голосований, у которых ends_at < now()            |

**Детали `send_subscription_reminders`:**
```
1. Выбрать подписки WHERE status='active':
   - ends_at BETWEEN now() + 29d AND now() + 30d → reminder_30d
   - ends_at BETWEEN now() + 6d AND now() + 7d → reminder_7d
   - ends_at BETWEEN now() + 2d AND now() + 3d → reminder_3d
   - ends_at BETWEEN now() AND now() + 1d → reminder_last_day
2. Для каждой — проверить что notification с таким типом
   за сегодня ещё не создавалась (дедупликация)
3. Создать notification, отправить email + Telegram
```

---

## 4. Безопасность

### 4.1 Валидация загружаемых файлов

| Тип контента       | Допустимые форматы        | Max размер | Проверка                               |
|--------------------|--------------------------|------------|----------------------------------------|
| Фото профиля       | JPG, PNG                  | 5 MB       | Magic bytes + расширение + размеры     |
| Документы врача     | PDF, JPG, PNG             | 10 MB      | Magic bytes + расширение               |
| Обложки мероприятий | JPG, PNG                  | 5 MB       | Magic bytes + расширение               |
| Фотогалереи        | JPG, PNG                  | 10 MB      | Magic bytes + расширение               |
| Документы орг.      | PDF                       | 20 MB      | Magic bytes + расширение               |
| Excel-импорт       | XLSX                      | 5 MB       | Magic bytes + расширение               |

**Правила:**
1. Проверять magic bytes файла (не доверять Content-Type и расширению)
2. Сканировать на вредоносное содержимое (ClamAV, опционально)
3. Генерировать новые имена файлов (UUID) при сохранении
4. Хранить файлы вне веб-корня, отдавать через presigned URL
5. Ограничить максимальный размер multipart-запроса на уровне nginx (client_max_body_size)

### 4.2 Защита от повторных платежей (идемпотентность)

```
Механизм:
1. Клиент генерирует idempotency_key (UUID v4) перед первым запросом
2. Сервер: при получении запроса на оплату проверяет idempotency_key в Redis
   - Ключ: idempotency:{user_id}:{endpoint}:{key}
   - TTL: 24 часа
3. Если ключ найден → вернуть ответ из кеша (тот же payment_url)
4. Если ключ не найден → создать платёж, сохранить ключ и ответ
5. На уровне БД: partial unique index на external_payment_id
6. Webhook: повторный вызов с тем же order_id не изменяет уже completed-платёж
```

### 4.3 Rate Limiting

| Эндпоинт                          | Лимит                    | Ключ                  |
|------------------------------------|--------------------------|-----------------------|
| POST /auth/register                | 3/мин                    | IP                    |
| POST /auth/login                   | 5/мин per email, 20/мин | IP + email            |
| POST /auth/forgot-password         | 3/час                    | email                 |
| POST /auth/verify-email            | 10/мин                   | IP                    |
| POST /subscriptions/pay            | 3/мин                    | user_id               |
| POST /events/*/register            | 5/мин                    | user_id или IP        |
| POST /events/*/register (отправка кода) | 3 / 10 мин            | email (Redis: `event_reg_send_count:{email}`) |
| POST /events/*/confirm-guest-registration (ввод кода) | 5 попыток / код | email (Redis: `event_reg_attempts:{email}`) |
| POST /*/upload (файлы)             | 10/мин                   | user_id               |
| POST /telegram/webhook             | 100/мин                  | IP (Telegram servers) |
| GET /* (публичные)                 | 60/мин                   | IP                    |
| GET /admin/*                       | 120/мин                  | user_id               |

**Реализация:** Redis-based sliding window counter. Header `X-RateLimit-Remaining` в ответах. При превышении — 429 Too Many Requests с `Retry-After`.

### 4.4 Дополнительные меры безопасности

| Мера                            | Реализация                                                      |
|---------------------------------|-----------------------------------------------------------------|
| CORS                            | Whitelist: frontend-домен. Credentials: true                    |
| CSRF                            | Не требуется (JWT, не cookie-based auth). SameSite=Strict для refresh |
| SQL Injection                   | Параметризованные запросы через SQLAlchemy (ORM)               |
| XSS                             | Sanitize HTML-контента при записи (bleach). CSP-заголовки      |
| Шифрование паспортных данных    | AES-256-GCM, ключ в env, расшифровка только при чтении admin    |
| Audit log                       | moderation_history для всех критичных действий                  |
| Webhook-безопасность (ПСБ)      | IP whitelist + HMAC подпись                                     |
| Webhook-безопасность (Telegram) | Secret token в заголовке X-Telegram-Bot-Api-Secret-Token        |
| Хранение секретов               | Переменные окружения, docker secrets, не в коде                 |
| HTTPS                           | Обязательно. HSTS header. TLS 1.2+                             |
| Логирование                     | Structured JSON logs. Не логировать пароли, токены, PD          |


