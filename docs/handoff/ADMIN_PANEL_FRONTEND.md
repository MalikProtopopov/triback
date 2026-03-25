# Админ-панель — сводка для фронтенда

Единая точка входа по **платежам, задолженностям, карточке врача и дашборду** после доработок по плану задолженностей. Детали по отдельным модулям — в связанных handoff-файлах.

**Источник контрактов:** `GET /api/v1/openapi.json` или `/docs`. При расхождении приоритет у OpenAPI.

---

## 1. Роли и доступ

| Роль | Типичные разделы |
|------|------------------|
| **admin** | Полный доступ, в т.ч. настройки сайта |
| **manager** | Дашборд, врачи, модерация (без части финансовых операций — см. OpenAPI) |
| **accountant** | Задолженности, ручные платежи, оверрайды оплаты у врача (как в роутерах) |

Эндпоинты задолженностей и ручных платежей: **admin** и **accountant** (как в коде роутеров).

---

## 2. Дашборд

**`GET /api/v1/admin/dashboard`**  
Роли: **admin**, **manager**.

Помимо метрик пользователей/врачей/подписок/платежей за месяц и год, учитывайте поля по задолженностям:

| Поле | Описание |
|------|----------|
| `arrears_open_total` | Сумма сумм по **открытым** долгам (`status=open`) |
| `arrears_open_count` | Количество строк с `open` |
| `arrears_paid_total` | Сумма по **оплаченным** через учёт долгов (`paid`) |
| `arrears_paid_count` | Количество таких строк |
| **`arrears_waived_total`** | Сумма **прощённых** (`waived`) — отчётность, не выручка |
| **`arrears_waived_count`** | Количество прощённых |

---

## 3. Врачи: список и карточка

### 3.1 Список и деталь

**`GET /api/v1/admin/doctors`** — список с фильтрами (см. OpenAPI).  
**`GET /api/v1/admin/doctors/{profile_id}`** — карточка врача.

В ответе **`DoctorDetailResponse`** для оплаты и задолженностей важны:

| Поле | Описание |
|------|----------|
| **`entry_fee_exempt`** | Не требовать вступительный при оплате (миграция / бухгалтерия) |
| **`membership_excluded_at`** | Дата исключения из ассоциации (если задана) — показать индикатор и текст по продукту |
| `subscription`, `payments` | Как раньше; в списке платежей могут быть строки с **`product_type: membership_arrears`** |

### 3.2 Оверрайды оплаты (вступительный)

**`PATCH /api/v1/admin/doctors/{profile_id}/payment-overrides`**  
Роли: **admin**, **accountant**.

Тело: `{ "entry_fee_exempt": true | false }`.

Ответ: обновлённая карточка врача (`DoctorDetailResponse`).

---

## 4. Задолженности (membership arrears)

Базовый префикс: **`/api/v1/admin/arrears`**. Роли: **admin**, **accountant**.

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/arrears` | Список с пагинацией и фильтрами |
| GET | `/arrears/summary` | Сводка: суммы/кол-ва по open, paid, **waived** |
| POST | `/arrears` | Создать долг вручную |
| PATCH | `/arrears/{id}` | Изменить сумму, описание, заметку (только `open`) |
| POST | `/arrears/{id}/cancel` | Статус `cancelled` (ошибочное начисление) |
| POST | `/arrears/{id}/waive` | Статус **`waived`**, аудит: `waived_at`, `waived_by`, `waive_reason` |
| POST | `/arrears/{id}/mark-paid` | Закрыть без провайдера (ручная отметка «оплачено») |

**Query-параметры списка `GET /arrears`:**

| Параметр | Описание |
|----------|----------|
| `user_id`, `year`, `status`, `source` | Фильтры; `status`: `open` / `paid` / `cancelled` / **`waived`** |
| **`include_inactive`** | `true` (по умолчанию): при **отсутствии** `status` — все статусы. `false`: только **`open`** (очередь к оплате). Если передан **`status`**, фильтр по статусу задаётся явно |

**Семантика:** **`cancel`** — отмена требования (ошибка). **`waive`** — осознанное прощение; строка **не удаляется**, остаётся в БД с аудитом для бухгалтерии.

**Карточка врача (UI):** рекомендуется блок «Задолженности»: открытые + история (оплаченные, прощённые, отменённые) — данные через **`GET /arrears?user_id=<uuid>`** с нужными фильтрами.

---

## 5. Платежи (админ)

### 5.1 Список платежей

**`GET /api/v1/admin/payments`**

Фильтр **`product_type`**: в т.ч. **`membership_arrears`** — оплата задолженности через Moneta/ручную отметку.

Статусы, **`status_label`**, **`expires_at`**, **`payment_url`** для pending — см. [PAYMENTS_UPDATE_ADMIN_FRONTEND.md](./PAYMENTS_UPDATE_ADMIN_FRONTEND.md).

### 5.2 Ручной платёж

**`POST /api/v1/admin/payments/manual`**

Тело (расширённое):

| Поле | Обязательность | Описание |
|------|----------------|----------|
| `user_id`, `amount`, `product_type`, `description` | да | `product_type`: `entry_fee` \| `subscription` \| `event` \| **`membership_arrears`** |
| `subscription_id` | для subscription/entry_fee при активации подписки | — |
| `event_registration_id` | для event | — |
| **`arrear_id`** | для **`membership_arrears`** | UUID долга; сумма должна **совпадать** с суммой долга; долг в статусе **`open`** |

При успешном создании ручного платежа с **`membership_arrears`** долг закрывается на бэкенде.

---

## 6. Настройки сайта

**`GET/PATCH /api/v1/admin/settings`** (роль **admin** — уточнить в OpenAPI).

Ключи, связанные с задолженностями:

| Ключ | Назначение |
|------|------------|
| `arrears_block_membership_features` | Блокировать привилегии члена при открытых долгах (каталог и т.д.) |
| `arrears_auto_accrual_enabled` | Включение автоматического начисления (на бэкенде пока заглушка job) |

---

## 7. Сценарий «возврат без долгов» (прощение)

- Старые требования **не удаляются**: перевод в **`waived`** через **`POST /arrears/{id}/waive`**.
- В личном кабинете врач прощённые долги **не видит** в списке к оплате.
- В админке строки с **`status=waived`**, поля **`waived_at`**, **`waived_by`**, **`waive_reason`** — для аудита.

---

## 8. Что вынесено в будущее (фаза 3)

Автонакопление, эскалация напоминаний, автоматическое исключение после N лет, Telegram по долгам — см. [ARREARS_PHASE3_BACKLOG.md](./ARREARS_PHASE3_BACKLOG.md).

---

## 9. Связанные документы

| Тема | Файл |
|------|------|
| Задолженности (детально, UI) | [ARREARS_ADMIN_FRONTEND.md](./ARREARS_ADMIN_FRONTEND.md) |
| Оплаты: статусы, labels, expired | [PAYMENTS_UPDATE_ADMIN_FRONTEND.md](./PAYMENTS_UPDATE_ADMIN_FRONTEND.md) |
| Отмена платежа | [PAYMENTS_CANCEL_ADMIN_FRONTEND.md](./PAYMENTS_CANCEL_ADMIN_FRONTEND.md) |
| Голосования, мероприятия, сертификаты, Telegram | см. `*_ADMIN_FRONTEND.md` в этой папке |

---

## 10. Чеклист фронта (админка)

- [ ] Список долгов с фильтрами **`status`**, **`include_inactive`**, **`user_id`**.
- [ ] Действия: создать, редактировать, **cancel**, **waive** (с причиной), **mark-paid**.
- [ ] Карточка врача: **`entry_fee_exempt`**, **`payment-overrides`**, **`membership_excluded_at`**, блок истории долгов.
- [ ] Ручной платёж: тип **`membership_arrears`** + **`arrear_id`**, валидация суммы.
- [ ] Список платежей: фильтр по **`membership_arrears`**.
- [ ] Дашборд: четыре метрики по долгам + **waived**.
- [ ] Настройки: тумблеры блокировки и авто-начисления.
