
from app.domain.enums import AttendanceAction
from app.config import get_settings
from app.services.attendance_service import AttendanceService
from app.schemas.student import StudentCreate
from app.services.student_service import StudentService

settings = get_settings()


def test_index_page(client):
    client.post(
        "/api/students",
        json={"student_code": "S100", "name": "Alice", "card_id": "CARD100"},
    )
    client.post(
        "/touch/simulate",
        data={"card_id": "CARD100", "action": "ENTER"},
    )
    res = client.get("/")
    assert res.status_code == 200
    assert "学生証をタッチしてください" in res.text
    assert "現在の在室者" in res.text
    assert "直近の入退室" in res.text
    assert "Alice" in res.text
    assert "1名在室中" in res.text


def test_admin_pages(client):
    login_res = client.post(
        "/login",
        data={"username": settings.admin_username, "password": settings.admin_password, "next": "/admin/today"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    for path in [
        "/admin/today",
        "/admin/current-times",
        "/admin/students",
        "/admin/students/new",
        "/admin/events",
        "/admin/export",
    ]:
        res = client.get(path)
        assert res.status_code == 200


def test_admin_today_shows_actual_and_business_minutes(client):
    login_res = client.post(
        "/login",
        data={"username": settings.admin_username, "password": settings.admin_password, "next": "/admin/today"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    client.post(
        "/api/students",
        json={"student_code": "S102", "name": "Biz User", "card_id": "CARD102"},
    )
    client.post(
        "/touch/simulate",
        data={"card_id": "CARD102", "action": "ENTER"},
    )

    res = client.get("/admin/today")
    assert res.status_code == 200
    assert "累計在室時間" in res.text
    assert "9-17換算" in res.text


def test_admin_current_times_sorted_by_student_code_and_filterable(client, db_session):
    login_res = client.post(
        "/login",
        data={"username": settings.admin_username, "password": settings.admin_password, "next": "/admin/current-times"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    student_service = StudentService(db_session)
    student_service.register_student(StudentCreate(student_code="S002", name="Outside User", card_id="CARD202"))
    student_service.register_student(StudentCreate(student_code="S001", name="In Room User", card_id="CARD201"))
    inactive = student_service.register_student(StudentCreate(student_code="S003", name="Inactive User", card_id="CARD203"))
    student_service.deactivate_student(inactive.id)
    attendance_service = AttendanceService(db_session)

    client.post(
        "/touch/simulate",
        data={"card_id": "CARD201", "action": "ENTER"},
    )
    entered_at = attendance_service.current_term_bounds()[0].replace(hour=9, minute=0, second=0, microsecond=0)
    pending = attendance_service.prepare_touch("CARD202", "reader", entered_at)
    attendance_service.confirm_touch(pending.touch_token, AttendanceAction.ENTER, entered_at)
    left_at = entered_at.replace(hour=10, minute=30, second=0, microsecond=0)
    pending = attendance_service.prepare_touch("CARD202", "reader", left_at)
    attendance_service.confirm_touch(pending.touch_token, AttendanceAction.LEAVE_FINAL, left_at)

    res_all = client.get("/admin/current-times?target=all")
    assert res_all.status_code == 200
    assert res_all.text.index("S001") < res_all.text.index("S002") < res_all.text.index("S003")
    assert "Outside User" in res_all.text
    assert "0時間0分" not in res_all.text.split("Outside User", 1)[1].split("</tr>", 1)[0]

    res_active = client.get("/admin/current-times?target=active")
    assert res_active.status_code == 200
    assert "S001" in res_active.text
    assert "S002" in res_active.text
    assert "S003" not in res_active.text

    res_in_room = client.get("/admin/current-times?target=in_room")
    assert res_in_room.status_code == 200
    assert "S001" in res_in_room.text
    assert "S002" not in res_in_room.text
    assert "S003" not in res_in_room.text


def test_admin_student_edit_can_update_student_code(client):
    login_res = client.post(
        "/login",
        data={"username": settings.admin_username, "password": settings.admin_password, "next": "/admin/students"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    create_res = client.post(
        "/api/students",
        json={"student_code": "S101", "name": "Edit Target", "card_id": "CARD101"},
    )
    assert create_res.status_code == 201
    student_id = create_res.json()["id"]

    update_res = client.post(
        f"/admin/students/{student_id}",
        data={
            "student_code": "S999",
            "name": "Edit Target",
            "card_id": "CARD101",
            "is_active": "true",
        },
        follow_redirects=False,
    )
    assert update_res.status_code == 303
    assert update_res.headers["location"] == "/admin/students"

    student_res = client.get(f"/api/students/{student_id}")
    assert student_res.status_code == 200
    assert student_res.json()["student_code"] == "S999"


def test_simulate_touch_unknown_card_shows_error_page(client):
    res = client.post(
        "/touch/simulate",
        data={"card_id": "NO_CARD", "action": "auto"},
    )
    assert res.status_code == 404
    assert "未登録のカードです" in res.text


def test_simulate_touch_success_page(client):
    client.post(
        "/api/students",
        json={"student_code": "S900", "name": "Sim User", "card_id": "CARD900"},
    )
    res = client.post(
        "/touch/simulate",
        data={"card_id": "CARD900", "action": "auto"},
    )
    assert res.status_code == 200
    assert "打刻完了" in res.text
    assert "入室しました" in res.text
    assert "5秒後に待受画面へ戻ります。" in res.text


def test_term_total_page(client):
    client.post(
        "/api/students",
        json={"student_code": "S901", "name": "Term User", "card_id": "CARD901"},
    )
    client.post(
        "/touch/simulate",
        data={"card_id": "CARD901", "action": "ENTER"},
    )
    client.post(
        "/touch/simulate",
        data={"card_id": "CARD901", "action": "LEAVE_FINAL"},
    )

    res = client.post(
        "/student/term-total",
        data={"card_id": "CARD901"},
    )
    assert res.status_code == 200
    assert "今期通算在室時間" in res.text
