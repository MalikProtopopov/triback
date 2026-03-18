"""Business logic tests for Moneta subscription payments."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import DoctorProfile
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.base import CreatePaymentResult
from app.services.subscription_service import SubscriptionService


@pytest.fixture
async def setup_plans(db_session: AsyncSession) -> tuple[Plan, Plan]:
    """Create entry_fee and subscription plans."""
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
        status="approved",
        has_medical_diploma=True,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest.mark.anyio
async def test_pay_entry_fee_creates_two_items(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    setup_plans,
    monkeypatch: pytest.MonkeyPatch,
):
    _, annual = setup_plans

    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")

    mock_result = CreatePaymentResult(
        external_id="op-111",
        payment_url="https://moneta.test/assistant.htm?operationId=op-111",
    )

    with patch(
        "app.services.subscription_service.get_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_get_provider.return_value = mock_provider

        svc = SubscriptionService(db_session, redis_mock)
        resp = await svc.pay(doctor_user.id, annual.id, f"idem-{uuid4().hex[:8]}")

    assert resp.payment_url == mock_result.payment_url
    assert resp.amount == 20000.0  # 5000 + 15000

    call_kwargs = mock_provider.create_payment.call_args.kwargs
    assert len(call_kwargs["items"]) == 2
    assert call_kwargs["total_amount"] == Decimal("20000.00")


@pytest.mark.anyio
async def test_pay_subscription_creates_one_item(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    setup_plans,
    monkeypatch: pytest.MonkeyPatch,
):
    _, annual = setup_plans

    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=annual.id,
        status="active",
        starts_at=None,
    )
    db_session.add(sub)
    await db_session.flush()

    entry_payment = Payment(
        user_id=doctor_user.id,
        amount=5000.00,
        product_type="entry_fee",
        payment_provider="moneta",
        status="succeeded",
    )
    db_session.add(entry_payment)
    await db_session.flush()

    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")

    mock_result = CreatePaymentResult(
        external_id="op-222",
        payment_url="https://moneta.test/assistant.htm?operationId=op-222",
    )

    with patch(
        "app.services.subscription_service.get_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_get_provider.return_value = mock_provider

        svc = SubscriptionService(db_session, redis_mock)
        resp = await svc.pay(doctor_user.id, annual.id, f"idem-{uuid4().hex[:8]}")

    assert resp.amount == 15000.0

    call_kwargs = mock_provider.create_payment.call_args.kwargs
    assert len(call_kwargs["items"]) == 1
    assert call_kwargs["total_amount"] == Decimal("15000.00")


@pytest.mark.anyio
async def test_status_entry_fee_required(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    setup_plans,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")

    with patch("app.services.subscription_service.get_provider") as mock_gp:
        mock_gp.return_value = AsyncMock()
        svc = SubscriptionService(db_session, redis_mock)
        status = await svc.get_status(doctor_user.id)

    assert status.entry_fee_required is True
    assert status.entry_fee_plan is not None
    assert status.entry_fee_plan.plan_type == "entry_fee"
    assert len(status.available_plans) >= 1
    assert status.next_action == "pay_entry_fee_and_subscription"


@pytest.mark.anyio
async def test_status_subscription_only(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    setup_plans,
    monkeypatch: pytest.MonkeyPatch,
):
    _, annual = setup_plans

    entry_payment = Payment(
        user_id=doctor_user.id,
        amount=5000.00,
        product_type="entry_fee",
        payment_provider="moneta",
        status="succeeded",
    )
    db_session.add(entry_payment)
    await db_session.flush()

    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")

    with patch("app.services.subscription_service.get_provider") as mock_gp:
        mock_gp.return_value = AsyncMock()
        svc = SubscriptionService(db_session, redis_mock)
        status = await svc.get_status(doctor_user.id)

    assert status.entry_fee_required is False
    assert status.has_paid_entry_fee is True
    assert status.next_action == "pay_subscription"


@pytest.mark.anyio
async def test_pay_returns_moneta_url(
    db_session: AsyncSession,
    redis_mock: AsyncMock,
    doctor_user,
    doctor_with_profile,
    setup_plans,
    monkeypatch: pytest.MonkeyPatch,
):
    _, annual = setup_plans

    monkeypatch.setattr("app.core.config.settings.PAYMENT_PROVIDER", "moneta")
    monkeypatch.setattr("app.core.config.settings.MONETA_SUCCESS_URL", "https://test.com/success")

    mock_result = CreatePaymentResult(
        external_id="op-333",
        payment_url="https://moneta.test/assistant.htm?operationId=op-333&version=v3",
    )

    with patch(
        "app.services.subscription_service.get_provider"
    ) as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.create_payment = AsyncMock(return_value=mock_result)
        mock_get_provider.return_value = mock_provider

        svc = SubscriptionService(db_session, redis_mock)
        resp = await svc.pay(doctor_user.id, annual.id, f"idem-{uuid4().hex[:8]}")

    assert "moneta.test" in resp.payment_url
    assert "operationId" in resp.payment_url
