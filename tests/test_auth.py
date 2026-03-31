
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


def test_touch_login_success(client):
    res = client.post(
        "/login/touch",
        data={"card_id": "ADMIN-CARD-001", "next": "/admin/today"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/admin/today"


def test_touch_login_failure(client):
    res = client.post(
        "/login/touch",
        data={"card_id": "NOT-ADMIN", "next": "/admin/today"},
    )
    assert res.status_code == 401
    assert "管理者カードではありません" in res.text
