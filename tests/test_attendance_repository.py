from datetime import timedelta

from app.domain.enums import AttendanceStatus
from app.domain.time_utils import now_jst
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.student_repository import StudentRepository


def test_attendance_repository_flows(db_session):
    srepo = StudentRepository(db_session)
    student = srepo.create("S001", "Alice", "CARD1")
    repo = AttendanceRepository(db_session)

    now = now_jst()
    event = repo.add_event(student.id, "ENTER", now, "reader")
    status = repo.upsert_status(student.id, AttendanceStatus.IN_ROOM.value, event.id)
    assert status.current_status == AttendanceStatus.IN_ROOM.value

    session = repo.create_session(student.id, now)
    assert repo.get_open_session(student.id).id == session.id

    repo.start_break(session.id, now + timedelta(minutes=10))
    repo.end_latest_open_break(session.id, now + timedelta(minutes=20))
    assert repo.sum_break_minutes(session.id, until=now + timedelta(minutes=30)) == 10

    closed = repo.close_session(session, now + timedelta(minutes=60), 50)
    assert closed.total_minutes == 50


def test_count_in_room(db_session):
    srepo = StudentRepository(db_session)
    student = srepo.create("S001", "Alice", "CARD1")
    repo = AttendanceRepository(db_session)
    ev = repo.add_event(student.id, "ENTER", now_jst(), "reader")
    repo.upsert_status(student.id, AttendanceStatus.IN_ROOM.value, ev.id)
    assert repo.count_in_room() == 1
