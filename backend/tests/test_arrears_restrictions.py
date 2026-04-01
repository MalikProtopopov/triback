"""Tests for arrears restriction logic across all affected areas.

When the ``arrears_block_membership_features`` toggle is enabled, users with
open arrears should be treated as non-members: hidden from public catalog,
certificates invalidated, event pricing = regular price.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arrears import MembershipArrear
from app.models.certificate_settings import CertificateSettings
from app.models.certificates import Certificate
from app.models.site import SiteSetting
from app.services.doctor_catalog_service import DoctorCatalogService
from app.services.event_registration.member_queries import is_association_member
from tests.factories import (
    create_doctor_profile,
    create_plan,
    create_subscription,
    create_user,
)


# ── helpers ──────────────────────────────────────────────────────


async def _enable_arrears_block(db: AsyncSession) -> None:
    db.add(SiteSetting(key="arrears_block_membership_features", value={"enabled": True}))
    await db.flush()


async def _create_open_arrear(db: AsyncSession, user_id, year: int = 2025) -> MembershipArrear:
    ar = MembershipArrear(
        user_id=user_id,
        year=year,
        amount=Decimal("100.00"),
        description="test arrear",
        status="open",
        source="manual",
    )
    db.add(ar)
    await db.flush()
    return ar


async def _create_cert(db: AsyncSession, *, user, profile, cert_number: str | None = None) -> Certificate:
    cert = Certificate(
        user_id=user.id,
        doctor_profile_id=profile.id,
        certificate_type="member",
        year=2026,
        certificate_number=cert_number or f"TRICH-2026-{uuid4().hex[:6].upper()}",
        file_url="certificates/test.pdf",
        is_active=True,
    )
    db.add(cert)
    await db.flush()
    return cert


async def _create_cert_settings(db: AsyncSession) -> CertificateSettings:
    settings = CertificateSettings(
        id=1,
        president_full_name="Тест Президент",
        president_title="Президент",
        organization_full_name="Тестовая организация",
        organization_short_name="ТО",
        certificate_member_text="является членом",
        certificate_number_prefix="TRICH",
        validity_text_template="Действителен с {year} г.",
    )
    db.add(settings)
    await db.flush()
    return settings


# ══════════════════════════════════════════════════════════════════
# 1. Public catalog: doctor hidden when arrears_block + open arrear
# ══════════════════════════════════════════════════════════════════


class TestCatalogArrearsBlock:

    @pytest.mark.anyio
    async def test_doctor_visible_without_arrears_block(self, db_session: AsyncSession):
        """Doctor with arrears is visible when toggle is OFF."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_open_arrear(db_session, user.id)

        svc = DoctorCatalogService(db_session)
        result = await svc.list_doctors(limit=20, offset=0)
        assert result["total"] == 1

    @pytest.mark.anyio
    async def test_doctor_hidden_with_arrears_block(self, db_session: AsyncSession):
        """Doctor with arrears is hidden when toggle is ON."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_open_arrear(db_session, user.id)
        await _enable_arrears_block(db_session)

        svc = DoctorCatalogService(db_session)
        result = await svc.list_doctors(limit=20, offset=0)
        assert result["total"] == 0

    @pytest.mark.anyio
    async def test_doctor_visible_with_arrears_block_no_debt(self, db_session: AsyncSession):
        """Doctor without arrears is visible even when toggle is ON."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _enable_arrears_block(db_session)

        svc = DoctorCatalogService(db_session)
        result = await svc.list_doctors(limit=20, offset=0)
        assert result["total"] == 1

    @pytest.mark.anyio
    async def test_doctor_detail_404_when_blocked(self, db_session: AsyncSession):
        """get_doctor raises NotFoundError when arrears block hides the doctor."""
        from app.core.exceptions import NotFoundError

        user = await create_user(db_session)
        profile = await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_open_arrear(db_session, user.id)
        await _enable_arrears_block(db_session)

        svc = DoctorCatalogService(db_session)
        with pytest.raises(NotFoundError):
            await svc.get_doctor(profile.slug)


# ══════════════════════════════════════════════════════════════════
# 2. Certificate verification: invalid when arrears_block + debt
# ══════════════════════════════════════════════════════════════════


class TestCertificateArrearsBlock:

    @pytest.mark.anyio
    async def test_cert_valid_no_arrears(self, client: AsyncClient, db_session: AsyncSession):
        """Certificate is valid for member without arrears."""
        await _create_cert_settings(db_session)
        user = await create_user(db_session)
        profile = await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        cert = await _create_cert(db_session, user=user, profile=profile, cert_number="TRICH-2026-AR0001")
        await _enable_arrears_block(db_session)

        resp = await client.get(f"/api/v1/public/certificates/verify/{cert.certificate_number}")
        assert resp.status_code == 200
        assert resp.json()["is_valid"] is True

    @pytest.mark.anyio
    async def test_cert_invalid_with_arrears_block(self, client: AsyncClient, db_session: AsyncSession):
        """Certificate becomes invalid when toggle ON and user has open arrears."""
        await _create_cert_settings(db_session)
        user = await create_user(db_session)
        profile = await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        cert = await _create_cert(db_session, user=user, profile=profile, cert_number="TRICH-2026-AR0002")
        await _create_open_arrear(db_session, user.id)
        await _enable_arrears_block(db_session)

        resp = await client.get(f"/api/v1/public/certificates/verify/{cert.certificate_number}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert data["invalid_reason"] is not None

    @pytest.mark.anyio
    async def test_cert_valid_with_arrears_toggle_off(self, client: AsyncClient, db_session: AsyncSession):
        """Certificate stays valid when toggle is OFF even with arrears."""
        await _create_cert_settings(db_session)
        user = await create_user(db_session)
        profile = await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_cert(db_session, user=user, profile=profile, cert_number="TRICH-2026-AR0003")
        await _create_open_arrear(db_session, user.id)
        # toggle is OFF (no SiteSetting row)

        resp = await client.get("/api/v1/public/certificates/verify/TRICH-2026-AR0003")
        assert resp.status_code == 200
        assert resp.json()["is_valid"] is True


# ══════════════════════════════════════════════════════════════════
# 3. Event pricing: regular price when arrears_block + debt
# ══════════════════════════════════════════════════════════════════


class TestMemberPricingArrearsBlock:

    @pytest.mark.anyio
    async def test_is_member_true_without_arrears(self, db_session: AsyncSession):
        """Active doctor + active sub + no debt = member."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _enable_arrears_block(db_session)

        assert await is_association_member(db_session, user.id) is True

    @pytest.mark.anyio
    async def test_is_member_false_with_arrears_block(self, db_session: AsyncSession):
        """Active doctor + active sub + open arrear + toggle ON = NOT member."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_open_arrear(db_session, user.id)
        await _enable_arrears_block(db_session)

        assert await is_association_member(db_session, user.id) is False

    @pytest.mark.anyio
    async def test_is_member_true_with_arrears_toggle_off(self, db_session: AsyncSession):
        """Active doctor + active sub + open arrear + toggle OFF = still member."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=user, plan=plan, status="active")
        await _create_open_arrear(db_session, user.id)
        # toggle OFF

        assert await is_association_member(db_session, user.id) is True

    @pytest.mark.anyio
    async def test_is_member_false_no_subscription(self, db_session: AsyncSession):
        """Doctor without subscription is not a member regardless of toggle."""
        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")

        assert await is_association_member(db_session, user.id) is False


# ══════════════════════════════════════════════════════════════════
# 4. Subscription status: arrears_block_active flag
# ══════════════════════════════════════════════════════════════════


class TestSubscriptionStatusArrearsBlock:

    @pytest.mark.anyio
    async def test_arrears_block_active_true(self, db_session: AsyncSession):
        """arrears_block_active=True when toggle ON + open arrears."""
        from app.services.subscriptions.subscription_status import SubscriptionUserStatusService

        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        await _create_open_arrear(db_session, user.id)
        await _enable_arrears_block(db_session)

        status = await SubscriptionUserStatusService(db_session).get_status(user.id)
        assert status.arrears_block_active is True
        assert len(status.open_arrears) == 1
        assert status.arrears_total == 100.0

    @pytest.mark.anyio
    async def test_arrears_block_active_false_toggle_off(self, db_session: AsyncSession):
        """arrears_block_active=False when toggle OFF even with open arrears."""
        from app.services.subscriptions.subscription_status import SubscriptionUserStatusService

        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        await _create_open_arrear(db_session, user.id)
        # toggle OFF

        status = await SubscriptionUserStatusService(db_session).get_status(user.id)
        assert status.arrears_block_active is False
        assert len(status.open_arrears) == 1

    @pytest.mark.anyio
    async def test_arrears_block_active_false_no_debt(self, db_session: AsyncSession):
        """arrears_block_active=False when toggle ON but no arrears."""
        from app.services.subscriptions.subscription_status import SubscriptionUserStatusService

        user = await create_user(db_session)
        await create_doctor_profile(db_session, user=user, status="active")
        await _enable_arrears_block(db_session)

        status = await SubscriptionUserStatusService(db_session).get_status(user.id)
        assert status.arrears_block_active is False
        assert status.arrears_total == 0.0
