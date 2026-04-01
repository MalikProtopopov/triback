# Сводка: расширение роли «Бухгалтер» (`accountant`) — всё в одном месте

Один файл вместо просмотра нескольких исходников и handoff-доков. Детали по полям API см. в OpenAPI и в [`PROTOCOL_HISTORY_ADMIN_FRONTEND.md`](../old_docs/handoff/PROTOCOL_HISTORY_ADMIN_FRONTEND.md).

---

## Зачем

У **`accountant`** тот же периметр, что у **`manager`**, для:

- раздела **врачи** (список, карточка, модерация и т.д.),
- **истории протоколов** (полный CRUD),
- **выгрузок** реестра врачей и истории протоколов (XLSX и Telegram).

**Не** расширялось: создание врача вручную и **импорт** врачей — по-прежнему только **`admin`**.

---

## Было → стало (кратко)

| Область | Было | Стало |
|--------|------|--------|
| `sidebar_sections` для `accountant` | `payments`, `arrears` | + **`doctors`**, **`protocol_history`** |
| `/admin/protocol-history*` | `admin`, `manager` | + **`accountant`** |
| `GET/POST /exports/doctors*`, `.../protocol-history*` | `admin`, `manager` | + **`accountant`** |
| большинство `/admin/doctors*` (кроме create/import) | `admin`, `manager` | + **`accountant`** |
| `POST /admin/doctors`, import, status import | `admin` | без изменений |

---

## Где что менялось в коде

| Файл | Суть изменений |
|------|----------------|
| [`backend/app/core/permissions.py`](../../backend/app/core/permissions.py) | В `_ADMIN_SIDEBAR["accountant"]`: порядок ключей `payments`, `arrears`, `doctors`, `protocol_history`. |
| [`backend/app/api/v1/protocol_history_admin.py`](../../backend/app/api/v1/protocol_history_admin.py) | Константа `ADMIN_PROTOCOL_STAFF = require_role("admin", "manager", "accountant")` на всех хендлерах раздела. |
| [`backend/app/api/v1/exports.py`](../../backend/app/api/v1/exports.py) | `STAFF_MANAGEMENT_EXPORTS = require_role("admin", "manager", "accountant")` для **`export_doctors`**, **`export_doctors_telegram`**, **`export_protocol_history`**, **`export_protocol_history_telegram`**. Остальные экспорты как раньше на `STAFF_FINANCE` (admin/manager/accountant). |
| [`backend/app/api/v1/doctors_admin.py`](../../backend/app/api/v1/doctors_admin.py) | `ADMIN_MANAGER_PLUS = require_role("admin", "manager", "accountant")` везде, где раньше был только admin+manager для «операционных» эндпоинтов. **`ADMIN_ONLY`** — create doctor, import, import status. **`ADMIN_ACCOUNTANT`** — `update_doctor_payment_overrides` (как было: admin + accountant). |

---

## API: что доступно бухгалтеру

Префикс **`/api/v1`**, заголовок **`Authorization: Bearer <access_token>`**.

### История протоколов

- `GET /admin/protocol-history`
- `GET /admin/protocol-history/{id}`
- `POST /admin/protocol-history`
- `PATCH /admin/protocol-history/{id}`
- `DELETE /admin/protocol-history/{id}`

### Экспорты (добавлен accountant к management-выгрузкам)

- `GET /exports/doctors`
- `POST /exports/doctors/telegram`
- `GET /exports/protocol-history`
- `POST /exports/protocol-history/telegram`

### Врачи (админ API)

Все маршруты с **`ADMIN_MANAGER_PLUS`**, включая список, деталь, board role, moderate, approve draft, toggle active, напоминания, e-mail, portal user, регистрации на события и т.п. — по коду в [`doctors_admin.py`](../../backend/app/api/v1/doctors_admin.py).

**Только `admin`:** `POST /admin/doctors`, эндпоинты импорта и статуса импорта.

---

## Сайдбар (фронт)

Для роли **`accountant`** в ответе логина / профиля в **`sidebar_sections`** приходят ключи:

`payments`, `arrears`, `doctors`, `protocol_history`

Рекомендуемый порядок в меню: сначала финансы, затем врачи, затем протоколы.

---

## Тесты

| Файл | Что проверяется для accountant |
|------|--------------------------------|
| [`backend/tests/test_protocol_history.py`](../../backend/tests/test_protocol_history.py) | `test_protocol_history_accountant_crud` — список, создание, PATCH, DELETE. |
| [`backend/tests/test_admin_doctors.py`](../../backend/tests/test_admin_doctors.py) | `test_admin_list_accountant_ok` — `GET /admin/doctors` → 200. |
| [`backend/tests/test_exports.py`](../../backend/tests/test_exports.py) | `test_export_doctors_ok_accountant`, `test_export_protocol_history_ok_accountant` (и при необходимости другие сценарии с `auth_headers_accountant` в том же файле). |

---

## Документация (куда смотреть дальше)

| Документ | Назначение |
|----------|------------|
| [`ADMIN_ACCOUNTANT_ROLE.md`](./ADMIN_ACCOUNTANT_ROLE.md) | Handoff для админ-фронта: меню, типовые роуты, что скрыть у бухгалтера. |
| [`../rules/BACKEND_RULES.md`](../rules/BACKEND_RULES.md) | Краткая строка про ключи сайдбара accountant и экспорты. |
| [`../old_docs/handoff/PROTOCOL_HISTORY_ADMIN_FRONTEND.md`](../old_docs/handoff/PROTOCOL_HISTORY_ADMIN_FRONTEND.md) | Поля запросов/ответов протоколов, таблица ролей (accountant включён). |

---

## Регрессия (ожидания)

- **`admin`** и **`manager`** — без потери доступа к перечисленным маршрутам.
- **`doctor`** и прочие не-staff — по-прежнему **403** на эти админские маршруты (существующие тесты).

Если этот файл устарел, сверяйтесь с актуальными `require_role` в перечисленных модулях API.
