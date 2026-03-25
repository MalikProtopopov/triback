# Онбординг и модерация врачей: Handoff для админки

## Обзор

Админ может просматривать заявки врачей, видеть анкеты и документы, принимать или отклонять заявки с комментарием. При отклонении пользователь видит причину и может исправить данные и подать повторно.

---

## API-эндпоинты

### 1. Список врачей

**`GET /api/v1/admin/doctors`**

Доступ: `admin`, `manager`.

| Query-параметр | Тип | Описание |
|----------------|-----|----------|
| `status` | string | Фильтр: `pending_review`, `approved`, `rejected`, `active`, `deactivated` |
| `search` | string | Поиск по ФИО/email (мин. 2 символа) |
| `city_id` | UUID | Фильтр по городу |
| `has_data_changed` | bool | Только с изменёнными данными |
| `sort_by` | string | `created_at` (default), `last_name`, `subscription_ends_at` |
| `sort_order` | string | `asc` / `desc` (default) |
| `limit` | int | 1–100, default 20 |
| `offset` | int | default 0 |

Ответ: `PaginatedResponse[DoctorListItemResponse]`

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
      "specialization": "Дерматология",
      "moderation_status": "pending_review",
      "has_medical_diploma": true,
      "subscription": null,
      "has_pending_changes": false,
      "created_at": "2026-03-10T12:00:00Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### 2. Карточка врача

**`GET /api/v1/admin/doctors/{id}`**

Доступ: `admin`, `manager`.

Ответ: `DoctorDetailResponse`

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "email": "doctor@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "phone": "+79001234567",
  "passport_data": "1234 567890",
  "city": { "id": "uuid", "name": "Москва" },
  "clinic_name": "Клиника здоровья",
  "position": "Врач-дерматолог",
  "specialization": "Дерматология",
  "academic_degree": "к.м.н.",
  "bio": "Опыт работы 10 лет...",
  "public_email": "ivan@clinic.ru",
  "public_phone": null,
  "photo_url": "https://cdn.example.com/photos/doctor.jpg",
  "moderation_status": "pending_review",
  "has_medical_diploma": true,
  "diploma_photo_url": null,
  "slug": "petrov-ivan",
  "documents": [
    {
      "id": "uuid",
      "document_type": "medical_diploma",
      "original_filename": "diploma.pdf",
      "file_url": "https://cdn.example.com/doctors/uuid/diploma.pdf",
      "file_size": 1048576,
      "mime_type": "application/pdf",
      "uploaded_at": "2026-03-10T12:00:00Z"
    }
  ],
  "subscription": null,
  "payments": [],
  "pending_draft": null,
  "moderation_history": [
    {
      "id": "uuid",
      "admin_email": "admin@example.com",
      "action": "reject",
      "comment": "Нечитаемая копия диплома",
      "created_at": "2026-03-11T14:30:00Z"
    }
  ],
  "content_blocks": [],
  "created_at": "2026-03-10T12:00:00Z"
}
```

---

### 3. Модерация (approve / reject)

**`POST /api/v1/admin/doctors/{id}/moderate`**

Доступ: `admin`, `manager`.

#### Request body

```json
{
  "action": "approve",
  "comment": null
}
```

или

```json
{
  "action": "reject",
  "comment": "Нечитаемая копия диплома. Загрузите скан в высоком разрешении."
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| `action` | `"approve"` \| `"reject"` | Да | Действие |
| `comment` | string \| null | При reject — обязательно | Комментарий (причина отклонения) |

#### Response 200

```json
{
  "moderation_status": "approved",
  "message": "Статус обновлён"
}
```

#### Что происходит при модерации

| Действие | Статус профиля | ModerationHistory | Email |
|----------|---------------|-------------------|-------|
| approve | `approved` | Запись с `action=approve` | «Заявка одобрена» |
| reject | `rejected` | Запись с `action=reject`, `comment=причина` | «Заявка отклонена. Причина: ...» |

---

## UX-рекомендации для админки

### Страница `/admin/doctors`

- Таблица: ФИО, email, город, статус (бейдж), дата регистрации.
- Фильтр по статусу: **Все** | **На модерации** (pending_review) | **Одобрены** (approved/active) | **Отклонены** (rejected).
- По умолчанию сортировка: newest first.
- Клик по строке открывает карточку.

### Карточка `/admin/doctors/{id}`

- Секция «Анкета»: личные и профессиональные данные.
- Секция «Документы»: список с превью/ссылками на скачивание.
- Секция «История модерации»: таблица (дата, действие, комментарий, админ).
- Блок «Модерация» (видим при `pending_review`):
  - Кнопка «Принять» (зелёная).
  - Кнопка «Отклонить» (красная) — при нажатии открывает текстовое поле «Причина отклонения» (обязательно).
  - Кнопка «Отправить решение».

### Повторная модерация

После отклонения пользователь может исправить данные и подать заявку повторно. Статус снова станет `pending_review`, и карточка появится в списке на модерации.
