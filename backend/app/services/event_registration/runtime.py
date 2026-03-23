"""Shared dependencies for event registration submodules."""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.payment_providers.protocols import PaymentProviderProtocol


@dataclass
class EventRegistrationRuntime:
    db: AsyncSession
    redis: Redis
    provider: PaymentProviderProtocol
