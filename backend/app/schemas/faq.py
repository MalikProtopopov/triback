"""Pydantic schemas for FAQ (Вопрос / Ответ)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Public responses ──────────────────────────────────────────────────


class FaqPublicItem(BaseModel):
    id: UUID
    question_title: str
    question_text: str
    answer_text: str | None = None
    author_name: str | None = None
    original_date: datetime | None = None


# ── Admin responses ───────────────────────────────────────────────────


class FaqAdminItem(BaseModel):
    id: UUID
    question_title: str
    question_text: str
    answer_text: str | None = None
    author_name: str | None = None
    is_active: bool
    original_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ── Admin requests ────────────────────────────────────────────────────


class FaqCreateRequest(BaseModel):
    question_title: str = Field(max_length=500)
    question_text: str
    answer_text: str | None = None
    author_name: str | None = Field(None, max_length=255)
    is_active: bool = True
    original_date: datetime | None = None


class FaqUpdateRequest(BaseModel):
    question_title: str | None = Field(None, max_length=500)
    question_text: str | None = None
    answer_text: str | None = None
    author_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    original_date: datetime | None = None
