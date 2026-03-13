# Анализ фантомных эндпоинтов: фронтенд vs бэкенд

**Дата:** 2026-03-12
**Swagger:** `https://trihoback.mediann.dev/docs`

---

## Сводка

| # | Эндпоинт на фронте | Вердикт | Действие |
|---|---------------------|---------|----------|
| 1 | `GET /admin/users/search?q=` | **Ошибка фронта** | Использовать `GET /admin/portal-users?search=...` |
| 2 | `GET /payments/{id}/receipt` | **Ошибка фронта** | Путь: `GET /subscriptions/payments/{id}/receipt` |
| 3 | `GET /cities` | **Корректно** | Публичный эндпоинт, работает |
| 4 | `CRUD /admin/users` | **Реализовано** | Новый модуль Admin - Users |
| 5 | `CRUD /admin/content-blocks` + `reorder` | **Реализовано** | Новый модуль Admin - Content Blocks |
| 6 | `PATCH /admin/organization-documents/reorder` | **Реализовано** | Добавлен в существующий роутер |
| 7 | `POST /admin/payments/{id}/refund` | **Реализовано** | Добавлен в payments_admin |
| 8 | `GET /admin/voting/{id}` | **Реализовано** | Добавлен в voting |

---

## A. Ошибки путей на фронтенде (бэкенд менять НЕ нужно)

### 1. GET /admin/users/search?q= → использовать portal-users

Фронтенд (`payments/page.tsx:68`) использует `/admin/users/search?q=` для поиска пользователей в модальном окне ручного платежа.

**Правильный эндпоинт:**
```
GET /api/v1/admin/portal-users?search=query&limit=10
```

Это существующий эндпоинт, который ищет по email (минимум 2 символа), возвращает пользователей с ролями `doctor` / `user`. Для ручного платежа (`ManualPaymentRequest.user_id`) это полностью покрывает потребность.

**Ответ:**
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "full_name": "Иванов Иван",
      "role": "doctor",
      "role_display": "Врач",
      "created_at": "2026-01-15T09:30:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### 2. GET /payments/{id}/receipt → путь не совпадает

Фронтенд использует `/payments/${id}/receipt`, реальный путь на бэкенде:

```
GET /api/v1/subscriptions/payments/{payment_id}/receipt
```

Роутер `subscriptions` имеет prefix `/subscriptions`, внутри эндпоинт `/payments/{payment_id}/receipt`.

### 3. GET /cities → корректно

Публичный эндпоинт `GET /api/v1/cities` работает, возвращает `{ "data": [...] }`.

---

## B. Реализованные недостающие эндпоинты

### 4. CRUD администраторов: /admin/users

Новый модуль для управления сотрудниками системы (admin, manager, accountant).

Существующий `GET /admin/portal-users` явно **исключает** admin/manager/accountant, показывая только doctor/user. Поэтому для управления сотрудниками нужны отдельные эндпоинты.

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET | `/api/v1/admin/users` | Список сотрудников с пагинацией и поиском | admin |
| POST | `/api/v1/admin/users` | Создание сотрудника | admin |
| GET | `/api/v1/admin/users/{id}` | Детали сотрудника | admin |
| PATCH | `/api/v1/admin/users/{id}` | Обновление (email, role, is_active) | admin |
| DELETE | `/api/v1/admin/users/{id}` | Soft-delete (нельзя удалить себя) | admin |

**Query-параметры GET /admin/users:**
- `limit` (1-100, default 20)
- `offset` (>=0, default 0)
- `role` — фильтр: `admin`, `manager`, `accountant`
- `search` — поиск по email (min 2 символа)

**POST /admin/users body:**
```json
{
  "email": "manager@example.com",
  "password": "SecurePass123!",
  "role": "manager"
}
```

**Response AdminUserDetailResponse:**
```json
{
  "id": "uuid",
  "email": "manager@example.com",
  "role": "manager",
  "role_display": "Менеджер",
  "is_active": true,
  "is_verified": false,
  "last_login_at": null,
  "created_at": "2026-03-12T10:00:00Z"
}
```

### 5. CRUD контентных блоков: /admin/content-blocks

Модель `ContentBlock` существует в БД (таблица `content_blocks`). Поддерживает типы сущностей: `article`, `event`, `doctor_profile`, `organization_document`. Типы блоков: `text`, `image`, `video`, `gallery`, `link`.

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET | `/api/v1/admin/content-blocks?entity_type=...&entity_id=...` | Список блоков для сущности | admin, manager |
| POST | `/api/v1/admin/content-blocks` | Создание блока | admin, manager |
| PATCH | `/api/v1/admin/content-blocks/{id}` | Обновление блока | admin, manager |
| DELETE | `/api/v1/admin/content-blocks/{id}` | Удаление блока | admin, manager |
| POST | `/api/v1/admin/content-blocks/reorder` | Массовая перестановка sort_order | admin, manager |

**POST body:**
```json
{
  "entity_type": "article",
  "entity_id": "uuid",
  "block_type": "text",
  "locale": "ru",
  "sort_order": 0,
  "title": "Введение",
  "content": "<p>Текст блока...</p>",
  "device_type": "both"
}
```

**Reorder body:**
```json
{
  "items": [
    {"id": "uuid-1", "sort_order": 0},
    {"id": "uuid-2", "sort_order": 1},
    {"id": "uuid-3", "sort_order": 2}
  ]
}
```

### 6. Перестановка документов организации

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| PATCH | `/api/v1/admin/organization-documents/reorder` | Массовая перестановка | admin, manager |

**Body:**
```json
{
  "items": [
    {"id": "uuid-1", "sort_order": 0},
    {"id": "uuid-2", "sort_order": 1}
  ]
}
```

### 7. Возврат платежа через YooKassa

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| POST | `/api/v1/admin/payments/{payment_id}/refund` | Инициирует возврат | admin, accountant |

Возврат идёт через YooKassa API (`POST /v3/refunds`). Поддерживается частичный и полный возврат. После инициации статус = `pending`, финальное подтверждение придёт через webhook `refund.succeeded`.

**Body:**
```json
{
  "amount": 5000.0,
  "reason": "Клиент запросил возврат"
}
```
Если `amount` не указан — полный возврат на сумму платежа.

**Response:**
```json
{
  "refund_id": "2da5c87d-...",
  "payment_id": "2da5c87d-...",
  "status": "pending",
  "amount": 5000.0
}
```

**Ограничения:**
- Нельзя вернуть платёж со статусом != `succeeded`
- Нельзя вернуть ручной платёж (без `external_payment_id`)
- Сумма возврата не может превышать сумму платежа

### 8. Детали сессии голосования по ID

| Метод | Путь | Описание | Доступ |
|-------|------|----------|--------|
| GET | `/api/v1/admin/voting/{session_id}` | Полные данные сессии с кандидатами | admin, manager |

**Response:**
```json
{
  "id": "uuid",
  "title": "Выборы президента 2026",
  "description": "Описание голосования",
  "status": "active",
  "starts_at": "2026-04-01T10:00:00Z",
  "ends_at": "2026-04-15T18:00:00Z",
  "candidates": [
    {
      "id": "uuid",
      "doctor_profile_id": "uuid",
      "full_name": "Иванов Иван",
      "photo_url": "/uploads/photo.jpg",
      "description": "Кандидат #1",
      "sort_order": 0
    }
  ],
  "created_at": "2026-03-20T09:00:00Z"
}
```

---

## Файлы реализации

### Новые файлы:
- `backend/app/api/v1/users_admin.py` — роутер Admin Users
- `backend/app/schemas/users_admin.py` — Pydantic-схемы Admin Users
- `backend/app/services/user_admin_service.py` — сервис Admin Users
- `backend/app/api/v1/content_blocks_admin.py` — роутер Content Blocks
- `backend/app/schemas/content_blocks.py` — Pydantic-схемы Content Blocks
- `backend/app/services/content_block_service.py` — сервис Content Blocks

### Обновлённые файлы:
- `backend/app/api/v1/__init__.py` — подключены новые роутеры
- `backend/app/main.py` — добавлены теги OpenAPI
- `backend/app/api/v1/content_admin.py` — добавлен reorder для org-docs
- `backend/app/schemas/content_admin.py` — добавлена схема OrgDocReorderRequest
- `backend/app/services/content_service.py` — добавлен метод reorder_org_docs
- `backend/app/api/v1/payments_admin.py` — добавлен refund endpoint
- `backend/app/schemas/payments.py` — добавлены RefundRequest/RefundResponse
- `backend/app/services/subscription_service.py` — добавлен initiate_refund
- `backend/app/services/payment_service.py` — добавлен create_refund в YooKassaClient
- `backend/app/api/v1/voting.py` — добавлен GET /admin/voting/{id}
- `backend/app/schemas/voting.py` — добавлен VotingSessionDetailResponse
- `backend/app/services/voting_service.py` — добавлен get_session
