"""GET /profile/event-registrations and admin portal-users/{id}/event-registrations."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscriptions import Payment
from app.models.users import User
from tests.conftest import _make_auth_headers


async def test_profile_event_registrations_includes_tariff_and_null_payment(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email=f"evt_owner_{uuid4().hex[:8]}@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(
        db_session, event=event, price=3000.0, member_price=1500.0
    )
    await create_event_registration(
        db_session,
        user=doctor_user,
        event=event,
        tariff=tariff,
        status="pending",
        applied_price=3000.0,
        is_member_price=False,
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/profile/event-registrations",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    row = data["data"][0]
    assert row["registration"]["status"] == "pending"
    assert row["event"]["slug"] == event.slug
    assert row["tariff"]["applied_price"] == 3000.0
    assert row["tariff"]["member_price"] == 1500.0
    assert row["payment"] is None


async def test_profile_event_registrations_with_payment(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email=f"evt_own2_{uuid4().hex[:8]}@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    reg = await create_event_registration(
        db_session,
        user=doctor_user,
        event=event,
        tariff=tariff,
        status="confirmed",
    )
    pay = Payment(
        user_id=doctor_user.id,
        amount=reg.applied_price,
        product_type="event",
        status="succeeded",
        event_registration_id=reg.id,
        external_payment_id="ext-123",
    )
    db_session.add(pay)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/profile/event-registrations",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()
    match = next(
        (x for x in data["data"] if x["registration"]["id"] == str(reg.id)),
        None,
    )
    assert match is not None
    assert match["payment"] is not None
    assert match["payment"]["status"] == "succeeded"
    assert match["payment"]["external_payment_id"] == "ext-123"


async def test_profile_event_registrations_filter_status(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email=f"evt_f_{uuid4().hex[:8]}@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    await create_event_registration(
        db_session,
        user=doctor_user,
        event=event,
        tariff=tariff,
        status="cancelled",
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/profile/event-registrations",
        headers=auth_headers_doctor,
        params={"status": "confirmed"},
    )
    assert resp.status_code == 200
    ids_cancel = [
        x["registration"]["id"]
        for x in resp.json()["data"]
        if x["registration"]["status"] == "cancelled"
    ]
    assert not ids_cancel


async def test_admin_portal_user_event_registrations(
    client: AsyncClient,
    doctor_user: User,
    admin_user: User,
    db_session: AsyncSession,
):
    from tests.factories import (
        create_event,
        create_event_registration,
        create_event_tariff,
        create_user,
    )

    admin = await create_user(db_session, email=f"evt_adm_{uuid4().hex[:8]}@test.com")
    event = await create_event(db_session, created_by=admin)
    tariff = await create_event_tariff(db_session, event=event)
    await create_event_registration(
        db_session,
        user=doctor_user,
        event=event,
        tariff=tariff,
        status="confirmed",
    )
    await db_session.commit()

    headers = _make_auth_headers(admin_user.id, "admin")
    resp = await client.get(
        f"/api/v1/admin/portal-users/{doctor_user.id}/event-registrations",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_admin_event_registrations_404_unknown_user(
    client: AsyncClient,
    admin_user: User,
):
    headers = _make_auth_headers(admin_user.id, "admin")
    fake_id = uuid4()
    resp = await client.get(
        f"/api/v1/admin/portal-users/{fake_id}/event-registrations",
        headers=headers,
    )
    assert resp.status_code == 404
