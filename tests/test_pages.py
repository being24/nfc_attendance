
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
    assert "直近の入退室ログ" in res.text
    assert "Alice" in res.text
    assert "1名在室中" in res.text


def test_admin_pages(client):
    login_res = client.post(
        "/login",
        data={"username": "admin", "password": "admin", "next": "/admin/today"},
        follow_redirects=False,
    )
    assert login_res.status_code == 303

    for path in [
        "/admin/today",
        "/admin/students",
        "/admin/students/new",
        "/admin/events",
        "/admin/export",
    ]:
        res = client.get(path)
        assert res.status_code == 200


def test_admin_student_edit_can_update_student_code(client):
    login_res = client.post(
        "/login",
        data={"username": "admin", "password": "admin", "next": "/admin/students"},
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
