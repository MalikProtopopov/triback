# Админ-панель: роль «Бухгалтер» (`accountant`)

Бэкенд отдаёт в `sidebar_sections` для роли **`accountant`** ключи: **`payments`**, **`arrears`**, **`doctors`**, **`protocol_history`**. Доступ к API совпадает с **`manager`** для врачей (кроме операций только **`admin`**) и истории протоколов; выгрузки реестра врачей и истории протоколов — тоже доступны.

Подробности RBAC: [`backend/app/core/permissions.py`](../../backend/app/core/permissions.py), [`backend/app/api/v1/doctors_admin.py`](../../backend/app/api/v1/doctors_admin.py), [`backend/app/api/v1/protocol_history_admin.py`](../../backend/app/api/v1/protocol_history_admin.py), [`backend/app/api/v1/exports.py`](../../backend/app/api/v1/exports.py).

## 1. Сайдбар

Показывать пункты по ключам:

- `payments`, `arrears` (как раньше)
- **`doctors`**
- **`protocol_history`**

Рекомендуемый порядок: финансы (`payments`, `arrears`) → врачи → протоколы.

## 2. История протоколов

- Роут как у admin/manager, например `/admin/protocol-history`.
- API (Bearer access token staff):
  - `GET /api/v1/admin/protocol-history`
  - `GET /api/v1/admin/protocol-history/{id}`
  - `POST /api/v1/admin/protocol-history`
  - `PATCH /api/v1/admin/protocol-history/{id}`
  - `DELETE /api/v1/admin/protocol-history/{id}`
- Выгрузки:
  - `GET /api/v1/exports/protocol-history`
  - `POST /api/v1/exports/protocol-history/telegram`

Документация по полям и ответам: [`docs/old_docs/handoff/PROTOCOL_HISTORY_ADMIN_FRONTEND.md`](../old_docs/handoff/PROTOCOL_HISTORY_ADMIN_FRONTEND.md).

## 3. Врачи

- Роут реестра: `/admin/doctors` (или текущий путь админки).
- Список, фильтры, карточка врача, модерация, активация, правление, напоминания, e-mail, portal user, регистрации на события — те же вызовы, что у **manager** (`/api/v1/admin/doctors/...`).

## 4. Только для `admin` (скрыть у бухгалтера в UI)

- `POST /api/v1/admin/doctors` — создание врача вручную
- Импорт врачей и статус импорта (`import` endpoints в `doctors_admin`)

Не показывать кнопки «Создать врача» / «Импорт» для роли `accountant`, даже если роут известен.

## 5. Выгрузка врачей

- `GET /api/v1/exports/doctors` — XLSX (те же query-параметры, что у manager)
- `POST /api/v1/exports/doctors/telegram` — отправка в Telegram

## 6. Ошибки и регрессия

- При `403` — сообщение о недостаточных правах (устаревший токен / частичный деплой).
- Регрессия: роли `admin` и `manager` без потери доступов; smoke под `accountant`: сайдбар из четырёх блоков, списки врачей и протоколов, одна операция CRUD, выгрузки doctors + protocol-history.
