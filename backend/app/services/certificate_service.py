"""Backward-compatible entry point for certificate service and PDF helpers."""

from app.services.certificates import (
    CertificateService,
    _generate_member_pdf,
    _generate_qr_image,
    _wrap_text,
    generate_event_certificate_pdf,
)

__all__ = [
    "CertificateService",
    "_generate_member_pdf",
    "_generate_qr_image",
    "_wrap_text",
    "generate_event_certificate_pdf",
]
