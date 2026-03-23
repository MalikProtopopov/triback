"""Admin event registrations list."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EventRegistrationStatus
from app.core.exceptions import NotFoundError
from app.models.events import Event, EventRegistration, EventTariff
from app.models.profiles import DoctorProfile
from app.models.users import User
from app.schemas.events_admin import (
    RegistrationListItem,
    RegistrationListResponse,
    RegistrationSummary,
    RegistrationTariffNested,
    RegistrationUserNested,
)


class EventsAdminRegistrations:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_registrations(
        self, event_id: UUID, *, limit: int = 20, offset: int = 0,
        status: str | None = None,
    ) -> RegistrationListResponse:
        event = await self.db.get(Event, event_id)
        if not event:
            raise NotFoundError("Event not found")

        base = select(EventRegistration).where(EventRegistration.event_id == event_id)
        count_q = select(func.count(EventRegistration.id)).where(
            EventRegistration.event_id == event_id,
        )

        if status:
            base = base.where(EventRegistration.status == status)
            count_q = count_q.where(EventRegistration.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0
        base = base.order_by(EventRegistration.created_at.desc()).offset(offset).limit(limit)
        regs = (await self.db.execute(base)).scalars().all()

        reg_user_ids = list({r.user_id for r in regs})
        reg_tariff_ids = list({r.event_tariff_id for r in regs})

        user_email_map: dict[UUID, str] = {}
        dp_name_map: dict[UUID, str] = {}
        tariff_map: dict[UUID, tuple[UUID, str]] = {}

        if reg_user_ids:
            u_q = await self.db.execute(
                select(User.id, User.email).where(User.id.in_(reg_user_ids))
            )
            for uid, email in u_q.all():
                user_email_map[uid] = email
            dp_q = await self.db.execute(
                select(DoctorProfile.user_id, DoctorProfile.first_name, DoctorProfile.last_name)
                .where(DoctorProfile.user_id.in_(reg_user_ids))
            )
            for uid, fn, ln in dp_q.all():
                dp_name_map[uid] = f"{ln} {fn}"

        if reg_tariff_ids:
            t_q = await self.db.execute(
                select(EventTariff.id, EventTariff.name).where(EventTariff.id.in_(reg_tariff_ids))
            )
            for tid, tname in t_q.all():
                tariff_map[tid] = (tid, tname)

        items: list[RegistrationListItem] = []
        for r in regs:
            t_info = tariff_map.get(r.event_tariff_id)
            items.append(
                RegistrationListItem(
                    id=r.id,
                    user=RegistrationUserNested(
                        id=r.user_id,
                        email=user_email_map.get(r.user_id, ""),
                        full_name=dp_name_map.get(r.user_id),
                    ),
                    tariff=RegistrationTariffNested(
                        id=t_info[0] if t_info else r.event_tariff_id,
                        name=t_info[1] if t_info else "",
                    ),
                    applied_price=float(r.applied_price),
                    is_member_price=r.is_member_price,
                    status=r.status,
                    created_at=r.created_at,
                )
            )

        summary_q = select(
            func.count(EventRegistration.id).label("total_registrations"),
            func.count(EventRegistration.id).filter(
                EventRegistration.status == EventRegistrationStatus.CONFIRMED
            ).label("confirmed"),
            func.count(EventRegistration.id).filter(
                EventRegistration.status == EventRegistrationStatus.PENDING
            ).label("pending"),
            func.count(EventRegistration.id).filter(
                EventRegistration.status == EventRegistrationStatus.CANCELLED
            ).label("cancelled"),
            func.coalesce(
                func.sum(EventRegistration.applied_price).filter(
                    EventRegistration.status == EventRegistrationStatus.CONFIRMED
                ), 0,
            ).label("total_revenue"),
        ).where(EventRegistration.event_id == event_id)
        s = (await self.db.execute(summary_q)).one()

        return RegistrationListResponse(
            data=items,
            summary=RegistrationSummary(
                total_registrations=s.total_registrations,
                confirmed=s.confirmed, pending=s.pending,
                cancelled=s.cancelled, total_revenue=float(s.total_revenue),
            ),
            total=total, limit=limit, offset=offset,
        )
