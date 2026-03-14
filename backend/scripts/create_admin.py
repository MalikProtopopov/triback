#!/usr/bin/env python3
"""Create the first admin user in the database.

Use after initial deploy when there are no admin/manager/accountant users yet.
Ensures all 5 roles exist in the `roles` table, then creates a user with the
given email/password and assigns the role `admin`.

Usage (from project root):
  docker compose -f docker-compose.prod.yml exec backend \\
    python scripts/create_admin.py --email admin@example.com --password 'YourSecurePass123!'

Or with env vars (non-interactive):
  CREATE_ADMIN_EMAIL=admin@example.com CREATE_ADMIN_PASSWORD=secret \\
  docker compose exec backend python scripts/create_admin.py

If --password is omitted and CREATE_ADMIN_PASSWORD is not set, the script
will prompt for the password (getpass).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

# Ensure backend/app is importable when run as script from /app (Docker) or backend/ (local)
if __name__ == "__main__" and "__file__" in dir():
    _here = os.path.dirname(os.path.abspath(__file__))
    _backend = os.path.dirname(_here)
    if _backend not in sys.path:
        sys.path.insert(0, _backend)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.users import Role, User, UserRoleAssignment

# UUID v7 for User.id (same as UUIDMixin)
try:
    import uuid_utils
    def _new_user_id():
        return uuid_utils.uuid7()
except ImportError:
    import uuid
    def _new_user_id():
        return uuid.uuid4()


ROLES = [
    ("admin", "Администратор"),
    ("manager", "Менеджер"),
    ("accountant", "Бухгалтер"),
    ("doctor", "Врач"),
    ("user", "Пользователь"),
]


async def ensure_roles(session: AsyncSession) -> dict[str, Role]:
    """Create missing roles; return name -> Role mapping."""
    result: dict[str, Role] = {}
    for name, title in ROLES:
        r = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if r is None:
            r = Role(name=name, title=title)
            session.add(r)
            await session.flush()
        result[name] = r
    return result


async def create_admin(email: str, password: str) -> None:
    engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        roles_map = await ensure_roles(session)
        await session.commit()
        print(f"Roles OK ({len(roles_map)} roles in DB)")

    async with async_session() as session:
        admin_role = (
            await session.execute(select(Role).where(Role.name == "admin"))
        ).scalar_one()

        user = User(
            id=_new_user_id(),
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            print(f"Error: user with email {email!r} already exists.", file=sys.stderr)
            sys.exit(1)

        session.add(UserRoleAssignment(user_id=user.id, role_id=admin_role.id))
        await session.commit()
        print(f"Admin user created: {email} (id={user.id})")
        print("You can now log in at the admin panel with this email and password.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first admin user.")
    parser.add_argument("--email", default=os.environ.get("CREATE_ADMIN_EMAIL"), help="Admin email")
    parser.add_argument("--password", default=os.environ.get("CREATE_ADMIN_PASSWORD"), help="Admin password (or set CREATE_ADMIN_PASSWORD)")
    args = parser.parse_args()

    email = (args.email or "").strip()
    if not email:
        print("Error: provide --email or set CREATE_ADMIN_EMAIL.", file=sys.stderr)
        sys.exit(1)

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
    if not password or len(password) < 8:
        print("Error: password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(create_admin(email, password))


if __name__ == "__main__":
    main()
