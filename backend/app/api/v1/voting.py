"""Voting router — 2 public (doctor) + 4 admin endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.openapi import error_responses
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

@router.get(
    "/voting/active",
    response_model=ActiveSessionResponse | None,
    summary="Активное голосование",
    responses=error_responses(401, 403),
)
async def get_active_session(
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> dict | None:
    """Возвращает текущую активную сессию голосования (если есть) с кандидатами
    и информацией, голосовал ли пользователь.

    - **401** — не авторизован
    - **403** — роль не doctor
    """
    svc = VotingService(db)
    return await svc.get_active_session(payload["sub"])


@router.post(
    "/voting/{session_id}/vote",
    response_model=VoteResponse,
    status_code=201,
    summary="Отдать голос",
    responses=error_responses(401, 403, 404, 409),
)
async def cast_vote(
    session_id: UUID,
    body: VoteRequest,
    payload: dict[str, Any] = require_role("doctor"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Голосует за кандидата. Каждый врач может проголосовать один раз.

    - **401** — не авторизован
    - **403** — роль не doctor, нет активной подписки
    - **404** — сессия или кандидат не найдены
    - **409** — уже проголосовал, сессия не активна
    """
    svc = VotingService(db)
    voted_at = await svc.vote(payload["sub"], session_id, body.candidate_id)
    return {"message": "Vote recorded", "voted_at": voted_at.isoformat()}


# ── Admin ─────────────────────────────────────────────────────────

@router.get(
    "/admin/voting",
    response_model=PaginatedResponse[VotingSessionListItem],
    summary="Список голосований",
    responses=error_responses(401, 403),
)
async def list_voting_sessions(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(None, description="Фильтр по статусу: active, finished, draft"),
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    """Пагинированный список всех сессий голосования.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = VotingService(db)
    return await svc.list_sessions(pagination.limit, pagination.offset, status)


@router.post(
    "/admin/voting",
    response_model=VotingSessionCreatedResponse,
    status_code=201,
    summary="Создать голосование",
    responses=error_responses(401, 403, 422),
)
async def create_voting_session(
    body: VotingSessionCreateRequest,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Создаёт новую сессию голосования с кандидатами.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    """
    svc = VotingService(db)
    data = body.model_dump()
    data["candidates"] = [c.model_dump() for c in body.candidates]
    return await svc.create_session(payload["sub"], data)


@router.patch(
    "/admin/voting/{session_id}",
    response_model=VotingSessionCreatedResponse,
    summary="Обновить голосование",
    responses=error_responses(401, 403, 404, 422),
)
async def update_voting_session(
    session_id: UUID,
    body: VotingSessionUpdateRequest,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Обновляет параметры сессии (название, статус, даты).

    - **401** — не авторизован
    - **403** — роль не admin/manager
    - **404** — сессия не найдена
    """
    svc = VotingService(db)
    return await svc.update_session(session_id, body.model_dump(exclude_unset=True))


@router.get(
    "/admin/voting/{session_id}/results",
    response_model=VotingResultsResponse,
    summary="Результаты голосования",
    responses=error_responses(401, 403, 404),
)
async def get_voting_results(
    session_id: UUID,
    payload: dict[str, Any] = require_role("admin", "manager"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Детальные результаты голосования с подсчётом голосов по кандидатам.

    - **401** — не авторизован
    - **403** — роль не admin/manager
    - **404** — сессия не найдена
    """
    svc = VotingService(db)
    return await svc.get_results(session_id)
