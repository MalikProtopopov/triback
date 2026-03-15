"""Doctor profile models: specializations, doctor_profiles, doctor_specializations,
doctor_documents, doctor_profile_changes, moderation_history, audit_log."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    ChangeStatus,
    DoctorStatus,
    DocumentType,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class Specialization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "specializations"
    __table_args__ = (
        Index("idx_specializations_active_sort", "is_active", "sort_order"),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    doctor_specializations: Mapped[list["DoctorSpecialization"]] = relationship(
        back_populates="specialization"
    )


class DoctorProfile(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        Index("idx_doctor_profiles_user_id", "user_id"),
        Index("idx_doctor_profiles_city", "city_id"),
        Index("idx_doctor_profiles_specialization", "specialization_id"),
        Index("idx_doctor_profiles_status", "status"),
        Index("idx_doctor_profiles_name", "last_name", "first_name"),
        Index(
            "idx_doctor_profiles_active",
            "last_name",
            "first_name",
            postgresql_where="status = 'active'",
        ),
        Index("idx_doctor_profiles_created", "created_at"),
        Index(
            "uix_doctor_profiles_slug",
            "slug",
            unique=True,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    passport_data: Mapped[str | None] = mapped_column(Text)
    city_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cities.id", ondelete="SET NULL")
    )
    specialization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("specializations.id", ondelete="SET NULL"),
        comment="Deprecated — use doctor_specializations M:N",
    )
    clinic_name: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[str | None] = mapped_column(String(255))
    academic_degree: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    public_email: Mapped[str | None] = mapped_column(String(255))
    public_phone: Mapped[str | None] = mapped_column(String(20))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        DoctorStatus, server_default="pending_review", nullable=False
    )
    has_medical_diploma: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    registration_address: Mapped[str | None] = mapped_column(Text)
    diploma_photo_url: Mapped[str | None] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    colleague_contacts: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="doctor_profile")  # type: ignore[name-defined]  # noqa: F821
    city: Mapped["City | None"] = relationship()  # type: ignore[name-defined]  # noqa: F821
    specialization: Mapped["Specialization | None"] = relationship()
    doctor_specializations: Mapped[list["DoctorSpecialization"]] = relationship(
        back_populates="doctor_profile", cascade="all, delete-orphan"
    )
    documents: Mapped[list["DoctorDocument"]] = relationship(
        back_populates="doctor_profile", cascade="all, delete-orphan"
    )
    profile_changes: Mapped[list["DoctorProfileChange"]] = relationship(
        back_populates="doctor_profile", cascade="all, delete-orphan"
    )


class DoctorSpecialization(Base):
    __tablename__ = "doctor_specializations"
    __table_args__ = (
        Index("idx_doctor_specializations_spec", "specialization_id"),
    )

    doctor_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    specialization_id: Mapped[UUID] = mapped_column(
        ForeignKey("specializations.id", ondelete="RESTRICT"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    doctor_profile: Mapped["DoctorProfile"] = relationship(
        back_populates="doctor_specializations"
    )
    specialization: Mapped["Specialization"] = relationship(
        back_populates="doctor_specializations"
    )


class DoctorDocument(Base, UUIDMixin):
    __tablename__ = "doctor_documents"
    __table_args__ = (
        Index("idx_doctor_docs_profile", "doctor_profile_id"),
        Index("idx_doctor_docs_type", "document_type"),
    )

    doctor_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(DocumentType, nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    doctor_profile: Mapped["DoctorProfile"] = relationship(back_populates="documents")


class DoctorProfileChange(Base, UUIDMixin):
    __tablename__ = "doctor_profile_changes"
    __table_args__ = (
        Index("idx_profile_changes_profile", "doctor_profile_id", "status"),
        Index(
            "uix_profile_changes_pending",
            "doctor_profile_id",
            unique=True,
            postgresql_where="status = 'pending'",
        ),
        Index(
            "idx_profile_changes_fields",
            "changed_fields",
            postgresql_using="gin",
        ),
    )

    doctor_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="CASCADE"), nullable=False
    )
    changes: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False
    )
    status: Mapped[str] = mapped_column(
        ChangeStatus, server_default="pending", nullable=False
    )
    moderation_comment: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    doctor_profile: Mapped["DoctorProfile"] = relationship(back_populates="profile_changes")


class ModerationHistory(Base, UUIDMixin):
    __tablename__ = "moderation_history"
    __table_args__ = (
        Index("idx_mod_history_entity", "entity_type", "entity_id"),
        Index("idx_mod_history_admin", "admin_id"),
        Index("idx_mod_history_created", "created_at"),
    )

    admin_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_created", "created_at"),
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
