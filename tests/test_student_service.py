import pytest

from app.schemas.student import StudentCreate, StudentUpdate
from app.services.exceptions import DuplicateStudentCodeError
from app.services.student_service import StudentService


def test_student_service_register_update_list_deactivate(db_session):
    svc = StudentService(db_session)
    student = svc.register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    assert student.id > 0
    updated = svc.update_student(student.id, StudentUpdate(name="Alicia"))
    assert updated.name == "Alicia"
    assert len(svc.list_students()) == 1
    svc.deactivate_student(student.id)
    assert len(svc.list_students()) == 0


def test_student_service_duplicate(db_session):
    svc = StudentService(db_session)
    svc.register_student(StudentCreate(student_code="S001", name="Alice", card_id="CARD1"))
    with pytest.raises(DuplicateStudentCodeError):
        svc.register_student(StudentCreate(student_code="S001", name="Bob", card_id="CARD2"))
