"""Admin CRUD for membership arrears."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.models.arrears import MembershipArrear
from app.models.profiles import DoctorProfile
from app.models.users import TelegramBinding, User
from app.schemas.arrears import (
    ArrearCreateRequest,
    ArrearListResponse,
    ArrearResponse,
    ArrearSummaryResponse,
    ArrearUpdateRequest,
    ArrearUserNested,
)


def _format_full_name(dp: DoctorProfile | None) -> str | None:
    if not dp:
        return None
    parts = [dp.last_name, dp.first_name, dp.middle_name]
    joined = " ".join(p.strip() for p in parts if p and str(p).strip())
    return joined or None


def _user_to_nested(
    u: User, dp: DoctorProfile | None, tg: TelegramBinding | None
) -> ArrearUserNested:
    return ArrearUserNested(
        id=u.id,
        email=u.email,
        full_name=_format_full_name(dp),
        phone=dp.phone if dp else None,
        telegram_username=tg.tg_username if tg and tg.tg_username else None,
    )


def _to_response(
    a: MembershipArrear, user: ArrearUserNested | None = None
) -> ArrearResponse:
    return ArrearResponse(
        id=a.id,
        user_id=a.user_id,
        year=a.year,
        amount=float(a.amount),
        description=a.description,
        admin_note=a.admin_note,
        status=a.status,
        source=a.source,
        escalation_level=a.escalation_level,
        created_by=a.created_by,
        payment_id=a.payment_id,
        paid_at=a.paid_at,
        waived_at=a.waived_at,
        waived_by=a.waived_by,
        waive_reason=a.waive_reason,
        created_at=a.created_at,
        updated_at=a.updated_at,
        user=user,
    )


class ArrearsAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _load_user_nested(self, user_id: UUID) -> ArrearUserNested:
        stmt = (
            select(User, DoctorProfile, TelegramBinding)
            .select_from(User)
            .where(User.id == user_id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .outerjoin(TelegramBinding, TelegramBinding.user_id == User.id)
        )
        row = (await self.db.execute(stmt)).one_or_none()
        if not row:
            return ArrearUserNested(
                id=user_id,
                email="",
                full_name=None,
                phone=None,
                telegram_username=None,
            )
        u, dp, tg = row
        return _user_to_nested(u, dp, tg)

    async def list_arrears(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        user_id: UUID | None = None,
        year: int | None = None,
        status: str | None = None,
        source: str | None = None,
        include_inactive: bool = True,
    ) -> ArrearListResponse:
        count_q = select(func.count(MembershipArrear.id))
        filters: list[Any] = []
        if user_id:
            filters.append(MembershipArrear.user_id == user_id)
        if year is not None:
            filters.append(MembershipArrear.year == year)
        if status:
            filters.append(MembershipArrear.status == status)
        elif not include_inactive:
            filters.append(MembershipArrear.status == "open")
        if source:
            filters.append(MembershipArrear.source == source)
        if filters:
            count_q = count_q.where(and_(*filters))
        total = (await self.db.execute(count_q)).scalar() or 0
        q = (
            select(MembershipArrear, User, DoctorProfile, TelegramBinding)
            .join(User, MembershipArrear.user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .outerjoin(TelegramBinding, TelegramBinding.user_id == User.id)
        )
        if filters:
            q = q.where(and_(*filters))
        q = q.order_by(MembershipArrear.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.db.execute(q)).all()
        return ArrearListResponse(
            data=[
                _to_response(a, _user_to_nested(u, dp, tg))
                for a, u, dp, tg in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def summary(self) -> ArrearSummaryResponse:
        open_row = await self.db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "open")
        )
        oa, oc = open_row.one()
        paid_row = await self.db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "paid")
        )
        pa, pc = paid_row.one()
        waived_row = await self.db.execute(
            select(
                func.coalesce(func.sum(MembershipArrear.amount), 0),
                func.count(MembershipArrear.id),
            ).where(MembershipArrear.status == "waived")
        )
        wa, wc = waived_row.one()
        return ArrearSummaryResponse(
            total_open_amount=float(oa or 0),
            count_open=int(oc or 0),
            total_paid_amount=float(pa or 0),
            count_paid=int(pc or 0),
            total_waived_amount=float(wa or 0),
            count_waived=int(wc or 0),
        )

    async def create(self, admin_id: UUID, body: ArrearCreateRequest) -> ArrearResponse:
        user = await self.db.get(User, body.user_id)
        if not user:
            raise NotFoundError("User not found")
        dup = await self.db.execute(
            select(MembershipArrear.id).where(
                and_(
                    MembershipArrear.user_id == body.user_id,
                    MembershipArrear.year == body.year,
                    MembershipArrear.status == "open",
                )
            )
        )
        if dup.scalar_one_or_none():
            raise ConflictError(
                f"Open arrear already exists for year {body.year}"
            )
        a = MembershipArrear(
            user_id=body.user_id,
            year=body.year,
            amount=Decimal(str(body.amount)),
            description=body.description,
            admin_note=body.admin_note,
            status="open",
            source=body.source,
            created_by=admin_id,
        )
        self.db.add(a)
        await self.db.commit()
        await self.db.refresh(a)
        from app.tasks.email_tasks import send_arrear_created_notification

        await send_arrear_created_notification.kiq(str(body.user_id), body.year, float(body.amount))
        un = await self._load_user_nested(a.user_id)
        return _to_response(a, un)

    async def update(
        self, arrear_id: UUID, body: ArrearUpdateRequest
    ) -> ArrearResponse:
        a = await self.db.get(MembershipArrear, arrear_id)
        if not a:
            raise NotFoundError("Arrear not found")
        if a.status != "open":
            raise AppValidationError("Можно редактировать только открытую задолженность")
        if body.amount is not None:
            a.amount = Decimal(str(body.amount))
        if body.description is not None:
            a.description = body.description
        if body.admin_note is not None:
            a.admin_note = body.admin_note
        await self.db.commit()
        await self.db.refresh(a)
        un = await self._load_user_nested(a.user_id)
        return _to_response(a, un)

    async def cancel(self, arrear_id: UUID) -> ArrearResponse:
        a = await self.db.get(MembershipArrear, arrear_id)
        if not a:
            raise NotFoundError("Arrear not found")
        if a.status != "open":
            raise AppValidationError("Можно отменить только открытую задолженность")
        a.status = "cancelled"
        await self.db.commit()
        await self.db.refresh(a)
        un = await self._load_user_nested(a.user_id)
        return _to_response(a, un)

    async def waive(
        self, arrear_id: UUID, admin_id: UUID, waive_reason: str | None
    ) -> ArrearResponse:
        a = await self.db.get(MembershipArrear, arrear_id)
        if not a:
            raise NotFoundError("Arrear not found")
        if a.status != "open":
            raise AppValidationError("Можно простить только открытую задолженность")
        now = datetime.now(UTC)
        a.status = "waived"
        a.waived_at = now
        a.waived_by = admin_id
        a.waive_reason = waive_reason
        await self.db.commit()
        await self.db.refresh(a)
        un = await self._load_user_nested(a.user_id)
        return _to_response(a, un)

    async def mark_paid_manual(self, arrear_id: UUID) -> ArrearResponse:
        a = await self.db.get(MembershipArrear, arrear_id)
        if not a:
            raise NotFoundError("Arrear not found")
        if a.status != "open":
            raise AppValidationError("Можно закрыть только открытую задолженность")
        now = datetime.now(UTC)
        a.status = "paid"
        a.paid_at = now
        await self.db.commit()
        await self.db.refresh(a)
        un = await self._load_user_nested(a.user_id)
        return _to_response(a, un)
