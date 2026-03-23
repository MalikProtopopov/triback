"""Auth endpoint tests — register, login, refresh, logout, verify-email."""

from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TEST_PASSWORD

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
VERIFY_EMAIL_URL = "/api/v1/auth/verify-email"


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


async def test_logout_all_revokes_all_refresh_tokens(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_user

    await create_user(db_session, email="logout_all@test.com")
    await db_session.commit()

    login_resp = await client.post(
        LOGIN_URL,
        json={"email": "logout_all@test.com", "password": TEST_PASSWORD},
    )
    assert login_resp.status_code == 200
    access = login_resp.json()["access_token"]
    token_value = ""
    for part in login_resp.headers.get("set-cookie", "").split(";"):
        part = part.strip()
        if part.startswith("refresh_token="):
            token_value = part.split("=", 1)[1]
            break
    assert token_value

    lo = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert lo.status_code == 200

    refresh_resp = await client.post(
        REFRESH_URL,
        cookies={"refresh_token": token_value},
    )
    assert refresh_resp.status_code == 401


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


async def test_verify_email_updates_onboarding_status(
    client: AsyncClient,
    db_session: AsyncSession,
    redis_mock: AsyncMock,
):
    """Verify that POST /verify-email sets email_verified_at and GET /onboarding/status returns email_verified: true."""
    from tests.factories import assign_role, create_role, create_user

    user = await create_user(
        db_session,
        email="verify_test@test.com",
        email_verified_at=None,
    )
    role = await create_role(db_session, name="user")
    await assign_role(db_session, user, role)
    await db_session.commit()

    # Simulate token stored by resend (or registration)
    verify_token = "test-verify-token-123"
    await redis_mock.set(f"email_verify:{verify_token}", str(user.id))

    # POST verify-email (no auth required)
    verify_resp = await client.post(
        VERIFY_EMAIL_URL,
        json={"token": verify_token},
    )
    assert verify_resp.status_code == 200

    # Login and check onboarding status
    login_resp = await client.post(
        LOGIN_URL,
        json={"email": "verify_test@test.com", "password": TEST_PASSWORD},
    )
    assert login_resp.status_code == 200
    access_token = login_resp.json()["access_token"]

    status_resp = await client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["email_verified"] is True
    assert data["next_step"] != "verify_email"
