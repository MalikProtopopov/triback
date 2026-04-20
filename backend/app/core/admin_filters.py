"""Shared helpers for admin list endpoints — date-range normalization and name search."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from sqlalchemy.sql.elements import ColumnElement

_MSK = ZoneInfo("Europe/Moscow")


def _is_midnight(dt: datetime) -> bool:
    return dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0


def normalize_msk_day_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    """Return a ``[lo, hi)`` UTC range from admin-list date filter inputs.

    The frontend typically passes a calendar date (e.g. ``2026-04-16``) which
    FastAPI parses as naive midnight. A naive ``<= date_to`` comparison then
    excludes everything after 00:00 on that day, so filtering "16th to 16th"
    returns zero rows even when there are payments on the 16th.

    This helper treats whole-day inputs (naive or midnight-aware) as MSK
    calendar days:

    - ``date_from`` → start of that day in MSK (inclusive lower bound)
    - ``date_to``   → start of the *next* day in MSK (exclusive upper bound)

    Non-midnight, tz-aware inputs are passed through as UTC unchanged, so
    callers that want precise timestamps are unaffected.
    """
    lo: datetime | None = None
    hi: datetime | None = None

    if date_from is not None:
        if date_from.tzinfo is None or _is_midnight(date_from):
            d = date_from.date()
            lo = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_MSK).astimezone(UTC)
        else:
            lo = date_from.astimezone(UTC)

    if date_to is not None:
        if date_to.tzinfo is None or _is_midnight(date_to):
            d = date_to.date()
            hi = (
                datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=_MSK)
                + timedelta(days=1)
            ).astimezone(UTC)
        else:
            hi = date_to.astimezone(UTC)

    return lo, hi


def build_name_ilike_filter(
    query: str | None, *columns: ColumnElement[Any]
) -> ColumnElement[bool] | None:
    """Build a partial-match name filter across the given columns.

    The input is split on whitespace; every token must match at least one of
    the columns via ``ILIKE '%token%'``. So "Романова Юлия" matches rows where
    *last_name* contains "Романова" AND *first_name* contains "Юлия", as well
    as the reverse ordering, without requiring exact ФИО.

    Returns ``None`` when the query is empty — caller should skip appending.
    """
    if not query:
        return None
    tokens = [t for t in query.strip().split() if t]
    if not tokens:
        return None
    clauses: list[ColumnElement[bool]] = []
    for tok in tokens:
        pattern = f"%{tok}%"
        clauses.append(or_(*(col.ilike(pattern) for col in columns)))
    return and_(*clauses)
