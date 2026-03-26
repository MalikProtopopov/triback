# Админка: «История протокола» — API и сайдбар

Раздел фиксирует решения по врачу: **приём в ассоциацию** или **исключение**, с реквизитами протокола (год, название), заметками и аудитом (кто создал / кто последний редактировал).

## Роли

| Роль | Доступ к API `/admin/protocol-history` | Ключ сайдбара |
|------|----------------------------------------|----------------|
| `admin` | да | `protocol_history`, также `arrears` |
| `manager` | да | `protocol_history` |
| `accountant` | нет (403) | `arrears`, **без** `protocol_history` |

Ключи приходят в **`sidebar_sections`** в ответе логина и в эндпоинте текущего пользователя (см. Auth). Фронт мапит ключ `protocol_history` на пункт меню и роут (например `/admin/protocol-history`).

Дополнительно для раздела «Задолженности»:

| Роль | Ключ `arrears` |
|------|----------------|
| `admin` | да |
| `accountant` | да |
| `manager` | нет |

## Базовый URL

Все пути ниже с префиксом **`/api/v1`**. Авторизация: **`Authorization: Bearer <access_token>`**.

---

## Эндпоинты

### GET `/admin/protocol-history` — список

**Query:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int, default 50, 1–200 | Пагинация |
| `offset` | int, default 0 | Смещение |
| `doctor_user_id` | UUID, optional | Только записи по этому врачу (`users.id`) |
| `action_type` | string, optional | `admission` или `exclusion` |

**Сортировка:** `created_at` по убыванию (новые сверху).

**Ответ 200:** `ProtocolHistoryListResponse`

```json
{
  "data": [ /* ProtocolHistoryResponse */ ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### GET `/admin/protocol-history/{entry_id}` — одна запись

**Ответ 200:** `ProtocolHistoryResponse`  
**404:** запись не найдена.

### POST `/admin/protocol-history` — создать

**Body (JSON):**

| Поле | Тип | Обязательно |
|------|-----|-------------|
| `year` | int | да, 2000–2100 |
| `protocol_title` | string | да, до 500 символов |
| `notes` | string \| null | нет |
| `doctor_user_id` | UUID | да, пользователь-врач с профилем врача |
| `action_type` | string | да: `admission` или `exclusion` |

`created_by` / `last_edited_by` с фронта **не передаются** — бэкенд берёт текущего пользователя из JWT.

**Ответ 201:** `ProtocolHistoryResponse`

**422:** например `doctor_user_id` не является врачом без профиля врача.

### PATCH `/admin/protocol-history/{entry_id}` — изменить

Частичное обновление: любое из `year`, `protocol_title`, `notes`, `doctor_user_id`, `action_type`.

После успешного PATCH обновляются **`last_edited_by_user_id`** (текущий пользователь) и **`updated_at`**. **`created_by_user_id`** не меняется.

**Ответ 200:** `ProtocolHistoryResponse`

### DELETE `/admin/protocol-history/{entry_id}` — удалить

**Ответ 204** без тела. **404** если записи нет.

---

## Схема `ProtocolHistoryResponse`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | |
| `year` | int | |
| `protocol_title` | string | |
| `notes` | string \| null | |
| `doctor_user_id` | UUID | |
| `action_type` | string | `admission` \| `exclusion` |
| `created_by_user_id` | UUID | |
| `last_edited_by_user_id` | UUID \| null | При создании `null`; после первого PATCH — id последнего редактора |
| `created_at` | string (ISO) | |
| `updated_at` | string (ISO) | |
| `doctor` | object | См. ниже |
| `created_by_user` | object | См. ниже |
| `last_edited_by_user` | object \| null | См. ниже |

### `doctor` (как у задолженностей)

| Поле | Описание |
|------|----------|
| `id` | UUID врача |
| `email` | почта |
| `full_name` | ФИО из профиля врача или null |
| `phone` | телефон профиля или null |
| `telegram_username` | username Telegram или null |

### `created_by_user` / `last_edited_by_user`

| Поле | Описание |
|------|----------|
| `id` | UUID |
| `email` | почта |
| `full_name` | ФИО, если у пользователя есть профиль врача; иначе null (типично staff) |

---

## Аудит (кратко)

- **POST:** `created_by_user_id` = текущий пользователь, `last_edited_by_user_id` = **null**.
- **PATCH:** `last_edited_by_user_id` = текущий пользователь; `created_by_user_id` без изменений.

---

## Ошибки

| Код | Когда |
|-----|--------|
| 401 | Нет или невалидный токен |
| 403 | Роль не `admin` и не `manager` |
| 404 | Запись не найдена (GET/PATCH/DELETE) |
| 422 | Ошибка валидации тела/врач не найден как врач |

---

## OpenAPI

После деплоя: **`/docs`** или **`/redoc`** на хосте API — тег **«Admin - Protocol History»**.

---

## Чеклист фронта

- [ ] Пункт меню по ключу `protocol_history` (admin, manager).
- [ ] Таблица: фильтры по врачу и типу действия; сортировка с бэка уже «новые сверху».
- [ ] Форма создания/редактирования; enum `action_type` на UI: «Приём» / «Исключение».
- [ ] Отображение `created_by_user` / `last_edited_by_user` и дат.
- [ ] Отдельно: пункт «Задолженности» по ключу `arrears` только для admin и accountant (не показывать менеджеру).
