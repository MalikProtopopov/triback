"""Voting router — 2 public (doctor) + 4 admin endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import require_role
from app.schemas.voting import (
    ActiveSessionResponse,
    VoteRequest,
    VoteResponse,
    VotingResultsResponse,
    VotingSessionCreatedResponse,
    VotingSessionCreateRequest,
    VotingSessionListItem,
    VotingSessionUpdateRequest,
)
from app.services.voting_service import VotingService

router = APIRouter()


# ── Public (Doctor) ───────────────────────────────────────────────

@router.get("/voting/active", response_model=ActiveSessionResponse | None)
async def get_active_session(
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> dict | None:
    svc = VotingService(db)
    return await svc.get_active_session(payload["sub"])


@router.post("/voting/{session_id}/vote", response_model=VoteResponse, status_code=201)
async def cast_vote(
    session_id: UUID,
    body: VoteRequest,
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VotingService(db)
    voted_at = await svc.vote(payload["sub"], session_id, body.candidate_id)
    return {"message": "Vote recorded", "voted_at": voted_at.isoformat()}


# ── Admin ─────────────────────────────────────────────────────────

@router.get("/admin/voting", response_model=PaginatedResponse[VotingSessionListItem])
async def list_voting_sessions(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(None),
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    svc = VotingService(db)
    return await svc.list_sessions(pagination.limit, pagination.offset, status)


@router.post("/admin/voting", response_model=VotingSessionCreatedResponse, status_code=201)
async def create_voting_session(
    body: VotingSessionCreateRequest,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VotingService(db)
    data = body.model_dump()
    data["candidates"] = [c.model_dump() for c in body.candidates]
    return await svc.create_session(payload["sub"], data)


@router.patch("/admin/voting/{session_id}", response_model=VotingSessionCreatedResponse)
async def update_voting_session(
    session_id: UUID,
    body: VotingSessionUpdateRequest,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VotingService(db)
    return await svc.update_session(session_id, body.model_dump(exclude_unset=True))


@router.get("/admin/voting/{session_id}/results", response_model=VotingResultsResponse)
async def get_voting_results(
    session_id: UUID,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    svc = VotingService(db)
    return await svc.get_results(session_id)
