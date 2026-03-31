from app.domain.time_utils import now_jst
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.student_repository import StudentRepository


def test_export_monthly_csv(client, db_session):
    student = StudentRepository(db_session).create("S300", "Hanako", "CARD300")
    AttendanceRepository(db_session).add_event(
        student_id=student.id,
        event_type="ENTER",
        occurred_at=now_jst().replace(year=2026, month=4, day=2, hour=10, minute=0, second=0, microsecond=0),
        source="reader",
        reader_name="reader-1",
    )

    res = client.get("/api/export/monthly.csv?year=2026&month=4")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    body = res.text
    assert "student_code,name,event_type" in body
    assert "S300,Hanako,ENTER" in body


def test_export_semester_csv(client, db_session):
    student = StudentRepository(db_session).create("S301", "Taro", "CARD301")
    repo = AttendanceRepository(db_session)
    repo.add_event(
        student_id=student.id,
        event_type="ENTER",
        occurred_at=now_jst().replace(year=2026, month=5, day=2, hour=10, minute=0, second=0, microsecond=0),
        source="reader",
        reader_name="reader-1",
    )
    repo.add_event(
        student_id=student.id,
        event_type="LEAVE_FINAL",
        occurred_at=now_jst().replace(year=2026, month=11, day=2, hour=17, minute=0, second=0, microsecond=0),
        source="reader",
        reader_name="reader-1",
    )

    res_h1 = client.get("/api/export/semester.csv?year=2026&semester=1")
    assert res_h1.status_code == 200
    assert "S301,Taro,ENTER" in res_h1.text
    assert "S301,Taro,LEAVE_FINAL" not in res_h1.text

    res_h2 = client.get("/api/export/semester.csv?year=2026&semester=2")
    assert res_h2.status_code == 200
    assert "S301,Taro,LEAVE_FINAL" in res_h2.text
