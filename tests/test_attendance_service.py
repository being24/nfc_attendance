from datetime import timedelta

import pytest

from app.domain.enums import AttendanceAction, AttendanceStatus
from app.domain.time_utils import now_jst
from app import realtime
from app.schemas.student import StudentCreate
from app.services.attendance_service import AttendanceService
from app.services.exceptions import (
    TouchTokenExpiredError,
    UnknownCardError,
)
from app.services.student_service import StudentService
from app.touch_panel import touch_panel_state


def test_prepare_touch_unknown_card(db_session):
    svc = AttendanceService(db_session)
    with pytest.raises(UnknownCardError):
        svc.prepare_touch("NOPE", "reader", now_jst())


def test_prepare_touch_unknown_card_publishes_realtime_event(db_session, monkeypatch):
    published = []
    monkeypatch.setattr(realtime.attendance_event_broker, "publish", lambda event="refresh": published.append(event))
    svc = AttendanceService(db_session)

    with pytest.raises(UnknownCardError):
        svc.prepare_touch("NOPE", "reader", now_jst())

    assert published == ["refresh"]


def test_attendance_flow_and_lock_alert(db_session):
    student = StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    t1 = now_jst().replace(hour=9, minute=0, second=0, microsecond=0)

    p = svc.prepare_touch("CARD1", "reader", t1)
    assert p.current_status == AttendanceStatus.OUTSIDE
    c1 = svc.confirm_touch(p.touch_token, AttendanceAction.ENTER, t1)
    assert c1.next_status == AttendanceStatus.IN_ROOM

    p2 = svc.prepare_touch("CARD1", "reader", t1 + timedelta(minutes=60))
    svc.confirm_touch(p2.touch_token, AttendanceAction.LEAVE_TEMP, t1 + timedelta(minutes=60))

    p3 = svc.prepare_touch("CARD1", "reader", t1 + timedelta(minutes=75))
    svc.confirm_touch(p3.touch_token, AttendanceAction.RETURN, t1 + timedelta(minutes=75))

    p4 = svc.prepare_touch("CARD1", "reader", t1 + timedelta(minutes=120))
    c4 = svc.confirm_touch(p4.touch_token, AttendanceAction.LEAVE_FINAL, t1 + timedelta(minutes=120))
    assert c4.lock_alert_required is True
    assert c4.student_id == student.id


def test_confirm_touch_publishes_realtime_event(db_session, monkeypatch):
    published = []
    monkeypatch.setattr(realtime.attendance_event_broker, "publish", lambda event="refresh": published.append(event))
    StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    t1 = now_jst().replace(hour=9, minute=0, second=0, microsecond=0)

    pending = svc.prepare_touch("CARD1", "reader", t1)
    svc.confirm_touch(pending.touch_token, AttendanceAction.ENTER, t1)

    assert published == ["refresh"]


def test_token_expiry(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    t = now_jst()
    p = svc.prepare_touch("CARD1", "reader", t)
    with pytest.raises(TouchTokenExpiredError):
        svc.confirm_touch(p.touch_token, AttendanceAction.ENTER, t + timedelta(seconds=25))


def test_compute_9_to_17(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    start = now_jst().replace(hour=8, minute=0, second=0, microsecond=0)
    p = svc.prepare_touch("CARD1", "reader", start)
    svc.confirm_touch(p.touch_token, AttendanceAction.ENTER, start)

    p2 = svc.prepare_touch("CARD1", "reader", start + timedelta(hours=2))
    svc.confirm_touch(p2.touch_token, AttendanceAction.LEAVE_TEMP, start + timedelta(hours=2))

    p3 = svc.prepare_touch("CARD1", "reader", start + timedelta(hours=3))
    svc.confirm_touch(p3.touch_token, AttendanceAction.RETURN, start + timedelta(hours=3))

    repo_open = svc.att_repo.get_open_session(1)
    business = svc.compute_9_to_17_minutes(start, start + timedelta(hours=10), repo_open.id)
    assert business == 420  # 9:00-17:00(480) - break 60


def test_get_today_attendance_fields(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    t = now_jst()
    p = svc.prepare_touch("CARD1", "reader", t)
    svc.confirm_touch(p.touch_token, AttendanceAction.ENTER, t)

    today = svc.get_today_attendance()
    assert len(today.in_room) == 1
    row = today.in_room[0]
    assert row.student_code == "S001"
    assert row.name == "Alice"
    assert row.current_status == AttendanceStatus.IN_ROOM.value
    assert len(today.events) == 1
    event = today.events[0]
    assert event.student_code == "S001"
    assert event.student_name == "Alice"


def test_get_today_attendance_events_are_latest_first(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    svc = AttendanceService(db_session)
    t = now_jst().replace(hour=9, minute=0, second=0, microsecond=0)

    p1 = svc.prepare_touch("CARD1", "reader", t)
    svc.confirm_touch(p1.touch_token, AttendanceAction.ENTER, t)

    later = t + timedelta(minutes=30)
    p2 = svc.prepare_touch("CARD1", "reader", later)
    svc.confirm_touch(p2.touch_token, AttendanceAction.LEAVE_FINAL, later)

    today = svc.get_today_attendance()
    assert [event.event_type for event in today.events] == [
        AttendanceAction.LEAVE_FINAL.value,
        AttendanceAction.ENTER.value,
    ]


def test_get_today_attendance_includes_recent_unknown_card_alert(db_session):
    svc = AttendanceService(db_session)
    detected_at = now_jst()

    with pytest.raises(UnknownCardError):
        svc.prepare_touch("NO_CARD", "reader-a", detected_at)

    today = svc.get_today_attendance()

    assert today.unknown_card_alert is not None
    assert today.unknown_card_alert.card_id == "NO_CARD"
    assert today.unknown_card_alert.reader_name == "reader-a"


def test_get_today_attendance_includes_recent_lock_alert(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S010", name="Lock User", card_id="LOCK1"))
    svc = AttendanceService(db_session)
    entered_at = now_jst() - timedelta(minutes=10)

    pending = svc.prepare_touch("LOCK1", "reader", entered_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)

    leaving_at = now_jst()
    pending = svc.prepare_touch("LOCK1", "reader", leaving_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, leaving_at)

    today = svc.get_today_attendance()

    assert today.lock_alert is not None
    assert "施錠してください" in today.lock_alert.message


def test_get_today_attendance_hides_lock_alert_when_someone_is_in_room(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S010", name="Lock User", card_id="LOCK1"))
    StudentService(db_session).register_student(StudentCreate(student_code="S011", name="Stay User", card_id="LOCK2"))
    svc = AttendanceService(db_session)
    entered_at = now_jst() - timedelta(minutes=10)

    pending = svc.prepare_touch("LOCK1", "reader", entered_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)
    pending = svc.prepare_touch("LOCK2", "reader", entered_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)

    leaving_at = now_jst()
    pending = svc.prepare_touch("LOCK1", "reader", leaving_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, leaving_at)

    today = svc.get_today_attendance()

    assert today.lock_alert is None


def test_get_today_attendance_includes_touch_panel_error(db_session):
    touch_panel_state.store_error("選択中の操作はこのカードでは使えません", now_jst())
    svc = AttendanceService(db_session)

    today = svc.get_today_attendance()

    assert today.touch_error is not None
    assert "使えません" in today.touch_error.message


def test_get_latest_unknown_card_alert_returns_recent_entry(db_session):
    svc = AttendanceService(db_session)
    detected_at = now_jst()

    with pytest.raises(UnknownCardError):
        svc.prepare_touch("NO_CARD", "reader-a", detected_at)

    latest = svc.get_latest_unknown_card_alert(now=detected_at)

    assert latest is not None
    assert latest.card_id == "NO_CARD"
    assert latest.reader_name == "reader-a"


def test_capture_term_total_updates_today_attendance(db_session):
    StudentService(db_session).register_student(StudentCreate(student_code="S002", name="Bob", card_id="CARD2"))
    svc = AttendanceService(db_session)
    entered_at = now_jst() - timedelta(minutes=90)

    pending = svc.prepare_touch("CARD2", "reader", entered_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)

    left_at = now_jst()
    pending = svc.prepare_touch("CARD2", "reader", left_at)
    svc.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, left_at)

    result = svc.capture_current_term_total_by_card("CARD2", "reader", left_at)
    today = svc.get_today_attendance()

    assert result.student_code == "S002"
    assert result.total_minutes == 90
    assert today.latest_term_total is not None
    assert today.latest_term_total.student_name == "Bob"
    assert today.latest_term_total.total_minutes == 90
