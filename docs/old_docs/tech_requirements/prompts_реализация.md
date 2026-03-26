# Промпты для реализации проекта «Ассоциация трихологов»

Отправлять подряд в Cursor **Agent mode**. Каждый промпт самодостаточен — прикрепляй @-файлы указанные в каждом.

---

## П1 — База данных: модели SQLAlchemy + миграции

```
Реализуй SQLAlchemy-модели и Alembic-миграцию для проекта «Ассоциация трихологов».

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/03_База_данных_v2.md

Задача:
1. Создай файлы моделей в backend/app/models/ — по одному файлу на группу таблиц:
   - users.py: users, telegram_bindings, notification_templates
   - profiles.py: doctor_profiles, doctor_documents, doctor_profile_changes, moderation_history, audit_log, specializations
   - subscriptions.py: plans, subscriptions, payments
   - events.py: events, event_tariffs, event_registrations, event_galleries, event_gallery_photos, event_recordings
   - content.py: articles, article_themes, article_theme_assignments, organization_documents, content_blocks, pages_seo
   - cities.py: cities
   - certificates.py: certificates
   - voting.py: voting_sessions, voting_candidates, votes
   - site.py: site_settings

2. Все модели:
   - UUID v7 как PK — используй библиотеку `uuid-utils` (python: `import uuid_utils; uuid_utils.uuid7()`)
   - Наследование от Base + TimestampMixin (created_at, updated_at)
   - SoftDeleteMixin (is_deleted, deleted_at) там где указано в ТЗ
   - FK с ondelete=CASCADE или SET NULL строго по ТЗ

3. Enum-типы — через PostgreSQL native enum (SQLAlchemy `Enum(..., native_enum=True)`):
   - doctor_status: pending_review, approved, rejected, active, deactivated
   - subscription_status: active, expired, pending_payment, cancelled
   - payment_status: pending, succeeded, failed, partially_refunded, refunded
   - product_type: entry_fee, subscription, event
   - change_status: pending, approved, rejected
   - event_status: upcoming, ongoing, finished, cancelled
   - Остальные из 03_База_данных_v2.md раздел «1. Enum-типы»

4. Индексы — строго по ТЗ, включая:
   - idx_doctor_profiles_created ON (created_at DESC)
   - idx_profile_changes_fields ON (changed_fields) USING GIN
   - uix_profile_changes_pending ON (doctor_profile_id) WHERE status='pending' (partial unique)
   - idx_doctor_profiles_active ON (status) WHERE status='active' (partial)

5. Создай Alembic-миграцию: `alembic revision --autogenerate -m "initial_schema"`
   - Проверь что downgrade() корректен

Чек-лист:
- [ ] Нет gen_random_uuid() — только uuid_utils.uuid7() на Python-уровне
- [ ] Все enum-типы соответствуют ТЗ (payment_status: succeeded, не completed!)
- [ ] GIN-индекс на changed_fields TEXT[]
- [ ] Partial unique index на doctor_profile_changes (только одна pending запись на профиль)
- [ ] alembic upgrade head проходит без ошибок
- [ ] alembic downgrade -1 тоже работает
```

---

## П2 — Backend: Auth модуль

```
Реализуй модуль аутентификации для проекта «Ассоциация трихологов».

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секция 2. Auth)

Задача — создай backend/app/api/v1/auth.py + backend/app/services/auth_service.py:

1. Pydantic-схемы (schemas/auth.py):
   - RegisterRequest: email, password (min 8), re_password
   - LoginRequest: email, password
   - TokenResponse: access_token, token_type="bearer"
   - ForgotPasswordRequest: email
   - ResetPasswordRequest: token, new_password
   - ChangePasswordRequest: current_password, new_password
   - ChangeEmailRequest: new_email, password
   - ConfirmEmailChangeRequest: token

2. AuthService (services/auth_service.py):
   - register(data) → создать user, отправить email-верификацию через TaskIQ
   - login(data) → Argon2id проверка, вернуть access JWT + refresh в Redis
   - refresh_token(refresh_token) → ротация, новая пара
   - logout(refresh_token) → удалить из Redis
   - forgot_password(email) → TaskIQ задача отправки письма
   - reset_password(token, new_password) → Redis проверка, обновить hash
   - change_password(user, current, new)
   - change_email(user, new_email, password) → TaskIQ задача подтверждения

3. JWT: RS256 алгоритм, access TTL=15 мин, refresh TTL=30 дней
   - Refresh хранится в Redis: ключ `refresh:{user_id}:{jti}`, значение = user_id
   - HttpOnly Secure cookie для refresh token

4. Все эндпоинты — POST методы, никаких PUT/PATCH

Чек-лист:
- [ ] POST /api/v1/auth/register → 201
- [ ] POST /api/v1/auth/login → access в body, refresh в HttpOnly cookie
- [ ] POST /api/v1/auth/refresh → ротация refresh токена
- [ ] POST /api/v1/auth/logout → удаление из Redis + очистка cookie
- [ ] Пароли: Argon2id через argon2-cffi
- [ ] Ошибки: {"error": {"code": "...", "message": "...", "details": {}}}
- [ ] Нет PUT запросов
```

---

## П3 — Backend: Онбординг + профиль врача

```
Реализуй модули онбординга и профиля врача.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Onboarding, Profile) @docs/tech_requirements/03_База_данных_v2.md @docs/tech_requirements/05_Интеграции.md

Задача — создай роутеры и сервисы:

1. Онбординг (api/v1/onboarding.py + services/onboarding_service.py):
   - GET /api/v1/onboarding/status → next_step: verify_email|choose_role|fill_profile|upload_documents|submit|await_moderation|pay_entry_fee|completed
   - POST /api/v1/onboarding/choose-role → body: {role: "doctor"|"user"}
   - PATCH /api/v1/onboarding/doctor-profile → частичное обновление анкеты (НЕ PUT!)
   - POST /api/v1/onboarding/documents → multipart, загрузка в S3 в папку doctors/{user_id}/documents/
   - POST /api/v1/onboarding/submit → проверить обязательные поля, статус → pending_review

2. Профиль (api/v1/profile.py + services/profile_service.py):
   - GET /api/v1/profile/personal
   - PATCH /api/v1/profile/personal → ФИО, phone, passport_data, registration_address, colleague_contacts
   - POST /api/v1/profile/diploma-photo → multipart → S3 doctors/{user_id}/documents/, вернуть diploma_photo_url
   - GET /api/v1/profile/public → включает поле pending_draft (если есть pending в doctor_profile_changes)
   - PATCH /api/v1/profile/public → создаёт запись в doctor_profile_changes со status=pending
   - POST /api/v1/profile/photo → multipart → S3 doctors/{user_id}/photo/, resize 800x800 + thumb 200x200

3. Загрузка файлов (services/file_service.py):
   - Валидация MIME: JPG/PNG/WebP, max 5MB
   - S3 через aioboto3 (Yandex Object Storage в prod, MinIO в dev)
   - Для приватных файлов — presigned URL с TTL 10 мин

Чек-лист:
- [ ] Нет ни одного PUT — только PATCH
- [ ] PATCH /profile/public создаёт doctor_profile_changes со status=pending
- [ ] Partial unique index соблюдается: нельзя создать вторую pending-запись (ловить IntegrityError → 409)
- [ ] GET /profile/public возвращает pending_draft если есть pending изменения
- [ ] Загрузка файлов: multipart/form-data, валидация типа и размера
```

---

## П4 — Backend: Модерация + Admin Doctors

```
Реализуй административный модуль управления врачами и модерации.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секция Admin — Doctors, Portal Users) @docs/tech_requirements/03_База_данных_v2.md

Задача — создай api/v1/doctors_admin.py + services/doctor_service.py:

1. GET /api/v1/admin/doctors — список с фильтрами + пагинация limit/offset:
   Query params: limit (default 20, max 100), offset (default 0), status (doctor_status enum),
   subscription_status, city_id, has_data_changed (bool), search (min 2 символа),
   sort_by (created_at|last_name|subscription_ends_at), sort_order (asc|desc)
   Response: { "data": [...], "total": N, "limit": 20, "offset": 0 }

2. GET /api/v1/admin/doctors/{id} — детальная карточка с pending_draft

3. POST /api/v1/admin/doctors/{id}/moderate — {action: "approve"|"reject", comment?: string}
   - approve: doctor_profiles.status → approved, запись в moderation_history
   - reject: doctor_profiles.status → rejected, rejection_reason, уведомление врача (TaskIQ)

4. POST /api/v1/admin/doctors/{id}/approve-draft — {action: "approve"|"reject", rejection_reason?: string}
   - approve: применить changes из doctor_profile_changes к doctor_profiles, status → approved
   - reject: doctor_profile_changes.status → rejected

5. POST /api/v1/admin/doctors/{id}/toggle-active — активация/деактивация

6. POST /api/v1/admin/doctors/{id}/send-reminder — TaskIQ задача отправки напоминания

7. POST /api/v1/admin/doctors/import — multipart Excel → TaskIQ задача → вернуть {task_id}
   GET /api/v1/admin/doctors/import/{task_id} → {status, processed, errors: [{row, message}]}

8. GET /api/v1/admin/portal-users — список не-врачей, limit/offset

Права: только Admin и Manager (не Accountant).

Чек-лист:
- [ ] Фильтр has_data_changed=true: WHERE EXISTS (SELECT 1 FROM doctor_profile_changes WHERE doctor_profile_id=id AND status='pending')
- [ ] moderation_history пишется при каждом approve/reject
- [ ] doctor_status использует pending_review, не new/pending
- [ ] Пагинация: limit/offset, ответ { data, total, limit, offset }
- [ ] Excel-импорт: построчная обработка, отчёт об ошибках по строкам
```

---

## П5 — Backend: Подписки, платежи, webhooks

```
Реализуй модуль подписок, платежей и интеграцию с YooKassa.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Subscriptions, Payments, Webhooks) @docs/tech_requirements/05_Интеграции.md (раздел YooKassa)

Задача:

1. POST /api/v1/subscriptions/pay (services/subscription_service.py):
   - Body: { plan_id, idempotency_key (UUID v4) }
   - Idempotency: Redis ключ `idempotency:pay:{user_id}:{key}`, TTL 24ч — если есть, вернуть кэш
   - Логика просрочки: если subscription.status=expired И разница между ends_at и now() ≤ 90 дней → product_type=subscription, starts_at=prev.ends_at
   - Если просрочка > 90 дней или нет подписки → product_type=entry_fee
   - Создать payments запись со status=pending
   - Вызвать YooKassa API (httpx async client): POST /v3/payments с Idempotence-Key header
   - Вернуть { payment_url }

2. GET /api/v1/admin/payments — список, limit/offset, фильтры: status, product_type, date_from, date_to, doctor_id
   Response: { data, total, limit, offset }

3. POST /api/v1/admin/payments/manual — ручной платёж (Admin/Accountant)

4. POST /api/v1/webhooks/yookassa:
   - Проверить IP YooKassa (whitelist)
   - Идемпотентность: если payment.status уже succeeded → return 200
   - При succeeded: payments.status → succeeded, subscription.status → active, doctor_profiles.status → active (если был approved)
   - При canceled: payments.status → failed
   - После коммита: TaskIQ задачи (уведомление email + Telegram, добавить в канал)
   - ВСЕГДА вернуть 200

5. YooKassa клиент (services/payment_service.py):
   - httpx.AsyncClient, retry с exponential backoff (3 попытки)
   - Idempotence-Key в заголовке каждого запроса

Чек-лист:
- [ ] payment_status: succeeded (не completed!)
- [ ] idempotency_key проверяется до создания payment
- [ ] Webhook: IP whitelist ИЛИ HMAC подпись
- [ ] Транзакция при обработке webhook (payment + subscription + doctor_profile одним коммитом)
- [ ] TaskIQ задачи после коммита (не внутри транзакции)
- [ ] Нет PUT запросов
```

---

## П6 — Backend: Публичный API (города, каталог, события, контент)

```
Реализуй публичные API эндпоинты для клиентского сайта.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Cities, Doctors public, Events public, Content public)

Задача:

1. GET /api/v1/cities — справочник городов (Guest):
   - Query: with_doctors=bool (default false), sort=name
   - Если with_doctors=true: добавить doctors_count, фильтровать city WHERE doctors_count > 0
   - Кеш Redis 5 мин
   - НЕТ отдельного GET /api/v1/cities-with-doctors (deprecated)

2. GET /api/v1/doctors — публичный каталог (Guest), limit/offset:
   - Только status=active профили
   - Фильтры: city_slug, specialization_slug, search
   - Response: { data, total, limit, offset }

3. GET /api/v1/doctors/{id} — публичная карточка (Guest)
   - Только status=active, иначе 404

4. GET /api/v1/events — список мероприятий (Guest), limit/offset:
   - Фильтры: period=upcoming|past
   - Response: { data, total, limit, offset }

5. GET /api/v1/events/{slug} — детальная страница (Guest)

6. GET /api/v1/articles — список статей (Guest), limit/offset:
   - Фильтры: theme_slug, search
   - Response: { data, total, limit, offset }

7. GET /api/v1/article-themes — публичный список активных тем (Guest):
   - Query: active=bool, has_articles=bool
   - Response: { data: [{id, slug, title}] } (без пагинации — тем немного)

8. GET /api/v1/articles/{slug} — статья (Guest)

ВАЖНО: POST /api/v1/events/{event_id}/register → немедленно возвращать HTTP 501 с телом:
{"error": {"code": "NOT_IMPLEMENTED", "message": "Регистрация на мероприятия будет доступна в следующей версии (M09)", "details": {}}}

Чек-лист:
- [ ] Все list-эндпоинты: limit/offset, ответ { data, total, limit, offset }
- [ ] GET /api/v1/cities?with_doctors=true работает, /cities-with-doctors отсутствует
- [ ] Только active врачи в публичном каталоге
- [ ] /events/{id}/register → 501
- [ ] Auth не требуется (Guest доступ)
- [ ] Кеш Redis для городов и каталога врачей
```

---

## П7 — Frontend (клиент): Публичный сайт + Личный кабинет

```
Реализуй клиентский фронтенд: публичные страницы и личный кабинет врача.

Контекст: @docs/rules/FRONTEND_RULES.md @docs/tech_requirements/07_Фронтенд_клиент.md @docs/tech_requirements/04_Backend_API.md

Стек: Next.js 15 App Router, TypeScript strict, TailwindCSS v4, React Query, React Hook Form + Zod.

СТАНДАРТ ПАГИНАЦИИ — все list-запросы: ?limit=20&offset=0, ответ { data, total, limit, offset }.

Хук пагинации (shared):
```typescript
function usePagination(defaultLimit = 20) {
  const [offset, setOffset] = useState(0);
  const limit = defaultLimit;
  const nextPage = () => setOffset(o => o + limit);
  const prevPage = () => setOffset(o => Math.max(0, o - limit));
  return { offset, limit, nextPage, prevPage };
}
```

ЧАСТЬ А — Публичные страницы (Server Components где возможно):
1. /cities — список городов (GET /api/v1/cities?with_doctors=true)
2. /cities/[slug] — врачи города (GET /api/v1/doctors?city_slug=...)
3. /doctors — каталог с фильтрами city, specialization, search (debounce 300ms)
4. /doctors/[id] — карточка врача
5. /events — список (только информационно, нет кнопки регистрации)
6. /events/[slug] — детальная страница, нет кнопки «Зарегистрироваться»
7. /articles — список с фильтром темы (GET /api/v1/article-themes для фильтра)
8. /articles/[slug] — статья

ЧАСТЬ Б — Личный кабинет (/cabinet, только Doctor):
1. /cabinet — дашборд: статус профиля, подписка, ближайшие мероприятия
2. /cabinet/profile/personal — PATCH /api/v1/profile/personal
   Zod-схема: { last_name?: .max(100), first_name?: .max(100), middle_name?: .max(100),
   phone?: .regex(/^\+7\d{10}$/), passport_data?: string, registration_address?: .max(500),
   colleague_contacts?: .max(500) }
   Загрузка фото: POST /api/v1/profile/photo (accept: image/jpeg,image/png, max 5MB)
   Загрузка диплома: POST /api/v1/profile/diploma-photo (accept: image/jpeg,image/png,image/webp, max 5MB)
3. /cabinet/profile/public — PATCH /api/v1/profile/public
   Блок «На модерации»: показывать если GET /api/v1/profile/public вернул pending_draft != null
   Форма disabled если pending_draft существует
4. /cabinet/payments — подписка + история платежей
   Кнопка «Оплатить»: POST /api/v1/subscriptions/pay → redirect на payment_url
   Показывать если subscription.status=expired ИЛИ (status=active И ends_at через <30 дней)
5. /cabinet/certificates — GET /api/v1/certificates (только если doctor_status=active)

Статусы (строго из БД):
- payment_status: pending | succeeded | failed | partially_refunded | refunded
- doctor_status: pending_review | approved | rejected | active | deactivated
- subscription_status: active | expired | pending_payment | cancelled

Чек-лист:
- [ ] TypeScript strict, нет any
- [ ] "use client" только для форм и интерактивных компонентов
- [ ] Все list-запросы используют limit/offset
- [ ] payment badge: "succeeded" → «Оплачен» (не "completed"!)
- [ ] Форма публичного профиля disabled при pending_draft
- [ ] Загрузка файлов: валидация типа и размера на клиенте до отправки
- [ ] Мобильная адаптивность (mobile-first Tailwind)
```

---

## П8 — Frontend (админка): Управление врачами, контент, настройки

```
Реализуй административную панель.

Контекст: @docs/rules/FRONTEND_RULES.md @docs/tech_requirements/06_Фронтенд_админка.md @docs/tech_requirements/04_Backend_API.md

Стек: Next.js 15, TypeScript strict, TailwindCSS v4, React Query, React Hook Form + Zod.
Все мутации обновления — PATCH (не PUT!). Все списки — limit/offset пагинация.

ЧАСТЬ А — Врачи (/admin/doctors):
1. Список с фильтрами: status (pending_review|approved|rejected|active|deactivated),
   subscription_status, city_id, has_data_changed (bool), search
   Таблица: Имя, Email, Город, Статус, Подписка до, Данные изменились (иконка), Действия
   Пагинация: limit/offset, варианты 20/50/100

2. Карточка врача /admin/doctors/[id]:
   - Текущий профиль
   - Блок «Ожидает модерации» (pending_draft != null): подсветить изменённые поля
   - Кнопки «Одобрить» / «Отклонить» изменения (rejection_reason — обязательное поле при отклонении)
   - Кнопки «Активировать» / «Деактивировать»

ЧАСТЬ Б — Контент:
3. /admin/content/articles — список + редактор (PATCH /api/v1/admin/articles/{id}, не PUT!)
4. /admin/content/article-themes — CRUD тем:
   - Таблица: slug, title, is_active, sort_order, кол-во статей
   - Модалка создания/редактирования: POST создание, PATCH обновление (не PUT!)
   - Удаление с confirm-диалогом

ЧАСТЬ В — Платежи (/admin/payments):
5. Список с фильтрами: status, product_type, date_from, date_to
   Статус badges: pending=Жёлтый, succeeded=Зелёный («Оплачен»), failed=Красный, refunded=Серый
   ВАЖНО: кнопки «Возврат» (refund) НЕ ОТОБРАЖАТЬ и не реализовывать

ЧАСТЬ Г — Настройки:
6. /admin/settings — GET + PATCH /api/v1/admin/settings (не PUT!)
7. /admin/cities — CRUD городов: PATCH обновление (не PUT!)
8. /admin/plans — CRUD тарифов: PATCH обновление (не PUT!)

Статусы (строго из БД, не придумывать новые):
- doctor_status: pending_review | approved | rejected | active | deactivated
- payment_status: pending | succeeded | failed | partially_refunded | refunded
- event_status: upcoming | ongoing | finished | cancelled (не draft/published/completed!)

Чек-лист:
- [ ] Нет ни одного PUT-запроса — только PATCH
- [ ] payment badge: "succeeded" → «Оплачен» (не "completed"!)
- [ ] doctor_status фильтр: значения pending_review, approved, rejected, active, deactivated
- [ ] event_status: upcoming/ongoing/finished/cancelled (не draft/published!)
- [ ] Кнопки возврата полностью убраны со страницы платежей
- [ ] Форма отклонения изменений: rejection_reason обязательное поле (Zod: .min(1))
- [ ] Все списки: limit/offset пагинация
```
