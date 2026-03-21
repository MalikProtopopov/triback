"""Pydantic schemas for certificate settings admin endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class CertificateSettingsResponse(BaseModel):
    id: int
    president_full_name: str | None = None
    president_title: str | None = None
    organization_full_name: str | None = None
    organization_short_name: str | None = None
    certificate_member_text: str | None = None
    logo_url: str | None = None
    stamp_url: str | None = None
    signature_url: str | None = None
    background_url: str | None = None
    certificate_number_prefix: str = "TRICH"
    validity_text_template: str | None = None
    updated_at: datetime


class CertificateSettingsUpdateRequest(BaseModel):
    president_full_name: str | None = Field(None, max_length=255)
    president_title: str | None = Field(None, max_length=255)
    organization_full_name: str | None = None
    organization_short_name: str | None = Field(None, max_length=255)
    certificate_member_text: str | None = None
    certificate_number_prefix: str | None = Field(None, max_length=20)
    validity_text_template: str | None = Field(None, max_length=255)
