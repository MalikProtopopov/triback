# FAQ (Вопрос / Ответ) — API документация

## Обзор

Модуль FAQ хранит вопросы пользователей и ответы экспертов-трихологов. Данные мигрированы с предыдущего сайта (260 записей).

**Таблица:** `faq_entries`

| Поле | Тип | Описание |
|---|---|---|
| `id` | UUID v7 | Первичный ключ |
| `question_title` | String(500) | Заголовок вопроса |
| `question_text` | Text | Полный текст вопроса |
| `answer_text` | Text, nullable | Текст ответа эксперта |
| `author_name` | String(255), nullable | Имя автора вопроса |
| `is_active` | Boolean | Показывать на сайте (default: true) |
| `original_date` | DateTime, nullable | Дата из старого сайта |
| `created_at` | DateTime | Дата создания записи |
| `updated_at` | DateTime | Дата последнего обновления |

---

## Публичные эндпоинты (клиентский фронт)

Авторизация **не требуется**.

### `GET /api/v1/faq` — Список вопросов

Пагинированный список активных FAQ-записей.

**Query-параметры:**

| Параметр | Тип | Default | Описание |
|---|---|---|---|
| `limit` | int (1–100) | 50 | Кол-во записей на страницу |
| `offset` | int (≥ 0) | 0 | Смещение для пагинации |
| `search` | string (≥ 2) | — | Поиск по тексту вопроса/заголовку |
| `answered_only` | bool | false | Только записи с непустым ответом |

**Ответ:** `200 OK`

```json
{
  "data": [
    {
      "id": "019d53a5-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "question_title": "Вопрос пользователя Ирина",
      "question_text": "После операции цистэктомии по поводу эндометриоза яичника...",
      "answer_text": "Возможно, речь идет о гнездной алопеции...",
      "author_name": "Ирина",
      "original_date": "2025-07-18T05:56:21Z"
    },
    {
      "id": "019d53a5-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
      "question_title": "Вопрос пользователя Андрей",
      "question_text": "Здравствуйте! Подскажите клинику...",
      "answer_text": null,
      "author_name": "Андрей",
      "original_date": "2025-01-05T14:21:24Z"
    }
  ],
  "total": 58,
  "limit": 50,
  "offset": 0
}
```

**Примеры запросов фронта:**

```typescript
// Все активные FAQ с ответами (для публичной страницы)
GET /api/v1/faq?answered_only=true&limit=20

// Поиск
GET /api/v1/faq?search=выпадение+волос&answered_only=true

// Вторая страница
GET /api/v1/faq?limit=20&offset=20&answered_only=true
```

---

### `GET /api/v1/faq/{faq_id}` — Один вопрос по ID

**Ответ:** `200 OK`

```json
{
  "id": "019d53a5-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "question_title": "Вопрос пользователя Ирина",
  "question_text": "После операции цистэктомии по поводу эндометриоза яичника...",
  "answer_text": "Возможно, речь идет о гнездной алопеции и анагеновой потери волос...",
  "author_name": "Ирина",
  "original_date": "2025-07-18T05:56:21Z"
}
```

**Ошибки:**

| Код | Ситуация |
|---|---|
| `404` | Запись не найдена или неактивна |

---

## Админские эндпоинты (админ-панель)

Требуется JWT-токен с ролью **admin** или **manager**.

Заголовок: `Authorization: Bearer <access_token>`

### `GET /api/v1/admin/faq` — Список всех FAQ (включая неактивные)

**Query-параметры:**

| Параметр | Тип | Default | Описание |
|---|---|---|---|
| `limit` | int (1–100) | 20 | Кол-во записей на страницу |
| `offset` | int (≥ 0) | 0 | Смещение |
| `is_active` | bool | — | Фильтр: `true` — активные, `false` — скрытые, не указан — все |
| `search` | string (≥ 2) | — | Поиск по тексту |

**Ответ:** `200 OK`

```json
{
  "data": [
    {
      "id": "019d53a5-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "question_title": "Вопрос пользователя Ирина",
      "question_text": "После операции...",
      "answer_text": "Возможно, речь идет...",
      "author_name": "Ирина",
      "is_active": true,
      "original_date": "2025-07-18T05:56:21Z",
      "created_at": "2026-04-03T13:56:00Z",
      "updated_at": "2026-04-03T13:56:00Z"
    }
  ],
  "total": 260,
  "limit": 20,
  "offset": 0
}
```

**Примеры:**

```typescript
// Все FAQ
GET /api/v1/admin/faq

// Только активные
GET /api/v1/admin/faq?is_active=true

// Только скрытые (без ответа)
GET /api/v1/admin/faq?is_active=false

// Поиск
GET /api/v1/admin/faq?search=алопеция
```

---

### `POST /api/v1/admin/faq` — Создать FAQ

**Тело запроса (JSON):**

```json
{
  "question_title": "Вопрос от Марии",
  "question_text": "Здравствуйте! Какие анализы сдать при выпадении волос?",
  "answer_text": "Рекомендуем сдать общий анализ крови, ферритин, ТТГ...",
  "author_name": "Мария",
  "is_active": true,
  "original_date": null
}
```

| Поле | Обязательное | Описание |
|---|---|---|
| `question_title` | **да** | Заголовок (max 500) |
| `question_text` | **да** | Текст вопроса |
| `answer_text` | нет | Текст ответа |
| `author_name` | нет | Имя автора (max 255) |
| `is_active` | нет (default: true) | Показывать на сайте |
| `original_date` | нет | Дата оригинала (ISO 8601) |

**Ответ:** `201 Created` — возвращает созданную запись (формат `FaqAdminItem`).

---

### `GET /api/v1/admin/faq/{faq_id}` — Детали FAQ

**Ответ:** `200 OK` — формат `FaqAdminItem`.

---

### `PATCH /api/v1/admin/faq/{faq_id}` — Обновить FAQ

Частичное обновление — передаются **только изменённые поля**.

**Тело запроса (JSON):**

```json
{
  "answer_text": "Обновлённый ответ эксперта...",
  "is_active": true
}
```

**Ответ:** `200 OK` — обновлённая запись.

**Типичные сценарии:**

```typescript
// Добавить ответ на вопрос
PATCH /api/v1/admin/faq/{id}
{ "answer_text": "Ответ...", "is_active": true }

// Скрыть вопрос
PATCH /api/v1/admin/faq/{id}
{ "is_active": false }

// Отредактировать заголовок
PATCH /api/v1/admin/faq/{id}
{ "question_title": "Исправленный заголовок" }
```

---

### `DELETE /api/v1/admin/faq/{faq_id}` — Удалить FAQ

Требуется роль **admin** (manager не может удалять).

**Ответ:** `204 No Content`

---

## Ошибки

Все ошибки возвращаются в стандартном формате:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "FAQ entry not found",
    "details": {}
  }
}
```

| HTTP код | `code` | Когда |
|---|---|---|
| 401 | `UNAUTHORIZED` | Нет токена или токен невалиден |
| 403 | `FORBIDDEN` | Роль не admin/manager |
| 404 | `NOT_FOUND` | Запись не найдена |
| 422 | `VALIDATION_ERROR` | Невалидные данные |

---

## Реализация на фронтах

### Клиентский сайт (trichologia.ru)

**Страница:** `/faq` или `/vopros-otvet`

**Компоненты:**
1. **Список FAQ** — карточки с вопросом и свёрнутым ответом (accordion)
   - Загрузка: `GET /api/v1/faq?answered_only=true&limit=20`
   - Пагинация: кнопка "Показать ещё" (offset += limit)
   - Поиск: debounced input → `?search=...`
2. **Страница одного вопроса** (опционально, для SEO): `GET /api/v1/faq/{id}`

**Данные для отображения:**
- `question_title` — заголовок карточки
- `question_text` — раскрывающийся текст вопроса
- `answer_text` — текст ответа (если есть)
- `author_name` — "Автор: {name}" (если есть)
- `original_date` — дата вопроса

### Админ-панель (admin.trichologia.ru)

**Раздел:** "Вопросы и ответы" в боковом меню

**Страницы:**

1. **Список FAQ** (`/admin/faq`)
   - Таблица: заголовок, автор, есть ли ответ, активность, дата
   - Фильтры: активность (все / активные / скрытые), поиск
   - Кнопки: "Создать", редактировать, удалить
   - API: `GET /api/v1/admin/faq?limit=20&offset=0`

2. **Создание/Редактирование** (`/admin/faq/new`, `/admin/faq/{id}/edit`)
   - Форма:
     - Заголовок вопроса (input, обязательный)
     - Текст вопроса (textarea, обязательный)
     - Текст ответа (rich-text editor)
     - Имя автора (input)
     - Активность (toggle)
   - Создание: `POST /api/v1/admin/faq`
   - Обновление: `PATCH /api/v1/admin/faq/{id}`

3. **Удаление** — confirm dialog → `DELETE /api/v1/admin/faq/{id}`

---

## TypeScript типы

```typescript
// ── Public ──

interface FaqPublicItem {
  id: string
  question_title: string
  question_text: string
  answer_text: string | null
  author_name: string | null
  original_date: string | null  // ISO 8601
}

interface PaginatedFaqResponse {
  data: FaqPublicItem[]
  total: number
  limit: number
  offset: number
}

// ── Admin ──

interface FaqAdminItem {
  id: string
  question_title: string
  question_text: string
  answer_text: string | null
  author_name: string | null
  is_active: boolean
  original_date: string | null
  created_at: string
  updated_at: string
}

interface FaqCreateRequest {
  question_title: string
  question_text: string
  answer_text?: string | null
  author_name?: string | null
  is_active?: boolean          // default: true
  original_date?: string | null
}

interface FaqUpdateRequest {
  question_title?: string
  question_text?: string
  answer_text?: string | null
  author_name?: string | null
  is_active?: boolean
  original_date?: string | null
}

interface PaginatedAdminFaqResponse {
  data: FaqAdminItem[]
  total: number
  limit: number
  offset: number
}
```

---

## Текущее состояние данных

| Показатель | Значение |
|---|---|
| Всего записей | 260 |
| Активные (с ответом) | 58 |
| Неактивные (без ответа) | 202 |
| Мигрировано из | Drupal 7, контент-тип `ask_expert` |
