"""kassa.payanyway.ru Pay URL (path A): INVENTORY/CLIENT JSON and MNT_RESPONSE XML (R8)."""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.enums import PlanType, ProductType
from app.models.arrears import MembershipArrear
from app.models.events import EventRegistration
from app.models.subscriptions import Payment, Plan, Subscription
from app.services.payment_providers.base import PaymentItem


class FiscalRebuildError(Exception):
    """Cannot reconstruct line items for kassa INVENTORY from DB."""


def kassa_fiscal_signature_r8(
    result_code: str,
    mnt_id: str,
    mnt_transaction_id: str,
    integrity_secret: str,
) -> str:
    """MD5(MNT_RESULT_CODE + MNT_ID + MNT_TRANSACTION_ID + код_целостности)."""
    raw = f"{result_code}{mnt_id}{mnt_transaction_id}{integrity_secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def normalize_position_name(name: str) -> str:
    """kassa: no quotes / problematic chars (PHP recipe from kassaspecification)."""
    step = html.escape(name, quote=False)
    step = re.sub(r"&?[a-z0-9]+;", "", step, flags=re.IGNORECASE)
    return step.strip()


def _vat_tag_from_payment_item(item: PaymentItem) -> int:
    """Map line to kassa productVatCode / vatTag (1105 = без НДС)."""
    if item.vat_code is None:
        return 1105
    # YooKassa-style 1..6 → default без НДС for unknown
    vc = item.vat_code
    if vc == 1:
        return 1105
    return 1105


def _sum_lines(items: list[PaymentItem]) -> Decimal:
    total = Decimal(0)
    for it in items:
        total += it.price * Decimal(it.quantity)
    return total


def reconcile_line_prices(
    items: list[PaymentItem], target_total: Decimal
) -> list[PaymentItem]:
    """Scale unit prices so sum matches MNT_AMOUNT (kassa manual / PDF)."""
    if not items:
        return items
    current = _sum_lines(items)
    if current == 0 or current == target_total:
        return [replace(it) for it in items]
    factor = target_total / current
    out: list[PaymentItem] = []
    for it in items:
        new_price = (it.price * factor).quantize(Decimal("0.01"))
        out.append(
            replace(
                it,
                price=new_price,
            )
        )
    # Fix rounding drift on last line
    drift = target_total - _sum_lines(out)
    if drift != 0 and out:
        last = out[-1]
        out[-1] = replace(
            last,
            price=(last.price + drift).quantize(Decimal("0.01")),
        )
    return out


@dataclass(frozen=True)
class FiscalSeller:
    inn: str
    name: str
    phone: str
    account: str


def fiscal_seller_from_settings() -> FiscalSeller:
    return FiscalSeller(
        inn=(settings.MONETA_FISCAL_SELLER_INN or "").strip(),
        name=(settings.MONETA_FISCAL_SELLER_NAME or "").strip(),
        phone=(settings.MONETA_FISCAL_SELLER_PHONE or "").strip(),
        account=(settings.MONETA_FISCAL_SELLER_ACCOUNT or "").strip(),
    )


def invent_positions_for_kassa(
    items: list[PaymentItem],
    seller: FiscalSeller,
) -> list[dict[str, Any]]:
    """Objects compatible with kassa INVENTORY JSON (see MONETA_INTEGRATION_PLAN example)."""
    rows: list[dict[str, Any]] = []
    for it in items:
        pname = normalize_position_name(it.name)
        vat = _vat_tag_from_payment_item(it)
        rows.append(
            {
                "sellerAccount": seller.account,
                "sellerInn": seller.inn,
                "sellerName": seller.name,
                "sellerPhone": seller.phone,
                "productName": pname,
                "productQuantity": it.quantity,
                "productPrice": float(it.price.quantize(Decimal("0.01"))),
                "productVatCode": vat,
                "po": it.payment_object or "service",
                "pm": it.payment_method or "full_payment",
            }
        )
    return rows


def build_client_json(email: str | None, phone: str | None) -> str:
    obj: dict[str, str] = {}
    if email:
        obj["email"] = email
    if phone:
        obj["phone"] = phone
    if not obj:
        obj["email"] = "noreply@invalid.local"
    return json.dumps(obj, ensure_ascii=False)


def build_inventory_json(
    items: list[PaymentItem],
    seller: FiscalSeller,
    mnt_amount: Decimal,
) -> str:
    adjusted = reconcile_line_prices(items, mnt_amount)
    inv = invent_positions_for_kassa(adjusted, seller)
    return json.dumps(inv, ensure_ascii=False)


def build_kassa_fiscal_xml(
    *,
    mnt_id: str,
    mnt_transaction_id: str,
    result_code: str,
    inventory_json: str,
    client_json: str,
    integrity_secret: str,
    sno: int | None = None,
) -> str:
    sig = kassa_fiscal_signature_r8(
        result_code, mnt_id, mnt_transaction_id, integrity_secret
    )
    attrs_inner = []
    attrs_inner.append(
        "<ATTRIBUTE><KEY>INVENTORY</KEY>"
        f"<VALUE><![CDATA[{inventory_json}]]></VALUE>"
        "</ATTRIBUTE>"
    )
    attrs_inner.append(
        "<ATTRIBUTE><KEY>CLIENT</KEY>"
        f"<VALUE><![CDATA[{client_json}]]></VALUE>"
        "</ATTRIBUTE>"
    )
    if sno is not None:
        attrs_inner.append(
            f"<ATTRIBUTE><KEY>SNO</KEY><VALUE>{sno}</VALUE></ATTRIBUTE>"
        )
    inner = "\n    ".join(attrs_inner)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<MNT_RESPONSE>\n"
        f"  <MNT_ID>{escape(mnt_id)}</MNT_ID>\n"
        f"  <MNT_TRANSACTION_ID>{escape(mnt_transaction_id)}</MNT_TRANSACTION_ID>\n"
        f"  <MNT_RESULT_CODE>{escape(result_code)}</MNT_RESULT_CODE>\n"
        f"  <MNT_SIGNATURE>{escape(sig)}</MNT_SIGNATURE>\n"
        "  <MNT_ATTRIBUTES>\n"
        f"    {inner}\n"
        "  </MNT_ATTRIBUTES>\n"
        "</MNT_RESPONSE>"
    )


def build_kassa_error_xml(
    *,
    mnt_id: str,
    mnt_transaction_id: str,
    result_code: str,
    integrity_secret: str,
) -> str:
    """Minimal XML without INVENTORY (signature still R8 on the triplet)."""
    sig = kassa_fiscal_signature_r8(
        result_code, mnt_id, mnt_transaction_id, integrity_secret
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<MNT_RESPONSE>\n"
        f"  <MNT_ID>{escape(mnt_id)}</MNT_ID>\n"
        f"  <MNT_TRANSACTION_ID>{escape(mnt_transaction_id)}</MNT_TRANSACTION_ID>\n"
        f"  <MNT_RESULT_CODE>{escape(result_code)}</MNT_RESULT_CODE>\n"
        f"  <MNT_SIGNATURE>{escape(sig)}</MNT_SIGNATURE>\n"
        "</MNT_RESPONSE>"
    )


def strip_return_prefix(mnt_transaction_id: str) -> tuple[str, bool]:
    """RETURN_<uuid> → (uuid str, is_refund)."""
    if mnt_transaction_id.startswith("RETURN_"):
        return mnt_transaction_id[len("RETURN_") :], True
    return mnt_transaction_id, False


async def get_payment_by_mnt_transaction_id(
    db: AsyncSession, transaction_id: str
) -> Payment | None:
    """Load ``Payment`` by ``MNT_TRANSACTION_ID`` (with optional ``RETURN_`` prefix)."""
    raw, _is_refund = strip_return_prefix(transaction_id)
    try:
        pid = UUID(raw)
    except ValueError:
        return None
    result = await db.execute(select(Payment).where(Payment.id == pid))
    return result.scalar_one_or_none()


async def payment_items_for_fiscal(
    db: AsyncSession, payment: Payment
) -> list[PaymentItem]:
    """Rebuild PaymentItem rows the same way as at payment creation time."""
    pt = str(payment.product_type)

    if pt == ProductType.MEMBERSHIP_ARREARS:
        if not payment.arrear_id:
            raise FiscalRebuildError("membership_arrears without arrear_id")
        ar = await db.get(MembershipArrear, payment.arrear_id)
        if not ar:
            raise FiscalRebuildError("arrear not found")
        total_amount = Decimal(str(ar.amount))
        return [
            PaymentItem(
                name=f"Задолженность членского взноса ({ar.year})",
                price=total_amount,
                quantity=1,
            )
        ]

    if pt == ProductType.EVENT:
        if not payment.event_registration_id:
            raise FiscalRebuildError("event without event_registration_id")
        reg = await db.get(
            EventRegistration,
            payment.event_registration_id,
            options=[
                selectinload(EventRegistration.event),
                selectinload(EventRegistration.tariff),
            ],
        )
        if not reg or not reg.event or not reg.tariff:
            raise FiscalRebuildError("event registration not found")
        event = reg.event
        tariff = reg.tariff
        description = f"{event.title} — {tariff.name}"
        price = Decimal(str(reg.applied_price))
        return [PaymentItem(name=description, price=price, quantity=1)]

    if pt in (ProductType.ENTRY_FEE, ProductType.SUBSCRIPTION):
        if not payment.subscription_id:
            raise FiscalRebuildError("subscription payment without subscription_id")
        sub = await db.get(Subscription, payment.subscription_id)
        if not sub:
            raise FiscalRebuildError("subscription not found")
        sub_plan = await db.get(Plan, sub.plan_id)
        if not sub_plan:
            raise FiscalRebuildError("plan not found")

        if pt == ProductType.ENTRY_FEE:
            entry_result = await db.execute(
                select(Plan).where(
                    Plan.plan_type == PlanType.ENTRY_FEE,
                    Plan.is_active.is_(True),
                ).limit(1)
            )
            entry_plan = entry_result.scalar_one_or_none()
            if not entry_plan:
                raise FiscalRebuildError("entry_fee plan not configured")
            return [
                PaymentItem(
                    name=entry_plan.name,
                    price=Decimal(str(entry_plan.price)),
                    quantity=1,
                ),
                PaymentItem(
                    name=sub_plan.name,
                    price=Decimal(str(sub_plan.price)),
                    quantity=1,
                ),
            ]

        return [
            PaymentItem(
                name=sub_plan.name,
                price=Decimal(str(sub_plan.price)),
                quantity=1,
            )
        ]

    raise FiscalRebuildError(f"unsupported product_type: {pt}")
