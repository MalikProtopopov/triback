"""Unit tests for management export helpers."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.exports.active_member import is_active_member


def test_is_active_member_yes():
    doctor = MagicMock()
    doctor.is_deleted = False
    doctor.status = "active"
    doctor.membership_excluded_at = None
    now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
    sub = SimpleNamespace(status="active", ends_at=now + timedelta(days=30))
    assert is_active_member(doctor, sub, now=now) == "Да"


def test_is_active_member_no_expired():
    doctor = MagicMock()
    doctor.is_deleted = False
    doctor.status = "active"
    doctor.membership_excluded_at = None
    now = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
    sub = SimpleNamespace(status="active", ends_at=now - timedelta(days=1))
    assert is_active_member(doctor, sub, now=now) == "Нет"
