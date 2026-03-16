# Роли и права доступа — Админка

> Документ описывает ролевую модель для административного интерфейса (admin panel) и порядок получения данных для построения сайдбара.

## Роли

| Роль        | Описание                                      |
|-------------|-----------------------------------------------|
| `admin`     | Полный доступ ко всем разделам админки        |
| `manager`   | Ограниченный доступ (врачи, мероприятия, контент и др.) |
| `accountant`| Только раздел «Платежи»                       |

## Матрица видимости разделов сайдбара

| Ключ               | Раздел              | Admin | Manager | Accountant |
|--------------------|---------------------|:-----:|:-------:|:----------:|
| dashboard          | Дашборд             | ✓     | ✓       |            |
| doctors            | Врачи               | ✓     | ✓       |            |
| doctors_import     | Импорт из Excel     | ✓     |         |            |
| events             | Мероприятия         | ✓     | ✓       |            |
| payments           | Платежи             | ✓     | ✓       | ✓          |
| content            | Контент (родитель)  | ✓     | ✓       |            |
| content_articles   | Статьи              | ✓     | ✓       |            |
| content_themes     | Темы статей         | ✓     | ✓       |            |
| content_documents  | Документы орг.      | ✓     | ✓       |            |
| settings           | Настройки (родитель)| ✓     | ✓       |            |
| settings_general   | Общие               | ✓     |         |            |
| settings_cities    | Города              | ✓     | ✓       |            |
| settings_plans     | Тарифы              | ✓     |         |            |
| settings_seo       | SEO                 | ✓     |         |            |
| voting             | Голосование         | ✓     |         |            |
| notifications      | Уведомления         | ✓     | ✓       |            |
| portal_users       | Пользователи портала| ✓     | ✓       |            |
| administrators     | Администраторы      | ✓     |         |            |

## Как получать данные

### 1. При входе — `POST /api/v1/auth/login`

Ответ содержит `role` для отображения и перенаправления:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "role": "manager"
}
```

### 2. После логина/refresh — `GET /api/v1/auth/me`

Используйте для построения сайдбара без дублирования констант на фронте.  
Требуется заголовок `Authorization: Bearer <access_token>`.

**Response 200:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "manager@example.com",
  "role": "manager",
  "is_staff": true,
  "sidebar_sections": [
    "dashboard",
    "doctors",
    "events",
    "payments",
    "content",
    "content_articles",
    "content_themes",
    "content_documents",
    "settings",
    "settings_cities",
    "notifications",
    "portal_users"
  ]
}
```

- `is_staff: true` — пользователь имеет роль admin, manager или accountant.
- `sidebar_sections` — ключи разделов, которые должен видеть пользователь. Отфильтруйте пункты сайдбара по этому списку.

### 3. При обновлении токена — `POST /api/v1/auth/refresh`

Ответ аналогичен login: `access_token`, `token_type`, `role`. После успешного refresh рекомендуется вызвать `GET /auth/me` для актуальных `sidebar_sections`.

## Рекомендации для фронтенда

1. **Построение сайдбара** — используйте `sidebar_sections` из `GET /auth/me` для отображения пунктов меню.
2. **Сохранение роли** — сохраняйте `role` из login/refresh в состоянии (store/localStorage) для редиректов и проверок.
3. **401** — при истечении сессии redirect на `/admin/login` с сообщением «Сессия истекла».
4. **Проверка прав на эндпоинты** — бэкенд проверяет роль через `require_role()`. Фронт может дополнительно скрывать UI для экономии запросов, но не полагаться только на скрытие как на защиту.

## API endpoints и роли

Основные защищённые эндпоинты проверяют роль на бэкенде (см. `docs/tech_requirements/04_Backend_API.md` и `backend/app/core/dependencies.py`).
