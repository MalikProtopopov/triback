# Онбординг клиентского портала — контракт API

Базовый префикс: `/api/v1`.

## Роли в JWT и в БД

- После регистрации **роль в БД не назначается**, пока пользователь не вызовет `POST /onboarding/choose-role`.
- В JWT при отсутствии записей в `UserRoleAssignment` в ответах логина/refresh и в поле `role` у **`GET /auth/me`** используется значение **`pending`** (не строка из таблицы `roles`).
- **`GET /auth/me`** всегда отдаёт `role`, `is_staff`, `sidebar_sections` **из БД** (эффективная роль через приоритет: admin → manager → accountant → doctor → user → иначе `pending`).

## `GET /onboarding/status`

Основной источник правды для шагов UI.

### Поля ответа

| Поле | Описание |
|------|----------|
| `email_verified` | Почта подтверждена |
| `role_chosen` | Выбрана роль `user` или `doctor` |
| `role` | `doctor` \| `user` \| `null` (до выбора) |
| `profile_filled`, `documents_uploaded`, `has_medical_diploma` | Для врача |
| `moderation_status`, `submitted_at`, `rejection_comment` | Для врача |
| `next_step` | См. таблицу ниже |
| `onboarding_applicable` | `false` для **staff** (admin / manager / accountant) — клиентский онбординг не показывать |
| `can_upgrade_to_doctor` | `true`, если в БД есть только роль `user`, можно вызвать `choose-role` с `doctor` |
| `status_label` | Краткая подпись шага на русском |
| `doctor_onboarding_summary` | Объект с `moderation_status`, `submitted_at`, `rejection_comment` для врача; у staff — `null` |

### Значения `next_step`

| Значение | Смысл |
|----------|--------|
| `verify_email` | Нужно подтвердить почту |
| `choose_role` | Почта ок, роль не выбрана |
| `completed` | Не-врач завершил выбор `user`, или врач одобрен/активен |
| `fill_profile` | Нужна анкета (или возврат после reject) |
| `upload_documents` | Нужен диплом и др. |
| `submit` | Отправить заявку |
| `await_moderation` | Заявка на проверке |
| `not_applicable` | Учётная запись **сотрудника** — онбординг портала не применяется |

### Staff (админ / менеджер / бухгалтер)

При входе на **клиентский** сайт с тем же аккаунтом:

- `next_step` = **`not_applicable`**
- `onboarding_applicable` = **`false`**
- Ориентир для UI: также `is_staff: true` в **`GET /auth/me`**

Не вызывать `POST /onboarding/choose-role` для staff — будет **403**.

## `POST /onboarding/choose-role`

Тело: `{ "role": "doctor" | "user" }`.

- Первый выбор роли после регистрации.
- **Апгрейд:** с `user` на `doctor` — повторный вызов с `"doctor"` (снимается роль `user`, добавляется `doctor`, создаётся профиль врача).
- **Идемпотентность:** повтор с уже выбранной ролью → **200**, сообщение «Роль уже выбрана», без нового `access_token`.
- **403** — учётная запись сотрудника.
- **409** — например запрос смены с врача на пользователя через портал (не поддерживается).

### Токены после смены роли

При **реальном** изменении ролей в ответе приходит **`access_token`** (и выставляется httpOnly cookie `access_token`, как при логине). Клиент должен подставлять новый токен в `Authorization`, иначе старый JWT может не совпадать с БД для ручек с проверкой роли врача.

## Прочие ручки онбординга

- `PATCH /onboarding/doctor-profile`, `POST /onboarding/documents`, `POST /onboarding/submit` — как раньше; требуют профиль врача (**404**, если не врач).

## Сценарии

1. **Регистрация → верификация email → логин** → `next_step`: `choose_role` (при отсутствии ролей в БД).
2. **Выбор «не врач»** → `user` → `next_step`: `completed`; позже **стать врачом** → снова `POST /choose-role` с `doctor`.
3. **Выбор врача** → шаги анкета → документы → submit → `await_moderation`.
4. **Гостевой поток мероприятия** может сразу назначить роль `user` в БД — это отдельный сценарий от регистрации с лендинга.
