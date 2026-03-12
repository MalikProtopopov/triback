"""Voting models: voting_sessions, voting_candidates, votes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, VotingSessionStatus


class VotingSession(Base, UUIDMixin):
    __tablename__ = "voting_sessions"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="chk_voting_dates"),
        Index("idx_voting_status", "status"),
        Index("idx_voting_dates", "starts_at", "ends_at"),
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        VotingSessionStatus, server_default="draft", nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    candidates: Mapped[list["VotingCandidate"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class VotingCandidate(Base, UUIDMixin):
    __tablename__ = "voting_candidates"
    __table_args__ = (
        UniqueConstraint(
            "voting_session_id", "doctor_profile_id",
            name="uix_candidates_session_profile",
        ),
        Index("idx_candidates_profile", "doctor_profile_id"),
    )

    voting_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voting_sessions.id", ondelete="CASCADE"), nullable=False
    )
    doctor_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    session: Mapped["VotingSession"] = relationship(back_populates="candidates")
    votes: Mapped[list["Vote"]] = relationship(back_populates="candidate")


class Vote(Base, UUIDMixin):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "voting_session_id", "user_id",
            name="uix_votes_session_user",
        ),
        Index("idx_votes_candidate", "candidate_id"),
    )

    voting_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voting_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("voting_candidates.id", ondelete="RESTRICT"), nullable=False
    )
    voted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    session: Mapped["VotingSession"] = relationship(back_populates="votes")
    candidate: Mapped["VotingCandidate"] = relationship(back_populates="votes")
