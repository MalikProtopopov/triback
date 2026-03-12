# Backend Rules — AI Coding Guide

> Этот файл используется как контекст/rules при работе с AI-ассистентом (Cursor, Claude).
> Подключай его к проекту чтобы AI следовал единым стандартам бэкенда.

---

## Стек

| Категория | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| Фреймворк | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| БД | PostgreSQL 16 |
| Кэш | Redis 7 |
| Миграции | Alembic |
| Auth | JWT (access + refresh), bcrypt |
| Валидация | Pydantic v2 |
| Логирование | structlog (JSON) |
| Линтинг | ruff, mypy |

---

## Архитектура: модульная структура

Каждый модуль — изолированная бизнес-область:

```
backend/app/modules/{module_name}/
  models.py      # SQLAlchemy модели
  schemas.py     # Pydantic схемы (Create/Update/Response)
  service.py     # Бизнес-логика (классы сервисов)
  router.py      # FastAPI эндпоинты
  dependencies.py  # (опционально) DI зависимости модуля
```

### Правила

- **Бизнес-логика** — только в `service.py`, НЕ в роутах
- **Роуты** — тонкие, только валидация входа → вызов сервиса → возврат ответа
- **Модели** — описание таблиц, связи, constraints
- **Схемы** — контракт API (что принимаем, что отдаём)

```python
# router.py — тонкий роутер
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: AdminUser = Depends(get_current_user),
):
    service = UserService(db)
    return await service.create(data, created_by=current_user.id)
```

---

## База данных

### Миксины (наследуй от них все модели)

```python
class UUIDMixin:
    """UUID v4 как первичный ключ"""
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

class TimestampMixin:
    """created_at / updated_at автоматические"""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SoftDeleteMixin:
    """Мягкое удаление вместо DELETE"""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class VersionMixin:
    """Optimistic locking"""
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

### Правила моделей

- UUID v4 для всех PK
- `server_default` для default-значений (не Python-level)
- `CheckConstraint` для enum-like полей:

```python
__table_args__ = (
    CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_posts_status"),
    Index("ix_posts_tenant_status", "tenant_id", "status"),
)
```

- Индексы на поля фильтрации и сортировки
- `ForeignKey(..., ondelete="CASCADE")` или `SET NULL` — указывать всегда
- `comment=` на полях для документирования

---

## Миграции (Alembic)

```bash
# Создать миграцию
alembic revision --autogenerate -m "add_users_table"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```

### Правила миграций

- Имена файлов: `NNN_description.py` (NNN — порядковый номер)
- Всегда проверять сгенерированный код (autogenerate не ловит всё)
- `downgrade()` обязателен и должен работать
- Данные: `INSERT` / `UPDATE` в миграциях, если нужна инициализация

---

## Pydantic-схемы

### Паттерн: Create / Update / Response

```python
# schemas.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    """Что принимаем при создании"""
    email: str
    first_name: str
    role: str = "editor"


class UserUpdate(BaseModel):
    """Что принимаем при обновлении (все поля Optional)"""
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None


class UserResponse(BaseModel):
    """Что отдаём клиенту"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    first_name: str
    last_name: str | None
    role: str
    is_active: bool
    created_at: datetime
```

### Правила

- `from_attributes=True` в Response-схемах (маппинг из ORM)
- Чувствительные данные (password, tokens) НИКОГДА не в Response
- Валидация через `@field_validator` или `@model_validator`
- Документирование полей: `Field(..., description="...")`

---

## API-дизайн

### URL-структура

```
/api/v1/{resource}          — CRUD коллекции
/api/v1/{resource}/{id}     — CRUD элемента
/api/v1/public/...          — Публичные эндпоинты (без auth)
/api/v1/auth/...            — Аутентификация
```

### HTTP-методы

| Метод | Использование | Код |
|-------|--------------|-----|
| GET | Получение | 200 |
| POST | Создание | 201 |
| PATCH | Частичное обновление | 200 |
| DELETE | Удаление | 204 |

### Пагинация

```python
# Стандартные параметры
class PaginationParams:
    page: int = Query(1, ge=1)
    page_size: int = Query(20, ge=1, le=100)

# Стандартный ответ
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int  # total / page_size
```

### Ошибки (RFC 7807)

```python
# Все ошибки в формате RFC 7807
{
    "type": "https://api.example.com/errors/not_found",
    "title": "Not Found",
    "status": 404,
    "detail": "User with id '...' not found",
    "instance": "/api/v1/users/..."
}
```

---

## Аутентификация и авторизация

### JWT

- **Access token**: короткий TTL (15-30 мин)
- **Refresh token**: длинный TTL (7-30 дней), хранится в БД
- `tenant_id` в payload — определяет контекст тенанта
- Ротация refresh-токенов при каждом обновлении

### RBAC

```python
# Роли
ROLES = ["platform_owner", "admin", "editor", "viewer"]

# Проверка в роутах
@router.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: UUID, ...):
    ...
```

---

## Dependency Injection (FastAPI Depends)

```python
# Стандартные зависимости
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД"""

async def get_current_user(token: str = Depends(oauth2_scheme)) -> AdminUser:
    """Текущий пользователь из JWT"""

async def get_current_tenant_id(request: Request) -> UUID:
    """Tenant ID из заголовка X-Tenant-ID или из JWT"""

def get_pagination(page: int = 1, page_size: int = 20) -> PaginationParams:
    """Параметры пагинации"""
```

---

## Транзакции

```python
# Декоратор для автоматического commit/rollback
@transactional
async def create_order(self, data: OrderCreate) -> Order:
    order = Order(**data.model_dump())
    self.db.add(order)
    await self.db.flush()  # Получить ID до commit
    # Если исключение — автоматический rollback
    return order
```

---

## Логирование (structlog)

```python
import structlog

logger = structlog.get_logger()

# Структурированные логи
logger.info("user_created", user_id=str(user.id), email=user.email, tenant_id=str(tenant_id))
logger.error("email_send_failed", error=str(e), provider="smtp", tenant_id=str(tenant_id))
```

Формат: JSON для машинного парсинга. Каждый лог — событие с контекстом.

---

## Код-стайл

| Правило | Значение |
|---------|---------|
| Type hints | Обязательны на всех функциях |
| Длина строки | 100 символов |
| Docstrings | Google-стиль |
| Линтер | ruff (format + lint) |
| Типы | mypy (strict) |
| Именование | snake_case для всего, PascalCase для классов |

```python
async def get_user_by_email(
    db: AsyncSession,
    email: str,
    *,
    include_deleted: bool = False,
) -> User | None:
    """Получить пользователя по email.

    Args:
        db: Сессия базы данных.
        email: Email пользователя.
        include_deleted: Включать мягко удалённые записи.

    Returns:
        Пользователь или None если не найден.
    """
    query = select(User).where(User.email == email)
    if not include_deleted:
        query = query.where(User.is_deleted == False)
    result = await db.execute(query)
    return result.scalar_one_or_none()
```

---

## Тестирование

```python
# Стек: pytest + pytest-asyncio + httpx + factory-boy
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "first_name": "Test"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

### Правила тестов

- Каждый тест — изолированный (fixture-based setup/teardown)
- Factory-boy для создания тестовых данных
- Отдельные фикстуры: `db_session`, `client`, `auth_headers`, `sample_user`
- Unit-тесты для сервисов, integration-тесты для API

---

## Чек-лист для AI

При создании нового модуля убедись что:

- [ ] Структура: `models.py`, `schemas.py`, `service.py`, `router.py`
- [ ] Модель наследует миксины (UUID, Timestamp, SoftDelete)
- [ ] Схемы: Create + Update + Response
- [ ] Сервис содержит бизнес-логику, роутер — тонкий
- [ ] Пагинация для list-эндпоинтов
- [ ] Ошибки в формате RFC 7807
- [ ] Type hints на всех функциях
- [ ] Миграция Alembic создана
- [ ] structlog для логирования
- [ ] Роутер зарегистрирован в главном `app`
