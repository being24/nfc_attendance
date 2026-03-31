from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.student import Student


class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, student_id: int) -> Student | None:
        return self.db.get(Student, student_id)

    def get_by_card_id(self, card_id: str) -> Student | None:
        return self.db.scalar(select(Student).where(Student.card_id == card_id))

    def get_by_student_code(self, student_code: str) -> Student | None:
        return self.db.scalar(select(Student).where(Student.student_code == student_code))

    def list_all(self, include_inactive: bool = False) -> list[Student]:
        stmt = select(Student)
        if not include_inactive:
            stmt = stmt.where(Student.is_active.is_(True))
        return list(self.db.scalars(stmt.order_by(Student.id)).all())

    def create(self, student_code: str, name: str, card_id: str, note: str | None = None) -> Student:
        student = Student(student_code=student_code, name=name, card_id=card_id, note=note)
        self.db.add(student)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(student)
        return student

    def update(self, student: Student, **kwargs) -> Student:
        for key, value in kwargs.items():
            if hasattr(student, key) and value is not None:
                setattr(student, key, value)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        self.db.refresh(student)
        return student

    def deactivate(self, student: Student) -> Student:
        student.is_active = False
        self.db.commit()
        self.db.refresh(student)
        return student
