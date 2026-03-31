from datetime import timedelta

from app.domain.time_utils import clamp_non_negative_minutes, minutes_between, now_jst


def test_now_jst_has_tz():
    assert now_jst().tzinfo is not None


def test_minutes_between_non_negative():
    start = now_jst()
    end = start + timedelta(minutes=10, seconds=30)
    assert minutes_between(start, end) == 10


def test_clamp_non_negative_minutes():
    assert clamp_non_negative_minutes(-3) == 0
