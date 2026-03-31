
def test_students_api_crud(client):
    payload = {
        "student_code": "S100",
        "name": "Taro",
        "card_id": "CARD100",
    }
    create_res = client.post("/api/students", json=payload)
    assert create_res.status_code == 201
    student_id = create_res.json()["id"]

    list_res = client.get("/api/students")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    get_res = client.get(f"/api/students/{student_id}")
    assert get_res.status_code == 200
    assert get_res.json()["student_code"] == "S100"

    patch_res = client.patch(f"/api/students/{student_id}", json={"name": "Jiro"})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Jiro"
