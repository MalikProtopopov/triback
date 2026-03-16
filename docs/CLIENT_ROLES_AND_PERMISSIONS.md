# Роли и права доступа — Клиентский портал (ЛК)

> Документ описывает ролевую модель для личного кабинета пользователя и порядок получения данных для построения навигации.

## Роли

| Роль     | Описание                                          |
|----------|---------------------------------------------------|
| `doctor` | Врач — полный доступ к разделам кабинета врача    |
| `user`   | Не-врач (Non-doctor) — ограниченный набор разделов|

## Матрица видимости разделов ЛК

| Ключ        | Раздел               | Doctor | User |
|-------------|----------------------|:------:|:----:|
| cabinet     | Главная ЛК           | ✓      | ✓    |
| personal    | Личная информация   | ✓      |      |
| public      | Публичный профиль   | ✓      |      |
| payments    | Оплаты и подписка   | ✓      |      |
| events      | Мероприятия         | ✓      | ✓    |
| certificate | Сертификат          | ✓      |      |
| telegram    | Telegram            | ✓      |      |
| settings    | Настройки           | ✓      | ✓    |
| voting      | Голосование         | ✓      |      |

## Как получать данные

### 1. При входе — `POST /api/v1/auth/login`

Ответ содержит `role`:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "role": "doctor"
}
```

### 2. После логина/refresh — `GET /api/v1/auth/me`

Используйте для построения меню ЛК без дублирования констант на фронте.  
Требуется заголовок `Authorization: Bearer <access_token>`.

**Response 200 (doctor):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "doctor@example.com",
  "role": "doctor",
  "is_staff": false,
  "sidebar_sections": [
    "cabinet",
    "personal",
    "public",
    "payments",
    "events",
    "certificate",
    "telegram",
    "settings",
    "voting"
  ]
}
```

**Response 200 (user):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "email": "user@example.com",
  "role": "user",
  "is_staff": false,
  "sidebar_sections": [
    "cabinet",
    "events",
    "settings"
  ]
}
```

- `is_staff: false` — для клиентских ролей (doctor, user).
- `sidebar_sections` — ключи разделов, которые должен видеть пользователь. Отфильтруйте пункты меню по этому списку.

### 3. При обновлении токена — `POST /api/v1/auth/refresh`

Ответ аналогичен login: `access_token`, `token_type`, `role`. После успешного refresh рекомендуется вызвать `GET /auth/me` для актуальных `sidebar_sections`.

## Рекомендации для фронтенда

1. **Построение меню ЛК** — используйте `sidebar_sections` из `GET /auth/me` для отображения пунктов.
2. **Doctor vs User** — разные разделы; не показывать пункты, отсутствующие в `sidebar_sections`.
3. **Голосование** — раздел `voting` в `sidebar_sections` доступен врачам. Дополнительно проверять активную сессию членства и подписку (логика на фронте).
4. **401** — при истечении сессии redirect на `/login` с сохранением текущего URL для возврата после входа.
