from datetime import date, datetime

from app.config import get_settings
from app.domain.enums import AttendanceAction
from app.domain.time_utils import JST
from app.schemas.student import StudentCreate
from app.services.attendance_service import AttendanceService
from app.services.student_service import StudentService
from app.services.term_settings_service import TermSettingsService


def test_selected_term_start_date_controls_student_totals(db_session):
    student = StudentService(db_session).register_student(
        StudentCreate(student_code="S700", name="Term User", card_id="CARD700")
    )
    service = AttendanceService(db_session)

    for entered_at, left_at in [
        (
            datetime(2026, 4, 5, 9, 0, tzinfo=JST),
            datetime(2026, 4, 5, 10, 0, tzinfo=JST),
        ),
        (
            datetime(2026, 4, 15, 9, 0, tzinfo=JST),
            datetime(2026, 4, 15, 11, 0, tzinfo=JST),
        ),
        (
            datetime(2026, 9, 20, 9, 0, tzinfo=JST),
            datetime(2026, 9, 20, 10, 30, tzinfo=JST),
        ),
    ]:
        pending = service.prepare_touch(student.card_id, "reader", entered_at)
        service.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)
        pending = service.prepare_touch(student.card_id, "reader", left_at)
        service.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, left_at)

    TermSettingsService(db_session).update_settings(
        active_term=1,
        first_term_start_date=date(2026, 4, 10),
        second_term_start_date=date(2026, 9, 10),
    )

    rows = service.list_student_current_times(
        now=datetime(2026, 9, 25, 12, 0, tzinfo=JST)
    )
    row = next(row for row in rows if row.student_id == student.id)
    assert row.cumulative_minutes == 210
    assert row.business_cumulative_minutes == 210

    TermSettingsService(db_session).update_settings(
        active_term=2,
        first_term_start_date=date(2026, 4, 10),
        second_term_start_date=date(2026, 9, 10),
    )
    rows = service.list_student_current_times(
        now=datetime(2026, 9, 25, 12, 0, tzinfo=JST)
    )
    row = next(row for row in rows if row.student_id == student.id)
    assert row.cumulative_minutes == 90
    assert row.business_cumulative_minutes == 90


def test_admin_can_save_active_term_and_start_dates(client):
    settings = get_settings()
    login = client.post(
        "/login",
        data={
            "username": settings.admin_username,
            "password": settings.admin_password,
            "next": "/admin/term-settings",
        },
        follow_redirects=False,
    )
    assert login.status_code == 303

    response = client.post(
        "/admin/term-settings",
        data={
            "active_term": "2",
            "first_term_start_date": "2026-04-07",
            "second_term_start_date": "2026-09-22",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    page = client.get("/admin/term-settings")
    assert page.status_code == 200
    assert 'value="2026-04-07"' in page.text
    assert 'value="2026-09-22"' in page.text
    assert '<option value="2" selected>後期</option>' in page.text
