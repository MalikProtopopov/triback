"""Tests for doctor payment list and receipt download."""


from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


async def test_list_my_payments(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_payment

    await create_payment(db_session, user=doctor_user, amount=3000.0, status="succeeded")
    await create_payment(db_session, user=doctor_user, amount=5000.0, status="pending")
    await db_session.commit()

    resp = await client.get("/api/v1/subscriptions/payments", headers=auth_headers_doctor)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2


async def test_list_my_payments_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/subscriptions/payments")
    assert resp.status_code == 401


async def test_get_receipt(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_payment, create_receipt

    payment = await create_payment(
        db_session, user=doctor_user, amount=5000.0, status="succeeded"
    )
    await create_receipt(db_session, payment=payment)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/subscriptions/payments/{payment.id}/receipt",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["receipt_url"] == "https://receipt.example.com/123"


async def test_get_receipt_not_found(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    doctor_user: User,
    db_session: AsyncSession,
):
    from tests.factories import create_payment

    payment = await create_payment(db_session, user=doctor_user, amount=5000.0, status="succeeded")
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/subscriptions/payments/{payment.id}/receipt",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 404


async def test_get_receipt_wrong_user(
    client: AsyncClient,
    auth_headers_doctor: dict[str, str],
    db_session: AsyncSession,
):
    from tests.factories import create_payment, create_receipt, create_user

    other_user = await create_user(db_session, email="other_pay@test.com")
    payment = await create_payment(db_session, user=other_user, amount=5000.0, status="succeeded")
    await create_receipt(db_session, payment=payment)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/subscriptions/payments/{payment.id}/receipt",
        headers=auth_headers_doctor,
    )
    assert resp.status_code == 404
