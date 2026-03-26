# Управленческие XLSX-выгрузки — handoff

Эндпоинты под **`/api/v1/exports`**, доступ только **`admin`** и **`manager`** (роль **`accountant`** получает **403**).

Ответ: бинарный **XLSX**, заголовок **`Content-Disposition: attachment`**. Лимит **10 000** строк данных — при превышении **400** с тем же текстом, что у финансовых выгрузок.

## GET `/api/v1/exports/doctors`

Реестр врачей, лист **«Врачи»**.

| Параметр | Описание |
|----------|----------|
| `status` | Повторяемый: статус профиля (`pending_review`, `approved`, …). |
| `city_id` | Повторяемый UUID городов. |
| `has_active_subscription` | `true` / `false` — фильтр по наличию активной подписки (`status=active`, `ends_at` не в прошлом). |
| `board_role` | Повторяемый: `pravlenie`, `president`. |
| `entry_fee_exempt` | `true` / `false`. |
| `membership_excluded` | `true` — с `membership_excluded_at`; `false` — без исключения. |
| `is_deleted` | По умолчанию `false` — не показывать soft-deleted профили; `true` — включить. |
| `created_from`, `created_to` | Диапазон по `users.created_at` (оба или ни одного). |

Имя файла: `doctors_YYYY-MM-DD.xlsx` (дата — текущий день в МСК).

## GET `/api/v1/exports/protocol-history`

Журнал протоколов, лист **«Протоколы»**; при **`active_doctors_only=true`** — два листа: **«Врачи»** (активные врачи по правилам ТЗ) и **«Протоколы»** (записи только по `doctor_user_id` с первого листа).

| Параметр | Описание |
|----------|----------|
| `date_from`, `date_to` | Фильтр по `protocol_history_entries.created_at` (оба или ни одного). Если оба не переданы и **нет** `doctor_user_id` — подставляется **текущий календарный год** (МСК). |
| `year` | Повторяемый: год протокола. |
| `action_type` | Повторяемый: `admission`, `exclusion`. |
| `doctor_user_id` | Только записи по этому врачу. Если указан **без** дат — фильтр по дате создания **не** применяется. |
| `created_by_user_id` | Кто создал запись. |
| `active_doctors_only` | `true` — режим двух листов (см. выше). |

Имя файла: `protocol_history_YYYY-MM-DD_YYYY-MM-DD.xlsx` или `protocol_history_doctor_{uuid}.xlsx`, если выгрузка **только по врачу без диапазона дат**.

## Примеры

```http
GET /api/v1/exports/doctors
Authorization: Bearer <manager_or_admin_token>
```

```http
GET /api/v1/exports/protocol-history?active_doctors_only=true
Authorization: Bearer <manager_or_admin_token>
```

Подробные колонки и бизнес-логика «активный член» — в [`docs/management_exports.docx`](docs/management_exports.docx).
