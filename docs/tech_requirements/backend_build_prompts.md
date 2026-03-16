# Последовательные промпты для сборки бекенда — «Ассоциация трихологов»

> **Как использовать:** Открывай Cursor в режиме **Agent**. Каждый промпт отправляй последовательно — следующий только после того, как прошёл чек-лист текущего. `@`-ссылки — это файлы, которые нужно прикрепить как контекст.

---

## Этап 0 — Scaffold: структура проекта и окружение

```
Создай структуру бекенд-проекта для «Ассоциации трихологов».

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md

Задача — создай следующую файловую структуру (пустые файлы-заглушки с docstring):

backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan, подключение всех роутеров
│   ├── core/
│   │   ├── config.py            # Pydantic Settings, все env-переменные
│   │   ├── database.py          # AsyncEngine, AsyncSession, get_db_session
│   │   ├── redis.py             # Redis pool, get_redis
│   │   ├── security.py          # JWT encode/decode, Argon2id, require_role
│   │   ├── dependencies.py      # get_current_user, pagination params
│   │   ├── exceptions.py        # HTTP-исключения, RFC 7807 handler
│   │   ├── pagination.py        # PaginatedResponse[T], PaginationParams
│   │   └── logging.py           # structlog настройка JSON-логов
│   ├── models/
│   │   ├── base.py              # Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
│   │   ├── users.py
│   │   ├── profiles.py
│   │   ├── subscriptions.py
│   │   ├── events.py
│   │   ├── content.py
│   │   ├── cities.py
│   │   ├── certificates.py
│   │   ├── voting.py
│   │   └── site.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── api/
│   │   └── v1/
│   │       └── __init__.py      # APIRouter объединяющий все роутеры
│   ├── services/
│   │   └── __init__.py
│   └── tasks/
│       └── __init__.py
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   └── __init__.py
├── alembic.ini
├── pyproject.toml               # ruff + mypy настройки
└── requirements.txt

В requirements.txt включи:
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.2
pydantic==2.9.2
pydantic-settings==2.5.2
redis[hiredis]==5.1.0
argon2-cffi==23.1.0
python-jose[cryptography]==3.3.0
httpx==0.27.2
aioboto3==13.1.1
taskiq[redis]==0.11.7
taskiq-fastapi==0.3.2
structlog==24.4.0
ruff==0.6.9
mypy==1.11.3
pillow==10.4.0
openpyxl==3.1.5
uuid-utils==0.9.0
pytest==8.3.3
pytest-asyncio==0.24.0
factory-boy==3.3.1

Чек-лист:
- [ ] Все директории и файлы созданы
- [ ] requirements.txt с версиями
- [ ] pyproject.toml с ruff и mypy настройками (line-length=100, strict mypy)
- [ ] alembic.ini ссылается на backend/alembic/
- [ ] main.py содержит FastAPI(lifespan=...) с подключением к БД при старте
```

**Самопроверка после выполнения:**
```
Проверь структуру scaffold: @backend/app/main.py @backend/app/core/config.py @backend/requirements.txt

Убедись что:
- [ ] FastAPI app создаётся с lifespan context manager
- [ ] config.py читает все переменные из .env через Pydantic Settings
- [ ] В requirements.txt нет конфликтующих версий
- [ ] ruff lint проходит без ошибок: ruff check backend/
```

---

## Этап 1 — БД: Base, миксины и enum-типы

```
Реализуй базовые классы и enum-типы для SQLAlchemy моделей.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/03_База_данных_v2.md

Файл: backend/app/models/base.py

Задача:
1. DeclarativeBase как Base
2. Миксины:
   - UUIDMixin: id = UUID v7 через uuid_utils.uuid7() (не uuid4!)
   - TimestampMixin: created_at, updated_at (DateTime timezone=True, server_default=func.now())
   - SoftDeleteMixin: is_deleted=False, deleted_at=None
3. Все PostgreSQL enum-типы через SAEnum с native_enum=True:
   - DoctorStatus: pending_review, approved, rejected, active, deactivated
   - SubscriptionStatus: active, expired, pending_payment, cancelled
   - PaymentStatus: pending, succeeded, failed, partially_refunded, refunded
   - ProductType: entry_fee, subscription, event
   - ChangeStatus: pending, approved, rejected
   - EventStatus: upcoming, ongoing, finished, cancelled
   - DocumentType: diploma, retraining_certificate, additional_certificate
   - ModerationAction: approve, reject
   - NotificationChannel: email, telegram
   - CertificateType: membership, participation
   - ContentBlockType: text, image, video, file
   - ArticleStatus: draft, published, archived
   - VotingStatus: pending, active, finished

Чек-лист:
- [ ] uuid_utils.uuid7() — не gen_random_uuid(), не uuid4()
- [ ] Все enum-значения точно соответствуют 03_База_данных_v2.md (payment_status: succeeded, не completed!)
- [ ] DoctorStatus: pending_review (не new, не pending)
- [ ] native_enum=True для всех SAEnum
- [ ] TimestampMixin: updated_at с onupdate=func.now()
```

**Самопроверка после выполнения:**
```
Проверь base.py: @backend/app/models/base.py @docs/tech_requirements/03_База_данных_v2.md

- [ ] Открой раздел «1. Enum-типы» в 03_База_данных_v2.md и сравни каждый enum
- [ ] Запусти: python -c "from app.models.base import DoctorStatus; print(list(DoctorStatus))"
- [ ] Убедись что нет import-ошибок
```

---

## Этап 2 — БД: SQLAlchemy модели (все таблицы)

```
Реализуй SQLAlchemy-модели для всех таблиц проекта.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/03_База_данных_v2.md @backend/app/models/base.py

Создай файлы строго по группам:

backend/app/models/users.py:
  - users (email UK, password_hash, is_email_verified, is_active, role FK→roles)
  - telegram_bindings (user_id FK→users, telegram_id UK, auth_code, is_active)
  - notification_templates (code UK, channel, subject, body_template, is_active)

backend/app/models/profiles.py:
  - specializations (slug UK, title, is_active, sort_order)
  - doctor_profiles (user_id FK→users, все поля анкеты, status DoctorStatus, slug UK)
  - doctor_specializations (doctor_profile_id FK, specialization_id FK — M:N)
  - doctor_documents (doctor_profile_id FK, document_type DocumentType, s3_key, is_verified)
  - doctor_profile_changes (doctor_profile_id FK, changes JSONB, changed_fields TEXT[], status ChangeStatus)
  - moderation_history (doctor_profile_id FK, admin_user_id FK, action ModerationAction, comment)
  - audit_log (entity_type, entity_id UUID, action, old_data JSONB, new_data JSONB, user_id FK)

backend/app/models/subscriptions.py:
  - plans (name, slug UK, price NUMERIC(12,2), duration_days, is_active)
  - subscriptions (user_id FK→users, plan_id FK, status SubscriptionStatus, starts_at, ends_at)
  - payments (user_id FK→users, product_type ProductType, amount NUMERIC(12,2), status PaymentStatus,
              idempotency_key UK, yookassa_payment_id, subscription_id FK nullable,
              event_registration_id FK nullable)
  - receipts (payment_id FK→payments, receipt_url, fiscal_data JSONB)

backend/app/models/events.py:
  - events (title, slug UK, description, status EventStatus, starts_at, ends_at, location,
            max_seats, seats_taken, cover_image_url)
  - event_tariffs (event_id FK→events, title, price NUMERIC(12,2), is_member_price bool)
  - event_registrations (event_id FK, user_id FK nullable, tariff_id FK, email, full_name,
                         payment_id FK nullable)
  - event_galleries (event_id FK→events, title, is_visible)
  - event_gallery_photos (gallery_id FK, s3_key, sort_order)
  - event_recordings (event_id FK→events, title, video_url, is_visible_to_participants)

backend/app/models/content.py:
  - articles (title, slug UK, body, status ArticleStatus, author_id FK nullable,
              preview_image_url, seo_title, seo_description)
  - article_themes (slug UK, title, is_active, sort_order)
  - article_theme_assignments (article_id FK, theme_id FK — M:N)
  - organization_documents (title, slug UK, file_url, sort_order, is_published)
  - content_blocks (entity_type, entity_id UUID, block_type ContentBlockType, content JSONB, sort_order)
  - pages_seo (path UK, title, description, og_image_url)

backend/app/models/cities.py:
  - cities (name, slug UK, region, is_active, sort_order)

backend/app/models/certificates.py:
  - certificates (user_id FK→users, doctor_profile_id FK, certificate_type CertificateType,
                  pdf_url, issued_at)

backend/app/models/voting.py:
  - voting_sessions (title, status VotingStatus, starts_at, ends_at, description)
  - voting_candidates (session_id FK→voting_sessions, full_name, bio, photo_url, sort_order)
  - votes (session_id FK, candidate_id FK, user_id FK→users — UK на session_id+user_id)

backend/app/models/site.py:
  - site_settings (key UK, value TEXT, description)

Правила для ВСЕХ моделей:
- Наследование: Base + UUIDMixin + TimestampMixin (обязательно!)
- SoftDeleteMixin добавлять только: users, doctor_profiles, articles, events
- FK с ondelete указан ЯВНО (CASCADE или SET NULL)
- Индексы строго по ТЗ (включая GIN на changed_fields, partial unique на doctor_profile_changes)
- __tablename__ в snake_case множественное число

Чек-лист:
- [ ] Нет ни одного поля без типа (Mapped[...])
- [ ] Partial unique index: uix_profile_changes_pending на doctor_profile_changes
      WHERE status='pending' (один pending на профиль)
- [ ] GIN-индекс: idx_profile_changes_fields на changed_fields
- [ ] Votes: уникальная пара (session_id, user_id) — нельзя голосовать дважды
- [ ] payments.idempotency_key имеет UniqueConstraint
- [ ] SoftDeleteMixin только на указанных моделях, не на всех подряд
```

**Самопроверка после выполнения:**
```
Проверь модели: @backend/app/models/ @docs/tech_requirements/03_База_данных_v2.md

- [ ] python -c "from app.models import *" — нет import-ошибок
- [ ] Сравни количество таблиц: в ТЗ 33 таблицы — столько же должно быть в моделях
- [ ] Найди в коде: grep -r "ondelete" backend/app/models/ — каждый FK должен иметь ondelete
- [ ] Найди partial unique: grep -r "postgresql_where" backend/app/models/ — должен быть минимум 1
```

---

## Этап 3 — БД: Alembic миграция

```
Создай Alembic-миграцию для всех моделей проекта.

Контекст: @docs/rules/BACKEND_RULES.md @backend/app/models/ @backend/alembic/env.py

Задача:
1. Настрой alembic/env.py:
   - Импортировать все модели из app.models.*
   - target_metadata = Base.metadata
   - Использовать asyncpg (async engine в run_migrations_online)
   - Читать DATABASE_URL из env

2. Создай начальную миграцию:
   alembic revision --autogenerate -m "001_initial_schema"

3. Проверь сгенерированный файл alembic/versions/001_initial_schema.py:
   - Все enum-типы создаются через CREATE TYPE ... AS ENUM(...)
   - Partial unique index присутствует (uix_profile_changes_pending)
   - GIN-индекс присутствует (idx_profile_changes_fields)
   - downgrade() содержит DROP TABLE в обратном порядке и DROP TYPE для enum-ов

4. Примени миграцию:
   alembic upgrade head

Чек-лист:
- [ ] alembic upgrade head проходит без ошибок
- [ ] alembic downgrade -1 работает без ошибок
- [ ] alembic upgrade head повторно — idempotent (нет дублей)
- [ ] В БД созданы все 33 таблицы: SELECT count(*) FROM information_schema.tables WHERE table_schema='public'
- [ ] В БД созданы все enum-типы: SELECT typname FROM pg_type WHERE typcategory='E'
```

**Самопроверка после выполнения:**
```
Проверь миграцию: @backend/alembic/versions/ @backend/alembic/env.py

- [ ] Запусти: alembic upgrade head && alembic downgrade -1 && alembic upgrade head
- [ ] Все три команды выполнились без ошибок
- [ ] payment_status в миграции содержит 'succeeded' (не 'completed')
- [ ] doctor_status содержит 'pending_review' (не 'pending')
```

---

## Этап 4 — Core: конфиг, зависимости, исключения, пагинация

```
Реализуй core-модули бекенда.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md @backend/app/core/

Задача — реализуй 6 файлов:

1. backend/app/core/config.py:
   class Settings(BaseSettings):
   - DATABASE_URL: PostgresDsn
   - REDIS_URL: RedisDsn
   - SECRET_KEY: str (для JWT подписи, RS256)
   - ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
   - REFRESH_TOKEN_EXPIRE_DAYS: int = 30
   - S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET: str
   - YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY: str
   - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM: str
   - TELEGRAM_BOT_TOKEN: str
   - DEBUG: bool = False
   - ALLOWED_HOSTS: list[str] = ["*"]
   - model_config = SettingsConfigDict(env_file=".env")

2. backend/app/core/database.py:
   - async_engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=20)
   - AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
   - async def get_db_session() → AsyncGenerator[AsyncSession, None]
   - async def check_db_connection() → bool (для healthcheck)

3. backend/app/core/redis.py:
   - redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
   - async def get_redis() → Redis
   - async def check_redis_connection() → bool

4. backend/app/core/security.py:
   - create_access_token(user_id, role) → str (JWT, RS256, exp=15min)
   - create_refresh_token(user_id, jti) → str (JWT, RS256, exp=30days)
   - decode_token(token) → dict | None
   - hash_password(password) → str (Argon2id)
   - verify_password(plain, hashed) → bool
   - def require_role(*roles) → Depends (RBAC dependency)

5. backend/app/core/exceptions.py:
   - class AppError(HTTPException): тело в формате RFC 7807
     {"error": {"code": str, "message": str, "details": dict}}
   - Классы: NotFoundError(404), ForbiddenError(403), ConflictError(409),
     UnauthorizedError(401), ValidationError(422), NotImplementedError(501)
   - exception_handler для FastAPI регистрирующий все эти типы

6. backend/app/core/pagination.py:
   class PaginationParams:
     limit: int = Query(20, ge=1, le=100)
     offset: int = Query(0, ge=0)
   
   class PaginatedResponse(BaseModel, Generic[T]):
     data: list[T]
     total: int
     limit: int
     offset: int

Чек-лист:
- [ ] RS256 для JWT (не HS256!)
- [ ] Ошибки строго в формате {"error": {"code": "...", "message": "...", "details": {}}}
- [ ] PaginatedResponse использует поля data/total/limit/offset (не items/page/page_size!)
- [ ] get_db_session использует try/finally для гарантированного закрытия сессии
- [ ] Argon2id через argon2-cffi (не bcrypt!)
```

**Самопроверка после выполнения:**
```
Проверь core: @backend/app/core/

- [ ] python -c "from app.core.config import settings; print(settings.model_fields.keys())"
- [ ] python -c "from app.core.pagination import PaginatedResponse; print(PaginatedResponse.model_fields)"
- [ ] Убедись что PaginatedResponse имеет поля: data, total, limit, offset
- [ ] ruff check backend/app/core/ — нет ошибок
```

---

## Этап 5 — Auth модуль

```
Реализуй модуль аутентификации.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секция 2. Auth) @backend/app/core/ @backend/app/models/users.py

Создай файлы:
- backend/app/schemas/auth.py
- backend/app/services/auth_service.py
- backend/app/api/v1/auth.py

Задача:

1. schemas/auth.py:
   - RegisterRequest: email (EmailStr), password (min 8 символов), re_password (совпадает с password)
   - LoginRequest: email, password
   - TokenResponse: access_token, token_type="bearer"
   - ForgotPasswordRequest: email
   - ResetPasswordRequest: token, new_password
   - ChangePasswordRequest: current_password, new_password
   - ChangeEmailRequest: new_email, password
   - ConfirmEmailChangeRequest: token

2. services/auth_service.py (AuthService):
   - register(data) → User: создать user, положить email-verify token в Redis TTL=24h, TaskIQ задача отправки письма
   - verify_email(token) → User: достать из Redis, пометить is_email_verified=True
   - login(data) → dict: Argon2id verify, создать access + refresh JWT, refresh в Redis "refresh:{user_id}:{jti}" TTL=30d, вернуть access+refresh
   - refresh_token(refresh_token) → dict: ротация — удалить старый из Redis, создать новую пару
   - logout(refresh_token): удалить из Redis
   - forgot_password(email): TaskIQ задача → письмо со ссылкой, reset-token в Redis TTL=1h
   - reset_password(token, new_password): Redis проверка, обновить password_hash
   - change_password(user, current, new): verify текущего, обновить hash
   - change_email(user, new_email, password): verify пароля, TaskIQ → подтверждение на новый email

3. api/v1/auth.py (роутер prefix="/api/v1/auth"):
   - POST /register → 201 + {"message": "Проверьте email для подтверждения"}
   - POST /verify-email → 200
   - POST /login → access в body TokenResponse + refresh в HttpOnly Secure cookie "refresh_token"
   - POST /refresh → ротация токенов
   - POST /logout → очистка Redis + clear cookie
   - POST /forgot-password → 200 (всегда, не раскрывать существование email)
   - POST /reset-password → 200
   - POST /change-password → 200 (только авторизованный)
   - POST /change-email → 200 (только авторизованный)
   - POST /confirm-email-change → 200

Чек-лист:
- [ ] Только POST методы — нет GET/PUT/PATCH в auth
- [ ] Refresh token: HttpOnly + Secure + SameSite=Lax cookie (не в body!)
- [ ] Redis ключи: "refresh:{user_id}:{jti}", "email_verify:{token}", "reset_pwd:{token}"
- [ ] forgot_password НЕ раскрывает существует ли email (всегда 200)
- [ ] Argon2id через argon2-cffi, не bcrypt
- [ ] register проверяет что email ещё не занят → ConflictError(409)
```

**Самопроверка после выполнения:**
```
Проверь auth: @backend/app/api/v1/auth.py @backend/app/services/auth_service.py

- [ ] Запусти сервер: uvicorn app.main:app --reload
- [ ] Открой http://localhost:8000/docs — все /auth/* эндпоинты видны
- [ ] POST /api/v1/auth/register → 201
- [ ] POST /api/v1/auth/login → access_token в теле, cookie refresh_token в заголовках
- [ ] POST /api/v1/auth/logout → cookie удалена
- [ ] ruff check backend/app/services/auth_service.py
```

---

## Этап 6 — Онбординг + Профиль врача

```
Реализуй модули онбординга и профиля врача.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Onboarding, Profile) @docs/tech_requirements/03_База_данных_v2.md @backend/app/models/profiles.py

Создай:
- backend/app/schemas/onboarding.py
- backend/app/schemas/profile.py
- backend/app/services/onboarding_service.py
- backend/app/services/profile_service.py
- backend/app/services/file_service.py
- backend/app/api/v1/onboarding.py
- backend/app/api/v1/profile.py

Онбординг (prefix="/api/v1/onboarding"):
- GET /status → next_step: verify_email|choose_role|fill_profile|upload_documents|submit|await_moderation|pay_entry_fee|completed
- POST /choose-role → body: {role: "doctor"|"user"} → присвоить роль пользователю
- PATCH /doctor-profile → частичное обновление анкеты (НЕ PUT!)
- POST /documents → multipart/form-data, загрузка документа в S3: doctors/{user_id}/documents/{filename}
- POST /submit → проверить заполнение обязательных полей, status → pending_review

Профиль (prefix="/api/v1/profile"):
- GET /personal → личные данные (ФИО, phone, passport_data, registration_address, colleague_contacts)
- PATCH /personal → обновление личных данных (НЕ PUT!)
- POST /diploma-photo → multipart → S3 doctors/{user_id}/documents/, вернуть diploma_photo_url
- GET /public → публичный профиль + поле pending_draft (если есть pending в doctor_profile_changes)
- PATCH /public → создаёт запись в doctor_profile_changes со status=pending (НЕ PUT!)
- POST /photo → multipart → S3 doctors/{user_id}/photo/, resize 800x800 + thumb 200x200

services/file_service.py (FileService):
- upload_file(file, path, allowed_types, max_size_mb) → str (S3 key)
- get_presigned_url(s3_key, ttl=600) → str
- delete_file(s3_key)
- Разрешённые MIME: image/jpeg, image/png, image/webp
- Максимум: 5MB по умолчанию
- Клиент: aioboto3 (async)
- В dev: MinIO (endpoint от config.S3_ENDPOINT_URL)

Чек-лист:
- [ ] Нет ни одного PUT — только PATCH и POST
- [ ] PATCH /profile/public создаёт doctor_profile_changes со status='pending'
- [ ] IntegrityError при втором pending → ConflictError(409) "Изменения уже на модерации"
- [ ] GET /profile/public содержит поле pending_draft (None если нет)
- [ ] POST /documents: проверка MIME до загрузки в S3
- [ ] resize фото: Pillow, 800x800 + 200x200 thumbnail
- [ ] presigned URL для приватных документов (TTL 10 мин)
```

**Самопроверка после выполнения:**
```
Проверь онбординг и профиль: @backend/app/api/v1/onboarding.py @backend/app/api/v1/profile.py @backend/app/services/

- [ ] Swagger /docs: все /onboarding/* и /profile/* видны
- [ ] GET /api/v1/onboarding/status → {"next_step": "verify_email"} для нового пользователя
- [ ] PATCH /api/v1/profile/public дважды для одного юзера → второй вызов возвращает 409
- [ ] Попытка загрузить .pdf как фото → 422 (неверный MIME)
- [ ] ruff check backend/app/services/file_service.py
```

---

## Этап 7 — Модерация + Admin: управление врачами

```
Реализуй административные модули модерации и управления врачами.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секция Admin — Doctors) @backend/app/models/profiles.py @backend/app/core/

Создай:
- backend/app/schemas/doctor_admin.py
- backend/app/services/doctor_service.py
- backend/app/api/v1/doctors_admin.py

Задача (prefix="/api/v1/admin", require_role admin или manager):

1. GET /doctors — список с фильтрами + пагинация:
   - Query: limit (default 20, max 100), offset (default 0)
   - Фильтры: status (DoctorStatus), subscription_status, city_id, has_data_changed (bool), search (мин 2 символа), sort_by (created_at|last_name|subscription_ends_at), sort_order (asc|desc)
   - has_data_changed=true: WHERE EXISTS (SELECT 1 FROM doctor_profile_changes WHERE doctor_profile_id=id AND status='pending')
   - Response: PaginatedResponse[DoctorListItemResponse]

2. GET /doctors/{id} — детальная карточка:
   - Включает: профиль, документы, pending_draft (если status='pending' в doctor_profile_changes), история платежей, подписка

3. POST /doctors/{id}/moderate — {action: "approve"|"reject", comment?: str}
   - approve: doctor_profiles.status → approved, запись в moderation_history, TaskIQ: отправить уведомление
   - reject: doctor_profiles.status → rejected, rejection_reason, TaskIQ: уведомление врача

4. POST /doctors/{id}/approve-draft — {action: "approve"|"reject", rejection_reason?: str}
   - approve: применить changes JSONB к doctor_profiles, doctor_profile_changes.status → approved
   - reject: doctor_profile_changes.status → rejected
   - rejection_reason обязательна при reject!

5. POST /doctors/{id}/toggle-active — активация/деактивация профиля

6. POST /doctors/{id}/send-reminder — TaskIQ задача отправки email-напоминания

7. POST /doctors/import — multipart Excel (.xlsx) → TaskIQ задача async обработки → {task_id}
   GET /doctors/import/{task_id} → {status: pending|processing|done|error, processed: N, errors: [{row, message}]}

8. GET /portal-users — список пользователей с role=user, limit/offset

Чек-лист:
- [ ] Все эндпоинты: require_role("admin", "manager") — accountant не имеет доступа к врачам
- [ ] moderation_history пишется при КАЖДОМ approve/reject (не только при первом)
- [ ] approve-draft: применить JSONB changes через dict merge, НЕ обновлять поля вручную
- [ ] Excel-импорт: построчный разбор, ошибки не останавливают обработку остальных строк
- [ ] Пагинация: limit/offset, ответ строго { data, total, limit, offset }
- [ ] sort_by=subscription_ends_at: JOIN subscriptions, сортировка по ends_at
```

**Самопроверка после выполнения:**
```
Проверь admin: @backend/app/api/v1/doctors_admin.py @backend/app/services/doctor_service.py

- [ ] GET /api/v1/admin/doctors — требует авторизацию (без токена → 401)
- [ ] GET /api/v1/admin/doctors — с токеном accountant → 403
- [ ] GET /api/v1/admin/doctors?has_data_changed=true — SQL запрос содержит EXISTS подзапрос
- [ ] POST /api/v1/admin/doctors/{id}/approve-draft с reject без rejection_reason → 422
- [ ] ruff check backend/app/api/v1/doctors_admin.py
```

---

## Этап 8 — Подписки, платежи, YooKassa webhook

```
Реализуй модуль подписок, платежей и интеграцию с YooKassa.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Subscriptions, Payments, Webhooks) @docs/tech_requirements/05_Интеграции.md @backend/app/models/subscriptions.py

Создай:
- backend/app/schemas/subscriptions.py
- backend/app/schemas/payments.py
- backend/app/services/subscription_service.py
- backend/app/services/payment_service.py
- backend/app/api/v1/subscriptions.py
- backend/app/api/v1/payments_admin.py
- backend/app/api/v1/webhooks.py

1. services/payment_service.py (YooKassaClient):
   - create_payment(amount, description, idempotency_key, return_url) → dict (ответ YooKassa)
   - HTTP клиент: httpx.AsyncClient, Basic Auth (shop_id:secret_key)
   - Заголовок: Idempotence-Key: {idempotency_key}
   - URL: https://api.yookassa.ru/v3/payments
   - Retry: 3 попытки с exponential backoff (1s, 2s, 4s) при 5xx

2. POST /api/v1/subscriptions/pay (авторизованный doctor):
   - Body: { plan_id: UUID, idempotency_key: UUID }
   - Idempotency Redis: "idempotency:pay:{user_id}:{idempotency_key}" TTL=24h — если есть, вернуть кэш
   - Логика просрочки:
     * Нет подписки ИЛИ просрочка > 90 дней → product_type='entry_fee'
     * Есть подписка, просрочка ≤ 90 дней → product_type='subscription', starts_at=prev.ends_at
   - Создать payments запись status='pending'
   - Вызвать YooKassaClient.create_payment()
   - Вернуть { payment_url: str }

3. GET /api/v1/subscriptions/status — текущий статус подписки (авторизованный)

4. GET /api/v1/admin/payments — список платежей (admin, manager, accountant):
   - Фильтры: status, product_type, date_from, date_to, doctor_id
   - PaginatedResponse, limit/offset

5. POST /api/v1/admin/payments/manual — ручной платёж:
   - Body: { user_id, product_type, amount, comment }
   - Сразу status='succeeded', обновить подписку
   - Права: только Admin и Accountant

6. POST /api/v1/webhooks/yookassa:
   - Проверить X-Real-IP в whitelist YooKassa (185.71.76.0/27, 185.71.77.0/27, 77.75.153.0/25, 77.75.156.11, 77.75.156.35, 2a02:5180::/32)
   - Тело: {type: "notification", event: "payment.succeeded"|"payment.canceled", object: {...}}
   - Идемпотентность: если payment.status уже 'succeeded' → return 200 без действий
   - payment.succeeded: одна транзакция (payments.status='succeeded' + subscription.status='active' + doctor_profiles.status='active' если был 'approved')
   - payment.canceled: payments.status='failed'
   - После коммита: TaskIQ задачи (email уведомление + Telegram + добавить в канал)
   - ВСЕГДА return 200 (YooKassa требует 200 даже при ошибках)

Чек-лист:
- [ ] payment_status: 'succeeded' (не 'completed'!)
- [ ] idempotency_key проверяется ПЕРВЫМ — до создания payments записи
- [ ] Webhook: обязательная проверка IP whitelist
- [ ] Webhook транзакция: payment + subscription + doctor_profile в одном db.commit()
- [ ] TaskIQ задачи запускаются ПОСЛЕ коммита (не внутри транзакции)
- [ ] Нет PUT-запросов
- [ ] manual payment: только admin и accountant (не manager!)
```

**Самопроверка после выполнения:**
```
Проверь платежи: @backend/app/api/v1/webhooks.py @backend/app/services/payment_service.py @backend/app/services/subscription_service.py

- [ ] POST /api/v1/subscriptions/pay дважды с одинаковым idempotency_key → второй вызов вернёт тот же payment_url из кэша
- [ ] POST /api/v1/webhooks/yookassa с не-whitelist IP → 403
- [ ] POST /api/v1/webhooks/yookassa симуляция payment.succeeded → payment.status='succeeded'
- [ ] Проверь что TaskIQ задачи не вызываются внутри транзакции
- [ ] ruff check backend/app/api/v1/webhooks.py
```

---

## Этап 9 — Публичный API

```
Реализуй публичные API эндпоинты (без авторизации).

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Cities, Doctors public, Events public, Content public) @backend/app/models/

Создай:
- backend/app/schemas/public.py (DoctorPublicResponse, EventPublicResponse, ArticlePublicResponse и т.д.)
- backend/app/services/public_service.py
- backend/app/api/v1/public.py (prefix="/api/v1")

Эндпоинты (все Guest — без auth):

1. GET /cities:
   - Query: with_doctors=bool (default false), sort=name
   - with_doctors=true: добавить doctors_count, исключить города с 0 врачами
   - Кэш Redis: "cache:cities:{with_doctors}" TTL=300s
   - НЕ создавать /cities-with-doctors (устаревший)

2. GET /doctors — публичный каталог, только status='active':
   - Фильтры: city_slug, specialization_slug, search
   - PaginatedResponse, limit/offset

3. GET /doctors/{id} — карточка, только status='active', иначе 404

4. GET /events — список мероприятий:
   - Фильтр: period=upcoming|past
   - PaginatedResponse, limit/offset

5. GET /events/{slug} — детальная страница мероприятия

6. POST /events/{event_id}/register → HTTP 501:
   {"error": {"code": "NOT_IMPLEMENTED", "message": "Регистрация на мероприятия будет доступна в следующей версии (M09)", "details": {}}}

7. GET /articles — список, фильтр: theme_slug, search, PaginatedResponse

8. GET /article-themes — список активных тем (без пагинации — тем немного):
   - Query: active=bool, has_articles=bool
   - Response: { data: [{id, slug, title}] }

9. GET /articles/{slug} — статья, только status='published'

Чек-лист:
- [ ] GET /cities?with_doctors=true — НЕТ отдельного маршрута /cities-with-doctors
- [ ] Только active врачи (не approved, не deactivated)
- [ ] POST /events/{id}/register → строго 501
- [ ] Кэш Redis для городов работает (второй запрос из кэша)
- [ ] Нет требования авторизации ни на одном из этих эндпоинтов
- [ ] limit/offset пагинация во всех list-эндпоинтах
```

**Самопроверка после выполнения:**
```
Проверь публичный API: @backend/app/api/v1/public.py @backend/app/services/public_service.py

- [ ] GET /api/v1/doctors — работает без Authorization header → 200
- [ ] GET /api/v1/doctors/{id_несуществующего} → 404
- [ ] POST /api/v1/events/any-id/register → 501 с нужным JSON
- [ ] GET /api/v1/cities?with_doctors=true — в ответе есть doctors_count
- [ ] ruff check backend/app/api/v1/public.py
```

---

## Этап 10 — Admin: события, контент, настройки

```
Реализуй административные модули управления событиями, контентом и настройками.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Admin Events, Content, Settings) @backend/app/models/

Создай:
- backend/app/schemas/events_admin.py
- backend/app/schemas/content_admin.py
- backend/app/services/events_service.py
- backend/app/services/content_service.py
- backend/app/api/v1/events_admin.py
- backend/app/api/v1/content_admin.py
- backend/app/api/v1/settings_admin.py

1. events_admin.py (prefix="/api/v1/admin/events"):
   - GET /events — список, фильтры: status (EventStatus), date_from, date_to — PaginatedResponse
   - POST /events → 201 (создание)
   - GET /events/{id} — детальная карточка
   - PATCH /events/{id} — обновление (НЕ PUT!)
   - DELETE /events/{id} → 204 (soft delete или status='cancelled')
   - POST /events/{id}/galleries — создать галерею
   - POST /events/{id}/galleries/{gallery_id}/photos — загрузить фото в галерею (multipart)
   - POST /events/{id}/recordings — добавить запись мероприятия

2. content_admin.py (prefix="/api/v1/admin"):
   - GET /articles — список, фильтры: status, theme_slug — PaginatedResponse
   - POST /articles → 201
   - GET /articles/{id}
   - PATCH /articles/{id} — НЕ PUT!
   - DELETE /articles/{id} → 204
   
   - GET /article-themes
   - POST /article-themes → 201
   - PATCH /article-themes/{id} — НЕ PUT!
   - DELETE /article-themes/{id} → 204
   
   - GET /organization-documents
   - POST /organization-documents → 201
   - PATCH /organization-documents/{id} — НЕ PUT!
   - DELETE /organization-documents/{id} → 204

3. settings_admin.py (prefix="/api/v1/admin"):
   - GET /settings — все site_settings ключ-значение
   - PATCH /settings — обновить несколько ключей одним запросом (не PUT!)
   
   - GET /cities + POST /cities + PATCH /cities/{id} + DELETE /cities/{id}
   - GET /plans + POST /plans + PATCH /plans/{id} + DELETE /plans/{id}

Чек-лист:
- [ ] event_status: upcoming/ongoing/finished/cancelled — нет draft/published/completed!
- [ ] Нет ни одного PUT — только PATCH
- [ ] EventStatus значения совпадают с enum в БД
- [ ] DELETE событий: soft delete (status='cancelled') или is_deleted=True — без реального удаления
- [ ] Загрузка фото галереи через FileService (не напрямую)
```

**Самопроверка после выполнения:**
```
Проверь admin events/content: @backend/app/api/v1/events_admin.py @backend/app/api/v1/content_admin.py

- [ ] POST /api/v1/admin/events с status='draft' → 422 (такого статуса нет)
- [ ] PATCH /api/v1/admin/events/{id} — работает
- [ ] PUT /api/v1/admin/events/{id} → 405 Method Not Allowed (нет такого маршрута)
- [ ] ruff check backend/app/api/v1/events_admin.py backend/app/api/v1/content_admin.py
```

---

## Этап 11 — Уведомления, сертификаты, Telegram, голосование

```
Реализуй вспомогательные модули: уведомления, сертификаты, Telegram-бот, голосование.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md (секции Notifications, Certificates, Telegram, Voting, Dashboard) @docs/tech_requirements/05_Интеграции.md @backend/app/models/

Создай:

1. services/notification_service.py:
   - send_email(to, template_code, context) → использует notification_templates из БД, SMTP
   - TaskIQ задачи: send_subscription_reminder(user_id, days_left), send_moderation_result(user_id, approved)
   - Автоматические напоминания: cron каждый день проверяет ends_at через 30/7/3/1 дней

2. services/certificate_service.py:
   - generate_membership_certificate(doctor_profile_id) → PDF (WeasyPrint или reportlab)
   - Сохранить в S3: certificates/{user_id}/{uuid}.pdf
   - Создать запись в certificates таблице
   - GET /api/v1/certificates — список сертификатов (только doctor со status=active)
   - GET /api/v1/certificates/{id}/download → redirect на presigned S3 URL

3. services/telegram_service.py:
   - TelegramBot через httpx (не aiogram, простые HTTP вызовы)
   - send_message(chat_id, text) — уведомление в Telegram
   - add_to_channel(telegram_id) — добавить в закрытый канал
   - remove_from_channel(telegram_id) — удалить из канала
   - generate_auth_code(user_id) → 6-значный код, Redis "tg_auth:{code}" TTL=10min
   - POST /api/v1/telegram/bind — связать Telegram через auth код
   - POST /api/v1/telegram/unbind — отвязать
   - POST /api/v1/telegram/webhook — обработка событий от бота (Telegram Bot API webhook)

4. api/v1/voting.py (prefix="/api/v1"):
   - GET /voting/active — активная сессия голосования (если есть)
   - POST /voting/{session_id}/vote — { candidate_id } → записать голос
     * Проверить: один голос на пользователя (UniqueConstraint)
     * Только авторизованный doctor со status=active
   - GET /api/v1/admin/voting — список сессий (admin)
   - POST /api/v1/admin/voting — создать сессию
   - PATCH /api/v1/admin/voting/{id} — обновить (НЕ PUT!)
   - GET /api/v1/admin/voting/{id}/results — результаты

5. GET /api/v1/admin/dashboard:
   - funnel: { registered, email_verified, profile_filled, moderation_passed, active }
   - expiring_subscriptions: список врачей у которых ends_at через ≤30 дней
   - payment_totals: { total_month, by_product_type: {...} }
   - upcoming_events: ближайшие 3 мероприятия

Чек-лист:
- [ ] Сертификаты: только для doctor_status=active (не approved, не deactivated)
- [ ] Голосование: один голос на session_id+user_id (IntegrityError → 409)
- [ ] Telegram auth code: Redis TTL=10min, одноразовый (удалять после использования)
- [ ] Dashboard: payment_totals используют payment_status='succeeded'
- [ ] Напоминания: cron job, не при каждом запросе
```

**Самопроверка после выполнения:**
```
Проверь доп. модули: @backend/app/services/notification_service.py @backend/app/api/v1/voting.py

- [ ] POST /api/v1/voting/{id}/vote дважды одним юзером → 409
- [ ] GET /api/v1/certificates недоступен для doctor со status=approved (только active)
- [ ] GET /api/v1/admin/dashboard → JSON с ключами funnel, expiring_subscriptions, payment_totals, upcoming_events
- [ ] ruff check backend/app/services/ backend/app/api/
```

---

## Этап 12 — TaskIQ: фоновые задачи

```
Реализуй систему фоновых задач через TaskIQ + Redis.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/05_Интеграции.md (раздел TaskIQ) @backend/app/services/

Создай: backend/app/tasks/

Файлы:
- tasks/__init__.py — инициализация broker (TaskIQ Redis broker)
- tasks/email_tasks.py:
  * send_verification_email(user_id, token)
  * send_password_reset_email(user_id, token)
  * send_subscription_reminder(user_id, days_left)
  * send_moderation_approved(user_id)
  * send_moderation_rejected(user_id, reason)
  * send_payment_success(user_id, amount, product_type)

- tasks/telegram_tasks.py:
  * notify_admin_new_registration(user_id)
  * add_user_to_channel(telegram_id)
  * remove_user_from_channel(telegram_id)

- tasks/profile_tasks.py:
  * process_excel_import(task_id, s3_key) → построчная обработка, результат в Redis
  * generate_certificate(doctor_profile_id)
  * resize_profile_photo(s3_key)

- tasks/scheduler.py (cron задачи):
  * check_expiring_subscriptions() — каждый день в 09:00 UTC
  * deactivate_expired_subscriptions() — каждый час

Настройка в main.py:
- broker = TaskiqRedisResultBackend + TaskiqAioAmqpBroker или Redis broker
- startup: await broker.startup()
- shutdown: await broker.shutdown()

Чек-лист:
- [ ] Задачи вызываются через .kiq() — НЕ await напрямую
- [ ] Все задачи идемпотентны (повторный запуск не ломает данные)
- [ ] process_excel_import пишет прогресс в Redis: "import:{task_id}" JSON {status, processed, errors}
- [ ] check_expiring_subscriptions: отправляет письма только тем кто НЕ получал напоминание за этот период
- [ ] Cron: используй taskiq-cron или APScheduler
```

**Самопроверка после выполнения:**
```
Проверь TaskIQ: @backend/app/tasks/ @backend/app/main.py

- [ ] Запусти worker: taskiq worker app.tasks:broker
- [ ] Убедись что worker стартует без ошибок
- [ ] Отправь тестовую задачу: await send_verification_email.kiq(user_id="test", token="test")
- [ ] Проверь что задача выполнилась в логах worker-а
- [ ] ruff check backend/app/tasks/
```

---

## Этап 13 — Деплой: Docker + Nginx + SSL

```
Настрой деплой проекта.

Контекст: @docs/rules/DEPLOY_RULES.md @backend/ @docs/tech_requirements/04_Backend_API.md

Создай файлы в корне проекта:

1. backend/Dockerfile (multi-stage):
   - Stage 1 (builder): python:3.11-slim, pip install --no-cache
   - Stage 2 (runtime): python:3.11-slim, копировать только venv и код
   - CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000

2. docker-compose.yml (dev):
   - services: backend (--reload, порт 8000), postgres:16-alpine, redis:7-alpine, minio
   - Volumes: postgres_data, redis_data, minio_data
   - env_file: .env
   - healthcheck на postgres и redis
   - backend depends_on postgres (condition: service_healthy)

3. docker-compose.prod.yml (prod):
   - services: backend (gunicorn с uvicorn workers), postgres, redis, nginx, certbot
   - Без minio (внешний S3)
   - Порты postgres и redis НЕ открыты наружу
   - backend: restart: unless-stopped

4. nginx/nginx.conf — базовый конфиг
   nginx/conf.d/api.conf — api.triho.ru → backend:8000
   nginx/conf.d/admin.conf — admin.triho.ru → статика Next.js

5. scripts/init-ssl.sh — Let's Encrypt через certbot
6. scripts/deploy.sh — zero-downtime деплой (pull → build → migrate → restart)
7. scripts/backup.sh — pg_dump, S3 upload, 30-day rotation
8. Makefile — команды: dev, prod, migrate, backup, ssl, logs

9. env.dev — шаблон переменных для разработки
   env.prod.example — шаблон для продакшена (без реальных секретов)

Чек-лист:
- [ ] docker compose up -d (dev) запускается без ошибок
- [ ] backend healthcheck: GET /api/v1/health → {"status": "ok", "db": true, "redis": true}
- [ ] alembic upgrade head запускается как часть deploy.sh (до рестарта контейнера)
- [ ] Nginx: X-Real-IP передаётся в backend (нужно для IP whitelist YooKassa)
- [ ] certbot: автообновление через cron каждые 12 часов
- [ ] Makefile: make dev, make migrate, make logs работают
```

**Самопроверка после выполнения:**
```
Проверь деплой: @docker-compose.yml @backend/Dockerfile @nginx/

- [ ] docker compose build — без ошибок
- [ ] docker compose up -d — все контейнеры healthy
- [ ] curl http://localhost:8000/api/v1/health → {"status": "ok", "db": true, "redis": true}
- [ ] docker compose down && docker compose up -d — данные сохранились (volumes)
- [ ] make migrate — выполняет alembic upgrade head внутри контейнера
```

---

## Этап 14 — Тесты: конфиг, fixtures, unit и integration

```
Реализуй тестовое покрытие бекенда.

Контекст: @docs/rules/BACKEND_RULES.md @backend/app/ @backend/tests/

Стек: pytest + pytest-asyncio + httpx.AsyncClient + factory-boy

1. tests/conftest.py — глобальные фикстуры:
   - engine_test: create_async_engine на тестовой БД (или SQLite для unit)
   - db_session: транзакция которая откатывается после теста
   - client: AsyncClient с app (httpx)
   - auth_headers_doctor: JWT токен с ролью doctor
   - auth_headers_admin: JWT токен с ролью admin
   - auth_headers_accountant: JWT токен с ролью accountant

2. tests/factories.py — factory-boy:
   - UserFactory, DoctorProfileFactory, PlanFactory, SubscriptionFactory, PaymentFactory, EventFactory, ArticleFactory

3. tests/test_auth.py:
   - test_register_success
   - test_register_duplicate_email → 409
   - test_login_success → access_token + refresh cookie
   - test_login_wrong_password → 401
   - test_refresh_token → новая пара токенов
   - test_logout → cookie удалена

4. tests/test_public.py:
   - test_doctors_list_only_active → не возвращает approved/deactivated
   - test_doctors_filter_by_city
   - test_event_register_501
   - test_cities_with_doctors

5. tests/test_admin_doctors.py:
   - test_admin_list_requires_auth → 401
   - test_admin_list_accountant_forbidden → 403
   - test_moderate_approve → doctor_status=approved, moderation_history запись
   - test_moderate_reject_no_comment → 422
   - test_approve_draft → изменения применяются к профилю

6. tests/test_payments.py:
   - test_pay_idempotency → второй запрос с тем же ключом возвращает кэш
   - test_webhook_payment_succeeded → payment+subscription+doctor все обновляются
   - test_webhook_ip_not_whitelisted → 403
   - test_webhook_already_succeeded → идемпотентность (200, без повторной обработки)

7. tests/test_subscriptions.py:
   - test_pay_entry_fee_no_subscription
   - test_pay_subscription_within_90_days → product_type=subscription
   - test_pay_entry_fee_over_90_days → product_type=entry_fee

Чек-лист:
- [ ] Все тесты изолированы (rollback в teardown)
- [ ] Нет реальных HTTP-запросов к YooKassa (mock httpx)
- [ ] pytest --asyncio-mode=auto в pyproject.toml
- [ ] Минимум 40 тестов, покрытие критических путей
- [ ] pytest -x — все тесты зелёные
```

**Самопроверка после выполнения:**
```
Запусти тесты: @backend/tests/

- [ ] pytest backend/tests/ -v — все тесты проходят
- [ ] pytest backend/tests/ --tb=short — нет FAILED
- [ ] pytest backend/tests/test_payments.py -v — все 4 payment теста зелёные
- [ ] pytest --co backend/tests/ | wc -l — минимум 40 тестов собрано
```

---

## Финальная проверка всего бекенда

```
Выполни финальный аудит бекенда перед деплоем.

Контекст: @docs/rules/BACKEND_RULES.md @docs/tech_requirements/04_Backend_API.md @backend/app/ @backend/tests/

Задача — пройди по каждому пункту и исправь найденные проблемы:

1. Статус-коды и методы:
   - Найди все PUT-запросы: grep -r "\.put\|router\.put\|method.*PUT" backend/app/api/ — должно быть 0 результатов
   - Проверь что все создания возвращают 201
   - Проверь что все DELETE возвращают 204

2. Enum-значения (критично!):
   - grep -r "completed" backend/app/ — не должно быть payment_status='completed'
   - grep -r '"pending"' backend/app/models/ — doctor_status должен быть 'pending_review'
   - grep -r "draft\|published\|completed" backend/app/api/ — не должно быть в event_status

3. Пагинация:
   - grep -r "page\|page_size\|items" backend/app/schemas/ — не должно быть устаревших полей
   - Все list-ответы: { data, total, limit, offset }

4. Безопасность:
   - grep -r "password" backend/app/schemas/ — password НЕ должен быть в Response-схемах
   - Все admin-эндпоинты имеют require_role

5. Рантайм проверка:
   - docker compose up -d
   - pytest backend/tests/ -x
   - curl http://localhost:8000/api/v1/health
   - ruff check backend/app/ — 0 ошибок
   - mypy backend/app/ — 0 ошибок (или только known issues)

6. Swagger документация:
   - Открой http://localhost:8000/docs
   - Убедись что все 14 роутеров видны
   - Проверь что схемы ответов корректны для /api/v1/admin/doctors

Чек-лист финальный:
- [ ] 0 PUT-запросов в API
- [ ] payment_status: 'succeeded' везде
- [ ] doctor_status: 'pending_review' везде
- [ ] event_status: upcoming/ongoing/finished/cancelled везде
- [ ] Все list-ответы: { data, total, limit, offset }
- [ ] pytest -x — зелёный
- [ ] ruff check — 0 ошибок
- [ ] /api/v1/health → 200
```

---

## Быстрый справочник

| Этап | Файлы | Зависит от |
|------|-------|-----------|
| 0 | scaffold, requirements.txt | — |
| 1 | models/base.py (миксины, enums) | 0 |
| 2 | models/*.py (все таблицы) | 1 |
| 3 | alembic/versions/ (миграция) | 2 |
| 4 | core/ (config, db, security, exceptions, pagination) | 0 |
| 5 | schemas/auth.py, services/auth_service.py, api/v1/auth.py | 3, 4 |
| 6 | onboarding, profile, file_service | 5 |
| 7 | doctor_admin (модерация) | 6 |
| 8 | subscriptions, payments, YooKassa webhook | 7 |
| 9 | public API (города, каталог, события, статьи) | 3, 4 |
| 10 | admin events, content, settings | 7 |
| 11 | notifications, certificates, telegram, voting, dashboard | 8, 10 |
| 12 | TaskIQ tasks (фоновые задачи) | 11 |
| 13 | Docker, Nginx, deploy scripts | 12 |
| 14 | Tests | все этапы |
