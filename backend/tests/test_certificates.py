"""Tests for certificate endpoints — client, admin, public verification, and PDF generation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate_settings import CertificateSettings
from app.models.certificates import Certificate
from tests.conftest import _make_auth_headers
from tests.factories import (
    create_doctor_profile,
    create_event,
    create_plan,
    create_subscription,
    create_user,
)


# ── helpers ────────────────────────────────────────────────────────

async def _create_cert_settings(db: AsyncSession, **overrides) -> CertificateSettings:
    defaults = {
        "id": 1,
        "president_full_name": "Гаджигороева Аида Гусейхановна",
        "president_title": "Президент д.м.н.",
        "organization_full_name": (
            'Межрегиональная общественная организация трихологов и специалистов '
            'в области исследования волос "Профессиональное общество трихологов"'
        ),
        "organization_short_name": "Профессиональное общество трихологов",
        "certificate_member_text": (
            "является действительным членом Межрегиональной общественной "
            'организации трихологов и специалистов в области исследования волос '
            '"Профессиональное общество трихологов"'
        ),
        "certificate_number_prefix": "TRICH",
        "validity_text_template": "Действителен с {year} г.",
    }
    defaults.update(overrides)
    settings = CertificateSettings(**defaults)
    db.add(settings)
    await db.flush()
    return settings


async def _create_certificate(
    db: AsyncSession,
    *,
    user,
    profile,
    cert_type: str = "member",
    year: int = 2026,
    cert_number: str | None = None,
    is_active: bool = True,
    event=None,
) -> Certificate:
    cert = Certificate(
        user_id=user.id,
        doctor_profile_id=profile.id,
        certificate_type=cert_type,
        year=year,
        certificate_number=cert_number or f"TRICH-{year}-{uuid4().hex[:6].upper()}",
        file_url="certificates/test.pdf",
        is_active=is_active,
        event_id=event.id if event else None,
    )
    db.add(cert)
    await db.flush()
    return cert


# ══════════════════════════════════════════════════════════════════
# Client endpoint tests
# ══════════════════════════════════════════════════════════════════


class TestClientCertificates:

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/certificates")
        assert resp.status_code == 401

    async def test_requires_active_profile(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        await create_doctor_profile(db_session, user=doctor_user, status="pending_review")
        headers = _make_auth_headers(doctor_user.id, "doctor")
        resp = await client.get("/api/v1/certificates", headers=headers)
        assert resp.status_code == 403

    @patch("app.services.certificate_service.file_service")
    async def test_list_with_active_sub(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
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
        assert "verify_url" in data[0]
        assert "/certificates/verify/" in data[0]["verify_url"]

    @patch("app.services.certificate_service.file_service")
    async def test_member_cert_hidden_without_active_sub(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan, status="expired")
        await _create_certificate(db_session, user=doctor_user, profile=profile)

        headers = _make_auth_headers(doctor_user.id, "doctor")
        resp = await client.get("/api/v1/certificates", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    @patch("app.services.certificate_service.file_service")
    async def test_event_cert_visible_without_sub(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, doctor_user, admin_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan, status="expired")
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
    async def test_download_active_certificate(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
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

    @patch("app.services.certificate_service.file_service")
    async def test_download_inactive_certificate_returns_403(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        cert = await _create_certificate(
            db_session, user=doctor_user, profile=profile, is_active=False
        )

        headers = _make_auth_headers(doctor_user.id, "doctor")
        resp = await client.get(
            f"/api/v1/certificates/{cert.id}/download",
            headers=headers,
            follow_redirects=False,
        )
        assert resp.status_code == 403

    async def test_download_nonexistent_certificate(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan)

        headers = _make_auth_headers(doctor_user.id, "doctor")
        resp = await client.get(
            f"/api/v1/certificates/{uuid4()}/download",
            headers=headers,
            follow_redirects=False,
        )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Public verification endpoint tests
# ══════════════════════════════════════════════════════════════════


class TestPublicVerification:

    async def test_verify_valid_certificate(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        await _create_cert_settings(db_session)
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
        cert = await _create_certificate(
            db_session, user=doctor_user, profile=profile, cert_number="TRICH-2026-000001"
        )

        resp = await client.get("/api/v1/public/certificates/verify/TRICH-2026-000001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["certificate_number"] == "TRICH-2026-000001"
        assert data["is_valid"] is True
        assert data["invalid_reason"] is None
        assert data["doctor_full_name"] != ""
        assert data["organization_name"] is not None
        assert data["president_full_name"] == "Гаджигороева Аида Гусейхановна"

    async def test_verify_invalid_expired_subscription(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        await _create_cert_settings(db_session)
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(
            db_session, user=doctor_user, plan=plan, status="active",
            starts_at=datetime.now(UTC) - timedelta(days=400),
            ends_at=datetime.now(UTC) - timedelta(days=1),
        )
        await _create_certificate(
            db_session, user=doctor_user, profile=profile, cert_number="TRICH-2026-000002"
        )

        resp = await client.get("/api/v1/public/certificates/verify/TRICH-2026-000002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert data["invalid_reason"] is not None

    async def test_verify_deactivated_certificate(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        await _create_cert_settings(db_session)
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
        await _create_certificate(
            db_session, user=doctor_user, profile=profile,
            cert_number="TRICH-2026-000003", is_active=False,
        )

        resp = await client.get("/api/v1/public/certificates/verify/TRICH-2026-000003")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False

    async def test_verify_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/public/certificates/verify/FAKE-0000-000000")
        assert resp.status_code == 404

    async def test_verify_no_settings_still_works(
        self, client: AsyncClient, db_session: AsyncSession, doctor_user
    ):
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(db_session, user=doctor_user, plan=plan, status="active")
        await _create_certificate(
            db_session, user=doctor_user, profile=profile, cert_number="TRICH-2026-000004"
        )

        resp = await client.get("/api/v1/public/certificates/verify/TRICH-2026-000004")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["organization_name"] is None


# ══════════════════════════════════════════════════════════════════
# Admin certificate settings tests
# ══════════════════════════════════════════════════════════════════


class TestAdminCertificateSettings:

    async def test_get_settings_requires_admin(
        self, client: AsyncClient, auth_headers_accountant
    ):
        resp = await client.get(
            "/api/v1/admin/certificate-settings", headers=auth_headers_accountant
        )
        assert resp.status_code == 403

    async def test_get_settings_creates_default(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        resp = await client.get(
            "/api/v1/admin/certificate-settings", headers=auth_headers_admin
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["certificate_number_prefix"] == "TRICH"

    async def test_get_existing_settings(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        await _create_cert_settings(db_session)
        resp = await client.get(
            "/api/v1/admin/certificate-settings", headers=auth_headers_admin
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["president_full_name"] == "Гаджигороева Аида Гусейхановна"

    async def test_update_settings(
        self, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        await _create_cert_settings(db_session)
        resp = await client.patch(
            "/api/v1/admin/certificate-settings",
            json={"president_full_name": "Новый Президент", "president_title": "к.м.н."},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["president_full_name"] == "Новый Президент"
        assert data["president_title"] == "к.м.н."
        assert data["organization_full_name"] is not None

    @patch("app.services.certificate_settings_service.file_service")
    async def test_upload_logo(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        mock_fs.upload_file = AsyncMock(return_value="certificate-assets/logo.png")
        mock_fs.build_media_url = MagicMock(return_value="https://s3/certificate-assets/logo.png")
        mock_fs.delete_file = AsyncMock()
        await _create_cert_settings(db_session)

        import io
        from PIL import Image

        img_buf = io.BytesIO()
        Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(img_buf, format="PNG")
        img_buf.seek(0)

        resp = await client.post(
            "/api/v1/admin/certificate-settings/logo",
            files={"file": ("logo.png", img_buf, "image/png")},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        mock_fs.upload_file.assert_called_once()

    @patch("app.services.certificate_settings_service.file_service")
    async def test_upload_stamp(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        mock_fs.upload_file = AsyncMock(return_value="certificate-assets/stamp.png")
        mock_fs.build_media_url = MagicMock(return_value="https://s3/certificate-assets/stamp.png")
        mock_fs.delete_file = AsyncMock()
        await _create_cert_settings(db_session)

        import io
        from PIL import Image

        img_buf = io.BytesIO()
        Image.new("RGBA", (100, 100), (0, 0, 255, 128)).save(img_buf, format="PNG")
        img_buf.seek(0)

        resp = await client.post(
            "/api/v1/admin/certificate-settings/stamp",
            files={"file": ("stamp.png", img_buf, "image/png")},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        mock_fs.upload_file.assert_called_once()

    @patch("app.services.certificate_settings_service.file_service")
    async def test_upload_signature(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession, auth_headers_admin
    ):
        mock_fs.upload_file = AsyncMock(return_value="certificate-assets/sig.png")
        mock_fs.build_media_url = MagicMock(return_value="https://s3/certificate-assets/sig.png")
        mock_fs.delete_file = AsyncMock()
        await _create_cert_settings(db_session)

        import io
        from PIL import Image

        img_buf = io.BytesIO()
        Image.new("RGBA", (200, 50), (0, 0, 0, 200)).save(img_buf, format="PNG")
        img_buf.seek(0)

        resp = await client.post(
            "/api/v1/admin/certificate-settings/signature",
            files={"file": ("sig.png", img_buf, "image/png")},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        mock_fs.upload_file.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# Admin certificate management tests
# ══════════════════════════════════════════════════════════════════


class TestAdminCertificateManagement:

    @patch("app.services.certificate_service.file_service")
    async def test_list_doctor_certificates(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession,
        admin_user, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        await _create_certificate(db_session, user=doctor_user, profile=profile)

        headers = _make_auth_headers(admin_user.id, "admin")
        resp = await client.get(
            f"/api/v1/admin/doctors/{profile.id}/certificates",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["certificate_type"] == "member"

    async def test_list_doctor_certs_nonexistent_doctor(
        self, client: AsyncClient, auth_headers_admin
    ):
        resp = await client.get(
            f"/api/v1/admin/doctors/{uuid4()}/certificates",
            headers=auth_headers_admin,
        )
        assert resp.status_code == 404

    @patch("app.api.v1.certificates_admin.file_service")
    async def test_toggle_certificate_active(
        self, mock_fs, client: AsyncClient, db_session: AsyncSession,
        admin_user, doctor_user
    ):
        mock_fs.get_presigned_url = AsyncMock(return_value="https://s3/cert.pdf")
        mock_fs.settings = MagicMock()
        mock_fs.settings.S3_BUCKET = "test"
        profile = await create_doctor_profile(db_session, user=doctor_user, status="active")
        cert = await _create_certificate(db_session, user=doctor_user, profile=profile)

        headers = _make_auth_headers(admin_user.id, "admin")
        resp = await client.patch(
            f"/api/v1/admin/certificates/{cert.id}",
            json={"is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_toggle_nonexistent_cert(self, client: AsyncClient, auth_headers_admin):
        resp = await client.patch(
            f"/api/v1/admin/certificates/{uuid4()}",
            json={"is_active": False},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 404

    async def test_admin_endpoints_require_admin_role(
        self, client: AsyncClient, auth_headers_accountant
    ):
        resp = await client.get(
            "/api/v1/admin/certificate-settings", headers=auth_headers_accountant
        )
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════════
# PDF generation unit tests
# ══════════════════════════════════════════════════════════════════


class TestPDFGeneration:

    def test_generate_member_pdf_produces_valid_pdf(self):
        from app.services.certificate_service import _generate_member_pdf

        pdf_bytes = _generate_member_pdf(
            full_name="Маркова Юлия Алексеевна",
            cert_number="TRICH-2026-000001",
            year=2026,
            body_text=(
                "является действительным членом Межрегиональной общественной "
                'организации трихологов и специалистов в области исследования волос '
                '"Профессиональное общество трихологов"'
            ),
            validity_text="Действителен с 2026 г.",
            president_name="Гаджигороева Аида Гусейхановна",
            president_title="Президент д.м.н.",
            qr_url="https://trichology.ru/certificates/verify/TRICH-2026-000001",
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_generate_member_pdf_with_images(self):
        import io
        from PIL import Image
        from app.services.certificate_service import _generate_member_pdf

        def _make_png(w: int, h: int) -> bytes:
            buf = io.BytesIO()
            Image.new("RGBA", (w, h), (100, 100, 100, 128)).save(buf, format="PNG")
            return buf.getvalue()

        pdf_bytes = _generate_member_pdf(
            full_name="Иванов Иван Иванович",
            cert_number="TRICH-2026-000002",
            year=2026,
            body_text="является действительным членом ассоциации",
            validity_text="Действителен с 2026 г.",
            president_name="Президент Тестовый",
            president_title="Президент",
            qr_url="https://trichology.ru/certificates/verify/TRICH-2026-000002",
            logo_bytes=_make_png(200, 200),
            stamp_bytes=_make_png(300, 300),
            signature_bytes=_make_png(400, 100),
            background_bytes=_make_png(800, 500),
        )

        assert len(pdf_bytes) > 1000
        assert pdf_bytes[:5] == b"%PDF-"

    def test_generate_event_pdf(self):
        from app.services.certificate_service import generate_event_certificate_pdf

        pdf_bytes = generate_event_certificate_pdf(
            full_name="Петрова Мария Сергеевна",
            event_title="Конференция трихологов 2026",
            event_date="15 марта 2026",
            cert_number="EVT-2026-000001",
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_qr_code_generation(self):
        from app.services.certificate_service import _generate_qr_image

        qr = _generate_qr_image("https://trichology.ru/certificates/verify/TEST")
        assert qr is not None

    def test_wrap_text(self):
        from app.services.certificate_service import _wrap_text

        lines = _wrap_text(
            "Это длинный текст который должен быть разбит на несколько строк",
            100,
            "Helvetica",
            12,
        )
        assert len(lines) > 1

    def test_wrap_text_short(self):
        from app.services.certificate_service import _wrap_text

        lines = _wrap_text("Короткий", 1000, "Helvetica", 12)
        assert len(lines) == 1
        assert lines[0] == "Короткий"


# ══════════════════════════════════════════════════════════════════
# Certificate service unit tests (with mocked S3)
# ══════════════════════════════════════════════════════════════════


class TestCertificateService:

    @patch("app.services.certificate_service.file_service")
    async def test_generate_membership_certificate(
        self, mock_fs, db_session: AsyncSession, doctor_user
    ):
        mock_s3_client = AsyncMock()
        mock_s3_session = MagicMock()
        mock_s3_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fs._get_s3_session.return_value = mock_s3_session
        mock_fs._s3_client_kwargs.return_value = {"service_name": "s3"}
        mock_fs.settings = MagicMock()
        mock_fs.settings.S3_BUCKET = "test-bucket"

        await _create_cert_settings(db_session)
        profile = await create_doctor_profile(
            db_session, user=doctor_user, status="active"
        )

        from app.services.certificate_service import CertificateService

        svc = CertificateService(db_session)
        cert = await svc.generate_membership_certificate(profile.id, 2026)

        assert cert is not None
        assert cert.certificate_number.startswith("TRICH-2026-")
        assert cert.is_active is True
        assert cert.certificate_type == "member"
        assert cert.year == 2026
        mock_s3_client.put_object.assert_called_once()

    @patch("app.services.certificate_service.file_service")
    async def test_regenerate_existing_certificate(
        self, mock_fs, db_session: AsyncSession, doctor_user
    ):
        mock_s3_client = AsyncMock()
        mock_s3_session = MagicMock()
        mock_s3_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fs._get_s3_session.return_value = mock_s3_session
        mock_fs._s3_client_kwargs.return_value = {"service_name": "s3"}
        mock_fs.settings = MagicMock()
        mock_fs.settings.S3_BUCKET = "test-bucket"
        mock_fs.delete_file = AsyncMock()

        await _create_cert_settings(db_session)
        profile = await create_doctor_profile(
            db_session, user=doctor_user, status="active"
        )
        existing = await _create_certificate(
            db_session, user=doctor_user, profile=profile,
            cert_number="TRICH-2026-000001", year=2026,
        )

        from app.services.certificate_service import CertificateService

        svc = CertificateService(db_session)
        cert = await svc.generate_membership_certificate(profile.id, 2026)

        assert cert.id == existing.id
        assert cert.certificate_number == "TRICH-2026-000001"
        assert cert.is_active is True

    async def test_generate_certificate_nonexistent_profile(
        self, db_session: AsyncSession
    ):
        from app.core.exceptions import NotFoundError
        from app.services.certificate_service import CertificateService

        svc = CertificateService(db_session)
        with pytest.raises(NotFoundError):
            await svc.generate_membership_certificate(uuid4(), 2026)

    @patch("app.services.certificate_service.file_service")
    async def test_certificate_number_sequential(
        self, mock_fs, db_session: AsyncSession
    ):
        mock_s3_client = AsyncMock()
        mock_s3_session = MagicMock()
        mock_s3_session.client.return_value.__aenter__ = AsyncMock(return_value=mock_s3_client)
        mock_s3_session.client.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_fs._get_s3_session.return_value = mock_s3_session
        mock_fs._s3_client_kwargs.return_value = {"service_name": "s3"}
        mock_fs.settings = MagicMock()
        mock_fs.settings.S3_BUCKET = "test-bucket"

        await _create_cert_settings(db_session)

        user1 = await create_user(db_session)
        user2 = await create_user(db_session)
        p1 = await create_doctor_profile(db_session, user=user1, status="active")
        p2 = await create_doctor_profile(db_session, user=user2, status="active")

        from app.services.certificate_service import CertificateService

        svc = CertificateService(db_session)
        c1 = await svc.generate_membership_certificate(p1.id, 2026)
        c2 = await svc.generate_membership_certificate(p2.id, 2026)

        assert c1.certificate_number == "TRICH-2026-000001"
        assert c2.certificate_number == "TRICH-2026-000002"


# ══════════════════════════════════════════════════════════════════
# Scheduler tests
# ══════════════════════════════════════════════════════════════════


class TestCertificateScheduler:

    async def test_deactivate_expired_certificates_function(
        self, db_session: AsyncSession
    ):
        from sqlalchemy import and_, or_, select
        from app.models.certificates import Certificate
        from app.models.subscriptions import Subscription

        user = await create_user(db_session)
        profile = await create_doctor_profile(db_session, user=user, status="active")
        plan = await create_plan(db_session)
        await create_subscription(
            db_session, user=user, plan=plan, status="expired",
            starts_at=datetime.now(UTC) - timedelta(days=400),
            ends_at=datetime.now(UTC) - timedelta(days=1),
        )
        cert = await _create_certificate(
            db_session, user=user, profile=profile, is_active=True
        )

        now = datetime.now(UTC)
        active_sub_user_ids = (
            select(Subscription.user_id)
            .where(
                and_(
                    Subscription.status == "active",
                    or_(
                        Subscription.ends_at.is_(None),
                        Subscription.ends_at > now,
                    ),
                )
            )
        )
        result = await db_session.execute(
            select(Certificate).where(
                and_(
                    Certificate.certificate_type == "member",
                    Certificate.is_active.is_(True),
                    Certificate.user_id.notin_(active_sub_user_ids),
                )
            )
        )
        stale = result.scalars().all()
        assert len(stale) == 1
        assert stale[0].id == cert.id
