"""«Активный член ассоциации» — логика как в ТЗ management_exports (согласовать с продуктом при изменении правил)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.models.profiles import DoctorProfile


def is_active_member(
    doctor: DoctorProfile,
    subscription: Any | None,
    *,
    now: datetime | None = None,
) -> str:
    """Возвращает «Да» или «Нет». `now` — aware UTC; по умолчанию `datetime.now(UTC)`."""
    now_utc = now if now is not None else datetime.now(UTC)
    if doctor.is_deleted:
        return "Нет"
    if str(doctor.status) != "active":
        return "Нет"
    if doctor.membership_excluded_at is not None:
        return "Нет"
    if subscription is None:
        return "Нет"
    if str(getattr(subscription, "status", "")) != "active":
        return "Нет"
    ends = getattr(subscription, "ends_at", None)
    if ends is not None:
        end = ends
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        if end < now_utc:
            return "Нет"
    return "Да"
