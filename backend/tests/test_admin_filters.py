"""Unit tests for app.core.admin_filters."""

from __future__ import annotations

from datetime import UTC, datetime, timezone

from sqlalchemy import Column, MetaData, String, Table

from app.core.admin_filters import build_name_ilike_filter, normalize_msk_day_range


def _compile(clause) -> str:
    return str(clause.compile(compile_kwargs={"literal_binds": True}))


def test_normalize_day_range_naive_midnight_treats_as_msk_day() -> None:
    # "2026-04-16 to 2026-04-16" should cover the whole MSK calendar day.
    # MSK = UTC+3, so the range is [2026-04-15 21:00 UTC, 2026-04-16 21:00 UTC).
    lo, hi = normalize_msk_day_range(datetime(2026, 4, 16), datetime(2026, 4, 16))
    assert lo == datetime(2026, 4, 15, 21, 0, 0, tzinfo=UTC)
    assert hi == datetime(2026, 4, 16, 21, 0, 0, tzinfo=UTC)


def test_normalize_day_range_aware_midnight_also_treated_as_day() -> None:
    lo, hi = normalize_msk_day_range(
        datetime(2026, 4, 16, tzinfo=UTC),
        datetime(2026, 4, 16, tzinfo=UTC),
    )
    assert lo == datetime(2026, 4, 15, 21, 0, 0, tzinfo=UTC)
    assert hi == datetime(2026, 4, 16, 21, 0, 0, tzinfo=UTC)


def test_normalize_day_range_explicit_timestamps_pass_through() -> None:
    lo, hi = normalize_msk_day_range(
        datetime(2026, 4, 16, 10, 30, tzinfo=UTC),
        datetime(2026, 4, 16, 20, 45, tzinfo=UTC),
    )
    assert lo == datetime(2026, 4, 16, 10, 30, tzinfo=UTC)
    assert hi == datetime(2026, 4, 16, 20, 45, tzinfo=UTC)


def test_normalize_day_range_none_inputs() -> None:
    assert normalize_msk_day_range(None, None) == (None, None)


def test_normalize_day_range_only_from() -> None:
    lo, hi = normalize_msk_day_range(datetime(2026, 4, 16), None)
    assert lo is not None
    assert hi is None


def test_build_name_filter_none_or_blank_returns_none() -> None:
    md = MetaData()
    t = Table("t", md, Column("first_name", String))
    assert build_name_ilike_filter(None, t.c.first_name) is None
    assert build_name_ilike_filter("", t.c.first_name) is None
    assert build_name_ilike_filter("   ", t.c.first_name) is None


def test_build_name_filter_single_token_ors_columns() -> None:
    md = MetaData()
    t = Table("t", md, Column("ln", String), Column("fn", String))
    sql = _compile(build_name_ilike_filter("Романова", t.c.ln, t.c.fn))
    # Both columns should appear inside one OR group, wrapped in ILIKE.
    assert "ln" in sql and "fn" in sql
    assert "Романова" in sql


def test_build_name_filter_multiple_tokens_ands_groups() -> None:
    md = MetaData()
    t = Table("t", md, Column("ln", String), Column("fn", String))
    sql = _compile(build_name_ilike_filter("Романова Юлия", t.c.ln, t.c.fn))
    # Both tokens must be present, combined with AND.
    assert "Романова" in sql and "Юлия" in sql
    assert " AND " in sql
