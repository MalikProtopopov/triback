"""Pydantic schemas for voting endpoints (public + admin)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# ── Input ─────────────────────────────────────────────────────────

class CandidateInput(BaseModel):
    doctor_profile_id: UUID
    description: str | None = None


class VotingSessionCreateRequest(BaseModel):
    title: str = Field(max_length=500)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    candidates: list[CandidateInput] = Field(min_length=1)

    @model_validator(mode="after")
    def ends_after_starts(self) -> "VotingSessionCreateRequest":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class VotingSessionUpdateRequest(BaseModel):
    status: Literal["active", "closed", "cancelled"] | None = None
    title: str | None = Field(None, max_length=500)
    ends_at: datetime | None = None


class VoteRequest(BaseModel):
    candidate_id: UUID


# ── Responses (admin) ─────────────────────────────────────────────

class VotingSessionListItem(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    status: str
    starts_at: datetime
    ends_at: datetime
    candidates_count: int = 0


class VotingSessionCreatedResponse(BaseModel):
    id: UUID
    title: str
    status: str
    starts_at: datetime
    ends_at: datetime
    candidates_count: int = 0


# ── Responses (public) ────────────────────────────────────────────

class ActiveCandidateNested(BaseModel):
    id: UUID
    full_name: str
    photo_url: str | None = None
    description: str | None = None


class ActiveSessionResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    candidates: list[ActiveCandidateNested] = []
    has_voted: bool = False


class VoteResponse(BaseModel):
    message: str
    voted_at: datetime


# ── Results ───────────────────────────────────────────────────────

class ResultSessionNested(BaseModel):
    id: UUID
    title: str
    status: str
    total_votes: int
    total_eligible_voters: int


class ResultCandidateNested(BaseModel):
    id: UUID
    full_name: str


class ResultItemNested(BaseModel):
    candidate: ResultCandidateNested
    votes_count: int
    percentage: float


class VotingResultsResponse(BaseModel):
    session: ResultSessionNested
    results: list[ResultItemNested] = []
