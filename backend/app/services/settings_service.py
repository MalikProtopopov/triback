"""Admin service for site settings, cities, subscription plans."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.core.utils import generate_unique_slug
from app.models.cities import City
from app.models.profiles import DoctorProfile
from app.models.site import SiteSetting
from app.models.subscriptions import Plan, Subscription
from app.schemas.settings_admin import (
    CityAdminResponse,
    PlanAdminResponse,
)

logger = structlog.get_logger(__name__)

# Ключи site_settings, доступные публично (контакты, ссылка бота и т.д.)
PUBLIC_SETTINGS_KEYS = frozenset({
    "contact_email",
    "contact_phone",
    "telegram_bot_link",
    "site_name",
    "site_description",
})


class SettingsAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ══ Site Settings ═════════════════════════════════════════════

    async def get_settings(self) -> dict[str, Any]:
        rows = (await self.db.execute(select(SiteSetting))).scalars().all()
        return {s.key: s.value for s in rows}

    async def get_public_settings(self) -> dict[str, Any]:
        """Возвращает только публичные настройки (whitelist)."""
        rows = (await self.db.execute(select(SiteSetting))).scalars().all()
        return {
            s.key: s.value
            for s in rows
            if s.key in PUBLIC_SETTINGS_KEYS
        }

    async def update_settings(self, admin_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
        for key, value in data.items():
            result = await self.db.execute(
                select(SiteSetting).where(SiteSetting.key == key)
            )
            setting = result.scalar_one_or_none()

            if setting:
                setting.value = value
                setting.updated_by = admin_id
                setting.updated_at = datetime.now(UTC)
            else:
                self.db.add(
                    SiteSetting(
                        key=key,
                        value=value,
                        updated_by=admin_id,
                        updated_at=datetime.now(UTC),
                    )
                )

        await self.db.commit()
        return await self.get_settings()

    # ══ Cities ════════════════════════════════════════════════════

    async def list_cities(self) -> list[CityAdminResponse]:
        doctor_count = (
            func.count(DoctorProfile.id)
            .filter(DoctorProfile.city_id == City.id)
            .label("doctors_count")
        )
        q = (
            select(City, doctor_count)
            .outerjoin(DoctorProfile, DoctorProfile.city_id == City.id)
            .group_by(City.id)
            .order_by(City.sort_order, City.name)
        )
        rows = (await self.db.execute(q)).all()

        return [
            CityAdminResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                sort_order=c.sort_order,
                is_active=c.is_active,
                doctors_count=cnt,
            )
            for c, cnt in rows
        ]

    async def create_city(self, data: dict[str, Any]) -> CityAdminResponse:
        existing = (
            await self.db.execute(select(City).where(City.name == data["name"]))
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Город '{data['name']}' уже существует")

        slug = data.get("slug") or await generate_unique_slug(self.db, City, data["name"])

        city = City(
            name=data["name"],
            slug=slug,
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(city)
        await self.db.commit()
        await self.db.refresh(city)

        return CityAdminResponse(
            id=city.id,
            name=city.name,
            slug=city.slug,
            sort_order=city.sort_order,
            is_active=city.is_active,
            doctors_count=0,
        )

    async def update_city(self, city_id: UUID, data: dict[str, Any]) -> CityAdminResponse:
        city = await self.db.get(City, city_id)
        if not city:
            raise NotFoundError("City not found")

        new_name = data.get("name")
        if new_name and new_name != city.name:
            dup = (
                await self.db.execute(
                    select(City).where(and_(City.name == new_name, City.id != city_id))
                )
            ).scalar_one_or_none()
            if dup:
                raise ConflictError(f"Город '{new_name}' уже существует")
            city.name = new_name
            if not data.get("slug"):
                city.slug = await generate_unique_slug(
                    self.db, City, new_name, existing_id=city_id
                )

        if data.get("slug"):
            city.slug = data["slug"]

        if data.get("sort_order") is not None:
            city.sort_order = data["sort_order"]
        if data.get("is_active") is not None:
            city.is_active = data["is_active"]

        await self.db.commit()

        doctor_count = (
            await self.db.execute(
                select(func.count(DoctorProfile.id)).where(
                    DoctorProfile.city_id == city_id
                )
            )
        ).scalar() or 0

        return CityAdminResponse(
            id=city.id,
            name=city.name,
            slug=city.slug,
            sort_order=city.sort_order,
            is_active=city.is_active,
            doctors_count=doctor_count,
        )

    async def delete_city(self, city_id: UUID) -> None:
        city = await self.db.get(City, city_id)
        if not city:
            raise NotFoundError("City not found")

        doctor_count = (
            await self.db.execute(
                select(func.count(DoctorProfile.id)).where(
                    DoctorProfile.city_id == city_id
                )
            )
        ).scalar() or 0

        if doctor_count > 0:
            city.is_active = False
            await self.db.commit()
            logger.info("city_deactivated", city_id=str(city_id), doctors=doctor_count)
        else:
            await self.db.delete(city)
            await self.db.commit()

    # ══ Subscription Plans ════════════════════════════════════════

    async def list_plans(self) -> list[PlanAdminResponse]:
        rows = (
            await self.db.execute(
                select(Plan).order_by(Plan.sort_order, Plan.name)
            )
        ).scalars().all()

        return [
            PlanAdminResponse(
                id=p.id,
                code=p.code,
                name=p.name,
                description=p.description,
                price=float(p.price),
                duration_months=p.duration_months,
                is_active=p.is_active,
                sort_order=p.sort_order,
            )
            for p in rows
        ]

    async def create_plan(self, data: dict[str, Any]) -> PlanAdminResponse:
        existing = (
            await self.db.execute(select(Plan).where(Plan.code == data["code"]))
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Тариф с кодом '{data['code']}' уже существует")

        plan = Plan(
            code=data["code"],
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            duration_months=data.get("duration_months", 12),
            is_active=data.get("is_active", True),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        return PlanAdminResponse(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            description=plan.description,
            price=float(plan.price),
            duration_months=plan.duration_months,
            is_active=plan.is_active,
            sort_order=plan.sort_order,
        )

    async def update_plan(self, plan_id: UUID, data: dict[str, Any]) -> PlanAdminResponse:
        plan = await self.db.get(Plan, plan_id)
        if not plan:
            raise NotFoundError("Plan not found")

        if "code" in data:
            raise AppValidationError("Поле 'code' нельзя изменить после создания тарифа")

        for field, value in data.items():
            if value is not None and hasattr(plan, field):
                setattr(plan, field, value)

        await self.db.commit()
        await self.db.refresh(plan)

        return PlanAdminResponse(
            id=plan.id,
            code=plan.code,
            name=plan.name,
            description=plan.description,
            price=float(plan.price),
            duration_months=plan.duration_months,
            is_active=plan.is_active,
            sort_order=plan.sort_order,
        )

    async def delete_plan(self, plan_id: UUID) -> None:
        plan = await self.db.get(Plan, plan_id)
        if not plan:
            raise NotFoundError("Plan not found")

        active_subs = (
            await self.db.execute(
                select(func.count(Subscription.id)).where(
                    and_(
                        Subscription.plan_id == plan_id,
                        Subscription.status == "active",
                    )
                )
            )
        ).scalar() or 0

        if active_subs > 0:
            raise AppValidationError(
                f"Невозможно удалить тариф с {active_subs} активными подписками. "
                "Деактивируйте тариф вместо удаления."
            )

        plan.is_active = False
        await self.db.commit()
