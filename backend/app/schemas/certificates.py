"""Pydantic schemas for certificate endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CertificateEventNested(BaseModel):
    id: UUID
    title: str


class CertificateListItem(BaseModel):
    id: UUID
    certificate_type: str
    year: int | None = None
    event: CertificateEventNested | None = None
    certificate_number: str
    is_active: bool
    generated_at: datetime
    download_url: str | None = None
    verify_url: str | None = None


class CertificateVerifyResponse(BaseModel):
    certificate_number: str
    doctor_full_name: str
    doctor_slug: str
    certificate_type: str
    year: int | None = None
    issued_at: str
    is_valid: bool
    invalid_reason: str | None = None
    organization_name: str | None = None
    president_full_name: str | None = None
    president_title: str | None = None
