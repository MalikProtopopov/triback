"""Tests for voting endpoints."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.voting import VotingCandidate, VotingSession
from tests.conftest import _make_auth_headers
from tests.factories import create_doctor_profile, create_user


async def _create_voting_session(
    db: AsyncSession,
    *,
    admin_id: UUID,
    profile_ids: list[UUID],
    status: str = "active",
) -> tuple[VotingSession, list[VotingCandidate]]:
    now = datetime.now(UTC)
    session = VotingSession(
        title="Test Vote",
        description="Test",
        status=status,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=23),
        created_by=admin_id,
    )
    db.add(session)
    await db.flush()

    candidates = []
    for i, pid in enumerate(profile_ids):
        cand = VotingCandidate(
            voting_session_id=session.id,
            doctor_profile_id=pid,
            sort_order=i,
        )
        db.add(cand)
        candidates.append(cand)
    await db.flush()
    return session, candidates


async def test_voting_active_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/voting/active")
    assert resp.status_code == 401


async def test_voting_active_returns_session(
    client: AsyncClient, db_session: AsyncSession, doctor_user, admin_user
):
    profile = await create_doctor_profile(db_session, user=doctor_user)
    session, _ = await _create_voting_session(
        db_session, admin_id=admin_user.id, profile_ids=[profile.id]
    )

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.get("/api/v1/voting/active", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(session.id)
    assert len(data["candidates"]) == 1
    assert data["has_voted"] is False


async def test_voting_cast_vote(
    client: AsyncClient, db_session: AsyncSession, doctor_user, admin_user
):
    profile = await create_doctor_profile(db_session, user=doctor_user)
    session, candidates = await _create_voting_session(
        db_session, admin_id=admin_user.id, profile_ids=[profile.id]
    )
    candidate = candidates[0]

    headers = _make_auth_headers(doctor_user.id, "doctor")
    resp = await client.post(
        f"/api/v1/voting/{session.id}/vote",
        json={"candidate_id": str(candidate.id)},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == "Vote recorded"


async def test_voting_double_vote_rejected(
    client: AsyncClient, db_session: AsyncSession, doctor_user, admin_user
):
    profile = await create_doctor_profile(db_session, user=doctor_user)
    session, candidates = await _create_voting_session(
        db_session, admin_id=admin_user.id, profile_ids=[profile.id]
    )
    candidate = candidates[0]

    headers = _make_auth_headers(doctor_user.id, "doctor")
    await client.post(
        f"/api/v1/voting/{session.id}/vote",
        json={"candidate_id": str(candidate.id)},
        headers=headers,
    )
    resp2 = await client.post(
        f"/api/v1/voting/{session.id}/vote",
        json={"candidate_id": str(candidate.id)},
        headers=headers,
    )
    assert resp2.status_code == 409


async def test_admin_list_voting_sessions(
    client: AsyncClient, db_session: AsyncSession, admin_user, auth_headers_admin
):
    dp = await create_doctor_profile(db_session, user=await create_user(db_session))
    await _create_voting_session(
        db_session, admin_id=admin_user.id, profile_ids=[dp.id],
    )

    resp = await client.get("/api/v1/admin/voting", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


async def test_admin_create_voting_session(
    client: AsyncClient, db_session: AsyncSession, admin_user, auth_headers_admin
):
    dp = await create_doctor_profile(db_session, user=await create_user(db_session))
    now = datetime.now(UTC)
    resp = await client.post(
        "/api/v1/admin/voting",
        json={
            "title": "New Vote",
            "description": "Desc",
            "starts_at": (now + timedelta(hours=1)).isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
            "candidates": [
                {"doctor_profile_id": str(dp.id), "sort_order": 0}
            ],
        },
        headers=auth_headers_admin,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Vote"


async def test_admin_get_voting_results(
    client: AsyncClient, db_session: AsyncSession, admin_user, auth_headers_admin
):
    dp = await create_doctor_profile(db_session, user=await create_user(db_session))
    session, _ = await _create_voting_session(
        db_session, admin_id=admin_user.id, profile_ids=[dp.id], status="closed"
    )

    resp = await client.get(
        f"/api/v1/admin/voting/{session.id}/results",
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
