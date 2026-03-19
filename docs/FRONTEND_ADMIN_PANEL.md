# Админ-панель — полная документация API для фронтенда

**Дата:** 2026-03-19 (обновлено — истечение платежей, status_label, payment_url)  
**Базовый URL:** `{API_URL}/api/v1`  
**Swagger:** `{API_URL}/docs`  
**Провайдер оплаты:** Moneta (BPA PayAnyWay)

---

## Содержание

1. [Общие правила](#1-общие-правила)
2. [Dashboard](#2-dashboard)
3. [Врачи](#3-врачи)
4. [Пользователи портала](#4-пользователи-портала)
5. [Мероприятия](#5-мероприятия)
6. [Платежи и возвраты](#6-платежи-и-возвраты)
7. [Подписки и планы](#7-подписки-и-планы)
8. [Статьи и темы](#8-статьи-и-темы)
9. [Документы организации](#9-документы-организации)
10. [Контентные блоки](#10-контентные-блоки)
11. [Настройки сайта и города](#11-настройки-и-города)
12. [SEO-страницы](#12-seo-страницы)
13. [Сотрудники (admin users)](#13-сотрудники)
14. [Уведомления](#14-уведомления)
15. [Голосование](#15-голосование)
16. [Как работает платёжная система](#16-платёжная-система)
17. [Карта страниц → эндпоинты](#17-карта-страниц)

---

## 1. Общие правила

### 1.1 Авторизация

JWT RS256, заголовок `Authorization: Bearer {access_token}`.  
Refresh — HttpOnly cookie `refresh_token_admin`, path `/api/v1/auth`.

### 1.2 Роли доступа

| Роль | Доступ |
|------|--------|
| `admin` | Все операции, включая удаление, настройки, планы |
| `manager` | Врачи, мероприятия, контент, уведомления, dashboard (без настроек, удаления, планов) |
| `accountant` | Только платежи |

### 1.3 Формат ответов

**Пагинация:** `{ data: [...], total, limit, offset }`.  
**Ошибка:** `{ error: { code, message, details } }`.  
**Стандартные коды ошибок:** 401, 403, 404, 409, 422.

### 1.4 Общие query-параметры для списков

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | ≥0 |
| `sort_by` | string | `"created_at"` | Поле сортировки |
| `sort_order` | string | `"desc"` | `asc` / `desc` |

---

## 2. Dashboard

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/dashboard` | admin, manager |

**Ответ:**
```json
{
  "total_users": 1250,
  "total_doctors": 85,
  "active_doctors": 62,
  "pending_review_doctors": 8,
  "active_subscriptions": 55,
  "expiring_30d": 12,
  "payment_total_month": 450000.0,
  "payment_total_year": 3200000.0,
  "upcoming_events": 3,
  "moderation_queue": 5
}
```

---

## 3. Врачи

### 3.1 Список врачей

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/doctors` | admin, manager |

**Query параметры:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | — |
| `status` | string? | — | `active` / `pending_review` / `rejected` |
| `subscription_status` | string? | — | `active` / `expired` / `none` |
| `city_id` | UUID? | — | Фильтр по городу |
| `has_data_changed` | bool? | — | Только с изменёнными данными (черновиками) |
| `search` | string? | — | Поиск по имени (мин. 2 символа) |
| `sort_by` | string | `created_at` | — |
| `sort_order` | string | `desc` | — |

### 3.2 Создание врача

| Метод | Путь | Роль |
|-------|------|------|
| POST | `/admin/doctors` | admin, manager |

**Body:**
```json
{
  "email": "doctor@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "phone": "+79001234567",
  "middle_name": "Сергеевич",
  "city_id": "uuid",
  "clinic_name": "Клиника А",
  "position": "Главный врач",
  "academic_degree": "к.м.н.",
  "bio": "...",
  "public_email": "doctor@clinic.ru",
  "public_phone": "+7...",
  "specialization_ids": ["uuid", "uuid"],
  "status": "approved",
  "send_invite": true
}
```

**`send_invite: true`** — отправит email с временным паролем. **409** — email уже существует.

### 3.3 Карточка врача

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/doctors/{profile_id}` | admin, manager |

### 3.4 Модерация

| Метод | Путь | Body | Описание |
|-------|------|------|----------|
| POST | `/admin/doctors/{id}/moderate` | `{ action: "approve"/"reject", comment: "..." }` | Одобрить/отклонить анкету. `comment` обязателен при reject |
| POST | `/admin/doctors/{id}/approve-draft` | `{ action: "approve"/"reject", rejection_reason: "..." }` | Одобрить/отклонить черновик изменений |
| POST | `/admin/doctors/{id}/toggle-active` | `{ is_public: true/false }` | Вкл/выкл видимость в каталоге |

### 3.5 Коммуникация

| Метод | Путь | Body |
|-------|------|------|
| POST | `/admin/doctors/{id}/send-reminder` | `{ message: "..." }` |
| POST | `/admin/doctors/{id}/send-email` | `{ subject: "...", body: "..." }` |

### 3.6 Импорт из Excel

| Метод | Путь | Body | Описание |
|-------|------|------|----------|
| POST | `/admin/doctors/import` | FormData: `file` | Фоновый импорт |
| GET | `/admin/doctors/import/{task_id}` | — | Статус импорта |

---

## 4. Пользователи портала

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/portal-users` | admin, manager |
| GET | `/admin/portal-users/{user_id}` | admin, manager |

**Query:** `limit`, `offset`, `search` (мин. 2), `sort_by`, `sort_order`.

---

## 5. Мероприятия

### 5.1 CRUD

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/events` | Список мероприятий |
| POST | `/admin/events` | Создать мероприятие (FormData) |
| GET | `/admin/events/{id}` | Детали |
| PATCH | `/admin/events/{id}` | Обновить (FormData) |
| DELETE | `/admin/events/{id}` | Удалить (только admin) |

**GET `/admin/events` — Query:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 20 | — |
| `offset` | int | 0 | — |
| `status` | string? | — | `upcoming` / `ongoing` / `finished` / `cancelled` |
| `date_from` | datetime? | — | — |
| `date_to` | datetime? | — | — |
| `sort_by` | string | `event_date` | — |
| `sort_order` | string | `desc` | — |

**POST/PATCH — FormData поля:**

| Поле | Тип | Обязателен | Описание |
|------|-----|------------|----------|
| `title` | string | POST: да | Макс 500 |
| `slug` | string? | нет | Генерируется из title если не указан |
| `event_date` | datetime | POST: да | — |
| `event_end_date` | datetime? | нет | — |
| `description` | string? | нет | — |
| `location` | string? | нет | — |
| `status` | string | нет | Default: `upcoming` |
| `cover_image` | File? | нет | — |

### 5.2 Тарифы

| Метод | Путь | Body |
|-------|------|------|
| POST | `/admin/events/{id}/tariffs` | см. ниже |
| PATCH | `/admin/events/{id}/tariffs/{tid}` | те же поля, все optional |
| DELETE | `/admin/events/{id}/tariffs/{tid}` | — |

**POST body:**
```json
{
  "name": "Участник",
  "description": "...",
  "conditions": "...",
  "details": "...",
  "price": 10000.0,
  "member_price": 5000.0,
  "benefits": ["Сертификат", "Обед"],
  "seats_limit": 100,
  "sort_order": 0
}
```

**`member_price`** — льготная цена для врачей с активной подпиской. Бекенд автоматически применяет при регистрации.

### 5.3 Регистрации

| Метод | Путь | Query |
|-------|------|-------|
| GET | `/admin/events/{id}/registrations` | `limit`, `offset`, `status` |

### 5.4 Галереи и фото

| Метод | Путь | Body |
|-------|------|------|
| POST | `/admin/events/{id}/galleries` | `{ title, access_level: "public"/"members_only" }` |
| POST | `/admin/events/{id}/galleries/{gid}/photos` | FormData: `files` (multiple) |

### 5.5 Видеозаписи

| Метод | Путь | Body |
|-------|------|------|
| POST | `/admin/events/{id}/recordings` | FormData: `title`, `video_source`, `video_url`, `duration_seconds`, `access_level`, `recording_status`, `video_file` |
| PATCH | `/admin/events/{id}/recordings/{rid}` | JSON: те же поля optional |

**`access_level`:** `public` / `members_only` / `participants_only`.

---

## 6. Платежи и возвраты

### 6.1 Список платежей

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/payments` | admin, manager, accountant |

**Query параметры:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `limit` | int | 20 | 1–100 |
| `offset` | int | 0 | — |
| `status` | string? | — | `pending` / `succeeded` / `failed` / `expired` / `refunded` |
| `product_type` | string? | — | `entry_fee` / `subscription` / `event` |
| `user_id` | UUID? | — | Фильтр по пользователю |
| `date_from` | datetime? | — | — |
| `date_to` | datetime? | — | — |
| `sort_by` | string | `created_at` | — |
| `sort_order` | string | `desc` | — |

**Ответ:**
```json
{
  "data": [{
    "id": "uuid",
    "user": { "id": "uuid", "email": "doctor@example.com", "full_name": "Иван Петров" },
    "amount": 20000.0,
    "product_type": "entry_fee",
    "payment_provider": "moneta",
    "status": "succeeded",
    "status_label": "Оплачен",
    "description": "Вступительный + Годовой взнос",
    "payment_url": null,
    "expires_at": null,
    "has_receipt": true,
    "paid_at": "2026-01-15T14:30:00Z",
    "created_at": "2026-01-15T14:25:00Z"
  }],
  "summary": {
    "total_amount": 450000.0,
    "count_completed": 30,
    "count_pending": 2
  },
  "total": 32, "limit": 20, "offset": 0
}
```

**Новые поля (обновление 2026-03-19):**

| Поле | Тип | Описание |
|------|-----|----------|
| `status_label` | string | Человекочитаемый статус на русском. Используйте для отображения в таблице вместо raw `status` |
| `payment_url` | string \| null | Ссылка на оплату. Возвращается **только** для `status=pending` и если срок не истёк. Админ может скопировать и отправить пользователю |
| `expires_at` | datetime \| null | Срок действия платежа. Только для `status=pending`. После этой даты ссылка = `null`, платёж переходит в `expired` |

**Маппинг статусов для отображения (status → status_label):**

| status | status_label | Цвет (рекомендация) |
|--------|-------------|---------------------|
| `pending` | Ожидает оплаты | Жёлтый/оранжевый |
| `succeeded` | Оплачен | Зелёный |
| `failed` | Отклонён | Красный |
| `expired` | Истёк | Серый |
| `refunded` | Возвращён | Фиолетовый |
| `partially_refunded` | Частичный возврат | Фиолетовый светлый |

**ВАЖНО:** Ранее фронт мог ошибочно интерпретировать `status: "pending"` как «На модерации». Это **неверно**. Статус `pending` у платежа = «Ожидает оплаты». «На модерации» — это статус **профиля врача** (`moderation_status: "pending_review"`), который не связан с платежами. Используйте `status_label` для корректного отображения
```

### 6.2 Ручной платёж

| Метод | Путь | Роль |
|-------|------|------|
| POST | `/admin/payments/manual` | admin, manager, accountant |

**Body:**
```json
{
  "user_id": "uuid",
  "amount": 20000.0,
  "product_type": "entry_fee",
  "description": "Оплата наличными на конференции",
  "subscription_id": "uuid",
  "event_registration_id": null
}
```

Бекенд активирует подписку или подтверждает регистрацию автоматически.

### 6.3 Возврат

| Метод | Путь | Роль |
|-------|------|------|
| POST | `/admin/payments/{payment_id}/refund` | admin, manager, accountant |

**Body:**
```json
{
  "amount": 5000.0,
  "reason": "Клиент запросил возврат"
}
```

**`amount: null`** — полный возврат.

**Ответ:**
```json
{
  "refund_id": "...",
  "payment_id": "...",
  "status": "pending",
  "amount": 5000.0
}
```

**ВАЖНО:** Для Moneta автоматический возврат **не поддерживается**. Бекенд вернёт ошибку 422 с сообщением: «Возвраты через текущий провайдер не поддерживаются. Используйте ЛК провайдера». Админу нужно делать возврат через личный кабинет Moneta вручную.

---

## 7. Подписки и планы

### 7.1 CRUD планов

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/plans` | admin |
| POST | `/admin/plans` | admin |
| PATCH | `/admin/plans/{plan_id}` | admin |
| DELETE | `/admin/plans/{plan_id}` | admin |

**POST body:**
```json
{
  "code": "annual",
  "name": "Годовой членский взнос",
  "description": "Ежегодный взнос для членства в ассоциации",
  "price": 15000.0,
  "duration_months": 12,
  "is_active": true,
  "sort_order": 0,
  "plan_type": "subscription"
}
```

**PATCH body:** те же поля, все optional.

**`plan_type`:** `entry_fee` (вступительный) или `subscription` (членский). Должен быть **ровно один** активный entry_fee план. **409** — `code` уже существует. **DELETE** не удалит, если есть активные подписки.

### 7.2 Как работает подписка (для понимания)

1. Врач проходит онбординг → модерация → `approved`.
2. Оплачивает → webhook → `Subscription.status=active`, `DoctorProfile.status=active`.
3. Профиль появляется в публичном каталоге.
4. Cron каждый час: если `ends_at < now` → `Subscription.status=expired` → врач скрыт из каталога.
5. Cron ежедневно: напоминания за 30/7/3/1 день до истечения.
6. Продление: новый `POST /subscriptions/pay` → `ends_at` продлевается **от текущего ends_at**.

---

## 8. Статьи и темы

### 8.1 Статьи

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/articles` | Список (Query: `limit`, `offset`, `status`, `theme_slug`) |
| POST | `/admin/articles` | Создать (FormData) |
| GET | `/admin/articles/{id}` | Детали |
| PATCH | `/admin/articles/{id}` | Обновить (FormData) |
| DELETE | `/admin/articles/{id}` | Удалить (только admin) |

**POST/PATCH — FormData поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Заголовок |
| `content` | string | Текст (HTML/Markdown) |
| `slug` | string? | Генерируется из title |
| `excerpt` | string? | Краткое описание |
| `status` | string | `draft` / `published` / `archived` (default: `draft`) |
| `seo_title` | string? | — |
| `seo_description` | string? | — |
| `theme_ids` | string | JSON-массив UUID тем: `["uuid1","uuid2"]`. Пустой массив `[]` — снять все темы |
| `cover_image` | File? | — |

### 8.2 Темы

| Метод | Путь | Body |
|-------|------|------|
| GET | `/admin/article-themes` | Query: `active`, `has_articles` |
| POST | `/admin/article-themes` | `{ title, slug, is_active, sort_order }` |
| PATCH | `/admin/article-themes/{id}` | те же, optional |
| DELETE | `/admin/article-themes/{id}` | — (только admin) |

---

## 9. Документы организации

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/organization-documents` | Список (Query: `limit`, `offset`) |
| POST | `/admin/organization-documents` | Создать (FormData) |
| PATCH | `/admin/organization-documents/{id}` | Обновить (FormData) |
| PATCH | `/admin/organization-documents/reorder` | Перестановка: `{ items: [{ id, sort_order }] }` |
| DELETE | `/admin/organization-documents/{id}` | — (только admin) |

**POST/PATCH — FormData:**

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Название |
| `content` | string? | Текст |
| `slug` | string? | — |
| `sort_order` | int | 0 |
| `is_active` | bool | true |
| `file` | File? | Прикреплённый файл |
| `remove_file` | string? | `"true"` — удалить файл |

---

## 10. Контентные блоки

Универсальные блоки контента, привязанные к сущности (статья, мероприятие, профиль врача, документ).

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/content-blocks` | Список блоков сущности |
| POST | `/admin/content-blocks` | Создать блок |
| PATCH | `/admin/content-blocks/{id}` | Обновить |
| DELETE | `/admin/content-blocks/{id}` | Удалить |
| POST | `/admin/content-blocks/reorder` | Перестановка |

**GET — обязательные Query:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `entity_type` | string | `article` / `event` / `doctor_profile` / `organization_document` |
| `entity_id` | UUID | ID сущности-владельца |
| `locale` | string | Default: `ru` |

**POST body:**
```json
{
  "entity_type": "article",
  "entity_id": "uuid",
  "block_type": "text",
  "locale": "ru",
  "sort_order": 0,
  "title": "Заголовок блока",
  "content": "Текст...",
  "media_url": null,
  "thumbnail_url": null,
  "link_url": null,
  "link_label": null,
  "device_type": "both",
  "block_metadata": null
}
```

**`block_type`:** `text` / `image` / `video` / `gallery` / `link`.  
**`device_type`:** `both` / `mobile` / `desktop`.

**Перестановка:**
```json
{ "items": [{ "id": "uuid", "sort_order": 0 }, { "id": "uuid", "sort_order": 1 }] }
```

---

## 11. Настройки и города

### 11.1 Настройки сайта

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/settings` | admin |
| PATCH | `/admin/settings` | admin |

**Body:** `{ data: { "contact_email": "...", "contact_phone": "...", ... } }`.

Частичное обновление — передать только изменённые ключи.

### 11.2 Города

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/cities` | admin, manager |
| POST | `/admin/cities` | admin, manager |
| PATCH | `/admin/cities/{id}` | admin, manager |
| DELETE | `/admin/cities/{id}` | admin |

**POST body:** `{ name: "Москва", slug: "moskva", sort_order: 0 }`.  
**PATCH body:** `{ name?, slug?, sort_order?, is_active? }`.

**Ответ:**
```json
{ "id": "uuid", "name": "Москва", "slug": "moskva", "sort_order": 0, "is_active": true, "doctors_count": 15 }
```

---

## 12. SEO-страницы

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/seo-pages` | admin, manager |
| GET | `/admin/seo-pages/{slug}` | admin, manager |
| POST | `/admin/seo-pages` | admin, manager |
| PATCH | `/admin/seo-pages/{slug}` | admin, manager |
| DELETE | `/admin/seo-pages/{slug}` | admin |

**Query (GET list):** `limit` (default 50, max 200), `offset`.

**POST/PATCH body:**
```json
{
  "slug": "home",
  "title": "Ассоциация трихологов",
  "description": "...",
  "og_title": "...",
  "og_description": "...",
  "og_image_url": "https://...",
  "og_url": "https://trichology.ru",
  "og_type": "website",
  "twitter_card": "summary_large_image",
  "canonical_url": "https://trichology.ru",
  "custom_meta": { "key": "value" }
}
```

---

## 13. Сотрудники

| Метод | Путь | Роль |
|-------|------|------|
| GET | `/admin/users` | admin |
| POST | `/admin/users` | admin |
| GET | `/admin/users/{id}` | admin |
| PATCH | `/admin/users/{id}` | admin |
| DELETE | `/admin/users/{id}` | admin |

**GET Query:** `limit`, `offset`, `role` (`admin`/`manager`/`accountant`), `search`.

**POST body:**
```json
{ "email": "manager@example.com", "password": "securepassword", "role": "manager" }
```

**PATCH body:** `{ email?, role?, is_active? }`.

**DELETE:** Мягкое удаление. Нельзя удалить **себя** (403).

---

## 14. Уведомления

| Метод | Путь | Роль |
|-------|------|------|
| POST | `/admin/notifications/send` | admin, manager |
| GET | `/admin/notifications` | admin, manager |

**POST body:**
```json
{
  "user_id": "uuid",
  "type": "reminder",
  "title": "Напоминание о продлении",
  "body": "Ваша подписка истекает через 7 дней",
  "channels": ["email", "telegram"]
}
```

**GET Query:** `limit`, `offset`, `user_id`, `status` (`sent`/`failed`/`pending`).

---

## 15. Голосование

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/admin/voting` | Список сессий (Query: `limit`, `offset`, `status`) |
| POST | `/admin/voting` | Создать сессию |
| GET | `/admin/voting/{id}` | Детали сессии |
| PATCH | `/admin/voting/{id}` | Обновить (status, title, ends_at) |
| GET | `/admin/voting/{id}/results` | Результаты голосования |

**POST body:**
```json
{
  "title": "Выборы председателя 2026",
  "description": "...",
  "starts_at": "2026-04-01T09:00:00Z",
  "ends_at": "2026-04-15T18:00:00Z",
  "candidates": [
    { "doctor_profile_id": "uuid", "description": "Кандидат 1..." },
    { "doctor_profile_id": "uuid", "description": "Кандидат 2..." }
  ]
}
```

**PATCH body:** `{ status?: "active"/"closed"/"cancelled", title?, ends_at? }`.

**Результаты:**
```json
{
  "session": { "id": "uuid", "title": "...", "status": "closed", "total_votes": 45, "total_eligible_voters": 62 },
  "results": [
    { "candidate": { "id": "uuid", "full_name": "Иван Петров" }, "votes_count": 28, "percentage": 62.2 },
    { "candidate": { "id": "uuid", "full_name": "Мария Сидорова" }, "votes_count": 17, "percentage": 37.8 }
  ]
}
```

---

## 16. Как работает платёжная система

### 16.1 Провайдер

**Moneta** (Moneta.Assistant + BPA PayAnyWay). Переключается через `PAYMENT_PROVIDER` env var. YooKassa сохранена как fallback.

### 16.2 Типы платежей

| product_type | Что включает | Когда |
|-------------|--------------|-------|
| `entry_fee` | Вступительный + годовой в одном платеже | Первая оплата или перерыв >60 дней |
| `subscription` | Только годовой | Продление (перерыв ≤60 дней) |
| `event` | Оплата мероприятия | При регистрации |

### 16.3 Фискализация (54-ФЗ)

BPA PayAnyWay формирует чеки автоматически. `inventory[]` с наименованиями позиций передаётся при создании invoice. Чек приходит через receipt webhook (1–30 мин после оплаты). Бекенд сохраняет `receipt_url` и шлёт email пользователю.

### 16.4 Что видно в админке

- **`GET /admin/payments`** — все платежи с фильтрами, summary.
- **`has_receipt: true`** — чек сформирован.
- **`payment_provider: "moneta"`** — через Moneta.
- **Ручной платёж** — `POST /admin/payments/manual` создаёт запись `succeeded`, активирует подписку/регистрацию.
- **Возврат Moneta** — только вручную через ЛК провайдера. Бекенд вернёт 422.

### 16.5 Статусы платежей

| Status | status_label | Описание |
|--------|-------------|----------|
| `pending` | Ожидает оплаты | Создан, ожидает оплату на стороне Moneta. Есть `payment_url` и `expires_at` |
| `succeeded` | Оплачен | Оплачен (webhook получен) |
| `failed` | Отклонён | Отменён пользователем или ошибка платёжной системы |
| `expired` | Истёк | Не оплачен в отведённое время (по умолчанию 24 часа). Связанная подписка отменена — пользователь может создать новый платёж |
| `refunded` | Возвращён | Полный возврат |
| `partially_refunded` | Частичный возврат | Частичный возврат |

**Жизненный цикл платежа:**
```
pending → succeeded (webhook оплаты от Moneta)
pending → failed    (webhook отмены от Moneta)
pending → expired   (автоматически через 24 часа, если нет оплаты)
succeeded → refunded / partially_refunded (возврат)
```

### 16.6 Cron-задачи (автоматические)

| Задача | Частота | Описание |
|--------|---------|----------|
| `deactivate_expired_subscriptions` | Каждый час | `active` → `expired`, удаление из Telegram-канала |
| `check_expiring_subscriptions` | Ежедневно | Email-напоминания за 30/7/3/1 день |
| `expire_stale_pending_payments` | Каждые 30 мин | `pending` платежи с `expires_at < now()` → `expired`. Связанные `pending_payment` подписки → `cancelled` |

---

## 17. Карта страниц → эндпоинты

| Страница | Эндпоинты |
|----------|-----------|
| Dashboard | `GET /admin/dashboard` |
| Врачи (список) | `GET /admin/doctors`, `GET /admin/cities` |
| Врач (карточка) | `GET /admin/doctors/{id}`, `POST .../moderate`, `POST .../approve-draft`, `POST .../toggle-active`, `POST .../send-reminder`, `POST .../send-email` |
| Импорт врачей | `POST /admin/doctors/import`, `GET .../import/{task_id}` |
| Мероприятия (список) | `GET /admin/events` |
| Мероприятие (создание) | `POST /admin/events` |
| Мероприятие (редакт.) | `GET /admin/events/{id}`, `PATCH /admin/events/{id}`, тарифы, галереи, записи |
| Регистрации | `GET /admin/events/{id}/registrations` |
| Платежи | `GET /admin/payments`, `POST /admin/payments/manual`, `POST .../refund` |
| Статьи | `GET/POST/PATCH/DELETE /admin/articles` |
| Темы статей | `GET/POST/PATCH/DELETE /admin/article-themes` |
| Документы орг. | `GET/POST/PATCH/DELETE /admin/organization-documents`, `PATCH .../reorder` |
| Контентные блоки | `GET/POST/PATCH/DELETE /admin/content-blocks`, `POST .../reorder` |
| Настройки | `GET/PATCH /admin/settings` |
| Города | `GET/POST/PATCH/DELETE /admin/cities` |
| Планы подписок | `GET/POST/PATCH/DELETE /admin/plans` |
| SEO | `GET/POST/PATCH/DELETE /admin/seo-pages` |
| Сотрудники | `GET/POST/PATCH/DELETE /admin/users` |
| Уведомления | `GET /admin/notifications`, `POST .../send` |
| Голосование | `GET/POST/PATCH /admin/voting`, `GET .../results` |
| Пользователи портала | `GET /admin/portal-users`, `GET .../{ id}` |

---

## Enum-справочник

| Группа | Значения |
|--------|----------|
| Subscription status | `pending_payment`, `active`, `expired` |
| Payment status | `pending`, `succeeded`, `failed`, `expired`, `refunded`, `partially_refunded` |
| Product type | `entry_fee`, `subscription`, `event` |
| Doctor status | `pending_review`, `approved`, `active`, `inactive` |
| Event status | `upcoming`, `ongoing`, `finished`, `cancelled` |
| Registration status | `pending`, `confirmed`, `cancelled` |
| Article status | `draft`, `published`, `archived` |
| Plan type | `entry_fee`, `subscription` |
| Content block type | `text`, `image`, `video`, `gallery`, `link` |
| Access level | `public`, `members_only`, `participants_only` |
| Staff role | `admin`, `manager`, `accountant` |
| Notification status | `sent`, `failed`, `pending` |
| Voting status | `active`, `closed`, `cancelled` |
