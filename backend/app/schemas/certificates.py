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
