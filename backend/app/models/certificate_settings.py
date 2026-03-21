"""Certificate settings model — singleton configuration for certificate generation."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class CertificateSettings(Base, TimestampMixin):
    __tablename__ = "certificate_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    president_full_name: Mapped[str | None] = mapped_column(String(255))
    president_title: Mapped[str | None] = mapped_column(String(255))
    organization_full_name: Mapped[str | None] = mapped_column(Text)
    organization_short_name: Mapped[str | None] = mapped_column(String(255))
    certificate_member_text: Mapped[str | None] = mapped_column(Text)
    logo_s3_key: Mapped[str | None] = mapped_column(String(500))
    stamp_s3_key: Mapped[str | None] = mapped_column(String(500))
    signature_s3_key: Mapped[str | None] = mapped_column(String(500))
    background_s3_key: Mapped[str | None] = mapped_column(String(500))
    certificate_number_prefix: Mapped[str] = mapped_column(
        String(20), server_default="TRICH", nullable=False
    )
    validity_text_template: Mapped[str | None] = mapped_column(String(255))
