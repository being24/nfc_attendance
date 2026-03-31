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
