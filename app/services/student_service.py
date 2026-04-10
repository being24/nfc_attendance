from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.student import Student
from app.repositories.student_repository import StudentRepository
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.exceptions import (
    DuplicateCardIdError,
    DuplicateStudentCodeError,
    StudentNotFoundError,
)


class StudentService:
    def __init__(self, db: Session):
        self.repo = StudentRepository(db)

    def register_student(self, payload: StudentCreate) -> Student:
        try:
            return self.repo.create(
                student_code=payload.student_code,
                name=payload.name,
                card_id=payload.card_id,
                is_admin=payload.is_admin,
                note=payload.note,
            )
        except IntegrityError as e:
            msg = str(e.orig).lower() if getattr(e, "orig", None) else str(e).lower()
            if "student_code" in msg:
                raise DuplicateStudentCodeError("学籍番号が重複しています") from e
            if "card_id" in msg:
                raise DuplicateCardIdError("カードIDが重複しています") from e
            raise

    def update_student(self, student_id: int, payload: StudentUpdate) -> Student:
        student = self.repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"学生が見つかりません: {student_id}")
        try:
            return self.repo.update(student, **payload.model_dump(exclude_unset=True))
        except IntegrityError as e:
            msg = str(e.orig).lower() if getattr(e, "orig", None) else str(e).lower()
            if "student_code" in msg:
                raise DuplicateStudentCodeError("学籍番号が重複しています") from e
            if "card_id" in msg:
                raise DuplicateCardIdError("カードIDが重複しています") from e
            raise

    def list_students(self, include_inactive: bool = False) -> list[Student]:
        return self.repo.list_all(include_inactive=include_inactive)

    def get_by_card_id(self, card_id: str) -> Student | None:
        return self.repo.get_by_card_id(card_id)

    def get_student(self, student_id: int) -> Student:
        student = self.repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"学生が見つかりません: {student_id}")
        return student

    def deactivate_student(self, student_id: int) -> Student:
        student = self.repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"学生が見つかりません: {student_id}")
        return self.repo.deactivate(student)
