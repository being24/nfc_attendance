from datetime import timedelta

from app.domain.enums import AttendanceAction, AttendanceStatus
from app.domain.pending_touch import PendingTouch
from app.domain.time_utils import now_jst


def test_pending_touch_expiry():
    now = now_jst()
    p = PendingTouch(
        touch_token="abc",
        student_id=1,
        card_id="card",
        reader_name="reader",
        detected_at=now,
        current_status=AttendanceStatus.OUTSIDE,
        allowed_actions=[AttendanceAction.ENTER],
        expires_at=now + timedelta(seconds=20),
    )
    assert p.is_expired(now + timedelta(seconds=21)) is True
    assert p.is_expired(now + timedelta(seconds=5)) is False
