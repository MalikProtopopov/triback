# Онбординг врачей: Handoff для клиентского фронтенда

## Обзор

После регистрации и подтверждения email пользователь проходит онбординг: выбирает роль, заполняет анкету, загружает документы и отправляет на модерацию. Фронт определяет текущий шаг через `GET /onboarding/status` и направляет пользователя на нужный экран.

---

## API-эндпоинты

### 1. GET /api/v1/onboarding/status

Возвращает текущее состояние онбординга. Вызывается **после каждого логина** и **при входе на защищённые страницы**.

```json
{
  "email_verified": true,
  "role_chosen": true,
  "role": "doctor",
  "profile_filled": true,
  "documents_uploaded": true,
  "has_medical_diploma": true,
  "moderation_status": "pending_review",
  "submitted_at": "2026-03-10T12:00:00Z",
  "rejection_comment": null,
  "next_step": "await_moderation"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `email_verified` | bool | Email подтверждён |
| `role_chosen` | bool | Роль выбрана (doctor/user) |
| `role` | string \| null | `"doctor"` / `"user"` / null |
| `profile_filled` | bool | Заполнены ФИО и телефон |
| `documents_uploaded` | bool | Есть хотя бы 1 документ |
| `has_medical_diploma` | bool | Диплом загружен |
| `moderation_status` | string \| null | `pending_review` / `approved` / `rejected` / `active` / `deactivated` |
| `submitted_at` | datetime \| null | Дата отправки заявки на модерацию |
| `rejection_comment` | string \| null | Причина отклонения (при `moderation_status = rejected`) |
| `next_step` | string | Текущий шаг (см. таблицу ниже) |

---

### 2. POST /api/v1/onboarding/choose-role

Выбор роли. Вызывается один раз.

```json
{ "role": "doctor" }
```

Ответ:
```json
{
  "message": "Заполните анкету врача для прохождения модерации",
  "next_step": "fill_profile",
  "profile_id": "uuid",
  "moderation_status": "pending_review"
}
```

---

### 3. PATCH /api/v1/onboarding/doctor-profile

Частичное обновление анкеты. Отправлять только изменённые поля.

```json
{
  "first_name": "Иван",
  "last_name": "Петров",
  "middle_name": "Сергеевич",
  "phone": "+79001234567",
  "passport_data": "1234 567890",
  "city_id": "uuid",
  "clinic_name": "Клиника здоровья",
  "position": "Врач-дерматолог",
  "academic_degree": "к.м.н."
}
```

---

### 4. POST /api/v1/onboarding/documents

Загрузка документа. Multipart/form-data.

| Поле | Тип | Описание |
|------|-----|----------|
| `file` | File | Файл (PDF/JPG/PNG, до 10 МБ) |
| `document_type` | string | `medical_diploma` (обязательно), `retraining_cert`, `oncology_cert`, `additional_cert` |

Ответ 201:
```json
{
  "id": "uuid",
  "document_type": "medical_diploma",
  "original_filename": "diploma.pdf",
  "uploaded_at": "2026-03-10T12:00:00Z"
}
```

---

### 5. POST /api/v1/onboarding/submit

Отправка заявки на модерацию. Доступна при первой подаче и повторно после отклонения.

Валидация:
- ФИО и телефон заполнены
- Диплом загружен

Ответ:
```json
{
  "message": "Заявка отправлена на модерацию. Мы уведомим вас о результате",
  "next_step": "await_moderation",
  "profile_id": "uuid",
  "moderation_status": "pending_review"
}
```

Ошибки:
- `422` — обязательные поля не заполнены или диплом не загружен
- `409` — заявка уже одобрена

---

## Маппинг next_step → маршруты

| next_step | Маршрут | Экран |
|-----------|---------|-------|
| `verify_email` | Экран «Подтвердите email» | Инструкция и ссылка «Отправить письмо повторно» |
| `choose_role` | `/onboarding/role` | Выбор «Я врач» / «Я не врач» |
| `fill_profile` | `/onboarding/profile` | Форма анкеты (секция личных данных) |
| `upload_documents` | `/onboarding/profile` | Форма анкеты (фокус на блок документов) |
| `submit` | `/onboarding/profile` | Форма анкеты (кнопка «Отправить заявку» активна) |
| `await_moderation` | `/onboarding/pending` | Экран ожидания с polling |
| `completed` | `/cabinet` | Полный доступ в ЛК |

---

## Логика после логина

```
POST /auth/login → сохранить токен
→ GET /onboarding/status
→ если next_step !== "completed" → редирект на маршрут по таблице выше
→ если next_step === "completed" → /cabinet
```

---

## Guard для защищённых страниц

Перед рендером `/cabinet` и `/cabinet/*`:
1. Вызвать `GET /onboarding/status`.
2. Если `next_step !== "completed"` → редирект на соответствующий экран.
3. Если `completed` → показать ЛК.

На `/onboarding/*`: проверять авторизацию и текущий шаг, при несовпадении — редиректить на правильный шаг.

---

## Описание экранов

### Выбор роли (`/onboarding/role`)

- Две карточки: «Я — врач» и «Я — не врач».
- При выборе «врач» → `POST /onboarding/choose-role {role: "doctor"}` → редирект на `/onboarding/profile`.
- При выборе «не врач» → `POST /onboarding/choose-role {role: "user"}` → экран «Спасибо, данные сохранены».

### Анкета врача (`/onboarding/profile`)

**Секция 1 — Личные данные:**
- ФИО (обязательно), телефон (обязательно), паспортные данные, город (из справочника `GET /api/v1/cities`).

**Секция 2 — Профессиональные данные:**
- Клиника, должность, специализация, учёная степень.

**Секция 3 — Документы:**
- Диплом о высшем медицинском образовании (обязательно).
- Сертификат о переподготовке (опционально).
- Дополнительные сертификаты (опционально).
- Drag-and-drop, progress-bar, форматы PDF/JPG/PNG до 10 МБ.

**Кнопка «Отправить заявку»:**
- Видна когда: анкета заполнена + диплом загружен.
- Вызывает `POST /onboarding/submit`.
- После успеха → редирект на `/onboarding/pending`.

**При `moderation_status = rejected`:**
- Яркая плашка вверху: «Заявка отклонена. Причина: {rejection_comment}».
- Форма доступна для редактирования.
- Кнопка: «Исправить и отправить заново» → повторный `POST /onboarding/submit`.

### Ожидание модерации (`/onboarding/pending`)

- Текст: «Ваша заявка на проверке. Мы уведомим вас по email в течение 2–3 рабочих дней.»
- Дата подачи (из `submitted_at`).
- Polling: `GET /onboarding/status` каждые 30 секунд.
- При смене статуса:
  - `approved` / `active` → редирект в `/cabinet/payments` + toast «Заявка одобрена! Оплатите вступительный взнос».
  - `rejected` → редирект на `/onboarding/profile` + плашка с `rejection_comment`.

### Прогресс онбординга

Визуальный индикатор шагов: **Роль** → **Анкета** → **Документы** → **Отправка**. Текущий шаг выделен.

---

## Матрица доступа

| Условие | Доступ в ЛК | Что показывать |
|---------|-------------|----------------|
| role=user, next_step=completed | Полный | ЛК без функций врача |
| role=doctor, next_step=await_moderation | Ограничен | Баннер «Аккаунт на проверке», без оплат/сертификата |
| role=doctor, next_step ∈ (fill_profile, upload_documents, submit) | Нет | Редирект на `/onboarding/profile` |
| role=doctor, moderation_status=rejected | Нет | Редирект на `/onboarding/profile` с плашкой причины |
| role=doctor, next_step=completed | Полный | Все разделы ЛК |

---

## Повторная отправка после отклонения

1. Пользователь получает email «Заявка отклонена. Причина: ...».
2. При входе `GET /onboarding/status` вернёт `next_step = "fill_profile"` и `rejection_comment`.
3. Фронт перенаправляет на `/onboarding/profile` с плашкой причины.
4. Пользователь редактирует анкету/документы.
5. Нажимает «Отправить заново» → `POST /onboarding/submit`.
6. Статус становится `pending_review`, `next_step = "await_moderation"`.
7. Цикл повторяется.
