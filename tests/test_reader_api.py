from app.schemas.student import StudentCreate
from app.services.student_service import StudentService


def test_reader_touch_and_confirm_api(client, db_session):
    StudentService(db_session).register_student(
        StudentCreate(student_code="S001", name="Alice", card_id="CARD1")
    )

    headers = {"X-Reader-Token": "dev-reader-token"}
    touch_res = client.post(
        "/api/reader/touches",
        headers=headers,
        json={
            "card_id": "CARD1",
            "reader_name": "reader-a",
            "detected_at": "2026-04-01T09:00:00+09:00",
        },
    )
    assert touch_res.status_code == 200
    token = touch_res.json()["touch_token"]

    confirm_res = client.post(
        f"/api/reader/touches/{token}/confirm",
        headers=headers,
        json={
            "action": "ENTER",
            "now": "2026-04-01T09:00:03+09:00",
        },
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["next_status"] == "IN_ROOM"


def test_reader_token_auth(client):
    res = client.post(
        "/api/reader/touches",
        headers={"X-Reader-Token": "bad-token"},
        json={
            "card_id": "CARD1",
            "reader_name": "reader-a",
            "detected_at": "2026-04-01T09:00:00+09:00",
        },
    )
    assert res.status_code == 401
