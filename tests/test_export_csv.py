from app.domain.time_utils import now_jst
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.student_repository import StudentRepository


def test_export_monthly_csv(client, db_session):
    student = StudentRepository(db_session).create("S300", "Hanako", "CARD300")
    AttendanceRepository(db_session).add_event(
        student_id=student.id,
        event_type="ENTER",
        occurred_at=now_jst().replace(
            year=2026, month=4, day=2, hour=10, minute=0, second=0, microsecond=0
        ),
        source="reader",
        reader_name="reader-1",
    )

    res = client.get("/api/export/monthly.csv?year=2026&month=4")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    body = res.text
    assert "student_code,name,event_type" in body
    assert "S300,Hanako,ENTER" in body


def test_export_semester_totals_csv_uses_shift_jis_and_business_hours(
    client, db_session, monkeypatch
):
    from datetime import datetime

    from app.domain.time_utils import JST
    from app.domain.enums import AttendanceAction
    from app.routers import export as export_router
    from app.services.attendance_service import AttendanceService

    student = StudentRepository(db_session).create("S302", "日本 花子", "CARD302")
    service = AttendanceService(db_session)
    entered_at = datetime(2026, 4, 2, 8, 0, tzinfo=JST)
    pending = service.prepare_touch(student.card_id, "reader-1", entered_at)
    service.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)
    left_at = entered_at.replace(hour=19)
    pending = service.prepare_touch(student.card_id, "reader-1", left_at)
    service.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, left_at)
    monkeypatch.setattr(
        export_router,
        "now_jst",
        lambda: datetime(2026, 4, 10, 12, 0, tzinfo=JST),
    )

    res = client.get("/api/export/semester-totals.csv?as_of=2026-04-02")

    assert res.status_code == 200
    assert "charset=shift_jis" in res.headers["content-type"]
    body = res.content.decode("cp932")
    assert "学籍番号,氏名,半期通算時間,半期通算分" in body
    assert "S302,日本 花子,8:00,480,2026-04-01,2026-04-02" in body


def test_export_semester_totals_csv_rejects_future_date(client, monkeypatch):
    from datetime import datetime

    from app.domain.time_utils import JST
    from app.routers import export as export_router

    monkeypatch.setattr(
        export_router,
        "now_jst",
        lambda: datetime(2026, 4, 10, 12, 0, tzinfo=JST),
    )

    res = client.get("/api/export/semester-totals.csv?as_of=2026-04-11")

    assert res.status_code == 400
    assert res.json()["detail"] == "未来の日付は指定できません"


def test_export_semester_csv(client, db_session):
    student = StudentRepository(db_session).create("S301", "Taro", "CARD301")
    repo = AttendanceRepository(db_session)
    repo.add_event(
        student_id=student.id,
        event_type="ENTER",
        occurred_at=now_jst().replace(
            year=2026, month=5, day=2, hour=10, minute=0, second=0, microsecond=0
        ),
        source="reader",
        reader_name="reader-1",
    )
    repo.add_event(
        student_id=student.id,
        event_type="LEAVE_FINAL",
        occurred_at=now_jst().replace(
            year=2026, month=11, day=2, hour=17, minute=0, second=0, microsecond=0
        ),
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
