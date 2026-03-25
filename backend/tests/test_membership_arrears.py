"""Membership arrears: pay-arrears, webhook close, entry_fee_exempt, catalog block, calendar year."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProductType, SubscriptionStatus
from app.models.arrears import MembershipArrear
from app.models.profiles import DoctorProfile
from app.models.site import SiteSetting
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.doctor_catalog_service import DoctorCatalogService
from app.services.payment_webhook_service import PaymentWebhookService
from app.services.subscription_service import SubscriptionService
from app.services.subscriptions import subscription_helpers as sub_helpers

_MSK = ZoneInfo("Europe/Moscow")


@pytest.fixture
async def setup_plans(db_session: AsyncSession) -> tuple[Plan, Plan]:
    entry = Plan(
        code="entry_fee",
        name="Членский взнос",
        price=5000.00,
        duration_months=0,
        is_active=True,
        plan_type="entry_fee",
    )
    annual = Plan(
        code="annual",
        name="Годовая подписка",
        price=15000.00,
        duration_months=12,
        is_active=True,
        plan_type="subscription",
    )
    db_session.add_all([entry, annual])
    await db_session.flush()
    return entry, annual


@pytest.fixture
async def doctor_with_profile(db_session: AsyncSession, doctor_user) -> DoctorProfile:
    profile = DoctorProfile(
        user_id=doctor_user.id,
        first_name="Test",
        last_name="Doctor",
        phone="+79001234567",
        slug=f"test-doctor-{uuid4().hex[:8]}",
        status="active",
        has_medical_diploma=True,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest.mark.anyio
async def test_pay_arrear_creates_pending_payment(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")

    from app.services.payment_providers.base import CreatePaymentResult

    mock_result = CreatePaymentResult(
        external_id="op-arrear",
        payment_url="https://moneta.test/pay",
    )

    ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2025,
        amount=Decimal("100.00"),
        description="Test arrear",
        status="open",
        source="manual",
    )
    db_session.add(ar)
    await db_session.flush()

    with patch(
        "app.services.subscription_service.get_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_get_provider.return_value = mock_provider

        svc = SubscriptionService(db_session, redis_mock)
        resp = await svc.pay_arrear(
            doctor_user.id, ar.id, f"idem-{uuid4().hex[:8]}"
        )

    assert resp.amount == 100.0
    pay = (
        await db_session.execute(
            select(Payment).where(Payment.id == resp.payment_id)
        )
    ).scalar_one()
    assert pay.product_type == ProductType.MEMBERSHIP_ARREARS
    assert pay.arrear_id == ar.id
    assert pay.subscription_id is None


@pytest.mark.anyio
async def test_webhook_marks_arrear_paid(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
):
    ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2024,
        amount=Decimal("250.00"),
        description="Debt",
        status="open",
        source="manual",
    )
    db_session.add(ar)
    await db_session.flush()

    pay = Payment(
        user_id=doctor_user.id,
        amount=250.0,
        product_type=ProductType.MEMBERSHIP_ARREARS,
        payment_provider="moneta",
        status="pending",
        arrear_id=ar.id,
        subscription_id=None,
    )
    db_session.add(pay)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    await svc._apply_payment_succeeded(pay, receipt_obj=None, send_user_telegram=False)
    await db_session.refresh(ar)

    assert ar.status == "paid"
    assert ar.payment_id == pay.id


@pytest.mark.anyio
async def test_entry_fee_exempt_forces_subscription_product(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
):
    doctor_with_profile.entry_fee_exempt = True
    await db_session.flush()

    pt = await sub_helpers.determine_product_type(db_session, doctor_user.id)
    assert pt == ProductType.SUBSCRIPTION


@pytest.mark.anyio
async def test_activate_subscription_new_calendar_year_msk(
    db_session: AsyncSession,
    doctor_user,
    setup_plans,
):
    _, annual = setup_plans
    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=annual.id,
        status=SubscriptionStatus.PENDING_PAYMENT,
    )
    db_session.add(sub)
    await db_session.flush()

    pay = Payment(
        user_id=doctor_user.id,
        amount=15000.0,
        product_type=ProductType.SUBSCRIPTION,
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
    )
    db_session.add(pay)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)
    await svc._activate_subscription(pay, now)
    await db_session.refresh(sub)

    assert sub.ends_at is not None
    assert sub.ends_at.astimezone(_MSK).year == 2026
    assert sub.ends_at.astimezone(_MSK).month == 12
    assert sub.ends_at.astimezone(_MSK).day == 31


@pytest.mark.anyio
async def test_activate_subscription_renewal_extends_next_calendar_year(
    db_session: AsyncSession,
    doctor_user,
    setup_plans,
):
    _, annual = setup_plans
    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=annual.id,
        status=SubscriptionStatus.ACTIVE,
        starts_at=datetime(2027, 1, 1, tzinfo=UTC),
        ends_at=datetime(2027, 12, 31, 23, 59, 59, tzinfo=_MSK),
    )
    db_session.add(sub)
    await db_session.flush()

    pay = Payment(
        user_id=doctor_user.id,
        amount=15000.0,
        product_type=ProductType.SUBSCRIPTION,
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
    )
    db_session.add(pay)
    await db_session.flush()

    svc = PaymentWebhookService(db_session)
    now = datetime(2027, 11, 10, 12, 0, 0, tzinfo=UTC)
    await svc._activate_subscription(pay, now)
    await db_session.refresh(sub)

    assert sub.ends_at is not None
    assert sub.ends_at.astimezone(_MSK).year == 2028


@pytest.mark.anyio
async def test_catalog_hides_doctor_when_arrears_block_and_open_arrear(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
    setup_plans,
):
    _, annual = setup_plans
    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=annual.id,
        status=SubscriptionStatus.ACTIVE,
        starts_at=datetime(2026, 1, 1, tzinfo=UTC),
        ends_at=datetime(2026, 12, 31, 23, 59, 59, tzinfo=_MSK),
    )
    db_session.add(sub)
    ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2025,
        amount=Decimal("99.00"),
        description="open",
        status="open",
        source="manual",
    )
    db_session.add(ar)
    db_session.add(
        SiteSetting(
            key="arrears_block_membership_features",
            value={"enabled": True},
        )
    )
    await db_session.flush()

    svc = DoctorCatalogService(db_session)
    out = await svc.list_doctors(limit=20, offset=0)
    assert out["total"] == 0


@pytest.mark.anyio
async def test_manual_payment_membership_arrears_closes_arrear(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
    admin_user,
):
    ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2023,
        amount=Decimal("400.00"),
        description="manual close",
        status="open",
        source="manual",
    )
    db_session.add(ar)
    await db_session.flush()

    from app.schemas.payments import ManualPaymentRequest
    from app.services.payment_admin_service import PaymentAdminService

    admin = PaymentAdminService(db_session)
    await admin.create_manual_payment(
        admin_user.id,
        ManualPaymentRequest(
            user_id=doctor_user.id,
            amount=400.0,
            product_type="membership_arrears",
            description="manual",
            arrear_id=ar.id,
        ),
    )
    await db_session.refresh(ar)
    assert ar.status == "paid"


@pytest.mark.anyio
async def test_waived_arrear_excluded_from_subscription_status_open_arrears(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
):
    ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2019,
        amount=Decimal("50.00"),
        description="forgiven",
        status="waived",
        source="manual",
        waived_at=datetime.now(UTC),
    )
    db_session.add(ar)
    await db_session.flush()

    from app.services.subscriptions.subscription_status import (
        SubscriptionUserStatusService,
    )

    st = await SubscriptionUserStatusService(db_session).get_status(doctor_user.id)
    assert st.open_arrears == []
    assert st.arrears_total == 0.0


@pytest.mark.anyio
async def test_list_arrears_include_inactive_false_only_open(
    db_session: AsyncSession,
    doctor_user,
    doctor_with_profile,
):
    open_ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2021,
        amount=Decimal("10.00"),
        description="open",
        status="open",
        source="manual",
    )
    waived_ar = MembershipArrear(
        user_id=doctor_user.id,
        year=2020,
        amount=Decimal("20.00"),
        description="waived",
        status="waived",
        source="manual",
        waived_at=datetime.now(UTC),
    )
    db_session.add_all([open_ar, waived_ar])
    await db_session.flush()

    from app.services.arrears_admin_service import ArrearsAdminService

    svc = ArrearsAdminService(db_session)
    all_rows = await svc.list_arrears(
        limit=50, offset=0, user_id=doctor_user.id, include_inactive=True
    )
    only_open = await svc.list_arrears(
        limit=50, offset=0, user_id=doctor_user.id, include_inactive=False
    )
    assert len(all_rows.data) == 2
    assert len(only_open.data) == 1
    assert only_open.data[0].status == "open"
    row0 = only_open.data[0]
    assert row0.user is not None
    assert row0.user.email
    assert row0.user.full_name == "Doctor Test"
    assert row0.user.phone == "+79001234567"
