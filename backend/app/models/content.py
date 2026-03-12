"""Content models: articles, article_themes, article_theme_assignments,
organization_documents, content_blocks, pages_seo."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    ArticleStatus,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class Article(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "articles"
    __table_args__ = (
        Index("idx_articles_status_published", "status", "published_at"),
        Index("idx_articles_author", "author_id"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        ArticleStatus, server_default="draft", nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(Text)

    theme_assignments: Mapped[list["ArticleThemeAssignment"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleTheme(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "article_themes"
    __table_args__ = (
        Index("idx_article_themes_active", "is_active"),
    )

    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    theme_assignments: Mapped[list["ArticleThemeAssignment"]] = relationship(
        back_populates="theme", cascade="all, delete-orphan"
    )


class ArticleThemeAssignment(Base, UUIDMixin):
    __tablename__ = "article_theme_assignments"
    __table_args__ = (
        UniqueConstraint("article_id", "theme_id", name="uix_ata_article_theme"),
        Index("idx_ata_article", "article_id"),
        Index("idx_ata_theme", "theme_id"),
    )

    article_id: Mapped[UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    theme_id: Mapped[UUID] = mapped_column(
        ForeignKey("article_themes.id", ondelete="CASCADE"), nullable=False
    )

    article: Mapped["Article"] = relationship(back_populates="theme_assignments")
    theme: Mapped["ArticleTheme"] = relationship(back_populates="theme_assignments")


class OrganizationDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organization_documents"
    __table_args__ = (
        Index("idx_org_docs_active_sort", "is_active", "sort_order"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class ContentBlock(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "content_blocks"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('article', 'event', 'doctor_profile', 'organization_document')",
            name="chk_cb_entity_type",
        ),
        CheckConstraint(
            "block_type IN ('text', 'image', 'video', 'gallery', 'link')",
            name="chk_cb_block_type",
        ),
        CheckConstraint(
            "device_type IN ('mobile', 'desktop', 'both')",
            name="chk_cb_device_type",
        ),
        Index("idx_content_blocks_entity", "entity_type", "entity_id", "locale"),
        Index("idx_content_blocks_entity_sorted", "entity_type", "entity_id", "locale", "sort_order"),
    )

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    locale: Mapped[str] = mapped_column(String(5), server_default="ru", nullable=False)
    block_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str | None] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    link_url: Mapped[str | None] = mapped_column(String(500))
    link_label: Mapped[str | None] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column(String(10), server_default="both", nullable=False)
    block_metadata: Mapped[dict | None] = mapped_column(JSONB)


class PageSeo(Base, UUIDMixin):
    __tablename__ = "pages_seo"

    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    og_title: Mapped[str | None] = mapped_column(String(255))
    og_description: Mapped[str | None] = mapped_column(Text)
    og_image_url: Mapped[str | None] = mapped_column(String(500))
    og_url: Mapped[str | None] = mapped_column(String(500))
    og_type: Mapped[str | None] = mapped_column(String(50))
    twitter_card: Mapped[str | None] = mapped_column(
        String(50), server_default="summary_large_image"
    )
    canonical_url: Mapped[str | None] = mapped_column(String(500))
    custom_meta: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
