
def test_index_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "学生証をタッチしてください" in res.text


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
