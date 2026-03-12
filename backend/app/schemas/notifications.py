"""Pydantic schemas for admin notification endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SendNotificationRequest(BaseModel):
    user_id: UUID
    type: str = Field(max_length=100)
    title: str = Field(max_length=500)
    body: str
    channels: list[Literal["email", "telegram"]] = ["email"]


class NotificationResponse(BaseModel):
    id: UUID
    status: str


class NotificationListItem(BaseModel):
    id: UUID
    user_id: UUID
    template_code: str
    channel: str
    title: str
    status: str
    sent_at: datetime | None = None
    created_at: datetime
