"""Voting service — active session, vote, admin CRUD, results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppValidationError, ConflictError, NotFoundError
from app.core.pagination import PaginatedResponse
from app.models.profiles import DoctorProfile
from app.models.voting import Vote, VotingCandidate, VotingSession

logger = structlog.get_logger(__name__)

_VALID_STATUS_TRANSITIONS = {
    "draft": {"active", "cancelled"},
    "active": {"closed", "cancelled"},
}


class VotingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public ────────────────────────────────────────────────────

    async def get_active_session(self, user_id: str) -> dict | None:
        """Return the currently active voting session with candidates and has_voted flag."""
        now = datetime.now(UTC)

        result = await self.db.execute(
            select(VotingSession)
            .options(selectinload(VotingSession.candidates))
            .where(
                VotingSession.status == "active",
                VotingSession.starts_at <= now,
                VotingSession.ends_at > now,
            )
            .order_by(VotingSession.starts_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if not session:
            return None

        has_voted = (
            await self.db.execute(
                select(Vote.id).where(
                    Vote.voting_session_id == session.id,
                    Vote.user_id == user_id,
                )
            )
        ).scalar_one_or_none() is not None

        candidates: list[dict] = []
        for cand in sorted(session.candidates, key=lambda c: c.sort_order):
            profile = await self.db.get(DoctorProfile, cand.doctor_profile_id)
            full_name = ""
            photo_url = None
            if profile:
                full_name = f"{profile.last_name} {profile.first_name}"
                photo_url = profile.photo_url

            candidates.append({
                "id": str(cand.id),
                "full_name": full_name,
                "photo_url": photo_url,
                "description": cand.description,
            })

        return {
            "id": str(session.id),
            "title": session.title,
            "description": session.description,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "candidates": candidates,
            "has_voted": has_voted,
        }

    async def vote(
        self,
        user_id: str,
        session_id: UUID,
        candidate_id: UUID,
    ) -> datetime:
        """Cast a vote. Returns voted_at. Raises 409 on duplicate."""
        session = await self.db.get(VotingSession, session_id)
        if not session or session.status != "active":
            raise NotFoundError("Active voting session not found")

        now = datetime.now(UTC)
        if now < session.starts_at or now >= session.ends_at:
            raise AppValidationError("Voting period is over or not started yet")

        cand = await self.db.get(VotingCandidate, candidate_id)
        if not cand or cand.voting_session_id != session_id:
            raise NotFoundError("Candidate not found in this session")

        vote = Vote(
            voting_session_id=session_id,
            user_id=user_id,
            candidate_id=candidate_id,
        )
        self.db.add(vote)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("You have already voted in this session") from None

        await self.db.commit()
        return vote.voted_at

    # ── Admin CRUD ────────────────────────────────────────────────

    async def get_session(self, session_id: UUID) -> dict:
        result = await self.db.execute(
            select(VotingSession)
            .options(selectinload(VotingSession.candidates))
            .where(VotingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Voting session not found")

        candidates: list[dict] = []
        for cand in sorted(session.candidates, key=lambda c: c.sort_order):
            profile = await self.db.get(DoctorProfile, cand.doctor_profile_id)
            full_name = ""
            photo_url = None
            if profile:
                full_name = f"{profile.last_name} {profile.first_name}"
                photo_url = profile.photo_url
            candidates.append({
                "id": str(cand.id),
                "doctor_profile_id": str(cand.doctor_profile_id),
                "full_name": full_name,
                "photo_url": photo_url,
                "description": cand.description,
                "sort_order": cand.sort_order,
            })

        return {
            "id": str(session.id),
            "title": session.title,
            "description": session.description,
            "status": session.status,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "candidates": candidates,
            "created_at": session.created_at.isoformat(),
        }

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> PaginatedResponse:
        q = select(VotingSession)
        count_q = select(func.count(VotingSession.id))

        if status:
            q = q.where(VotingSession.status == status)
            count_q = count_q.where(VotingSession.status == status)

        total = (await self.db.execute(count_q)).scalar() or 0

        result = await self.db.execute(
            q.options(selectinload(VotingSession.candidates))
            .order_by(VotingSession.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = result.scalars().all()

        data = [
            {
                "id": str(s.id),
                "title": s.title,
                "description": s.description,
                "status": s.status,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "candidates_count": len(s.candidates),
            }
            for s in sessions
        ]

        return PaginatedResponse(data=data, total=total, limit=limit, offset=offset)

    async def create_session(
        self,
        admin_id: str,
        data: dict[str, Any],
    ) -> dict:
        session = VotingSession(
            title=data["title"],
            description=data.get("description"),
            starts_at=data["starts_at"],
            ends_at=data["ends_at"],
            status="draft",
            created_by=admin_id,
        )
        self.db.add(session)
        await self.db.flush()

        for idx, cand_data in enumerate(data["candidates"]):
            profile = await self.db.get(DoctorProfile, cand_data["doctor_profile_id"])
            if not profile:
                raise NotFoundError(
                    f"Doctor profile {cand_data['doctor_profile_id']} not found"
                )

            cand = VotingCandidate(
                voting_session_id=session.id,
                doctor_profile_id=cand_data["doctor_profile_id"],
                description=cand_data.get("description"),
                sort_order=idx,
            )
            self.db.add(cand)

        await self.db.commit()

        return {
            "id": str(session.id),
            "title": session.title,
            "status": session.status,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "candidates_count": len(data["candidates"]),
        }

    async def update_session(self, session_id: UUID, data: dict[str, Any]) -> dict:
        session = await self.db.get(VotingSession, session_id)
        if not session:
            raise NotFoundError("Voting session not found")

        new_status = data.get("status")
        if new_status:
            allowed = _VALID_STATUS_TRANSITIONS.get(session.status, set())
            if new_status not in allowed:
                raise AppValidationError(
                    f"Cannot transition from '{session.status}' to '{new_status}'"
                )
            session.status = new_status  # type: ignore[assignment]

        if "title" in data and data["title"] is not None:
            session.title = data["title"]
        if "ends_at" in data and data["ends_at"] is not None:
            session.ends_at = data["ends_at"]

        await self.db.commit()

        cands = (
            await self.db.execute(
                select(func.count(VotingCandidate.id)).where(
                    VotingCandidate.voting_session_id == session_id
                )
            )
        ).scalar() or 0

        return {
            "id": str(session.id),
            "title": session.title,
            "status": session.status,
            "starts_at": session.starts_at.isoformat(),
            "ends_at": session.ends_at.isoformat(),
            "candidates_count": cands,
        }

    async def get_results(self, session_id: UUID) -> dict:
        result = await self.db.execute(
            select(VotingSession)
            .options(selectinload(VotingSession.candidates))
            .where(VotingSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("Voting session not found")

        total_votes = (
            await self.db.execute(
                select(func.count(Vote.id)).where(Vote.voting_session_id == session_id)
            )
        ).scalar() or 0

        total_eligible = (
            await self.db.execute(
                select(func.count(DoctorProfile.id)).where(
                    DoctorProfile.status == "active"
                )
            )
        ).scalar() or 0

        results: list[dict] = []
        for cand in session.candidates:
            cand_votes = (
                await self.db.execute(
                    select(func.count(Vote.id)).where(Vote.candidate_id == cand.id)
                )
            ).scalar() or 0

            profile = await self.db.get(DoctorProfile, cand.doctor_profile_id)
            full_name = ""
            if profile:
                full_name = f"{profile.last_name} {profile.first_name}"

            pct = round((cand_votes / total_votes * 100), 2) if total_votes > 0 else 0.0

            results.append({
                "candidate": {"id": str(cand.id), "full_name": full_name},
                "votes_count": cand_votes,
                "percentage": pct,
            })

        results.sort(key=lambda r: r["votes_count"], reverse=True)

        return {
            "session": {
                "id": str(session.id),
                "title": session.title,
                "status": session.status,
                "total_votes": total_votes,
                "total_eligible_voters": total_eligible,
            },
            "results": results,
        }
