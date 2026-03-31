from app.models.student import Student


def test_tables_and_student_insert(db_session):
    student = Student(student_code="S001", name="Alice", card_id="CARD1")
    db_session.add(student)
    db_session.commit()
    got = db_session.get(Student, student.id)
    assert got is not None
    assert got.student_code == "S001"


def test_student_unique_constraint(db_session):
    db_session.add(Student(student_code="S001", name="Alice", card_id="CARD1"))
    db_session.commit()
    db_session.add(Student(student_code="S001", name="Bob", card_id="CARD2"))
    import pytest

    with pytest.raises(Exception):
        db_session.commit()
