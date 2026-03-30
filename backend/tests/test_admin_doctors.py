"""Admin doctor management tests."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _make_auth_headers

ADMIN_DOCTORS_URL = "/api/v1/admin/doctors"


# ── Create doctor tests ──────────────────────────────────────────


async def test_create_doctor_success(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    resp = await client.post(
        ADMIN_DOCTORS_URL,
        headers=auth_headers_admin,
        json={
            "email": "new_doctor@test.com",
            "first_name": "Иван",
            "last_name": "Петров",
            "phone": "+79001234567",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new_doctor@test.com"
    assert data["first_name"] == "Иван"
    assert data["last_name"] == "Петров"
    assert data["status"] == "approved"
    assert data["profile_id"] is not None
    assert data["user_id"] is not None
    assert data["temp_password"] is None


async def test_create_doctor_no_invite_returns_password(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    resp = await client.post(
        ADMIN_DOCTORS_URL,
        headers=auth_headers_admin,
        json={
            "email": "noinvite@test.com",
            "first_name": "Анна",
            "last_name": "Сидорова",
            "phone": "+79005555555",
            "send_invite": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["temp_password"] is not None
    assert len(data["temp_password"]) >= 8


async def test_create_doctor_full_fields(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    resp = await client.post(
        ADMIN_DOCTORS_URL,
        headers=auth_headers_admin,
        json={
            "email": "full_doctor@test.com",
            "first_name": "Мария",
            "last_name": "Козлова",
            "phone": "+79009876543",
            "middle_name": "Андреевна",
            "clinic_name": "Клиника Здоровья",
            "position": "Трихолог",
            "academic_degree": "к.м.н.",
            "bio": "Опытный трихолог",
            "public_email": "maria@clinic.com",
            "public_phone": "+79009876544",
            "specialization": "Трихолог",
            "status": "pending_review",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_review"
    assert data["first_name"] == "Мария"

    detail = await client.get(
        f"{ADMIN_DOCTORS_URL}/{data['profile_id']}",
        headers=auth_headers_admin,
    )
    assert detail.status_code == 200
    assert detail.json().get("specialization") == "Трихолог"


async def test_create_doctor_duplicate_email(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_user

    await create_user(db_session, email="duplicate@test.com")
    await db_session.commit()

    resp = await client.post(
        ADMIN_DOCTORS_URL,
        headers=auth_headers_admin,
        json={
            "email": "duplicate@test.com",
            "first_name": "Тест",
            "last_name": "Дубль",
            "phone": "+79001111111",
        },
    )
    assert resp.status_code == 409


async def test_create_doctor_forbidden_for_manager(
    client: AsyncClient,
    db_session: AsyncSession,
):
    from tests.factories import assign_role, create_role, create_user

    user = await create_user(db_session, email="mgr@test.com")
    role = await create_role(db_session, name="manager")
    await assign_role(db_session, user, role)
    await db_session.flush()

    headers = _make_auth_headers(user.id, "manager")
    resp = await client.post(
        ADMIN_DOCTORS_URL,
        headers=headers,
        json={
            "email": "blocked@test.com",
            "first_name": "Блок",
            "last_name": "Тест",
            "phone": "+79002222222",
        },
    )
    assert resp.status_code == 403


async def test_create_doctor_unauthorized(client: AsyncClient):
    resp = await client.post(
        ADMIN_DOCTORS_URL,
        json={
            "email": "noauth@test.com",
            "first_name": "А",
            "last_name": "Б",
            "phone": "+79003333333",
        },
    )
    assert resp.status_code == 401


# ── List doctors tests ────────────────────────────────────────────


async def test_admin_list_requires_auth(client: AsyncClient):
    resp = await client.get(ADMIN_DOCTORS_URL)
    assert resp.status_code == 401


async def test_admin_list_accountant_ok(
    client: AsyncClient, auth_headers_accountant: dict[str, str]
):
    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_accountant)
    assert resp.status_code == 200
    assert "data" in resp.json()


async def test_admin_list_success(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, status="pending_review")
    await db_session.commit()

    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


async def test_admin_list_has_photo_in_draft_false_without_draft(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    """Врач без черновика — has_photo_in_draft: false."""
    from tests.factories import create_doctor_profile

    await create_doctor_profile(db_session, status="active")
    await db_session.commit()

    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 1
    doctor = items[0]
    assert doctor["has_photo_in_draft"] is False


async def test_admin_list_has_photo_in_draft_false_draft_without_photo(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    """Врач с pending-черновиком без photo_url — has_photo_in_draft: false."""
    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, status="active")
    await create_profile_change(
        db_session, profile=profile, changes={"bio": "New bio text"}
    )
    await db_session.commit()

    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["data"]
    doctor = next(d for d in items if d["id"] == str(profile.id))
    assert doctor["has_pending_changes"] is True
    assert doctor["has_photo_in_draft"] is False


async def test_admin_list_has_photo_in_draft_true(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    """Врач с pending-черновиком с photo_url — has_photo_in_draft: true."""
    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, status="active")
    await create_profile_change(
        db_session,
        profile=profile,
        changes={"photo_url": "doctors/uuid/photo/new.jpg"},
    )
    await db_session.commit()

    resp = await client.get(ADMIN_DOCTORS_URL, headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["data"]
    doctor = next(d for d in items if d["id"] == str(profile.id))
    assert doctor["has_pending_changes"] is True
    assert doctor["has_photo_in_draft"] is True


async def test_moderate_approve(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(
        db_session, status="pending_review"
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["moderation_status"] == "approved"
    await db_session.refresh(profile)
    # ФИО из фабрики: LnameN FnameN → lname{n}-fname{n}
    assert profile.slug.startswith("lname")
    assert "fname" in profile.slug


async def test_moderate_approve_slug_from_cyrillic_fio(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(
        db_session,
        status="pending_review",
        first_name="Иван",
        last_name="Иванов",
        specialization="Трихолог",
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert resp.status_code == 200
    await db_session.refresh(profile)
    assert profile.slug == "ivanov-ivan"


async def test_moderate_second_same_fio_adds_specialization_to_slug(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    p1 = await create_doctor_profile(
        db_session,
        status="pending_review",
        first_name="Иван",
        last_name="Иванов",
        specialization="Трихолог",
    )
    p2 = await create_doctor_profile(
        db_session,
        status="pending_review",
        first_name="Иван",
        last_name="Иванов",
        specialization="Кардиолог",
    )
    await db_session.commit()

    r1 = await client.post(
        f"{ADMIN_DOCTORS_URL}/{p1.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert r1.status_code == 200
    r2 = await client.post(
        f"{ADMIN_DOCTORS_URL}/{p2.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert r2.status_code == 200

    await db_session.refresh(p1)
    await db_session.refresh(p2)
    assert p1.slug == "ivanov-ivan"
    assert p2.slug == "ivanov-ivan-kardiolog"


async def test_moderate_reject_no_comment(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(
        db_session, status="pending_review"
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/moderate",
        headers=auth_headers_admin,
        json={"action": "reject"},
    )
    assert resp.status_code == 422


async def test_approve_draft(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile, create_profile_change

    profile = await create_doctor_profile(db_session, status="active")
    await create_profile_change(
        db_session, profile=profile, changes={"bio": "New bio text"}
    )
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/approve-draft",
        headers=auth_headers_admin,
        json={"action": "approve"},
    )
    assert resp.status_code == 200


async def test_toggle_active(
    client: AsyncClient,
    auth_headers_admin: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_doctor_profile

    profile = await create_doctor_profile(db_session, status="approved")
    await db_session.commit()

    resp = await client.post(
        f"{ADMIN_DOCTORS_URL}/{profile.id}/toggle-active",
        headers=auth_headers_admin,
        json={"is_public": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_public"] is True
