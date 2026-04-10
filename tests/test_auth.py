
from app.domain.time_utils import now_jst
from app.kiosk import kiosk_state
from app.schemas.student import StudentCreate
from app.schemas.student import StudentUpdate
from app.services.student_service import StudentService


def test_admin_page_requires_login(client):
    res = client.get("/admin/students", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"].startswith("/login")


def test_login_success_and_logout(client):
    login_res = client.post(
        "/login",
        data={"username": "admin", "password": "admin", "next": "/admin/today"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303
    assert login_res.headers["location"] == "/admin/today"

    after_login = client.get("/admin/today")
    assert after_login.status_code == 200

    logout_res = client.post("/logout", follow_redirects=False)
    assert logout_res.status_code == 303
    assert logout_res.headers["location"] == "/login"

    after_logout = client.get("/admin/today", follow_redirects=False)
    assert after_logout.status_code == 200
    protected_after_logout = client.get("/admin/students", follow_redirects=False)
    assert protected_after_logout.status_code == 303


def test_login_failure(client):
    res = client.post(
        "/login",
        data={"username": "admin", "password": "wrong", "next": "/admin/today"},
    )
    assert res.status_code == 401
    assert "ユーザー名またはパスワードが正しくありません" in res.text


def test_admin_api_requires_login(client):
    res = client.post(
        "/api/admin/corrections",
        json={
            "student_id": 1,
            "action": "ENTER",
            "occurred_at": "2026-04-01T10:00:00+09:00",
        },
    )
    assert res.status_code == 401

    res_latest_unknown = client.get("/api/admin/latest-unknown-card")
    assert res_latest_unknown.status_code == 401


def test_touch_login_success(client):
    client.post(
        "/api/students",
        json={"student_code": "A001", "name": "Admin User", "card_id": "ADMIN-CARD-001", "is_admin": True},
    )
    res = client.post(
        "/login/touch",
        data={"card_id": "ADMIN-CARD-001", "next": "/admin/today"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/admin/today"


def test_touch_login_failure(client):
    client.post(
        "/api/students",
        json={"student_code": "S001", "name": "Normal User", "card_id": "NOT-ADMIN", "is_admin": False},
    )
    res = client.post(
        "/login/touch",
        data={"card_id": "NOT-ADMIN", "next": "/admin/today"},
    )
    assert res.status_code == 401
    assert "管理者カードではありません" in res.text


def test_touch_login_failure_for_inactive_admin_card(client, db_session):
    student_service = StudentService(db_session)
    student = student_service.register_student(
        StudentCreate(student_code="A002", name="Inactive Admin", card_id="ADMIN-CARD-002", is_admin=True)
    )
    student_service.update_student(student.id, StudentUpdate(is_active=False))

    res = client.post(
        "/login/touch",
        data={"card_id": "ADMIN-CARD-002", "next": "/admin/today"},
    )
    assert res.status_code == 401


def test_touch_login_success_uses_student_admin_flag(client):
    create_res = client.post(
        "/api/students",
        json={"student_code": "A003", "name": "Flag Admin", "card_id": "ADMIN-CARD-003", "is_admin": True},
    )
    assert create_res.status_code == 201
    assert create_res.json()["is_admin"] is True

    res = client.post(
        "/login/touch",
        data={"card_id": "ADMIN-CARD-003", "next": "/admin/today"},
        follow_redirects=False,
    )
    assert res.status_code == 303


def test_logout_clears_admin_login_card_capture(client):
    kiosk_state.store_admin_login_capture("ADMIN-CARD-001", "reader-a", now_jst())

    logout_res = client.post("/logout", follow_redirects=False)

    assert logout_res.status_code == 303
    assert kiosk_state.get_latest_admin_login_capture(now=now_jst()) is None


def test_touch_login_failure_clears_admin_login_card_capture(client):
    kiosk_state.store_admin_login_capture("NOT-ADMIN", "reader-a", now_jst())
    client.post(
        "/api/students",
        json={"student_code": "S001", "name": "Normal User", "card_id": "NOT-ADMIN", "is_admin": False},
    )

    res = client.post(
        "/login/touch",
        data={"card_id": "NOT-ADMIN", "next": "/admin/today"},
    )

    assert res.status_code == 401
    assert kiosk_state.get_latest_admin_login_capture(now=now_jst()) is None
