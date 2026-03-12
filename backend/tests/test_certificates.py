"""Tests for certificate endpoints."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificates import Certificate
from tests.conftest import _make_auth_headers
from tests.factories import (
    create_doctor_profile,
    create_event,
    create_plan,
    create_subscription,
)


async def _create_certificate(
    db: AsyncSession,
    *,
    user,
    profile,
    cert_type: str = "member",
    event=None,
) -> Certificate:
    cert = Certificate(
        user_id=user.id,
        doctor_profile_id=profile.id,
        certificate_type=cert_type,
        year=2025,
        certificate_number="MBR-2025-TEST",
        file_url="certificates/test.pdf",
        is_active=True,
        event_id=event.id if event else None,
    )
    db.add(cert)
    await db.flush()
    return cert


async def test_certificates_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/certificates")
    assert resp.status_code == 401


async def test_certificates_requires_active_profile(
    client: AsyncClient, db_session: AsyncSession, doctor_user
):
    await create_doctor_profile(
        db_session, user=doctor_user, status="pending_review"
    )
    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/certificates", headers=headers)
    assert resp.status_code == 403


@patch("app.services.certificate_service.file_service")
async def test_certificates_list_with_active_sub(
    mock_fs,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
):
    mock_fs.get_presigned_url = AsyncMock(return_value="https://s3.example.com/cert.pdf")
    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
    await _create_certificate(db_session, user=doctor_user, profile=profile)

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/certificates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["certificate_type"] == "member"


@patch("app.services.certificate_service.file_service")
async def test_member_cert_hidden_without_active_sub(
    mock_fs,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
):
    mock_fs.get_presigned_url = AsyncMock(return_value="https://s3.example.com/cert.pdf")
    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(
        db_session, user=doctor_user, plan=plan, status="expired"
    )
    await _create_certificate(db_session, user=doctor_user, profile=profile)

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/certificates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


@patch("app.services.certificate_service.file_service")
async def test_event_cert_visible_without_sub(
    mock_fs,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
    admin_user,
):
    mock_fs.get_presigned_url = AsyncMock(return_value="https://s3.example.com/cert.pdf")
    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(
        db_session, user=doctor_user, plan=plan, status="expired"
    )
    event = await create_event(db_session, created_by=admin_user)
    await _create_certificate(
        db_session, user=doctor_user, profile=profile, cert_type="event", event=event
    )

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/certificates", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["certificate_type"] == "event"


@patch("app.services.certificate_service.file_service")
async def test_download_certificate(
    mock_fs,
    client: AsyncClient,
    db_session: AsyncSession,
    doctor_user,
):
    mock_fs.get_presigned_url = AsyncMock(return_value="https://s3.example.com/cert.pdf")
    profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
    cert = await _create_certificate(db_session, user=doctor_user, profile=profile)

    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get(
        f"/api/v1/certificates/{cert.id}/download",
        headers=headers,
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "s3.example.com" in resp.headers["location"]


async def test_download_nonexistent_certificate(
    client: AsyncClient, db_session: AsyncSession, doctor_user
):
    await create_doctor_profile(db_session, user=doctor_user, status="active")
    plan = await create_plan(db_session)
    await create_subscription(db_session, user=doctor_user, plan=plan, status="active")

    headers = _make_auth_headers(doctor_user.id, "doctor")
    from uuid import uuid4

    resp = await client.get(
        f"/api/v1/certificates/{uuid4()}/download",
        headers=headers,
        follow_redirects=False,
    )
    assert resp.status_code == 404
