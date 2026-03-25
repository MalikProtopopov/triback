"""Pytest configuration and shared fixtures.

Uses a real PostgreSQL test database (triho_db_test) with per-test
transaction rollback for isolation.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.base import Base
from app.models.users import Role, User, UserRoleAssignment
from app.tasks import broker as taskiq_broker

TEST_DB_URL = str(settings.DATABASE_URL).rsplit("/", 1)[0] + "/triho_db_test"

# Same set as scripts/create_admin.py — app code expects these rows (e.g. create_doctor).
_TEST_ROLES_SEED: list[tuple[str, str]] = [
    ("admin", "Администратор"),
    ("manager", "Менеджер"),
    ("accountant", "Бухгалтер"),
    ("doctor", "Врач"),
    ("user", "Пользователь"),
]


# ── One-time schema setup (runs outside the test event loop) ──────

def pytest_configure(config: pytest.Config) -> None:
    async def _create() -> None:
        eng = create_async_engine(TEST_DB_URL, echo=False)
        async with eng.begin() as conn:
            # Orphan tables from pre–free-text specialization schema are not in metadata;
            # remove them so drop_all can recreate doctor_profiles cleanly.
            await conn.execute(text("DROP TABLE IF EXISTS doctor_specializations CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS specializations CASCADE"))
            await conn.execute(
                text("""
                DO $$ BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'doctor_profiles'
                  ) THEN
                    ALTER TABLE doctor_profiles
                      DROP CONSTRAINT IF EXISTS doctor_profiles_specialization_id_fkey;
                    ALTER TABLE doctor_profiles DROP COLUMN IF EXISTS specialization_id;
                  END IF;
                END $$;
                """)
            )
            # Breaks circular FK: payments.arrear_id ↔ membership_arrears.payment_id
            await conn.execute(text("DROP TABLE IF EXISTS membership_arrears CASCADE"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await eng.dispose()

    async def _seed_roles() -> None:
        """Committed baseline roles so per-test transactions see them (create_doctor, etc.)."""
        eng = create_async_engine(TEST_DB_URL, echo=False)
        factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            for name, title in _TEST_ROLES_SEED:
                existing = (
                    await session.execute(select(Role).where(Role.name == name))
                ).scalar_one_or_none()
                if existing is None:
                    session.add(Role(name=name, title=title))
            await session.commit()
        await eng.dispose()

    asyncio.run(_create())
    asyncio.run(_seed_roles())


# ── Disable TaskIQ broker in tests (no-op kiq) ───────────────────

@pytest.fixture(autouse=True)
def _mock_taskiq_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop_kick(message) -> None:  # noqa: ANN001
        pass

    monkeypatch.setattr(taskiq_broker, "kick", _noop_kick)


# ── Per-test transactional session ────────────────────────────────

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    conn = await engine.connect()
    txn = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await txn.rollback()
        await conn.close()
        await engine.dispose()


@pytest.fixture(name="async_session")
async def async_session_alias(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, None]:
    """Alias for ``db_session`` (per-test rollback semantics)."""
    yield db_session


# ── Redis mock ────────────────────────────────────────────────────

@pytest.fixture
def redis_mock() -> AsyncMock:
    r = AsyncMock()
    _store: dict[str, str] = {}

    async def _get(key: str) -> str | None:
        return _store.get(key)

    async def _set(key: str, value: str, **kwargs) -> bool | None:  # noqa: ANN003
        if kwargs.get("nx") and key in _store:
            return None
        _store[key] = value
        return True

    async def _delete(*keys: str) -> None:
        for k in keys:
            _store.pop(k, None)

    async def _incr(key: str) -> int:
        val = int(_store.get(key, "0")) + 1
        _store[key] = str(val)
        return val

    async def _expire(key: str, ttl: int) -> None:
        pass

    async def _scan_iter(match: str = "*"):  # noqa: ANN001
        import fnmatch

        for k in list(_store.keys()):
            if fnmatch.fnmatch(k, match):
                yield k

    r.get = AsyncMock(side_effect=_get)
    r.set = AsyncMock(side_effect=_set)
    r.delete = AsyncMock(side_effect=_delete)
    r.incr = AsyncMock(side_effect=_incr)
    r.expire = AsyncMock(side_effect=_expire)
    r.ping = AsyncMock(return_value=True)
    r.scan_iter = _scan_iter
    return r


# ── httpx AsyncClient with dependency overrides ──────────────────

@pytest.fixture
async def client(
    db_session: AsyncSession, redis_mock: AsyncMock
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.database import get_db_session
    from app.core.redis import get_redis
    from app.main import app

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_redis] = lambda: redis_mock

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ── Helper: create user with role ─────────────────────────────────

TEST_PASSWORD = "TestPass123!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


async def _create_user_with_role(
    db: AsyncSession, email: str, role_name: str
) -> User:
    user = User(
        email=email,
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    role = (
        await db.execute(select(Role).where(Role.name == role_name))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name=role_name, title=role_name.capitalize())
        db.add(role)
        await db.flush()

    assignment = UserRoleAssignment(user_id=user.id, role_id=role.id)
    db.add(assignment)
    await db.flush()
    return user


def _make_auth_headers(user_id, role: str) -> dict[str, str]:
    token = create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


# ── Auth header fixtures ──────────────────────────────────────────

@pytest.fixture
async def doctor_user(db_session: AsyncSession) -> User:
    return await _create_user_with_role(
        db_session, f"doctor_{uuid4().hex[:8]}@test.com", "doctor"
    )


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await _create_user_with_role(
        db_session, f"admin_{uuid4().hex[:8]}@test.com", "admin"
    )


@pytest.fixture
async def accountant_user(db_session: AsyncSession) -> User:
    return await _create_user_with_role(
        db_session, f"acct_{uuid4().hex[:8]}@test.com", "accountant"
    )


@pytest.fixture
def auth_headers_doctor(doctor_user: User) -> dict[str, str]:
    return _make_auth_headers(doctor_user.id, "doctor")


@pytest.fixture
def auth_headers_admin(admin_user: User) -> dict[str, str]:
    return _make_auth_headers(admin_user.id, "admin")


@pytest.fixture
def auth_headers_accountant(accountant_user: User) -> dict[str, str]:
    return _make_auth_headers(accountant_user.id, "accountant")


@pytest.fixture
def user_factory(db_session: AsyncSession):
    """Create a user with any seeded role (``admin``, ``doctor``, ``user``, …)."""

    async def _make(*, role: str = "user", email: str | None = None) -> User:
        return await _create_user_with_role(
            db_session, email or f"u_{uuid4().hex[:8]}@test.com", role
        )

    return _make
