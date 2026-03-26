# Ручное создание врача из админки

> Документ для фронтенд-разработчика.  
> API реализован на бэкенде и доступен в Swagger: `GET /docs`

---

## API

### `POST /api/v1/admin/doctors`

**Авторизация:** Bearer JWT, роль `admin`

---

### Request body (JSON)

| Поле | Тип | Обязательное | Описание |
|------|-----|:------------:|----------|
| `email` | string (email) | да | Email будущего аккаунта |
| `first_name` | string (1–100) | да | Имя |
| `last_name` | string (1–100) | да | Фамилия |
| `phone` | string (1–20) | да | Телефон |
| `middle_name` | string | нет | Отчество |
| `city_id` | UUID | нет | ID города из `/api/v1/admin/cities` |
| `clinic_name` | string | нет | Название клиники |
| `position` | string | нет | Должность |
| `academic_degree` | string | нет | Учёная степень |
| `bio` | string | нет | Биография / описание |
| `public_email` | string | нет | Публичный email (для каталога) |
| `public_phone` | string | нет | Публичный телефон |
| `specialization_ids` | UUID[] | нет | Массив ID специализаций |
| `status` | `"approved"` / `"pending_review"` | нет | Статус профиля (по умолчанию `approved`) |
| `send_invite` | boolean | нет | Отправить приглашение на email (по умолчанию `true`) |

### Пример запроса

```json
{
  "email": "doctor@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "phone": "+79001234567",
  "middle_name": "Сергеевич",
  "city_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "clinic_name": "Клиника здоровья",
  "position": "Трихолог",
  "specialization_ids": ["11111111-2222-3333-4444-555555555555"],
  "send_invite": true
}
```

---

### Response (201 Created)

```json
{
  "user_id": "019cebea-b94d-7e92-a31a-e6444801ee65",
  "profile_id": "019cebea-b94d-7e92-a31a-f7555912ff76",
  "email": "doctor@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "status": "approved",
  "temp_password": null
}
```

> `temp_password` возвращается **только** если `send_invite = false`, чтобы админ мог передать пароль врачу вручную. Если `send_invite = true` — пароль не отображается, письмо уходит автоматически.

---

### Ошибки

| Код | Когда | Тело |
|-----|-------|------|
| 401 | Нет токена / истёк | `{"error": {"code": "UNAUTHORIZED", ...}}` |
| 403 | Роль не `admin` (например `manager`) | `{"error": {"code": "FORBIDDEN", ...}}` |
| 409 | Email уже зарегистрирован | `{"error": {"code": "CONFLICT", "message": "User with this email already exists"}}` |
| 422 | Невалидный body (нет обязательных полей, неверный email и т.д.) | `{"error": {"code": "VALIDATION_ERROR", ...}}` |

---

## Рекомендации по UI

### Расположение

Кнопка **"Добавить врача"** на странице `/admin/doctors` (справа от кнопки "Импорт из Excel").

### Форма создания

Модальное окно или отдельная страница `/admin/doctors/create`.

**Обязательные поля** (отмечены `*`):
- Email *
- Фамилия *
- Имя *
- Телефон *

**Опциональные поля** (в расширяемой секции или второй вкладке):
- Отчество
- Город (select из `GET /api/v1/admin/cities`)
- Клиника
- Должность
- Учёная степень
- Биография (textarea)
- Публичный email
- Публичный телефон
- Специализации (multiselect из `GET /api/v1/specializations`)

**Настройки:**
- Статус: radio/select (`Одобрен` / `На модерации`), по умолчанию "Одобрен"
- Чекбокс "Отправить приглашение на email" (по умолчанию включён)

### Поведение после отправки

1. При успехе (201) — показать уведомление "Врач создан"
2. Если `send_invite = false` — показать диалог с временным паролем (из `temp_password`)
3. Редирект на карточку врача: `/admin/doctors/{profile_id}`

### Обработка ошибок

- **409**: показать inline-ошибку под полем email — "Пользователь с таким email уже зарегистрирован"
- **422**: подсветить невалидные поля
- **401/403**: стандартная обработка (редирект на логин / уведомление)

---

## Что происходит на бэкенде

При вызове `POST /admin/doctors`:

1. Создаётся `User` (email, временный пароль, email подтверждён)
2. Назначается роль `doctor`
3. Создаётся `DoctorProfile` со всеми переданными полями
4. Если `send_invite = true` — в фоне через TaskIQ отправляется email с логином и паролем
5. Врач сразу появляется в списке `/admin/doctors` и может войти в систему
