from app.schemas.student import StudentCreate
from app.services.student_service import StudentService


def test_service_error_mapped_to_json(client):
    headers = {"X-Reader-Token": "dev-reader-token"}
    res = client.post(
        "/api/reader/touches",
        headers=headers,
        json={
            "card_id": "NO_CARD",
            "reader_name": "reader-a",
            "detected_at": "2026-04-01T09:00:00+09:00",
        },
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "未登録のカードです"


def test_service_error_mapped_to_html(client, db_session):
    StudentService(db_session).register_student(
        StudentCreate(student_code="S001", name="Alice", card_id="CARD1")
    )

    client.post(
        "/login",
        data={"username": "admin", "password": "admin", "next": "/admin/students/new"},
    )

    # 同じ学籍番号で登録 -> DuplicateStudentCodeError
    res = client.post(
        "/admin/students",
        data={
            "student_code": "S001",
            "name": "Bob",
            "card_id": "CARD2",
            "note": "",
        },
    )
    assert res.status_code == 409
    assert "duplicate student_code" in res.text
