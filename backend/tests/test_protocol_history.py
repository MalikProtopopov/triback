"""Protocol history admin API: CRUD, filters, audit, RBAC."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile
from app.models.users import User


@pytest.fixture
async def doctor_with_profile(
    db_session: AsyncSession, doctor_user: User
) -> DoctorProfile:
    profile = DoctorProfile(
        user_id=doctor_user.id,
        first_name="Test",
        last_name="Doctor",
        phone="+79001234567",
        slug=f"test-ph-{uuid4().hex[:8]}",
        status="active",
        has_medical_diploma=True,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest.mark.anyio
async def test_protocol_history_create_list_patch_delete(
    client: AsyncClient,
    doctor_user: User,
    doctor_with_profile: DoctorProfile,
    admin_user: User,
    auth_headers_admin: dict[str, str],
):
    r = await client.post(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_admin,
        json={
            "year": 2025,
            "protocol_title": "Протокол №1",
            "notes": "заметка",
            "doctor_user_id": str(doctor_user.id),
            "action_type": "admission",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["last_edited_by_user_id"] is None
    assert body["created_by_user_id"] == str(admin_user.id)
    assert body["doctor"]["email"] == doctor_user.email
    entry_id = body["id"]

    r_list = await client.get(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_admin,
    )
    assert r_list.status_code == 200
    assert r_list.json()["total"] == 1

    r_f = await client.get(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_admin,
        params={"doctor_user_id": str(doctor_user.id)},
    )
    assert r_f.json()["total"] == 1

    r_ex = await client.get(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_admin,
        params={"action_type": "exclusion"},
    )
    assert r_ex.json()["total"] == 0

    r_patch = await client.patch(
        f"/api/v1/admin/protocol-history/{entry_id}",
        headers=auth_headers_admin,
        json={"notes": "обновлено"},
    )
    assert r_patch.status_code == 200
    patched = r_patch.json()
    assert patched["last_edited_by_user_id"] == str(admin_user.id)
    assert patched["notes"] == "обновлено"

    r_del = await client.delete(
        f"/api/v1/admin/protocol-history/{entry_id}",
        headers=auth_headers_admin,
    )
    assert r_del.status_code == 204

    r_gone = await client.get(
        f"/api/v1/admin/protocol-history/{entry_id}",
        headers=auth_headers_admin,
    )
    assert r_gone.status_code == 404


@pytest.mark.anyio
async def test_protocol_history_accountant_crud(
    client: AsyncClient,
    doctor_user: User,
    doctor_with_profile: DoctorProfile,
    accountant_user: User,
    auth_headers_accountant: dict[str, str],
):
    r = await client.get(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_accountant,
    )
    assert r.status_code == 200

    r = await client.post(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_accountant,
        json={
            "year": 2025,
            "protocol_title": "Бухгалтер",
            "doctor_user_id": str(doctor_user.id),
            "action_type": "admission",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created_by_user_id"] == str(accountant_user.id)
    entry_id = body["id"]

    r_patch = await client.patch(
        f"/api/v1/admin/protocol-history/{entry_id}",
        headers=auth_headers_accountant,
        json={"notes": "acct"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["last_edited_by_user_id"] == str(accountant_user.id)

    r_del = await client.delete(
        f"/api/v1/admin/protocol-history/{entry_id}",
        headers=auth_headers_accountant,
    )
    assert r_del.status_code == 204


@pytest.mark.anyio
async def test_protocol_history_non_doctor_doctor_id_422(
    client: AsyncClient,
    admin_user: User,
    auth_headers_admin: dict[str, str],
):
    r = await client.post(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_admin,
        json={
            "year": 2025,
            "protocol_title": "X",
            "doctor_user_id": str(admin_user.id),
            "action_type": "admission",
        },
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_manager_can_create_protocol_history(
    client: AsyncClient,
    doctor_user: User,
    doctor_with_profile: DoctorProfile,
    manager_user: User,
    auth_headers_manager: dict[str, str],
):
    r = await client.post(
        "/api/v1/admin/protocol-history",
        headers=auth_headers_manager,
        json={
            "year": 2024,
            "protocol_title": "M",
            "doctor_user_id": str(doctor_user.id),
            "action_type": "exclusion",
        },
    )
    assert r.status_code == 201
    assert r.json()["created_by_user_id"] == str(manager_user.id)
