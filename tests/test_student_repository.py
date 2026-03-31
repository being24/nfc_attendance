import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.student_repository import StudentRepository


def test_student_repository_crud(db_session):
    repo = StudentRepository(db_session)
    st = repo.create("S001", "Alice", "CARD1")
    assert repo.get_by_id(st.id) is not None
    assert repo.get_by_card_id("CARD1").name == "Alice"
    assert repo.get_by_student_code("S001").card_id == "CARD1"
    assert len(repo.list_all()) == 1
    repo.update(st, name="Alicia")
    assert repo.get_by_id(st.id).name == "Alicia"
    repo.deactivate(st)
    assert len(repo.list_all()) == 0
    assert len(repo.list_all(include_inactive=True)) == 1


def test_student_repository_unique(db_session):
    repo = StudentRepository(db_session)
    repo.create("S001", "Alice", "CARD1")
    with pytest.raises(IntegrityError):
        repo.create("S001", "Bob", "CARD2")
