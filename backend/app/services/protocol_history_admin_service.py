"""Admin CRUD for protocol history (admission / exclusion)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, NotFoundError
from app.models.profiles import DoctorProfile
from app.models.protocol_history import ProtocolHistoryEntry
from app.models.users import TelegramBinding, User
from app.schemas.arrears import ArrearUserNested
from app.schemas.protocol_history import (
    AdminUserSnapshot,
    ProtocolHistoryCreateRequest,
    ProtocolHistoryListResponse,
    ProtocolHistoryResponse,
    ProtocolHistoryUpdateRequest,
)
from app.services.arrears_admin_service import _user_to_nested


def _staff_snapshot(u: User, dp: DoctorProfile | None) -> AdminUserSnapshot:
    full_name = None
    if dp:
        parts = [dp.last_name, dp.first_name, dp.middle_name]
        full_name = " ".join(p.strip() for p in parts if p and str(p).strip()) or None
    return AdminUserSnapshot(id=u.id, email=u.email, full_name=full_name)


async def _ensure_doctor_exists(db: AsyncSession, doctor_user_id: UUID) -> None:
    row = await db.execute(
        select(DoctorProfile.id).where(DoctorProfile.user_id == doctor_user_id)
    )
    if row.scalar_one_or_none() is None:
        raise AppValidationError("Пользователь не является врачом или профиль не найден")


class ProtocolHistoryAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _users_snapshots(
        self, user_ids: set[UUID]
    ) -> dict[UUID, tuple[User, DoctorProfile | None]]:
        if not user_ids:
            return {}
        stmt = (
            select(User, DoctorProfile)
            .where(User.id.in_(user_ids))
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        )
        rows = (await self.db.execute(stmt)).all()
        return {u.id: (u, dp) for u, dp in rows}

    def _build_response(
        self,
        row: ProtocolHistoryEntry,
        doctor_u: User,
        doctor_dp: DoctorProfile | None,
        doctor_tg: TelegramBinding | None,
        author_map: dict[UUID, tuple[User, DoctorProfile | None]],
    ) -> ProtocolHistoryResponse:
        doctor = _user_to_nested(doctor_u, doctor_dp, doctor_tg)
        cb = author_map.get(row.created_by_user_id)
        if not cb:
            raise NotFoundError("Author user not found")
        created_snap = _staff_snapshot(cb[0], cb[1])
        last_snap = None
        if row.last_edited_by_user_id:
            le = author_map.get(row.last_edited_by_user_id)
            if le:
                last_snap = _staff_snapshot(le[0], le[1])
        return ProtocolHistoryResponse(
            id=row.id,
            year=row.year,
            protocol_title=row.protocol_title,
            notes=row.notes,
            doctor_user_id=row.doctor_user_id,
            action_type=row.action_type,
            created_by_user_id=row.created_by_user_id,
            last_edited_by_user_id=row.last_edited_by_user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            doctor=doctor,
            created_by_user=created_snap,
            last_edited_by_user=last_snap,
        )

    async def list_entries(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        doctor_user_id: UUID | None = None,
        action_type: str | None = None,
    ) -> ProtocolHistoryListResponse:
        count_q = select(func.count(ProtocolHistoryEntry.id))
        filters: list[Any] = []
        if doctor_user_id:
            filters.append(ProtocolHistoryEntry.doctor_user_id == doctor_user_id)
        if action_type:
            filters.append(ProtocolHistoryEntry.action_type == action_type)
        if filters:
            count_q = count_q.where(and_(*filters))
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(ProtocolHistoryEntry, User, DoctorProfile, TelegramBinding)
            .join(User, ProtocolHistoryEntry.doctor_user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .outerjoin(TelegramBinding, TelegramBinding.user_id == User.id)
        )
        if filters:
            q = q.where(and_(*filters))
        q = (
            q.order_by(ProtocolHistoryEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.db.execute(q)).all()

        author_ids: set[UUID] = set()
        for e, _, _, _ in rows:
            author_ids.add(e.created_by_user_id)
            if e.last_edited_by_user_id:
                author_ids.add(e.last_edited_by_user_id)
        author_map = await self._users_snapshots(author_ids)

        data: list[ProtocolHistoryResponse] = [
            self._build_response(e, u, dp, tg, author_map)
            for e, u, dp, tg in rows
        ]
        return ProtocolHistoryListResponse(
            data=data, total=total, limit=limit, offset=offset
        )

    async def get_by_id(self, entry_id: UUID) -> ProtocolHistoryResponse:
        q = (
            select(ProtocolHistoryEntry, User, DoctorProfile, TelegramBinding)
            .join(User, ProtocolHistoryEntry.doctor_user_id == User.id)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .outerjoin(TelegramBinding, TelegramBinding.user_id == User.id)
            .where(ProtocolHistoryEntry.id == entry_id)
        )
        row = (await self.db.execute(q)).one_or_none()
        if not row:
            raise NotFoundError("Запись не найдена")
        e, u, dp, tg = row
        author_ids = {e.created_by_user_id}
        if e.last_edited_by_user_id:
            author_ids.add(e.last_edited_by_user_id)
        author_map = await self._users_snapshots(author_ids)
        return self._build_response(e, u, dp, tg, author_map)

    async def create(
        self, actor_user_id: UUID, body: ProtocolHistoryCreateRequest
    ) -> ProtocolHistoryResponse:
        await _ensure_doctor_exists(self.db, body.doctor_user_id)
        ent = ProtocolHistoryEntry(
            year=body.year,
            protocol_title=body.protocol_title,
            notes=body.notes,
            doctor_user_id=body.doctor_user_id,
            action_type=body.action_type.value,
            created_by_user_id=actor_user_id,
            last_edited_by_user_id=None,
        )
        self.db.add(ent)
        await self.db.commit()
        await self.db.refresh(ent)
        return await self.get_by_id(ent.id)

    async def update(
        self, entry_id: UUID, actor_user_id: UUID, body: ProtocolHistoryUpdateRequest
    ) -> ProtocolHistoryResponse:
        ent = await self.db.get(ProtocolHistoryEntry, entry_id)
        if not ent:
            raise NotFoundError("Запись не найдена")
        if body.doctor_user_id is not None:
            await _ensure_doctor_exists(self.db, body.doctor_user_id)
            ent.doctor_user_id = body.doctor_user_id
        if body.year is not None:
            ent.year = body.year
        if body.protocol_title is not None:
            ent.protocol_title = body.protocol_title
        if body.notes is not None:
            ent.notes = body.notes
        if body.action_type is not None:
            ent.action_type = body.action_type.value
        ent.last_edited_by_user_id = actor_user_id
        await self.db.commit()
        await self.db.refresh(ent)
        return await self.get_by_id(ent.id)

    async def delete(self, entry_id: UUID) -> None:
        ent = await self.db.get(ProtocolHistoryEntry, entry_id)
        if not ent:
            raise NotFoundError("Запись не найдена")
        await self.db.delete(ent)
        await self.db.commit()
