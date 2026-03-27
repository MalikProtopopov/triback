"""Unit tests for kassa.payanyway.ru fiscal XML helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.kassa_payanyway_fiscal import (
    FiscalSeller,
    build_inventory_json,
    build_kassa_fiscal_xml,
    get_payment_by_mnt_transaction_id,
    kassa_fiscal_signature_r8,
    normalize_position_name,
    reconcile_line_prices,
    strip_return_prefix,
)
from app.services.payment_providers.base import PaymentItem


def test_kassa_fiscal_signature_r8() -> None:
    secret = "integrity-code"
    sig = kassa_fiscal_signature_r8("200", "mnt1", "txn-uuid", secret)
    assert len(sig) == 32
    # deterministic
    assert (
        sig
        == kassa_fiscal_signature_r8("200", "mnt1", "txn-uuid", secret)
    )


def test_normalize_position_name_strips_entities() -> None:
    assert "quote" not in normalize_position_name('Товар "А" & улуги')
    assert normalize_position_name("  plain  ") == "plain"


def test_reconcile_line_prices_scales_to_target() -> None:
    items = [
        PaymentItem(name="A", price=Decimal("100.00"), quantity=1),
        PaymentItem(name="B", price=Decimal("100.00"), quantity=1),
    ]
    adjusted = reconcile_line_prices(items, Decimal("150.00"))
    assert len(adjusted) == 2
    total = sum((it.price * it.quantity for it in adjusted), Decimal(0))
    assert total == Decimal("150.00")


def test_build_kassa_fiscal_xml_structure() -> None:
    xml = build_kassa_fiscal_xml(
        mnt_id="m1",
        mnt_transaction_id="t1",
        result_code="200",
        inventory_json='[{"productName":"x"}]',
        client_json='{"email":"a@b.ru"}',
        integrity_secret="sec",
        sno=1,
    )
    assert "<?xml" in xml
    assert "<MNT_RESPONSE>" in xml
    assert "<MNT_RESULT_CODE>200</MNT_RESULT_CODE>" in xml
    assert "INVENTORY" in xml
    assert "CLIENT" in xml
    assert "SNO" in xml
    assert "<![CDATA[" in xml


def test_build_inventory_json_uses_seller_and_reconcile() -> None:
    seller = FiscalSeller(
        inn="7700000000",
        name="ООО Тест",
        phone="79000000000",
        account="123",
    )
    items = [PaymentItem(name='Услуга "1"', price=Decimal("100.00"), quantity=1)]
    raw = build_inventory_json(items, seller, Decimal("100.00"))
    assert "7700000000" in raw
    assert "productPrice" in raw


@pytest.mark.anyio
async def test_strip_return_prefix_and_get_payment(
    db_session,
    doctor_user,
):
    from app.models.subscriptions import Payment, Plan, Subscription

    plan = Plan(
        code="kassa-t-plan",
        name="P",
        price=10.0,
        duration_months=12,
        is_active=True,
        plan_type="subscription",
    )
    db_session.add(plan)
    await db_session.flush()
    sub = Subscription(
        user_id=doctor_user.id,
        plan_id=plan.id,
        status="pending_payment",
    )
    db_session.add(sub)
    await db_session.flush()
    pay = Payment(
        user_id=doctor_user.id,
        amount=10.0,
        product_type="subscription",
        payment_provider="moneta",
        status="pending",
        subscription_id=sub.id,
    )
    db_session.add(pay)
    await db_session.flush()

    raw, is_ref = strip_return_prefix(f"RETURN_{pay.id}")
    assert is_ref is True
    assert raw == str(pay.id)

    loaded = await get_payment_by_mnt_transaction_id(db_session, str(pay.id))
    assert loaded is not None
    assert loaded.id == pay.id

    loaded2 = await get_payment_by_mnt_transaction_id(
        db_session, f"RETURN_{pay.id}"
    )
    assert loaded2 is not None
    assert loaded2.id == pay.id
