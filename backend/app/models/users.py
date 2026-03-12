"""User-related models: users, user_roles, telegram_bindings, notifications, notification_templates."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    NotificationChannel,
    NotificationStatus,
    SoftDeleteMixin,
    TimestampMixin,
    UserRole,
    UUIDMixin,
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(UserRole, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)

    user_roles: Mapped[list["UserRoleAssignment"]] = relationship(back_populates="role")


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_created_at", "created_at"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_roles: Mapped[list["UserRoleAssignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="user", uselist=False
    )
    telegram_binding: Mapped["TelegramBinding | None"] = relationship(
        back_populates="user", uselist=False
    )


class UserRoleAssignment(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("idx_user_roles_role_id", "role_id"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")


class TelegramBinding(Base, UUIDMixin):
    __tablename__ = "telegram_bindings"
    __table_args__ = (
        Index(
            "uix_tg_user_id",
            "tg_user_id",
            unique=True,
            postgresql_where="tg_user_id IS NOT NULL",
        ),
        Index(
            "uix_tg_auth_code",
            "auth_code",
            unique=True,
            postgresql_where="auth_code IS NOT NULL",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tg_user_id: Mapped[int | None] = mapped_column(BigInteger)
    tg_username: Mapped[str | None] = mapped_column(String(255))
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    auth_code: Mapped[str | None] = mapped_column(String(10))
    auth_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_in_channel: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="telegram_binding")


class Notification(Base, UUIDMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notif_user_status", "user_id", "status"),
        Index("idx_notif_template", "template_code"),
        Index("idx_notif_status_created", "status", "created_at"),
        Index("idx_notif_created", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_code: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(NotificationChannel, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        NotificationStatus, server_default="pending", nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(SmallInteger, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )


class NotificationTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_templates"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(NotificationChannel, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500))
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
