from app.schemas.student import StudentCreate
from app.domain.time_utils import now_jst
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


def test_today_api_includes_student_fields_and_latest_first(client, db_session):
    StudentService(db_session).register_student(
        StudentCreate(student_code="S001", name="Alice", card_id="CARD1")
    )
    base = now_jst().replace(hour=9, minute=0, second=0, microsecond=0)

    headers = {"X-Reader-Token": "dev-reader-token"}
    first_touch = client.post(
        "/api/reader/touches",
        headers=headers,
        json={
            "card_id": "CARD1",
            "reader_name": "reader-a",
            "detected_at": base.isoformat(),
        },
    )
    first_token = first_touch.json()["touch_token"]
    client.post(
        f"/api/reader/touches/{first_token}/confirm",
        headers=headers,
        json={
            "action": "ENTER",
            "now": base.replace(second=1).isoformat(),
        },
    )

    later = base.replace(minute=30)
    second_touch = client.post(
        "/api/reader/touches",
        headers=headers,
        json={
            "card_id": "CARD1",
            "reader_name": "reader-a",
            "detected_at": later.isoformat(),
        },
    )
    second_token = second_touch.json()["touch_token"]
    client.post(
        f"/api/reader/touches/{second_token}/confirm",
        headers=headers,
        json={
            "action": "LEAVE_FINAL",
            "now": later.replace(second=1).isoformat(),
        },
    )

    res = client.get("/api/attendance/today")
    assert res.status_code == 200
    payload = res.json()
    assert payload["events"][0]["student_code"] == "S001"
    assert payload["events"][0]["student_name"] == "Alice"
    assert [event["event_type"] for event in payload["events"][:2]] == ["LEAVE_FINAL", "ENTER"]
