"""Europe/Moscow formatting for export cells."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

_MSK = ZoneInfo("Europe/Moscow")


def msk_now() -> datetime:
    return datetime.now(tz=_MSK)


def default_month_date_range() -> tuple[date, date]:
    """First day of current month (MSK) through today (MSK)."""
    now = msk_now().date()
    start = now.replace(day=1)
    return start, now


def default_year_date_range_msk() -> tuple[date, date]:
    """Jan 1 — Dec 31 of current calendar year in Europe/Moscow."""
    y = msk_now().date().year
    return date(y, 1, 1), date(y, 12, 31)


def msk_range_to_utc_exclusive_end(d_from: date, d_to: date) -> tuple[datetime, datetime]:
    """Start of d_from MSK (inclusive) and start of day after d_to MSK (exclusive), as UTC."""
    start_local = datetime(
        d_from.year, d_from.month, d_from.day, 0, 0, 0, tzinfo=_MSK
    )
    end_local = datetime(
        d_to.year, d_to.month, d_to.day, 0, 0, 0, tzinfo=_MSK
    ) + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def format_dt_msk(dt: datetime | None) -> str | None:
    """DD.MM.YYYY HH:MM in MSK, or None -> empty."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_MSK)
    return local.strftime("%d.%m.%Y %H:%M")


def format_date_msk(dt: datetime | None) -> str | None:
    """DD.MM.YYYY in MSK."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_MSK)
    return local.strftime("%d.%m.%Y")
