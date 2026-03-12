"""Auth endpoint tests — register, login, refresh, logout."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_PASSWORD

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"


async def test_register_success(client: AsyncClient):
    resp = await client.post(
        REGISTER_URL,
        json={
            "email": "new_user@test.com",
            "password": "StrongPass1!",
            "re_password": "StrongPass1!",
        },
    )
    assert resp.status_code == 201
    assert "message" in resp.json()


async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup_user@test.com",
        "password": "StrongPass1!",
        "re_password": "StrongPass1!",
    }
    resp1 = await client.post(REGISTER_URL, json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post(REGISTER_URL, json=payload)
    assert resp2.status_code == 409


async def test_login_success(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_user

    await create_user(
        db_session,
        email="login_test@test.com",
        email_verified_at=None,
    )
    await db_session.commit()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "login_test@test.com", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_user

    await create_user(db_session, email="wrong_pwd@test.com")
    await db_session.commit()

    resp = await client.post(
        LOGIN_URL,
        json={"email": "wrong_pwd@test.com", "password": "WrongPassword1!"},
    )
    assert resp.status_code == 401


async def test_refresh_token(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_user

    await create_user(db_session, email="refresh_test@test.com")
    await db_session.commit()

    login_resp = await client.post(
        LOGIN_URL,
        json={"email": "refresh_test@test.com", "password": TEST_PASSWORD},
    )
    assert login_resp.status_code == 200

    raw_cookie = login_resp.headers.get("set-cookie", "")
    token_value = ""
    for part in raw_cookie.split(";"):
        part = part.strip()
        if part.startswith("refresh_token="):
            token_value = part.split("=", 1)[1]
            break

    refresh_resp = await client.post(
        REFRESH_URL,
        cookies={"refresh_token": token_value},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


async def test_logout(client: AsyncClient, db_session: AsyncSession):
    from tests.factories import create_user

    await create_user(db_session, email="logout_test@test.com")
    await db_session.commit()

    login_resp = await client.post(
        LOGIN_URL,
        json={"email": "logout_test@test.com", "password": TEST_PASSWORD},
    )
    raw_cookie = login_resp.headers.get("set-cookie", "")
    token_value = ""
    for part in raw_cookie.split(";"):
        part = part.strip()
        if part.startswith("refresh_token="):
            token_value = part.split("=", 1)[1]
            break

    logout_resp = await client.post(
        LOGOUT_URL,
        cookies={"refresh_token": token_value},
    )
    assert logout_resp.status_code == 200
    assert "message" in logout_resp.json()


async def test_register_password_mismatch(client: AsyncClient):
    resp = await client.post(
        REGISTER_URL,
        json={
            "email": f"mismatch_{uuid4().hex[:6]}@test.com",
            "password": "StrongPass1!",
            "re_password": "DifferentPass1!",
        },
    )
    assert resp.status_code == 422


async def test_register_short_password(client: AsyncClient):
    resp = await client.post(
        REGISTER_URL,
        json={
            "email": f"short_{uuid4().hex[:6]}@test.com",
            "password": "short",
            "re_password": "short",
        },
    )
    assert resp.status_code == 422
